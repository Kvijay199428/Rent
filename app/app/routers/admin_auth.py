from fastapi import datastructures
from fastapi import APIRouter, Depends, Request, Response, Form, HTTPException

from app.core.routes_manifest import Routes, Names

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

# router = APIRouter(tags=["Admin Authentication"])
router = APIRouter()

# ─── Request Models ────────────────────────────────────────────────

class EncryptedPayload(BaseModel):
    encryptedKey: str
    encryptedData: str
    nonce: str
    remember_me: bool = False


# ─── Setup & User Creation ───────────────────────────────────────────

@router.get(Routes.ADMINAPISETUPREQUIRED, name=Names.ADMINSETUPREQUIRED)
async def check_setup_required():
    """Check if admin setup is required (no admin exists yet)."""
    return {
        "setup_required": not admin_exists(),
        "message": "No admin user found. Please create an admin account to continue." if not admin_exists() else "Admin account exists."
    }

@router.post(Routes.ADMINAPISETUPCREATE, name=Names.ADMINSETUPCREATE)
async def create_first_admin(req: EncryptedPayload):
    """Create the first admin user (only works when no admins exist)."""
    if admin_exists():
        raise HTTPException(status_code=403, detail="Admin user already exists. Use the settings page to manage admins.")
    
    try:
        decrypted = decrypt_payload(req.encryptedKey, req.encryptedData, req.nonce)
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

# ─── Login Flow ────────────────────────────────────────────────────

@router.post(Routes.ADMINAPIAUTHLOGIN, name=Names.ADMINLOGIN)
async def admin_login(request: Request, login_req: EncryptedPayload):
    """Standard admin login (requires TOTP if configured)."""
    try:
        decrypted = decrypt_payload(login_req.encryptedKey, login_req.encryptedData, login_req.nonce)
        username = decrypted.get("username", "")
        password = decrypted.get("password", "")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid encrypted payload")

    admin = get_admin_by_username(username)
    
    if not admin or not verify_pin(password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    
    # If TOTP is configured, require it
    if admin["totp_secret"]:
        return {
            "status": "totp_required",
            "message": "TOTP verification required.",
            "username": username
        }
    
    # No TOTP - proceed with login (fallback for legacy or initial setup)
    session_id, refresh_token = create_admin_session(admin['id'], request, login_req.remember_me)
    access_token = create_admin_access_token(admin['id'], session_id)
    
    cookie_val = f"{session_id}:{refresh_token}"
    
    response = JSONResponse({
        "status": "success",
        "message": "Login successful",
        "admin_id": admin['id'],
        "username": admin['username']
    })
    set_admin_auth_cookies(response, access_token, cookie_val, login_req.remember_me, request)
    
    return response

@router.post(Routes.ADMINAPIAUTHLOGINTOTP, name=Names.ADMINLOGINTOTP)
async def admin_login_with_totp(request: Request, login_req: EncryptedPayload):
    """Complete login with TOTP verification."""
    try:
        decrypted = decrypt_payload(login_req.encryptedKey, login_req.encryptedData, login_req.nonce)
        username = decrypted.get("username", "")
        password = decrypted.get("password", "")
        totp_token = decrypted.get("totp_token", "")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid encrypted payload")

    admin = get_admin_by_username(username)
    
    if not admin or not verify_pin(password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    
    if not admin["totp_secret"]:
        raise HTTPException(status_code=400, detail="TOTP not configured for this account.")
    
    if not verify_totp(admin["totp_secret"], totp_token):
        raise HTTPException(status_code=401, detail="Invalid TOTP code. Please try again.")
    
    session_id, refresh_token = create_admin_session(admin['id'], request, login_req.remember_me)
    access_token = create_admin_access_token(admin['id'], session_id)
    
    cookie_val = f"{session_id}:{refresh_token}"
    
    response = JSONResponse({
        "status": "success",
        "message": "Login successful",
        "admin_id": admin['id'],
        "username": admin['username']
    })
    set_admin_auth_cookies(response, access_token, cookie_val, login_req.remember_me, request)
    
    return response

# ─── Forgot Password ───────────────────────────────────────────────

@router.post(Routes.ADMINAPIPASSWORDFORGOTVERIFY, name=Names.ADMINFORGOTVERIFY)
async def verify_forgot_password(req: EncryptedPayload):
    """Verify username and TOTP for password reset."""
    try:
        decrypted = decrypt_payload(req.encryptedKey, req.encryptedData, req.nonce)
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

@router.post(Routes.ADMINAPIPASSWORDFORGOTRESET, name=Names.ADMINFORGOTRESET)
async def reset_password(req: EncryptedPayload):
    """Reset password after TOTP verification."""
    try:
        decrypted = decrypt_payload(req.encryptedKey, req.encryptedData, req.nonce)
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

# ─── Refresh Token ─────────────────────────────────────────────────

@router.post(Routes.ADMINAPIAUTHREFRESH)
async def admin_refresh(request: Request, response: Response):
    """Admin Refresh Token Rotation Flow"""
    refresh_token = request.cookies.get("admin_refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
        
    parts = refresh_token.split(":")
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="Malformed refresh token")
    
    session_id, token_secret = parts[0], parts[1]
    
    session = get_admin_session_db(session_id)
    if not session or not verify_pin(token_secret, session["refresh_token_hash"]):
        revoke_admin_session_db(session_id)
        clear_admin_auth_cookies(response, request)
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    revoke_admin_session_db(session_id) 
    
    new_session_id, new_refresh_token = create_admin_session(session["admin_id"], request, remember_me=True)
    new_access_token = create_admin_access_token(session["admin_id"], new_session_id)
    
    new_cookie_val = f"{new_session_id}:{new_refresh_token}"
    set_admin_auth_cookies(response, new_access_token, new_cookie_val, remember_me=True, request=request)
    
    return {"status": "success", "message": "Admin tokens refreshed silently"}

# ─── Logout ────────────────────────────────────────────────────────

@router.get(Routes.ADMINPAGELOGOUT, name=Names.ADMINLOGOUT)
async def ADMINLOGOUT(request: Request):
    """Logs the admin out and clears cookies"""
    token = request.cookies.get("admin_access_token")
    if token:
        try:
            from app.authentication.admin.jwt import decode_admin_access_token
            payload = decode_admin_access_token(token)
            revoke_admin_session_db(payload.get("sid"))
        except Exception:
            pass
            
    root_path = request.scope.get("root_path", "")
    login_url = f"{root_path}/admin/login"
    response = RedirectResponse(url=login_url, status_code=303)
    clear_admin_auth_cookies(response, request)
    return response

@router.post(Routes.ADMINAPIAUTHLOGOUT, name=Names.ADMINLOGOUTJSON)
async def ADMINLOGOUTJSON(request: Request, response: Response):
    """Logs the admin out via JSON request"""
    token = request.cookies.get("admin_access_token")
    if token:
        try:
            from app.authentication.admin.jwt import decode_admin_access_token
            payload = decode_admin_access_token(token)
            revoke_admin_session_db(payload.get("sid"))
        except Exception:
            pass
            
    clear_admin_auth_cookies(response, request)
    return {"status": "success"}

# ─── Current User & TOTP Management ──────────────────────────────────

from app.authentication.admin.middleware import get_current_admin_api
from app.core.routes_manifest import Routes

@router.get(Routes.ADMINAPIAUTHME, name=Names.ADMINME)
async def ADMINME(admin: dict = Depends(get_current_admin_api)):
    """Returns the current admin session info"""
    admin_data = get_admin_by_id(admin.id)
    if not admin_data:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    return {
        "admin": {
            "id": admin_data["id"],
            "username": admin_data["username"],
            "email": admin_data["email"] or ""
        }
    }

@router.get(Routes.ADMINAPITOTPQR, name=Names.ADMINTOTPQR)
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

@router.post(Routes.ADMINAPITOTPREGENERATE, name=Names.ADMINTOTPREGENERATE)
async def regenerate_totp(req: EncryptedPayload, admin: dict = Depends(get_current_admin_api)):
    """Regenerate TOTP secret (requires password confirmation)."""
    admin_data = get_admin_by_id(admin.id)
    if not admin_data:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    try:
        decrypted = decrypt_payload(req.encryptedKey, req.encryptedData, req.nonce)
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

@router.get(Routes.ADMINAPIAUTHPUBLICKEY, name=Names.ADMINPUBLICKEY)
async def admin_public_key():
    from app.encryption import get_public_key_pem
    return {"publicKey": get_public_key_pem()}
