from fastapi import datastructures
from fastapi import APIRouter, Depends, Request, Response, Form, HTTPException

from app.core.routes_manifest_platform_admin import PlatformAdminRoutes as Routes, PlatformAdminNames as Names

from pydantic import BaseModel
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.core.dependencies import templates
from app.core.db import get_conn
from app.authentication.common.utils import verify_pin, hash_pin
from app.authentication.admin.jwt import create_admin_access_token
from app.authentication.admin.sessions import create_admin_session, get_admin_session_db, revoke_admin_session_db
from app.authentication.admin.cookies import set_admin_auth_cookies, clear_admin_auth_cookies
from app.database.auth_repository import (
    admin_exists, create_admin, get_admin_by_username, get_admin_by_id,
    verify_totp, generate_totp_qr_base64, get_totp_uri, update_admin_password,
    regenerate_totp_secret
)
from app.encryption import decrypt_payload
from app.core.config_service import config

# router = APIRouter(tags=["Admin Authentication"])
router = APIRouter()

# ─── Request Models ────────────────────────────────────────────────

class EncryptedPayload(BaseModel):
    key: str
    data: str
    nonce: str
    remember_me: bool = False


# ─── Setup & User Creation ───────────────────────────────────────────

@router.get(Routes.PLATFORMADMINAPISETUPREQUIRED, name=Names.PLATFORMADMINSETUPREQUIRED)
async def check_setup_required():
    """Check if admin setup is required (no admin exists yet)."""
    return {
        "setup_required": not admin_exists(),
        "message": "No admin user found. Please create an admin account to continue." if not admin_exists() else "Admin account exists."
    }

@router.post(Routes.PLATFORMADMINAPISETUPCREATE, name=Names.PLATFORMADMINSETUPCREATE)
async def create_first_admin(req: EncryptedPayload):
    """Create the first admin user (only works when no admins exist)."""
    if admin_exists():
        raise HTTPException(status_code=403, detail="Admin user already exists. Use the settings page to manage admins.")
    
    try:
        decrypted = decrypt_payload(req.key, req.data, req.nonce)
        username = decrypted.get("username", "").strip()
        password = decrypted.get("password", "")
        confirm_password = decrypted.get("confirm_password", "")
        email = decrypted.get("email", "")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid encrypted payload")

    if not username or len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters long.")
    
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")
    
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    
    password_hash = hash_pin(password)
    admin_data = create_admin(username, password_hash, email or None)
    
    # Generate QR code for TOTP
    qr_base64 = generate_totp_qr_base64(admin_data["username"], admin_data["totp_secret"])
    
    return {
        "status": "success",
        "message": "Admin user created successfully. Save your TOTP secret securely!",
        "admin": {
            "id": admin_data["id"],
            "username": admin_data["username"],
            "email": admin_data["email"]
        },
        "totp": {
            "secret": admin_data["totp_secret"],
            "qr_code_base64": qr_base64,
            "provisioning_uri": get_totp_uri(admin_data["username"], admin_data["totp_secret"])
        }
    }

# ─── Forgot Password ───────────────────────────────────────────────

@router.post(Routes.PLATFORMADMINAPIPASSWORDFORGOTVERIFY, name=Names.PLATFORMADMINFORGOTVERIFY)
async def verify_forgot_password(req: EncryptedPayload):
    """Verify username and TOTP for password reset."""
    try:
        decrypted = decrypt_payload(req.key, req.data, req.nonce)
        username = decrypted.get("username", "").strip()
        totp_token = decrypted.get("totp_token", "").strip()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid encrypted payload")
    
    if not username or not totp_token:
        raise HTTPException(status_code=400, detail="Username and TOTP code are required.")
    
    admin = get_admin_by_username(username)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin user not found.")
    
    if not admin["totp_secret"]:
        raise HTTPException(status_code=400, detail="TOTP not configured. Contact system administrator.")
    
    if not verify_totp(admin["totp_secret"], totp_token):
        raise HTTPException(status_code=401, detail="Invalid TOTP code. Please try again.")
    
    return {
        "status": "success",
        "message": "TOTP verified. You may now reset your password.",
        "username": username
    }

@router.post(Routes.PLATFORMADMINAPIPASSWORDFORGOTRESET, name=Names.PLATFORMADMINFORGOTRESET)
async def reset_password(req: EncryptedPayload):
    """Reset password after TOTP verification."""
    try:
        decrypted = decrypt_payload(req.key, req.data, req.nonce)
        username = decrypted.get("username", "")
        totp_token = decrypted.get("totp_token", "")
        new_password = decrypted.get("new_password", "")
        confirm_password = decrypted.get("confirm_password", "")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid encrypted payload")

    if not username or not totp_token:
        raise HTTPException(status_code=400, detail="Username and TOTP code are required.")
    
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")
    
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    
    admin = get_admin_by_username(username)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin user not found.")
    
    # Re-verify TOTP
    if not verify_totp(admin["totp_secret"], totp_token):
        raise HTTPException(status_code=401, detail="Invalid TOTP code. Please try again.")
    
    new_hash = hash_pin(new_password)
    update_admin_password(admin["id"], new_hash)
    
    return {
        "status": "success",
        "message": "Password reset successfully. Please login with your new password."
    }

# ─── Current User & TOTP Management ──────────────────────────────────

from app.authentication.admin.middleware import get_current_admin_api


@router.get(Routes.PLATFORMADMINAPITOTPQR, name=Names.PLATFORMADMINTOTPQR)
async def get_totp_qr(admin: dict = Depends(get_current_admin_api)):
    """Get TOTP QR code and secret for current admin."""
    admin_data = get_admin_by_id(admin.id)
    if not admin_data or not admin_data["totp_secret"]:
        raise HTTPException(status_code=404, detail="TOTP not configured")
    
    qr_base64 = generate_totp_qr_base64(admin_data["username"], admin_data["totp_secret"])
    
    return {
        "status": "success",
        "totp": {
            "secret": admin_data["totp_secret"],
            "qr_code_base64": qr_base64,
            "provisioning_uri": get_totp_uri(admin_data["username"], admin_data["totp_secret"])
        }
    }

@router.post(Routes.PLATFORMADMINAPITOTPREGENERATE, name=Names.PLATFORMADMINTOTPREGENERATE)
async def regenerate_totp(req: EncryptedPayload, admin: dict = Depends(get_current_admin_api)):
    """Regenerate TOTP secret (requires password confirmation)."""
    admin_data = get_admin_by_id(admin.id)
    if not admin_data:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    try:
        decrypted = decrypt_payload(req.key, req.data, req.nonce)
        password = decrypted.get("password", "")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid encrypted payload")

    if not verify_pin(password, admin_data["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid password.")
    
    new_secret = regenerate_totp_secret(admin.id)
    qr_base64 = generate_totp_qr_base64(admin_data["username"], new_secret)
    
    return {
        "status": "success",
        "message": "TOTP secret regenerated successfully. Update your authenticator app!",
        "totp": {
            "secret": new_secret,
            "qr_code_base64": qr_base64,
            "provisioning_uri": get_totp_uri(admin_data["username"], new_secret)
        }
    }

# ─── Public Key for Encryption ─────────────────────────────────────

@router.get(Routes.PLATFORMADMINAPIAUTHPUBLICKEY, name=Names.PLATFORMADMINPUBLICKEY)
async def admin_public_key():
    from app.encryption import get_public_key_pem
    return {"publicKey": get_public_key_pem()}
