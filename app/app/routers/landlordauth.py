"""
app/routers/landlordauth.py

Public landlord authentication endpoints:
  GET  /landlord/api/auth/check-username   — username availability + suggestions
  POST /landlord/api/auth/signup           — create landlord account
  POST /landlord/api/auth/login            — authenticate + set cookies
  POST /landlord/api/login/totp            — complete login with TOTP verification
  POST /landlord/api/auth/logout           — clear cookies + revoke session
  GET  /landlord/api/auth/me               — return current landlord identity

Protected landlord TOTP management endpoints:
  GET  /landlord/{landlordUuid}/api/totp/qr         — get TOTP QR code
  POST /landlord/{landlordUuid}/api/totp/regenerate  — regenerate TOTP secret
"""
import json
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.authentication.common.utils import hash_pin, verify_pin
from app.authentication.landlord.cookies import (
    clear_landlord_auth_cookies,
    set_landlord_auth_cookies,
)
from app.authentication.landlord.jwt import create_landlord_access_token
from app.authentication.landlord.middleware import get_current_landlord_api
from app.authentication.landlord.sessions import (
    create_landlord_session,
    revoke_landlord_session_db,
)
from app.core.routes_manifest_landlord import LandlordRoutes as Routes, LandlordNames as Names
from app.database.landlord_repository import (
    create_landlord,
    create_landlord_audit_log,
    get_landlord_by_email,
    get_landlord_by_username,
    get_landlord_by_uuid,
    get_landlord_totp_secret,
    update_landlord_totp_secret,
    generate_totp_qr_base64,
    get_totp_uri,
    verify_totp,
    regenerate_landlord_totp_secret,
    username_exists,
    is_landlord_locked_out,
    record_landlord_failed_attempt,
    reset_landlord_failed_attempts,
)
from app.models.landlord import LandlordLoginRequest, LandlordLoginWithTotpRequest, LandlordSignupRequest
from app.core.config_service import config
from app.core.db import get_conn

router = APIRouter(tags=["Landlord Authentication"])

# ── Username rules ─────────────────────────────────────────────────────────────

RESERVED = {
    "admin", "root", "api", "login", "signup", "tenant",
    "landlord", "support", "system", "platform", "superuser",
}


def normalize_username(username: str) -> str:
    """Lowercase, strip whitespace, remove any char that is not [a-z0-9_]."""
    username = username.strip().lower()
    username = re.sub(r"[^a-z0-9_]", "", username)
    return username


def suggest_usernames(base: str) -> list[str]:
    """Generate 3–5 available username alternatives for *base*."""
    base = normalize_username(base) or "user"
    candidates = [
        f"{base}91",
        f"{base}123",
        f"{base}_01",
        f"{base}_91",
        f"{base}2026",
        f"{base}786",
    ]
    result = []
    for candidate in candidates:
        if candidate not in RESERVED and not username_exists(candidate):
            result.append(candidate)
        if len(result) >= 5:
            break
    return result


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get(Routes.LANDLORDAPIAUTHPUBLICKEY, name=Names.LANDLORDPUBLICKEY)
async def landlord_public_key():
    from app.encryption import get_public_key_pem
    return {"publicKey": get_public_key_pem()}


@router.get(Routes.LANDLORDAPIAUTHCHECKUSERNAME, name=Names.LANDLORDCHECKUSERNAME)
async def check_username(username: str):
    """
    Return whether *username* is available and, if not, suggest alternatives.
    Response: { username, available, suggestions[] }
    """
    normalized = normalize_username(username)
    if len(normalized) < 3:
        return {"username": normalized, "available": False, "suggestions": []}

    available = normalized not in RESERVED and not username_exists(normalized)
    return {
        "username": normalized,
        "available": available,
        "suggestions": [] if available else suggest_usernames(normalized),
    }


@router.get(Routes.LANDLORDAPIAUTHCHECKEMAIL, name=Names.LANDLORDCHECKEMAIL)
async def check_email(email: str):
    """Return whether *email* is available."""
    email_clean = email.strip().lower()
    if "@" not in email_clean or "." not in email_clean.split("@")[-1]:
        return {"email": email_clean, "available": False, "error": "Invalid email format"}
    available = get_landlord_by_email(email_clean) is None
    return {"email": email_clean, "available": available, "error": None}


@router.post(Routes.LANDLORDAPIAUTHSIGNUP, name=Names.LANDLORDSIGNUP)
async def landlord_signup(request: Request, payload: LandlordSignupRequest):
    """
    Create a new landlord account.
    Validates: username format, password match, uniqueness of username + email.
    Returns: { status, landlord: { id, landlordUuid, username, fullName } }
    """
    username = normalize_username(payload.username)

    # ── Input validation ──
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if username in RESERVED:
        raise HTTPException(status_code=400, detail="Username is reserved.")
    if payload.password != payload.confirmPassword:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    # ── Unified uniqueness checks ──
    conflicts = []

    if username in RESERVED:
        conflicts.append({
            "field": "username",
            "code": "RESERVED",
            "message": "Username is reserved.",
            "suggestions": suggest_usernames(username),
        })
    elif username_exists(username):
        conflicts.append({
            "field": "username",
            "code": "USERNAME_TAKEN",
            "message": "Username is already registered.",
            "suggestions": suggest_usernames(username),
        })

    if payload.email and get_landlord_by_email(payload.email.strip().lower()):
        conflicts.append({
            "field": "email",
            "code": "EMAIL_TAKEN",
            "message": "Email is already registered.",
        })

    if conflicts:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICTS", "message": "Some fields need attention.", "conflicts": conflicts},
        )

    # ── Create account ──
    landlord_uuid = str(uuid.uuid4())
    password_hash = hash_pin(payload.password)

    landlord = create_landlord(
        full_name=payload.fullName.strip(),
        email=payload.email.strip().lower() if payload.email else None,
        phone=payload.phone.strip() if payload.phone else None,
        username=username,
        password_hash=password_hash,
        landlord_uuid=landlord_uuid,
    )

    # Store encrypted password in admin vault (for platform admin reveal)
    from app.authentication.common.pin_vault import encrypt_admin_view_pin
    from app.core.db import get_conn as _get_conn
    encrypted_pw = encrypt_admin_view_pin(payload.password)
    now_iso = datetime.utcnow().isoformat()
    with _get_conn() as vault_conn:
        vault_conn.execute(
            """INSERT OR REPLACE INTO landlord_password_admin_store
               (landlord_id, encrypted_password, updated_at) VALUES (?, ?, ?)""",
            (landlord["id"], encrypted_pw, now_iso),
        )
        vault_conn.commit()

    create_landlord_audit_log(
        landlord["id"],
        "signup_success",
        ip_address=request.client.host if request.client else None,
        meta_json=json.dumps({"username": username}),
    )

    return {
        "status": "success",
        "landlord": {
            "id": landlord["id"],
            "landlordUuid": landlord["landlord_uuid"],
            "username": landlord["username"],
            "fullName": landlord["full_name"],
        },
    }


@router.post(Routes.LANDLORDAPIAUTHLOGIN, name=Names.LANDLORDLOGIN)
async def landlord_login(
    request: Request, response: Response, payload: LandlordLoginRequest
):
    """
    Authenticate a landlord and issue access + refresh cookies.
    Returns: { status, landlord: { id, landlordUuid, username, fullName } }
    If TOTP is required and configured, returns { status: "totp_required" } instead.
    """
    username = normalize_username(payload.username)
    landlord = get_landlord_by_username(username)

    if not landlord:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    if is_landlord_locked_out(landlord):
        create_landlord_audit_log(
            landlord["id"],
            "login_locked_out",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"username": username}),
        )
        raise HTTPException(status_code=429, detail="Account locked. Try again later.")

    if not verify_pin(payload.password, landlord["password_hash"]):
        record_landlord_failed_attempt(landlord["id"])
        create_landlord_audit_log(
            landlord["id"],
            "login_failed",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"username": username}),
        )
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # Check if TOTP is required for login
    require_totp = config.get("system", {}).get("security", {}).get("adminTotpRequired", True)
    if require_totp and landlord["totp_secret"]:
        return {
            "status": "totp_required",
            "message": "TOTP verification required.",
            "username": username,
        }

    # Check if password change is required (admin reset)
    if landlord["requires_password_change"]:
        if dict(landlord).get("temp_password_consumed"):
            create_landlord_audit_log(
                landlord["id"],
                "temp_password_reuse_blocked",
                ip_address=request.client.host if request.client else None,
                meta_json=json.dumps({"username": username}),
            )
            raise HTTPException(
                status_code=403,
                detail="This temporary password has already been used. Contact your administrator to reset it again.",
            )

        # Mark temp password as consumed on first use
        now = datetime.utcnow().isoformat()
        with get_conn() as conn:
            conn.execute(
                "UPDATE landlord_accounts SET temp_password_consumed = 1 WHERE id = ?",
                (landlord["id"],),
            )
            conn.commit()

        reset_landlord_failed_attempts(landlord["id"])
        session_id, refresh_token = create_landlord_session(
            landlord["id"], request, payload.rememberMe
        )
        access_token = create_landlord_access_token(landlord["id"], session_id)
        cookie_value = f"{session_id}:{refresh_token}"
        set_landlord_auth_cookies(response, access_token, cookie_value, payload.rememberMe, request)

        create_landlord_audit_log(
            landlord["id"],
            "login_forced_password_change",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"username": username}),
        )

        return {
            "status": "password_change_required",
            "message": "You must change your password before continuing.",
            "username": username,
            "landlordUuid": landlord["landlord_uuid"],
        }

    reset_landlord_failed_attempts(landlord["id"])
    session_id, refresh_token = create_landlord_session(
        landlord["id"], request, payload.rememberMe
    )
    access_token = create_landlord_access_token(landlord["id"], session_id)
    cookie_value = f"{session_id}:{refresh_token}"

    set_landlord_auth_cookies(response, access_token, cookie_value, payload.rememberMe, request)

    create_landlord_audit_log(
        landlord["id"],
        "login_success",
        ip_address=request.client.host if request.client else None,
        meta_json=json.dumps({"username": username}),
    )

    return {
        "status": "success",
        "landlord": {
            "id": landlord["id"],
            "landlordUuid": landlord["landlord_uuid"],
            "username": landlord["username"],
            "fullName": landlord["full_name"],
        },
    }


@router.post(Routes.LANDLORDAPIAUTHLOGOUT, name=Names.LANDLORDLOGOUT)
async def landlord_logout(request: Request, response: Response):
    """
    Clear landlord cookies and revoke the active session.
    """
    clear_landlord_auth_cookies(response, request)
    token = request.cookies.get("landlord_refresh_token")
    if token and ":" in token:
        session_id = token.split(":", 1)[0]
        revoke_landlord_session_db(session_id)
    return {"status": "success"}


@router.get(Routes.LANDLORDAPIAUTHME, name=Names.LANDLORDME)
async def landlord_me(principal=Depends(get_current_landlord_api)):
    """
    Return the identity of the currently authenticated landlord.
    Requires a valid landlord_access_token cookie.
    Returns TOTP state and password change flag so frontend can sync state.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT totp_secret, requires_password_change FROM landlord_accounts WHERE id = ?",
            (principal.landlord_id,),
        ).fetchone()

    return {
        "status": "success",
        "landlord": {
            "id": principal.landlord_id,
            "landlordUuid": principal.landlord_uuid,
            "username": principal.username,
            "fullName": principal.fullname,
            "email": principal.email,
            "hasTotp": bool(row and row["totp_secret"]),
            "requiresPasswordChange": bool(row and row["requires_password_change"]),
        },
    }


# ─── TOTP Login ────────────────────────────────────────────────────

@router.post(Routes.LANDLORDAPIAUTHLOGINTOTP, name=Names.LANDLORDLOGINTOTP)
async def landlord_login_with_totp(
    request: Request, response: Response, payload: LandlordLoginWithTotpRequest
):
    """
    Complete landlord login with TOTP verification.
    Re-verifies username + password, then validates the TOTP code.
    """
    username = normalize_username(payload.username)
    landlord = get_landlord_by_username(username)

    if not landlord:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    if is_landlord_locked_out(landlord):
        create_landlord_audit_log(
            landlord["id"],
            "login_locked_out",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"username": username}),
        )
        raise HTTPException(status_code=429, detail="Account locked. Try again later.")

    if not verify_pin(payload.password, landlord["password_hash"]):
        record_landlord_failed_attempt(landlord["id"])
        create_landlord_audit_log(
            landlord["id"],
            "login_failed",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"username": username}),
        )
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    if not landlord["totp_secret"]:
        raise HTTPException(status_code=400, detail="TOTP not configured for this account.")

    if not verify_totp(landlord["totp_secret"], payload.totpToken):
        record_landlord_failed_attempt(landlord["id"])
        create_landlord_audit_log(
            landlord["id"],
            "totp_failed",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"username": username}),
        )
        raise HTTPException(status_code=401, detail="Invalid TOTP code. Please try again.")

    reset_landlord_failed_attempts(landlord["id"])

    # Check if password change is required (admin reset)
    if landlord["requires_password_change"]:
        if dict(landlord).get("temp_password_consumed"):
            create_landlord_audit_log(
                landlord["id"],
                "temp_password_reuse_blocked",
                ip_address=request.client.host if request.client else None,
                meta_json=json.dumps({"username": username}),
            )
            raise HTTPException(
                status_code=403,
                detail="This temporary password has already been used. Contact your administrator to reset it again.",
            )

        now = datetime.utcnow().isoformat()
        with get_conn() as conn:
            conn.execute(
                "UPDATE landlord_accounts SET temp_password_consumed = 1 WHERE id = ?",
                (landlord["id"],),
            )
            conn.commit()

        session_id, refresh_token = create_landlord_session(
            landlord["id"], request, payload.rememberMe
        )
        access_token = create_landlord_access_token(landlord["id"], session_id)
        cookie_value = f"{session_id}:{refresh_token}"
        set_landlord_auth_cookies(response, access_token, cookie_value, payload.rememberMe, request)

        create_landlord_audit_log(
            landlord["id"],
            "login_forced_password_change",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"username": username}),
        )

        return {
            "status": "password_change_required",
            "message": "You must change your password before continuing.",
            "username": username,
            "landlordUuid": landlord["landlord_uuid"],
        }

    session_id, refresh_token = create_landlord_session(
        landlord["id"], request, payload.rememberMe
    )
    access_token = create_landlord_access_token(landlord["id"], session_id)
    cookie_value = f"{session_id}:{refresh_token}"

    set_landlord_auth_cookies(response, access_token, cookie_value, payload.rememberMe, request)

    create_landlord_audit_log(
        landlord["id"],
        "login_success",
        ip_address=request.client.host if request.client else None,
        meta_json=json.dumps({"username": username}),
    )

    return {
        "status": "success",
        "landlord": {
            "id": landlord["id"],
            "landlordUuid": landlord["landlord_uuid"],
            "username": landlord["username"],
            "fullName": landlord["full_name"],
        },
    }


# ─── TOTP Management (protected) ───────────────────────────────────

@router.post(Routes.LANDLORDAPIAUTHCHANGEPASSWORD, name="landlordchangepassword")
async def landlord_change_password(
    request: Request,
    payload: dict,
):
    """
    Change landlord password. Used during forced password reset flow.
    Requires current password + new password + confirm password.
    Accepts encrypted (key/data/nonce) or plain JSON payload.
    """
    from app.authentication.common.pin_vault import encrypt_admin_view_pin
    from app.encryption import decrypt_payload

    # Handle encrypted payload from frontend apiPost
    if "key" in payload and "data" in payload and "nonce" in payload:
        try:
            decrypted = decrypt_payload(payload["key"], payload["data"], payload["nonce"])
            current_password = decrypted.get("currentPassword", "")
            new_password = decrypted.get("newPassword", "")
            confirm_password = decrypted.get("confirmPassword", "")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid encrypted payload")
    else:
        current_password = payload.get("currentPassword", "")
        new_password = payload.get("newPassword", "")
        confirm_password = payload.get("confirmPassword", "")

    if not current_password or not new_password or not confirm_password:
        raise HTTPException(status_code=400, detail="All fields are required.")
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match.")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    if current_password == new_password:
        raise HTTPException(status_code=400, detail="New password must be different from current password.")

    # Extract landlord from token
    token = request.cookies.get("landlord_access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from app.authentication.landlord.jwt import decode_landlord_access_token
    payload_token = decode_landlord_access_token(token)
    landlord_id = int(payload_token.get("landlord_id") or payload_token.get("sub"))

    with get_conn() as conn:
        landlord = conn.execute(
            "SELECT id, landlord_uuid, password_hash FROM landlord_accounts WHERE id = ?",
            (landlord_id,),
        ).fetchone()
        if not landlord:
            raise HTTPException(status_code=404, detail="Landlord not found.")

    if not verify_pin(current_password, landlord["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    new_hash = hash_pin(new_password)
    encrypted_pw = encrypt_admin_view_pin(new_password)
    now = datetime.utcnow().isoformat()

    with get_conn() as conn:
        conn.execute(
            """UPDATE landlord_accounts
               SET password_hash = ?,
                   requires_password_change = 0,
                   temp_password_created_at = NULL,
                   temp_password_consumed = 0,
                   updated_at = ?
               WHERE id = ?""",
            (new_hash, now, landlord_id),
        )
        conn.execute(
            """INSERT OR REPLACE INTO landlord_password_admin_store
               (landlord_id, encrypted_password, updated_at) VALUES (?, ?, ?)""",
            (landlord_id, encrypted_pw, now),
        )
        # Check if landlord has TOTP configured
        row = conn.execute(
            "SELECT totp_secret FROM landlord_accounts WHERE id = ?",
            (landlord_id,),
        ).fetchone()
        conn.commit()

    create_landlord_audit_log(
        landlord_id,
        "password_changed",
        ip_address=request.client.host if request.client else None,
    )

    # Broadcast auth state change
    try:
        from app.core.websocket_manager import sync_manager
        ll_uuid = landlord["landlord_uuid"]
        await sync_manager.broadcast(f"landlord:{ll_uuid}", {"type": "AUTH_STATE_CHANGED", "role": "landlord", "id": landlord_id})
        await sync_manager.broadcast("platform_admin", {"type": "AUTH_STATE_CHANGED", "role": "landlord", "id": landlord_id})
    except Exception:
        pass

    # Return TOTP data if configured, so frontend can show QR dialog
    if row and row["totp_secret"]:
        qr_base64 = generate_totp_qr_base64(landlord["username"] if landlord else "", row["totp_secret"])
        return {
            "status": "success",
            "message": "Password updated successfully.",
            "next_step": "totp_review",
            "totp": {
                "secret": row["totp_secret"],
                "qr_code_base64": qr_base64,
                "provisioning_uri": get_totp_uri(landlord["username"] if landlord else "", row["totp_secret"]),
            },
        }

    return {"status": "success", "message": "Password updated successfully."}


@router.get(Routes.LANDLORDAPITOTPQR, name=Names.LANDLORDTOTPQR)
async def landlord_totp_qr(
    landlordUuid: str,
    principal=Depends(get_current_landlord_api),
):
    """
    Get TOTP QR code and secret for the authenticated landlord.
    Auto-generates a secret on first access.
    """
    landlord = get_landlord_by_uuid(landlordUuid)
    if not landlord:
        raise HTTPException(status_code=404, detail="Landlord not found.")

    # Auto-generate TOTP secret on first access
    if not landlord["totp_secret"]:
        new_secret = regenerate_landlord_totp_secret(landlord["id"])
        landlord = get_landlord_by_uuid(landlordUuid)
    else:
        new_secret = landlord["totp_secret"]

    qr_base64 = generate_totp_qr_base64(landlord["username"], new_secret)

    return {
        "status": "success",
        "totp": {
            "secret": new_secret,
            "qr_code_base64": qr_base64,
            "provisioning_uri": get_totp_uri(landlord["username"], new_secret),
        },
    }


@router.post(Routes.LANDLORDAPITOTPREGENERATE, name=Names.LANDLORDTOTPREGENERATE)
async def landlord_totp_regenerate(
    landlordUuid: str,
    principal=Depends(get_current_landlord_api),
):
    """
    Regenerate TOTP secret for the authenticated landlord.
    Returns a new QR code and secret.
    """
    landlord = get_landlord_by_uuid(landlordUuid)
    if not landlord:
        raise HTTPException(status_code=404, detail="Landlord not found.")

    new_secret = regenerate_landlord_totp_secret(landlord["id"])
    qr_base64 = generate_totp_qr_base64(landlord["username"], new_secret)

    return {
        "status": "success",
        "message": "TOTP secret regenerated successfully. Update your authenticator app!",
        "totp": {
            "secret": new_secret,
            "qr_code_base64": qr_base64,
            "provisioning_uri": get_totp_uri(landlord["username"], new_secret),
        },
    }
