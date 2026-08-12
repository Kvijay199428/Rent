# // File: app\app\api\public.py
from fastapi import APIRouter, Request, Response, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks

from app.core.routes_manifest_landlord import LandlordRoutes as Routes, LandlordNames as Names
from app.core.routes_manifest_tenant import TenantRoutes, TenantNames

from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder

from typing import Optional
from datetime import datetime
from app.core.paths import KYC_DIR
from app.core.config_service import config
from app.models.tenant import Tenant
from app.models.receipt import BillRequest, PaymentStatusUpdate
import os, io, re, json
import mimetypes
import uuid
import shutil, logging

from app.services.tenant_service import (
    load_tenants, add_tenant, update_tenant, delete_tenant,
    get_occupants, save_occupant, delete_occupant
)
from app.services.billing_service import (
    get_all_receipts, get_receipt, get_billing_months,
    calculate_charges, create_bill, update_bill, delete_bill,
    get_dashboard_stats, archive_bill, restore_bill, update_paymentStatus
)
from app.services.backup_service import create_full_backup

router = APIRouter()


from app.authentication.tenant.middleware import get_current_tenant


def _property_belongs_to_tenant(tenant, propertyId: int) -> bool:
    """Property-first scoping: the URL propertyId must match the tenant's own property."""
    return int(getattr(tenant, "propertyId", 0) or 0) == int(propertyId or 0)


def _resolve_tenant_property_id(tenant_id: int, landlord_id):
    """Fallback for tenants without property_id (pre-backfill edge): returns the
    landlord's first property so a canonical /t/{propertyId}/ URL can still be built."""
    from app.core.db import get_conn
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM landlord_properties WHERE landlord_id = ? ORDER BY sort_order, id LIMIT 1",
            (landlord_id,),
        ).fetchone()
        if row:
            return row["id"]
    return None

# Legacy route (no landlordUuid prefix)
@router.get(TenantRoutes.TENANTAPIPROFILEGET, name=TenantNames.TENANTPROFILEGET)
async def public_tenant_profile_json(propertyId: int, tenantId: int, viewToken: str, request: Request):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "viewToken", "") == viewToken), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")
    if not _property_belongs_to_tenant(tenant, propertyId):
        raise HTTPException(status_code=403, detail="Property mismatch.")

    unlocked = False
    token = request.cookies.get("access_token")
    if token:
        from app.authentication.tenant.jwt import decode_access_token
        from app.authentication.tenant.sessions import get_tenant_session_db
        try:
            payload = decode_access_token(token)
            if payload.get("role") == "tenant" and int(payload.get("tenantId") or payload.get("sub")) == tenant.id:
                session_id = payload.get("sid")
                if get_tenant_session_db(session_id):
                    unlocked = True
        except Exception:
            pass
            
    base_info = {
        "id": tenant.id,
        "name": getattr(tenant, "name", ""),
        "viewToken": viewToken,
        "propertyId": getattr(tenant, "propertyId", None),
        "unlocked": unlocked,
        "readOnly": tenant.status != "Active",
        "phone": getattr(tenant, "phone", ""),
        "email": getattr(tenant, "email", ""),
        "address": getattr(tenant, "address", ""),
        "roomNumber": getattr(tenant, "roomNumber", ""),
        "occupation": getattr(tenant, "occupation", ""),
        "company": getattr(tenant, "company", ""),
    }

    if not unlocked:
        # Controlled disclosure: only the first-name greeting for the QR
        # unlock screen. No receipts, no occupants, no phone/email/address.
        return {
            "tenant": {
                "id": tenant.id,
                "name": getattr(tenant, "name", ""),
                "viewToken": viewToken,
                "propertyId": getattr(tenant, "propertyId", None),
                "unlocked": unlocked,
                "readOnly": tenant.status != "Active",
            }
        }

    receipts = get_all_receipts()
    tenant_receipts = [
        r for r in receipts
        if int(r.get("TenantId", 0) or 0) == tenant.id
        and (r.get("Status") or "").upper() != "ARCHIVED"
    ]
    tenant_receipts.reverse()
    tenant_receipts = tenant_receipts[:config.get("system.limits.public_history_months", 12)]
    occupants = get_occupants(tenant.id)

    return {
        "tenant": base_info,
        "receipts": tenant_receipts,
        "occupants": occupants
    }

@router.get(TenantRoutes.TENANTAPIAUTHPUBLICKEY, name=TenantNames.TENANTPUBLICKEY)
async def get_public_key():
    from app.encryption import get_public_key_pem
    return {"publicKey": get_public_key_pem()}


from pydantic import BaseModel

class EncryptedLoginRequest(BaseModel):
    key: str        # Base64-encoded RSA-encrypted AES key
    data: str       # Base64-encoded AES-GCM encrypted payload
    nonce: str      # Base64-encoded nonce

@router.post(TenantRoutes.TENANTAPIAUTHLOGIN, name=TenantNames.TENANTLOGIN)
async def public_tenant_login(propertyId: int, tenantId: int, viewToken: str, request: Request, response: Response, login_req: EncryptedLoginRequest):
    from datetime import datetime, timedelta
    from app.core.db import get_conn
    from app.authentication.common.utils import verify_pin, constant_time_eq
    from app.authentication.tenant.sessions import create_tenant_session
    from app.authentication.tenant.jwt import create_access_token
    from app.authentication.tenant.cookies import set_tenant_auth_cookies
    from app.database.auth_repository import log_audit

    ip = request.client.host if request.client else "Unknown IP"

    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "viewToken", "") == viewToken), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")
    if not _property_belongs_to_tenant(tenant, propertyId):
        raise HTTPException(status_code=403, detail="Property mismatch.")

    # Brute-force lockout (5 failed PIN/QR attempts -> 15 minute lock).
    with get_conn() as conn:
        row = conn.execute(
            "SELECT failed_attempts, locked_until FROM tenants WHERE id = ?",
            (tenant.id,),
        ).fetchone()

    if row and row["locked_until"]:
        try:
            locked_dt = datetime.fromisoformat(row["locked_until"])
            if datetime.utcnow() < locked_dt:
                log_audit(tenant.id, "Login Blocked - Too Many Failed PIN Attempts", ip)
                raise HTTPException(
                    status_code=429,
                    detail="Too many failed attempts. Account locked for 15 minutes.",
                )
        except ValueError:
            pass

    def _record_failed_attempt(detail: str):
        failed_attempts = (row["failed_attempts"] or 0) + 1 if row else 1
        locked_until_str = None
        if failed_attempts >= 5:
            locked_until_str = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
        with get_conn() as conn:
            conn.execute(
                "UPDATE tenants SET failed_attempts = ?, locked_until = ? WHERE id = ?",
                (failed_attempts, locked_until_str, tenant.id),
            )
            conn.commit()
        log_audit(tenant.id, detail, ip)
        return locked_until_str

    from app.encryption import decrypt_payload
    try:
        decrypted = decrypt_payload(login_req.key, login_req.data, login_req.nonce)
        pin = decrypted.get("pin", "")
        qr_key = (decrypted.get("qr_key") or "").strip()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid encrypted payload")

    # When a qr_key is supplied, it must match the tenant's stored key. This
    # binds each QR login to the specific printed QR (invalidateable by rotation).
    if qr_key:
        stored_key = (getattr(tenant, "qr_key", "") or "").strip()
        if not stored_key or not constant_time_eq(qr_key, stored_key):
            _record_failed_attempt("Login Failed - Wrong QR Key")
            raise HTTPException(status_code=401, detail="Invalid QR link")

    if not verify_pin(pin, getattr(tenant, "tenantPin", "")):
        _record_failed_attempt("Login Failed - Wrong PIN")
        raise HTTPException(status_code=401, detail="Invalid PIN")

    # Reset attempts on success
    if (row and row["failed_attempts"]) or (row and row["locked_until"]):
        with get_conn() as conn:
            conn.execute(
                "UPDATE tenants SET failed_attempts = 0, locked_until = NULL WHERE id = ?",
                (tenant.id,),
            )
            conn.commit()

    session_id, refresh_token = create_tenant_session(tenant.id, request, remember_me=True)
    access_token = create_access_token(tenant.id, session_id)
    
    set_tenant_auth_cookies(response, access_token, refresh_token, True, request)
    log_audit(tenant.id, "Login Success", ip)
    
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return {
        "status": "success", 
        "message": "Unlocked successfully",
        "tenant": {
            "id": tenant.id,
            "name": getattr(tenant, "name", ""),
            "unlocked": True,
            "readOnly": tenant.status != "Active",
        }
    }

@router.get("/tenant/api/auth/public-key", include_in_schema=False)
async def global_tenant_public_key():
    from app.encryption import get_public_key_pem
    return {"publicKey": get_public_key_pem()}


@router.post("/tenant/api/auth/login", include_in_schema=False)
async def global_tenant_login(request: Request, response: Response, login_req: EncryptedLoginRequest):
    """Portal login with tenant_username + password_hash."""
    from app.encryption import decrypt_payload
    from app.authentication.common.utils import verify_pin
    from app.authentication.tenant.sessions import create_tenant_session
    from app.authentication.tenant.jwt import create_access_token
    from app.core.db import get_conn
    from app.database.auth_repository import log_audit

    try:
        decrypted = decrypt_payload(login_req.key, login_req.data, login_req.nonce)
        username = decrypted.get("username", "").strip().lower()
        password = decrypted.get("password", "")
        remember_me = decrypted.get("rememberme", False)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid encrypted payload")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    from app.authentication.common.utils import validate_username, validate_password
    validate_username(username)
    validate_password(password)

    ip = request.client.host if request.client else "Unknown IP"

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, landlord_id, viewToken, password_hash, property_id, "
            "password_failed_attempts, password_locked_until, password_reset_required "
            "FROM tenants WHERE LOWER(tenant_username) = ? ORDER BY id LIMIT 1",
            (username,),
        ).fetchone()

    # Generic failure for unknown user OR missing password — do not leak account existence.
    def generic_fail():
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not row or not row["password_hash"]:
        generic_fail()

    from datetime import datetime, timedelta
    if row["password_locked_until"]:
        try:
            locked_until = datetime.fromisoformat(row["password_locked_until"])
            if datetime.utcnow() < locked_until:
                raise HTTPException(status_code=429, detail="Account locked. Try again later.")
        except ValueError:
            pass

    if not verify_pin(password, row["password_hash"]):
        log_audit(row["id"], "Portal Login Failed - Wrong Password", ip)
        failed_attempts = (row["password_failed_attempts"] or 0) + 1
        locked_until_str = None
        if failed_attempts >= 5:
            locked_until_str = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
        with get_conn() as conn:
            conn.execute(
                "UPDATE tenants SET password_failed_attempts = ?, password_locked_until = ? WHERE id = ?",
                (failed_attempts, locked_until_str, row["id"]),
            )
            conn.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if (row["password_failed_attempts"] or 0) > 0:
        with get_conn() as conn:
            conn.execute(
                "UPDATE tenants SET password_failed_attempts = 0, password_locked_until = NULL WHERE id = ?",
                (row["id"],),
            )
            conn.commit()

    with get_conn() as conn:
        landlord = conn.execute(
            "SELECT landlord_uuid FROM landlord_accounts WHERE id = ?",
            (row["landlord_id"],),
        ).fetchone()

    if not landlord:
        landlord = conn.execute(
            "SELECT landlord_uuid FROM landlord_accounts ORDER BY id LIMIT 1"
        ).fetchone()

    if not landlord:
        raise HTTPException(status_code=500, detail="Landlord account not found")

    landlord_uuid = landlord["landlord_uuid"]
    view_token = row["viewToken"]
    tenant_id = row["id"]
    property_id = row["property_id"] or _resolve_tenant_property_id(tenant_id, row["landlord_id"])

    session_id, refresh_token = create_tenant_session(tenant_id, request, remember_me)
    access_token = create_access_token(tenant_id, session_id)

    cookie_val = f"{session_id}:{refresh_token}"
    max_age_refresh = 180 * 24 * 60 * 60 if remember_me else 24 * 60 * 60
    rootpath = (request.scope.get("root_path") or "").rstrip("/")
    cookie_path = f"{rootpath}/{landlord_uuid}/t/{property_id}/{tenant_id}/{view_token}"

    response.set_cookie(
        key="access_token", value=access_token,
        httponly=True, secure=True, samesite="none",
        path=cookie_path, max_age=15 * 60,
    )
    response.set_cookie(
        key="refresh_token", value=cookie_val,
        httponly=True, secure=True, samesite="strict",
        path=f"{cookie_path}/api/auth", max_age=max_age_refresh,
    )

    log_audit(tenant_id, "Portal Login Success", ip)

    return {
        "status": "success",
        "tenant": {
            "id": tenant_id,
            "name": row["name"],
            "landlord_uuid": landlord_uuid,
            "property_id": property_id,
            "view_token": view_token,
        },
        "redirect_url": f"{rootpath}/{landlord_uuid}/t/{property_id}/{tenant_id}/{view_token}",
        "reset_required": bool(row["password_reset_required"]),
    }


@router.post("/tenant/api/auth/forgot-password", include_in_schema=False)
async def global_tenant_forgot_password(request: Request, login_req: EncryptedLoginRequest):
    """Request a password reset. Returns a generic message; the reset token is
    delivered by the landlord (v1) — no tenant email/SMS channel exists yet."""
    from app.encryption import decrypt_payload
    from app.authentication.common.utils import hash_pin
    from app.core.db import get_conn
    from app.database.auth_repository import log_audit
    import secrets as _secrets
    from datetime import datetime, timedelta

    try:
        decrypted = decrypt_payload(login_req.key, login_req.data, login_req.nonce)
        username = decrypted.get("username", "").strip().lower()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid encrypted payload")

    from app.authentication.common.utils import validate_username
    validate_username(username)

    ip = request.client.host if request.client else "Unknown IP"

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM tenants WHERE LOWER(tenant_username) = ? ORDER BY id LIMIT 1",
            (username,),
        ).fetchone()

    if row:
        token = _secrets.token_urlsafe(32)
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=15)
        with get_conn() as conn:
            conn.execute(
                "UPDATE tenants SET password_reset_token_hash = ?, password_reset_expires_at = ?, password_reset_requested_at = ? WHERE id = ?",
                (hash_pin(token), expires_at.isoformat(), now.isoformat(), row["id"]),
            )
            conn.execute(
                "INSERT INTO tenant_password_reset_events (tenantId, channel, token_hash, created_at, expires_at, requested_ip) VALUES (?, 'self-service', ?, ?, ?, ?)",
                (row["id"], hash_pin(token), now.isoformat(), expires_at.isoformat(), ip),
            )
            conn.commit()
        log_audit(row["id"], "Password Reset Requested", ip)
        # TODO(delivery): no tenant email/SMS channel exists. Landlord sets the
        # temporary password via portal-auth; self-service token delivery is a stub.

    return {
        "status": "success",
        "message": "If an account exists for that username, a password reset will be made available.",
    }


@router.post("/tenant/api/auth/reset-password", include_in_schema=False)
async def global_tenant_reset_password(request: Request, response: Response, login_req: EncryptedLoginRequest):
    """Complete a password reset using the token issued via forgot-password."""
    from app.encryption import decrypt_payload
    from app.authentication.common.utils import hash_pin, verify_pin
    from app.core.db import get_conn
    from app.database.auth_repository import log_audit, revoke_all_tenant_sessions
    from datetime import datetime

    try:
        decrypted = decrypt_payload(login_req.key, login_req.data, login_req.nonce)
        username = decrypted.get("username", "").strip().lower()
        token = decrypted.get("token", "")
        new_password = decrypted.get("new_password", "")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid encrypted payload")

    if not username or not token:
        raise HTTPException(status_code=400, detail="Username and reset token are required")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    from app.authentication.common.utils import validate_username, validate_password
    validate_username(username)
    validate_password(new_password)

    ip = request.client.host if request.client else "Unknown IP"

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, landlord_id, viewToken, password_reset_token_hash, password_reset_expires_at FROM tenants WHERE LOWER(tenant_username) = ? ORDER BY id LIMIT 1",
            (username,),
        ).fetchone()

    if not row or not row["password_reset_token_hash"]:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if not verify_pin(token, row["password_reset_token_hash"]):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if row["password_reset_expires_at"]:
        try:
            expires_at = datetime.fromisoformat(row["password_reset_expires_at"])
            if datetime.utcnow() > expires_at:
                raise HTTPException(status_code=400, detail="Reset token has expired")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid reset token state")

    now = datetime.utcnow()
    tenant_id = row["id"]
    with get_conn() as conn:
        conn.execute(
            "UPDATE tenants SET password_hash = ?, password_reset_token_hash = NULL, password_reset_expires_at = NULL, password_reset_requested_at = NULL, password_reset_required = 0, password_failed_attempts = 0, password_locked_until = NULL, last_password_change_at = ? WHERE id = ?",
            (hash_pin(new_password), now.isoformat(), tenant_id),
        )
        conn.execute(
            "INSERT INTO tenant_password_history (tenantId, password_hash, changed_at, changed_by) VALUES (?, ?, ?, 'tenant-reset')",
            (tenant_id, hash_pin(new_password), now.isoformat()),
        )
        conn.execute(
            "UPDATE tenant_password_reset_events SET used_at = ? WHERE tenantId = ? AND used_at IS NULL",
            (now.isoformat(), tenant_id),
        )
        conn.commit()

    revoke_all_tenant_sessions(tenant_id)
    log_audit(tenant_id, "Password Reset Completed", ip)

    return {"status": "success", "message": "Password updated. Please sign in."}


@router.post("/tenant/api/auth/change-password", include_in_schema=False)
async def global_tenant_change_password(request: Request, response: Response, login_req: EncryptedLoginRequest):
    """Change a tenant's password (current password required). Used for the
    forced first-login change after a landlord-assigned temporary password."""
    from app.encryption import decrypt_payload
    from app.authentication.common.utils import hash_pin, verify_pin
    from app.core.db import get_conn
    from app.database.auth_repository import log_audit, revoke_all_tenant_sessions
    from datetime import datetime

    try:
        decrypted = decrypt_payload(login_req.key, login_req.data, login_req.nonce)
        username = decrypted.get("username", "").strip().lower()
        current_password = decrypted.get("current_password", "")
        new_password = decrypted.get("new_password", "")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid encrypted payload")

    if not username or not current_password:
        raise HTTPException(status_code=400, detail="Username and current password are required")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    from app.authentication.common.utils import validate_username, validate_password
    validate_username(username)
    validate_password(new_password)

    ip = request.client.host if request.client else "Unknown IP"

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM tenants WHERE LOWER(tenant_username) = ? ORDER BY id LIMIT 1",
            (username,),
        ).fetchone()

    if not row or not row["password_hash"] or not verify_pin(current_password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    now = datetime.utcnow()
    tenant_id = row["id"]
    with get_conn() as conn:
        conn.execute(
            "UPDATE tenants SET password_hash = ?, password_reset_required = 0, password_reset_token_hash = NULL, password_reset_expires_at = NULL, password_reset_requested_at = NULL, password_failed_attempts = 0, password_locked_until = NULL, last_password_change_at = ? WHERE id = ?",
            (hash_pin(new_password), now.isoformat(), tenant_id),
        )
        conn.execute(
            "INSERT INTO tenant_password_history (tenantId, password_hash, changed_at, changed_by) VALUES (?, ?, ?, 'tenant-change')",
            (tenant_id, hash_pin(new_password), now.isoformat()),
        )
        conn.commit()

    revoke_all_tenant_sessions(tenant_id)
    log_audit(tenant_id, "Password Changed", ip)

    return {"status": "success", "message": "Password updated. Please sign in."}


@router.get(TenantRoutes.TENANTAPIPDFVIEW, name=TenantNames.TENANTPDFVIEW)
async def tenant_view_pdf(propertyId: int, tenantId: int, viewToken: str, billNo: str, principal = Depends(get_current_tenant)):
    receipt = get_receipt(tenantId, billNo)
    if not receipt:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    # Verify tenant owns this receipt by ID (name-based check breaks after a rename)
    tenants = load_tenants()
    tenant = next((t for t in tenants if t.id == principal.id), None)
    if not tenant or int(receipt.get("TenantId", 0) or 0) != tenant.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not _property_belongs_to_tenant(tenant, propertyId):
        raise HTTPException(status_code=403, detail="Property mismatch.")
        
    from app.services.pdf_service import generate_professional_pdf
    from app.services.landlord_config_service import get_effective_landlord_config
    landlord_conf = get_effective_landlord_config(getattr(tenant, "landlord_id", None))
    
    pdf_stream = generate_professional_pdf(receipt, landlord_conf)
    
    response = StreamingResponse(iter([pdf_stream.getvalue()]), media_type='application/pdf')
    response.headers["Content-Disposition"] = f"inline; filename=receipt_{billNo}.pdf"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@router.get(TenantRoutes.TENANTAPIPDFDOWNLOAD, name=TenantNames.TENANTPDFDOWNLOAD)
async def tenant_download_pdf(propertyId: int, tenantId: int, viewToken: str, billNo: str, principal = Depends(get_current_tenant)):
    receipt = get_receipt(tenantId, billNo)
    if not receipt:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    # Verify tenant owns this receipt by ID (name-based check breaks after a rename)
    tenants = load_tenants()
    tenant = next((t for t in tenants if t.id == principal.id), None)
    if not tenant or int(receipt.get("TenantId", 0) or 0) != tenant.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not _property_belongs_to_tenant(tenant, propertyId):
        raise HTTPException(status_code=403, detail="Property mismatch.")
        
    tenantName = receipt.get("Tenant", "Unknown").replace(" ", "_")
    try:
        formatted_date = datetime.strptime(receipt.get("Date", ""), "%d %B %Y").strftime("%Y%m%d")
    except:
        formatted_date = receipt.get("Date", "").replace(" ", "")
    custom_filename = f"{tenantName}_{formatted_date}_{billNo}.pdf"
        
    from app.services.pdf_service import generate_professional_pdf
    from app.services.landlord_config_service import get_effective_landlord_config
    landlord_conf = get_effective_landlord_config(getattr(tenant, "landlord_id", None))
    
    pdf_stream = generate_professional_pdf(receipt, landlord_conf)
    
    response = StreamingResponse(iter([pdf_stream.getvalue()]), media_type='application/pdf')
    response.headers["Content-Disposition"] = f'attachment; filename="{custom_filename}"'
    return response

@router.post(TenantRoutes.TENANTAPIKYCUPLOAD, name=TenantNames.TENANTKYCUPLOAD)
async def public_tenant_kyc_upload(
    propertyId: int,
    tenantId: int,
    viewToken: str,
    name: str = Form(...),
    mobile: str = Form(""),
    address: str = Form(""),
    residentSince: str = Form(""),
    aadhaarfront: Optional[UploadFile] = File(None),
    aadhaarback: Optional[UploadFile] = File(None),
    aadhaarcombined: Optional[UploadFile] = File(None),
    empfront: Optional[UploadFile] = File(None),
    empback: Optional[UploadFile] = File(None),
    principal = Depends(get_current_tenant)
):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "viewToken", "") == viewToken), None)
    if not tenant or tenant.id != principal.id:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")
    if not _property_belongs_to_tenant(tenant, propertyId):
        raise HTTPException(status_code=403, detail="Property mismatch.")

    if tenant.status != "Active":
        raise HTTPException(status_code=403, detail="KYC uploads are not allowed for inactive tenants.")

    # Enforce daily KYC upload cap
    from app.core.db import get_conn
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with get_conn() as conn:
        today_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM occupants WHERE tenantId = ? AND DATE(uploaddate) = ?",
            (tenant.id, today),
        ).fetchone()["cnt"]
    daily_limit = config.get("system", "security.kyc_daily_upload_limit", default=5)
    if today_count >= daily_limit:
        raise HTTPException(status_code=429, detail=f"Daily KYC upload limit of {daily_limit} reached. Try again tomorrow.")

    # Validate residentSince date if provided
    if residentSince:
        try:
            from datetime import date
            parsed_date = date.fromisoformat(residentSince)
            if parsed_date > date.today():
                raise HTTPException(status_code=400, detail="Residing-since date cannot be in the future.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Residing-since date must use YYYY-MM-DD format.")

    # Need either combined OR both front+back (check filename to exclude empty browser inputs)
    has_combined = bool(aadhaarcombined and aadhaarcombined.filename)
    has_both = bool(
        (aadhaarfront and aadhaarfront.filename) and
        (aadhaarback and aadhaarback.filename)
    )
    if not has_combined and not has_both:
        raise HTTPException(
            status_code=400,
            detail="Please upload either a Combined Aadhaar file, or both Front and Back files."
        )

    occupantUuid = str(uuid.uuid4())

    async def save_kyc_img(file_obj: UploadFile, side: str):
        if not file_obj or not file_obj.filename:
            return ""
        ext = file_obj.filename.split('.')[-1] if '.' in file_obj.filename else 'jpg'
        filename = f"{tenant.id}_{occupantUuid}_{side}.{ext}"
        os.makedirs(KYC_DIR, exist_ok=True)
        file_path = os.path.join(KYC_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(await file_obj.read())
        return filename

    af_path = await save_kyc_img(aadhaarfront, "aadhaar_front") if has_both else ""
    ab_path = await save_kyc_img(aadhaarback, "aadhaar_back") if has_both else ""
    ac_path = await save_kyc_img(aadhaarcombined, "aadhaar_combined") if has_combined else ""
    ef_path = await save_kyc_img(empfront, "emp_front") if (empfront and empfront.filename) else ""
    eb_path = await save_kyc_img(empback, "emp_back") if (empback and empback.filename) else ""

    now = datetime.now()
    save_occupant(tenant.id, {
        "uuid": occupantUuid,
        "name": name.strip(),
        "mobile": mobile.strip(),
        "address": address.strip(),
        "residentSince": residentSince,
        "status": "Active",
        "aadhaar_front": af_path,
        "aadhaar_back": ab_path,
        "aadhaar_combined": ac_path,
        "emp_front": ef_path,
        "emp_back": eb_path,
        "uploaddate": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "uploadmonth": now.strftime("%B %Y"),
    })

    return {"status": "success", "message": "KYC uploaded successfully"}

@router.put(TenantRoutes.TENANTAPIKYCMARKINACTIVE, name=TenantNames.TENANTKYCMARKINACTIVE)
async def public_tenant_kyc_mark_inactive(propertyId: int, tenantId: int, viewToken: str, occupantUuid: str, principal = Depends(get_current_tenant)):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "viewToken", "") == viewToken), None)
    if not tenant or tenant.id != principal.id:
        raise HTTPException(status_code=404, detail="Invalid link.")
    if not _property_belongs_to_tenant(tenant, propertyId):
        raise HTTPException(status_code=403, detail="Property mismatch.")

    if tenant.status != "Active":
        raise HTTPException(status_code=403, detail="KYC modifications are not allowed for inactive tenants.")
        
    from app.services.tenant_service import update_occupant_status
    update_occupant_status(occupantUuid, "Inactive")
    return {"status": "success"}

@router.delete(TenantRoutes.TENANTAPIKYCDELETE, name=TenantNames.TENANTKYCDELETE)
async def public_tenant_kyc_delete(propertyId: int, tenantId: int, viewToken: str, occupantUuid: str, principal = Depends(get_current_tenant)):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "viewToken", "") == viewToken), None)
    if not tenant or tenant.id != principal.id:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")
    if not _property_belongs_to_tenant(tenant, propertyId):
        raise HTTPException(status_code=403, detail="Property mismatch.")

    if tenant.status != "Active":
        raise HTTPException(status_code=403, detail="KYC deletions are not allowed for inactive tenants.")

    occupants = get_occupants(tenant.id)
    target = next((o for o in occupants if o.get("occupantUuid") == occupantUuid or o.get("Occupant UUID") == occupantUuid), None)

    if target:
        doc_keys = ["aadhaarfront", "aadhaarback", "aadhaarcombined", "empfront", "empback"]
        for key in doc_keys:
            filename = target.get(key)
            if filename:
                file_path = os.path.join(KYC_DIR, filename)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
            
    delete_occupant(occupantUuid)
    return {"status": "success"}

@router.get(TenantRoutes.TENANTAPIKYCGETFILE, name=TenantNames.TENANTKYCGETFILE)
async def tenant_public_get_kyc_file(propertyId: int, tenantId: int, viewToken: str, filename: str, principal = Depends(get_current_tenant)):
    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not safe_filename.startswith(f"{principal.id}_"):
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access this file")
    
    tenants = load_tenants()
    tenant = next((t for t in tenants if t.id == principal.id), None)
    if not tenant or not _property_belongs_to_tenant(tenant, propertyId):
        raise HTTPException(status_code=403, detail="Property mismatch.")

    file_path = os.path.join(KYC_DIR, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "application/octet-stream"
        
    headers = {
        "Content-Disposition": f'inline; filename="{safe_filename}"'
    }
    return FileResponse(file_path, media_type=mime_type, headers=headers)


# ─── Tenant Audit Logs ───────────────────────────────────────────────────────

@router.get(TenantRoutes.TENANTAPIAUDITLOGS, name=TenantNames.TENANTAUDITLOGS)
async def tenant_audit_logs(
    propertyId: int,
    tenantId: int,
    viewToken: str,
    request: Request,
    principal=Depends(get_current_tenant),
    action_type: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """Return audit logs for this tenant (scoped to property/tenant/viewToken URL)."""
    from app.routers.auth import _tenant_viewtoken_guard
    _tenant_viewtoken_guard(request, tenantId, viewToken, propertyId)

    from app.core.db import get_conn as _get_conn
    import json as _json

    query = """
        SELECT
            tl.id,
            'tenant' AS app_source,
            tl.tenantId AS actor_id,
            t.name AS actor_name,
            tl.action,
            NULL AS target_type,
            NULL AS target_id,
            tl.ip_address,
            tl.meta_json,
            tl.created_at
        FROM tenant_audit_logs tl
        LEFT JOIN tenants t ON tl.tenantId = t.id
        WHERE tl.tenantId = ?
    """
    params: list = [principal.id]

    if action_type:
        query += " AND tl.action LIKE ?"
        params.append(f"%{action_type}%")
    if search:
        query += " AND (tl.action LIKE ? OR tl.ip_address LIKE ?)"
        params.extend([f"%{search}%"] * 2)
    if date_from:
        query += " AND tl.created_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND tl.created_at <= ?"
        params.append(date_to + "T23:59:59")

    count_query = "SELECT COUNT(*) FROM (" + query + ")"
    with _get_conn() as conn:
        total = conn.execute(count_query, tuple(params)).fetchone()[0]

    query += " ORDER BY tl.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with _get_conn() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()

    items = []
    for r in rows:
        meta = {}
        if r["meta_json"]:
            try:
                meta = _json.loads(r["meta_json"])
            except Exception:
                pass
        items.append({
            "id": r["id"],
            "app_source": r["app_source"],
            "actor_id": r["actor_id"],
            "actor_name": r["actor_name"],
            "action": r["action"],
            "target_type": r["target_type"],
            "target_id": r["target_id"],
            "ip_address": r["ip_address"],
            "meta": meta,
            "created_at": r["created_at"],
        })

    return {"items": items, "total": total}
