# app\app\api\tenants.py

from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder

from app.core.routes_manifest_landlord import LandlordRoutes as Routes, LandlordNames as Names

from typing import Optional, List
from app.models.tenant import Tenant
from app.models.receipt import BillRequest, PaymentStatusUpdate
import os, io, re, json, datetime
import shutil, logging
from pydantic import BaseModel


async def _broadcast(channel: str, event: dict):
    """Fire-and-forget broadcast helper."""
    try:
        from app.core.websocket_manager import sync_manager
        await sync_manager.broadcast(channel, event)
    except Exception:
        pass


from app.services.tenant_service import (
    load_tenants, add_tenant, update_tenant, delete_tenant,
    get_occupants, save_occupant, delete_occupant,
    get_tenant, tenant_belongs_to_landlord
)
from app.services.billing_service import (
    get_all_receipts, get_receipt, get_billing_months,
    calculate_charges, create_bill, update_bill, delete_bill,
    get_dashboard_stats, archive_bill, restore_bill, update_paymentStatus
)
from app.services.backup_service import create_full_backup
from app.services.phone_service import normalize_phone
from app.authentication.landlord.middleware import get_current_landlord_api_strict

router = APIRouter()


def _validate_property_ownership(landlord_id: int, property_id):
    """Raise 400 if property_id is set but does not belong to this landlord."""
    if not property_id:
        return
    from app.database.property_repository import get_property
    if not get_property(landlord_id, int(property_id)):
        raise HTTPException(status_code=400, detail="Property not found or does not belong to this landlord.")


@router.get(Routes.LANDLORDAPITENANTSLIST, name=Names.APIGETTENANTS)
async def api_get_tenants(landlordUuid: str, principal=Depends(get_current_landlord_api_strict)):
    tenants = load_tenants(include_archived=False, landlord_id=principal.landlord_id)
    from app.services.payment_service import get_tenant_settlement_state, get_tenant_outstanding_balance
    from app.services.qr_service import tenant_qr_payload
    result = []
    for t in tenants:
        d = t.dict()
        # Canonical tenant portal URL — identical to the one embedded in the QR
        # so the landlord "Public Profile" button and the printed QR always agree.
        d["portalUrl"] = tenant_qr_payload(
            landlordUuid,
            getattr(t, "propertyId", None),
            t.id,
            getattr(t, "viewToken", "") or "",
            getattr(t, "qr_key", "") or "",
        )
        try:
            d["outstandingBalance"] = get_tenant_outstanding_balance(t.id)
            st = get_tenant_settlement_state(t.id)
            d["currentBillDue"] = st.get("currentBillDue", 0.0)
            d["advance"] = st.get("advance", 0.0)
            d["currentBill"] = st.get("currentBill")
        except Exception:
            d["outstandingBalance"] = 0.0
            d["currentBillDue"] = 0.0
            d["advance"] = 0.0
            d["currentBill"] = None
        result.append(d)
    return result

@router.get(Routes.LANDLORDAPITENANTSUPDATE, name=Names.APIGETTENANT)
async def api_get_tenant(landlordUuid: str, tenantId: int, principal=Depends(get_current_landlord_api_strict)):
    tenant = get_tenant(tenantId, landlord_id=principal.landlord_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

@router.get(Routes.LANDLORDAPITENANTSRECEIPTS, name=Names.APIGETTENANTRECEIPTS)
async def api_get_tenant_receipts(landlordUuid: str, tenantId: int, principal=Depends(get_current_landlord_api_strict)):
    # Use include_archived=True so admin can view receipts of archived tenants
    tenant = get_tenant(tenantId, landlord_id=principal.landlord_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # ID-based lookup only — name is display-only and must never be used for ownership
    receipts = get_all_receipts(include_archived_tenants=True, landlord_id=principal.landlord_id)
    tenant_receipts = [r for r in receipts if int(r.get("TenantId", 0) or 0) == tenantId]
    tenant_receipts.reverse()
    return tenant_receipts

@router.post(Routes.LANDLORDAPITENANTSLIST, name=Names.APIADDTENANT)
async def api_add_tenant(landlordUuid: str, t: Tenant, request: Request, background_tasks: BackgroundTasks, principal=Depends(get_current_landlord_api_strict)):
    from app.authentication.common.utils import hash_pin, validate_tenantPin
    from app.authentication.common.pin_vault import encrypt_admin_view_pin
    from app.database.landlord_repository import create_landlord_audit_log
    from app.core.db import get_conn
    from datetime import datetime
    
    background_tasks.add_task(create_full_backup, tag="add_tenant", landlord_id=principal.landlord_id)
    
    # Strictly validate 4-digit PIN on creation
    validate_tenantPin(t.tenantPin)
    
    plain_pin = str(t.tenantPin)
    hashed_pin = hash_pin(plain_pin)
    encrypted_pin = encrypt_admin_view_pin(plain_pin)
    
    t.tenantPin = hashed_pin
    
    landlord_id = principal.landlord_id
    t.landlord_id = landlord_id
    _validate_property_ownership(landlord_id, t.propertyId)

    tenantId = add_tenant(t)
    t.id = tenantId
    
    # Add to PIN history
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("INSERT INTO tenantPin_history (tenantId, pin_hash, changed_at) VALUES (?, ?, ?)", (tenantId, hashed_pin, now))
        conn.execute("INSERT OR REPLACE INTO tenantPin_admin_store (tenantId, encrypted_pin, updated_at) VALUES (?, ?, ?)", (tenantId, encrypted_pin, now))
        conn.commit()

    response_tenant = t.dict()
    response_tenant.pop("tenantPin", None)

    if landlord_id:
        create_landlord_audit_log(
            landlord_id, "tenant_created",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"tenant_id": tenantId, "tenant_name": t.name}),
        )

    await _broadcast(f"landlord:{landlordUuid}", {"type": "TENANT_CREATED", "tenantId": tenantId})

    return {"status": "success", "tenant": response_tenant}

@router.put(Routes.LANDLORDAPITENANTSUPDATE, name=Names.APIUPDATETENANT)
async def api_update_tenant(landlordUuid: str, tenantId: int, t: Tenant, request: Request, background_tasks: BackgroundTasks, principal=Depends(get_current_landlord_api_strict)):
    from app.database.landlord_repository import create_landlord_audit_log

    t.id = tenantId
    background_tasks.add_task(create_full_backup, tag="update_tenant", landlord_id=principal.landlord_id)
    
    existing_t = get_tenant(tenantId, landlord_id=principal.landlord_id)
    if not existing_t:
        raise HTTPException(status_code=404, detail="Tenant not found")

    _validate_property_ownership(principal.landlord_id, t.propertyId)

    # The general update endpoint does NOT change the PIN.
    # We forcefully retain the existing PIN hash.
    t.tenantPin = existing_t.tenantPin
            
    update_tenant(t)
    
    response_tenant = t.dict()
    response_tenant.pop("tenantPin", None)

    landlord_id = principal.landlord_id
    if landlord_id:
        create_landlord_audit_log(
            landlord_id, "tenant_updated",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"tenant_id": tenantId, "tenant_name": t.name}),
        )

    await _broadcast(f"landlord:{landlordUuid}", {"type": "TENANT_UPDATED", "tenantId": tenantId})

    return {"status": "success", "tenant": response_tenant}

from pydantic import BaseModel

class ChangePinRequest(BaseModel):
    pin: str
    logout_all: bool = True

@router.post(Routes.LANDLORDAPITENANTSCHANGEPIN, name=Names.CHANGETENANTPIN)
async def api_change_tenantPin(landlordUuid: str, tenantId: int, payload: ChangePinRequest, request: Request, background_tasks: BackgroundTasks, principal=Depends(get_current_landlord_api_strict)):
    from app.authentication.common.utils import hash_pin, validate_tenantPin, verify_pin
    from app.authentication.common.pin_vault import encrypt_admin_view_pin
    from app.authentication.tenant.sessions import revoke_all_tenant_sessions
    from app.database.auth_repository import log_audit
    from app.core.db import get_conn
    from datetime import datetime
    
    validate_tenantPin(payload.pin)
    
    existing_t = get_tenant(tenantId, landlord_id=principal.landlord_id)
    if not existing_t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Prevent immediate reuse (last 5 PINs)
    with get_conn() as conn:
        history = conn.execute("SELECT pin_hash FROM tenantPin_history WHERE tenantId = ? ORDER BY id DESC LIMIT 5", (tenantId,)).fetchall()
        for row in history:
            if verify_pin(payload.pin, row["pin_hash"]):
                raise HTTPException(status_code=400, detail="Cannot reuse a recently used PIN.")
                
    new_hash = hash_pin(payload.pin)
    encrypted_pin = encrypt_admin_view_pin(payload.pin)
    
    existing_t.tenantPin = new_hash
    update_tenant(existing_t)
    
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("INSERT INTO tenantPin_history (tenantId, pin_hash, changed_at) VALUES (?, ?, ?)", (tenantId, new_hash, now))
        conn.execute("INSERT OR REPLACE INTO tenantPin_admin_store (tenantId, encrypted_pin, updated_at) VALUES (?, ?, ?)", (tenantId, encrypted_pin, now))
        conn.commit()
    
    if payload.logout_all:
        revoke_all_tenant_sessions(tenantId)
        
    ip = request.client.host if request.client else "Unknown IP"
    log_audit(tenantId, "Tenant PIN Changed", ip)
    
    background_tasks.add_task(create_full_backup, tag="change_pin", landlord_id=principal.landlord_id)
    
    return {"status": "success", "message": "PIN changed successfully."}

@router.get(Routes.LANDLORDAPITENANTSREVEALPIN, name=Names.LANDLORDREVEALPIN)
async def admin_reveal_tenantPin(
    landlordUuid: str,
    tenantId: int,  # CHANGED: tenantId → tenantId
    principal=Depends(get_current_landlord_api_strict),
):
    from app.authentication.common.pin_vault import decrypt_admin_view_pin
    from app.core.db import get_conn

    if not tenant_belongs_to_landlord(tenantId, principal.landlord_id):
        raise HTTPException(status_code=404, detail="Tenant not found")

    with get_conn() as conn:
        row = conn.execute(
            "SELECT encrypted_pin, updated_at FROM tenantPin_admin_store WHERE tenantId = ?",
            (tenantId,)  # CHANGED: tenantId → tenantId
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="PIN not available for this tenant yet. Reset the PIN once to enable admin reveal."
        )

    return {
        "status": "success",
        "pin": decrypt_admin_view_pin(row["encrypted_pin"]),
        "updated_at": row["updated_at"]
    }


class PortalAuthRequest(BaseModel):
    tenantUsername: Optional[str] = None
    temporaryPassword: Optional[str] = None
    resetRequired: bool = True


@router.post(Routes.LANDLORDAPITENANTSPORTALAUTH, name=Names.LANDLORDTENANTPORTALAUTH)
async def api_tenant_portal_auth(landlordUuid: str, tenantId: int, payload: PortalAuthRequest, request: Request, background_tasks: BackgroundTasks, principal=Depends(get_current_landlord_api_strict)):
    """Assign or clear a tenant's portal username/password (username + password flow)."""
    from app.authentication.common.utils import hash_pin
    from app.authentication.tenant.sessions import revoke_all_tenant_sessions
    from app.database.auth_repository import log_audit
    from app.database.landlord_repository import create_landlord_audit_log
    from app.core.db import get_conn
    from datetime import datetime

    background_tasks.add_task(create_full_backup, tag="portal_auth", landlord_id=principal.landlord_id)

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id, name FROM tenants WHERE id = ? AND landlord_id = ?", (tenantId, principal.landlord_id)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Clear portal auth when nothing is provided
        if not payload.tenantUsername and not payload.temporaryPassword:
            conn.execute(
                "UPDATE tenants SET tenant_username = NULL, password_hash = NULL, "
                "password_reset_required = 0, password_failed_attempts = 0, password_locked_until = NULL, "
                "password_reset_token_hash = NULL, password_reset_expires_at = NULL "
                "WHERE id = ?",
                (tenantId,),
            )
            conn.commit()
            ip = request.client.host if request.client else "Unknown IP"
            log_audit(tenantId, "Portal Auth Disabled", ip)
            return {"status": "success", "message": "Portal login disabled for this tenant."}

        username = (payload.tenantUsername or "").strip().lower()
        if not username:
            raise HTTPException(status_code=400, detail="tenantUsername is required")

        from app.authentication.common.utils import validate_username, validate_password
        validate_username(username)

        # Uniqueness check
        conflict = conn.execute(
            "SELECT id FROM tenants WHERE LOWER(tenant_username) = ? AND id != ? LIMIT 1",
            (username, tenantId),
        ).fetchone()
        if conflict:
            raise HTTPException(status_code=409, detail="That username is already in use by another tenant.")

        now = datetime.utcnow().isoformat()

        updates = ["tenant_username = ?"]
        params = [username]

        if payload.temporaryPassword:
            if len(str(payload.temporaryPassword)) < 8:
                raise HTTPException(status_code=400, detail="Temporary password must be at least 8 characters.")
            from app.authentication.common.utils import validate_password
            validate_password(str(payload.temporaryPassword))
            pwd_hash = hash_pin(str(payload.temporaryPassword))
            updates.append("password_hash = ?")
            params.append(pwd_hash)
            updates.append("password_reset_required = ?")
            params.append(1 if payload.resetRequired else 0)
            updates.append("last_password_change_at = ?")
            params.append(now)
            conn.execute(
                "INSERT INTO tenant_password_history (tenantId, password_hash, changed_at, changed_by) VALUES (?, ?, ?, 'landlord')",
                (tenantId, pwd_hash, now),
            )
        else:
            updates.append("password_reset_required = 0")

        updates.append("password_failed_attempts = 0")
        updates.append("password_locked_until = NULL")
        params.append(tenantId)
        conn.execute(
            f"UPDATE tenants SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        conn.commit()

    revoke_all_tenant_sessions(tenantId)
    ip = request.client.host if request.client else "Unknown IP"
    log_audit(tenantId, "Portal Auth Configured", ip)

    landlord_id = principal.landlord_id
    if landlord_id:
        create_landlord_audit_log(
            landlord_id, "tenant_portal_auth_configured",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"tenant_id": tenantId, "tenant_username": username}),
        )

    await _broadcast(f"landlord:{landlordUuid}", {"type": "TENANT_UPDATED", "tenantId": tenantId})

    return {
        "status": "success",
        "message": "Portal login configured." if payload.temporaryPassword else "Portal username assigned.",
        "tenantUsername": username,
        "resetRequired": bool(payload.resetRequired) if payload.temporaryPassword else False,
    }


@router.post(Routes.LANDLORDAPITENANTSQRKEY, name=Names.LANDLORDTENANTQRKEY)
async def api_tenant_regenerate_qr_key(landlordUuid: str, tenantId: int, request: Request, background_tasks: BackgroundTasks, principal=Depends(get_current_landlord_api_strict)):
    """Regenerate a tenant's QR key (rotates the QR link; revokes all sessions)."""
    import uuid as _uuid
    from app.authentication.tenant.sessions import revoke_all_tenant_sessions
    from app.database.auth_repository import log_audit
    from app.database.landlord_repository import create_landlord_audit_log
    from app.core.db import get_conn

    background_tasks.add_task(create_full_backup, tag="regenerate_qr_key", landlord_id=principal.landlord_id)

    # Single 128-bit key — matches the length used at tenant creation. A longer
    # key bloats the QR payload into a larger matrix, which hurts scannability.
    new_key = _uuid.uuid4().hex
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id, name FROM tenants WHERE id = ? AND landlord_id = ?", (tenantId, principal.landlord_id)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Tenant not found")
        conn.execute("UPDATE tenants SET qr_key = ? WHERE id = ?", (new_key, tenantId))
        conn.commit()

    revoke_all_tenant_sessions(tenantId)
    ip = request.client.host if request.client else "Unknown IP"
    log_audit(tenantId, "QR Key Regenerated", ip)

    landlord_id = principal.landlord_id
    if landlord_id:
        create_landlord_audit_log(
            landlord_id, "tenant_qr_key_regenerated",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"tenant_id": tenantId}),
        )

    await _broadcast(f"landlord:{landlordUuid}", {"type": "TENANT_UPDATED", "tenantId": tenantId})

    return {"status": "success", "message": "QR key regenerated.", "qr_key": new_key}

@router.get(Routes.LANDLORDAPITENANTSQR, name=Names.LANDLORDTENANTQR)
async def api_tenant_qr(
    landlordUuid: str,
    tenantId: int,
    size: int = Query(200, ge=100, le=1000),
    format: str = Query("svg", pattern="^(svg|png)$"),
    principal=Depends(get_current_landlord_api_strict),
):
    """Return the PROPAURA-branded tenant portal QR as a data URI.

    Generated server-side at ECC H with the lockup embedded in the pattern,
    then decode-validated before being returned.
    """
    from app.core.db import get_conn
    from app.services.qr_service import QrBuildError, build_branded_qr, tenant_qr_payload

    if not tenant_belongs_to_landlord(tenantId, principal.landlord_id):
        raise HTTPException(status_code=404, detail="Tenant not found")

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, property_id, viewToken, qr_key FROM tenants WHERE id = ?",
            (tenantId,),
        ).fetchone()

    if not row or not row["viewToken"]:
        raise HTTPException(status_code=400, detail="Tenant portal token is missing.")
    if not row["qr_key"]:
        raise HTTPException(status_code=400, detail="Tenant QR key is missing.")

    url = tenant_qr_payload(landlordUuid, row["property_id"], tenantId, row["viewToken"], row["qr_key"])
    try:
        qr, fmt, count = build_branded_qr(url, size=size, fmt=format, validate=True)
    except QrBuildError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "status": "success",
        "qr": qr,
        "format": fmt,
        "error_correction": "H",
        "size": size,
        "modules": count,
        "url": url,
    }

@router.delete(Routes.LANDLORDAPITENANTSUPDATE, name=Names.APIDELETETENANT)
async def api_delete_tenant(
    landlordUuid: str,
    tenantId: int,
    request: Request,
    background_tasks: BackgroundTasks,
    action: str = "archive",
    principal=Depends(get_current_landlord_api_strict),
):
    from app.database.landlord_repository import create_landlord_audit_log

    action = (action or "archive").strip().lower()

    # ── New: permanent-with-recovery action ──────────────────────────────────
    if action == "permanent-with-recovery":
        from app.services.tenant_recovery_service import (
            create_tenant_recovery_snapshot,
            permanently_delete_tenant_data,
        )

        tenant = get_tenant(tenantId, landlord_id=principal.landlord_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found.")

        if (tenant.status or "").strip().lower() != "archived":
            raise HTTPException(
                status_code=409,
                detail="Only archived tenants can be permanently deleted. Archive the tenant first.",
            )

        try:
            # Step 1: Create recovery snapshot SYNCHRONOUSLY (must complete before deletion)
            snapshot = create_tenant_recovery_snapshot(
                tenant_id=tenantId,
                admin_id=None,  # admin principal not injected here; safe to omit
                landlord_id=principal.landlord_id,
            )
            # Step 2: Permanently delete all live data
            permanently_delete_tenant_data(tenantId)

            return {
                "status": "success",
                "action": "permanent-with-recovery",
                "snapshotId": snapshot["id"],
                "expiresAt": snapshot["expires_at"],
                "tenantId": tenantId,
                "tenantName": snapshot["tenant_name"],
            }
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Permanent deletion failed; no live data was deleted: {exc}",
            )

    # ── Existing actions ─────────────────────────────────────────────────────
    if action not in {"archive", "delete", "hard", "inactive"}:
        raise HTTPException(status_code=400, detail="Invalid tenant action.")

    # Must include archived tenants so an already-archived tenant is not missed
    tenant = get_tenant(tenantId, landlord_id=principal.landlord_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    try:
        background_tasks.add_task(create_full_backup, tag=f"{action}_tenant", landlord_id=principal.landlord_id)
        result = delete_tenant(tenantId, action, landlord_id=principal.landlord_id)

        landlord_id = principal.landlord_id
        if landlord_id:
            create_landlord_audit_log(
                landlord_id, f"tenant_{action}",
                ip_address=request.client.host if request.client else None,
                meta_json=json.dumps({"tenant_id": tenantId}),
            )

        await _broadcast(f"landlord:{landlordUuid}", {"type": "TENANT_DELETED", "tenantId": tenantId})
        return {"status": "success", "action": action, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tenant {action} failed: {str(e)}")


# ── Tenant Recovery Snapshot Endpoints ───────────────────────────────────────

@router.get(Routes.LANDLORDAPITENANTSNAPSHOTS, name=Names.APILISTRECOVERYSNAPSHOTS)
async def api_list_recovery_snapshots(landlordUuid: str, principal=Depends(get_current_landlord_api_strict)):
    """List all tenant recovery snapshots (runs expiry purge first)."""
    from app.services.tenant_recovery_service import get_tenant_recovery_snapshots
    snapshots = get_tenant_recovery_snapshots(landlord_id=principal.landlord_id)
    return {"status": "success", "snapshots": snapshots}


@router.get(Routes.LANDLORDAPITENANTSNAPSHOT_PREVIEW, name=Names.APIRECOVERYSNAPSHOT_PREVIEW)
async def api_recovery_snapshot_preview(landlordUuid: str, snapshotId: str, principal=Depends(get_current_landlord_api_strict)):
    """Return a conflict preview for restoring a tenant recovery snapshot."""
    from app.services.tenant_recovery_service import get_snapshot_restore_preview
    try:
        preview = get_snapshot_restore_preview(snapshotId, landlord_id=principal.landlord_id)
        return {"status": "success", **preview}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {e}")


class RestoreSnapshotRequest(BaseModel):
    force_new_id: bool = False


@router.post(Routes.LANDLORDAPITENANTSNAPSHOT_RESTORE, name=Names.APIRECOVERYSNAPSHOT_RESTORE)
async def api_restore_recovery_snapshot(landlordUuid: str, snapshotId: str, payload: RestoreSnapshotRequest = RestoreSnapshotRequest(), principal=Depends(get_current_landlord_api_strict)):
    """Restore a tenant from a recovery snapshot."""
    from app.services.tenant_recovery_service import restore_tenant_from_snapshot
    try:
        result = restore_tenant_from_snapshot(snapshotId, force_new_id=payload.force_new_id, landlord_id=principal.landlord_id)
        return {"status": "success", **result}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {e}")


@router.post(Routes.LANDLORDAPITENANTSRESTORE, name=Names.APIRESTORETENANT)
async def api_restore_tenant(
    landlordUuid: str,
    tenantId: int,
    background_tasks: BackgroundTasks,
    principal=Depends(get_current_landlord_api_strict),
):
    # Archived tenants must be visible for the existence check — this is why restore
    # cannot share the normal pre-check that excludes archived tenants.
    tenant = get_tenant(tenantId, landlord_id=principal.landlord_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    try:
        background_tasks.add_task(create_full_backup, tag="restore_tenant", landlord_id=principal.landlord_id)
        result = delete_tenant(tenantId, "restore", landlord_id=principal.landlord_id)
        return {"status": "success", "action": "restore", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tenant restore failed: {str(e)}")

from app.core.paths import KYC_DIR
import mimetypes

@router.get(Routes.LANDLORDAPIOCCUPANTSLIST, name=Names.APIGETOCCUPANTS)
async def admin_get_occupants(landlordUuid: str, tenantId: int, principal=Depends(get_current_landlord_api_strict)):
    if not tenant_belongs_to_landlord(tenantId, principal.landlord_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    occupants = get_occupants(tenantId)
    return {"occupants": occupants}

@router.post(Routes.LANDLORDAPIOCCUPANTSCREATE, name=Names.APICREATEOCCUPANT)
async def admin_post_occupants(
    landlordUuid: str,
    tenantId: int,
    name: str = Form(...),
    mobile: str = Form(""),
    address: str = Form(""),
    residentSince: str = Form(""),
    aadhaarfront: Optional[UploadFile] = File(None),
    aadhaarback: Optional[UploadFile] = File(None),
    aadhaarcombined: Optional[UploadFile] = File(None),
    empfront: Optional[UploadFile] = File(None),
    empback: Optional[UploadFile] = File(None),
    principal=Depends(get_current_landlord_api_strict),
):
    import uuid
    from app.core.paths import KYC_DIR
    import os
    import shutil

    if not tenant_belongs_to_landlord(tenantId, principal.landlord_id):
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate Aadhaar: need combined OR both front+back
    has_combined = aadhaarcombined and aadhaarcombined.filename
    has_both = (aadhaarfront and aadhaarfront.filename) and (aadhaarback and aadhaarback.filename)
    if not has_combined and not has_both:
        raise HTTPException(
            status_code=400,
            detail="Upload one combined Aadhaar document, or both front and back.",
        )

    # Validate residentSince date if provided
    if residentSince:
        try:
            from datetime import date
            parsed = date.fromisoformat(residentSince)
            if parsed > date.today():
                raise HTTPException(status_code=400, detail="Residing since date cannot be in the future.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid residentSince date format. Use YYYY-MM-DD.")

    occ_uuid = str(uuid.uuid4())
    prefix = f"{tenantId}_{occ_uuid}"
    doc_urls: dict = {}

    async def _save(upload: UploadFile, field: str):
        if not upload or not upload.filename:
            return
        ext = os.path.splitext(upload.filename)[-1].lower()
        safe_name = f"{prefix}_{field}{ext}"
        file_path = os.path.join(KYC_DIR, safe_name)
        with open(file_path, "wb") as buf:
            shutil.copyfileobj(upload.file, buf)
        doc_urls[field] = safe_name

    await _save(aadhaarcombined, "aadhaar_combined")
    await _save(aadhaarfront,    "aadhaar_front")
    await _save(aadhaarback,     "aadhaar_back")
    await _save(empfront,        "emp_front")
    await _save(empback,         "emp_back")

    from datetime import datetime
    now = datetime.utcnow()
    occ_data = {
        "occupantUuid":    occ_uuid,
        "name":            name,
        "mobile":          normalize_phone(mobile),
        "address":         address,
        "residentSince":   residentSince,
        "status":          "Active",
        "aadhaar_combined": doc_urls.get("aadhaar_combined", ""),
        "aadhaar_front":   doc_urls.get("aadhaar_front", ""),
        "aadhaar_back":    doc_urls.get("aadhaar_back", ""),
        "emp_front":       doc_urls.get("emp_front", ""),
        "emp_back":        doc_urls.get("emp_back", ""),
        "uploaddate":      now.strftime("%d %b %Y"),
        "uploadmonth":     now.strftime("%B %Y"),
    }
    save_occupant(tenantId, occ_data)
    return {"status": "success", "occupantUuid": occ_uuid}

@router.put(Routes.LANDLORDAPIOCCUPANTSMARKINACTIVE, name=Names.APIMARKOCCUPANTINACTIVE)
async def admin_tenant_kyc_mark_inactive(landlordUuid: str, tenantId: int, occupantUuid: str, principal=Depends(get_current_landlord_api_strict)):
    from app.services.tenant_service import update_occupant_status
    if not tenant_belongs_to_landlord(tenantId, principal.landlord_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    update_occupant_status(occupantUuid, "Inactive")
    return {"status": "success"}

@router.delete(Routes.LANDLORDAPIOCCUPANTSDELETE, name=Names.APIDELETEOCCUPANT)
async def admin_tenant_kyc_delete(landlordUuid: str, tenantId: int, occupantUuid: str, principal=Depends(get_current_landlord_api_strict)):
    if not tenant_belongs_to_landlord(tenantId, principal.landlord_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenantId = tenantId
    occupantUuid = occupantUuid
    occupants = get_occupants(tenantId)
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

@router.get(Routes.LANDLORDAPIOCCUPANTSGETFILE, name=Names.APIGETOCCUPANTFILE)
async def admin_get_kyc_file(landlordUuid: str, tenantId: int, filename: str, principal=Depends(get_current_landlord_api_strict)):
    if not tenant_belongs_to_landlord(tenantId, principal.landlord_id):
        raise HTTPException(status_code=404, detail="Tenant not found")

    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not safe_filename.startswith(f"{tenantId}_"):
        raise HTTPException(status_code=404, detail="File not found")

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

