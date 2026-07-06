from fastapi import APIRouter, Depends, Request, Response, HTTPException
from app.models.auth import LoginRequest, ChangePinRequest
from app.authentication.common.utils import verify_pin, hash_pin
from app.authentication.tenant.jwt import create_tenant_access_token
from app.authentication.tenant.sessions import create_tenant_session, get_tenant_session_db, revoke_tenant_session_db, revoke_all_tenant_sessions
from app.authentication.tenant.cookies import set_tenant_auth_cookies, clear_tenant_auth_cookies
from app.authentication.tenant.middleware import get_current_tenant
from app.database.auth_repository import log_audit
from app.core.db import get_conn

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login")
async def auth_login(request: Request, response: Response, payload: LoginRequest):
    ip = request.client.host if request.client else "Unknown IP"
    
    with get_conn() as conn:
        tenant = conn.execute("SELECT id, tenantpin, failed_attempts, locked_until FROM tenants WHERE viewtoken = ?", (payload.view_token,)).fetchone()
        
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid profile link.")
        
    from datetime import datetime, timedelta
    if tenant["locked_until"]:
        locked_until = datetime.fromisoformat(tenant["locked_until"])
        if datetime.utcnow() < locked_until:
            raise HTTPException(status_code=429, detail="Too many failed attempts. Account locked for 15 minutes.")
        
    if not verify_pin(payload.pin, tenant["tenantpin"]):
        log_audit(tenant["id"], "Login Failed - Wrong PIN", ip)
        
        failed_attempts = tenant["failed_attempts"] + 1
        locked_until_str = None
        if failed_attempts >= 5:
            locked_until_str = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
            
        with get_conn() as conn:
            conn.execute("UPDATE tenants SET failed_attempts = ?, locked_until = ? WHERE id = ?", (failed_attempts, locked_until_str, tenant["id"]))
            conn.commit()
            
        raise HTTPException(status_code=401, detail="Incorrect PIN.")
        
    # Reset attempts on success
    if tenant["failed_attempts"] > 0:
        with get_conn() as conn:
            conn.execute("UPDATE tenants SET failed_attempts = 0, locked_until = NULL WHERE id = ?", (tenant["id"],))
            conn.commit()
        
    # Generate Session & Tokens
    session_id, refresh_token = create_tenant_session(tenant["id"], request, payload.remember_me)
    access_token = create_tenant_access_token(tenant["id"], session_id)
    
    # Format cookie value correctly for rotation
    cookie_val = f"{session_id}:{refresh_token}"
    set_tenant_auth_cookies(response, access_token, cookie_val, payload.remember_me, request)
    log_audit(tenant["id"], "Login Success", ip)
    
    return {"status": "success", "message": "Logged in successfully"}

@router.post("/refresh")
async def auth_refresh(request: Request, response: Response):
    """Tenant Refresh Token Rotation Flow"""
    refresh_token = request.cookies.get("tenant_refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
        
    parts = refresh_token.split(":")
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="Malformed refresh token")
    
    session_id, token_secret = parts[0], parts[1]
    
    session = get_tenant_session_db(session_id)
    if not session or not verify_pin(token_secret, session["refresh_token_hash"]):
        revoke_tenant_session_db(session_id)
        clear_tenant_auth_cookies(response, request)
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    # Rotate Refresh Token (Invalidate old, issue new)
    revoke_tenant_session_db(session_id) 
    
    # Generate new session & tokens
    new_session_id, new_refresh_token = create_tenant_session(session["tenant_id"], request, remember_me=True)
    new_access_token = create_tenant_access_token(session["tenant_id"], new_session_id)
    
    # Format cookie value correctly
    new_cookie_val = f"{new_session_id}:{new_refresh_token}"
    set_tenant_auth_cookies(response, new_access_token, new_cookie_val, remember_me=True, request=request)
    
    return {"status": "success", "message": "Tokens refreshed silently"}

@router.post("/logout")
async def auth_logout(request: Request, response: Response):
    token = request.cookies.get("tenant_access_token")
    if token:
        try:
            from app.authentication.tenant.jwt import decode_tenant_access_token
            payload = decode_tenant_access_token(token)
            revoke_tenant_session_db(payload.get("sid"))
            log_audit(int(payload.get("tenant_id") or payload.get("sub")), "Logout Success", request.client.host)
        except Exception:
            pass
            
    clear_tenant_auth_cookies(response, request)
    return {"status": "success"}

@router.post("/logout-all")
async def auth_logout_all(principal = Depends(get_current_tenant)):
    revoke_all_tenant_sessions(principal.id)
    return {"status": "success", "message": "All devices logged out"}