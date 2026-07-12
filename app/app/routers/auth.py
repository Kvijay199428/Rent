from fastapi import APIRouter, Depends, Request, Response, HTTPException, Path
from app.models.auth import LoginRequest, ChangePinRequest
from app.authentication.common.utils import verify_pin, hash_pin
from app.authentication.tenant.jwt import create_tenant_access_token
from app.authentication.tenant.sessions import create_tenant_session, get_tenant_session_db, revoke_tenant_session_db, revoke_all_tenant_sessions
from app.authentication.tenant.cookies import set_tenant_auth_cookies, clear_tenant_auth_cookies
from app.authentication.tenant.middleware import get_current_tenant
from app.database.auth_repository import log_audit
from app.core.db import get_conn
from app.services.tenant_service import load_tenants  # ADD THIS

from app.core.routes_manifest import Routes, Names  # ADD Names import

router = APIRouter(tags=["Authentication"])


def _verify_tenant_view_token(request: Request, view_token: str) -> None:
    """
    Validates that the view_token in the URL path matches the tenant 
    identity from the JWT cookie. Prevents cross-tenant session attacks.
    """
    token = request.cookies.get("tenant_access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Access token missing")
    
    from app.authentication.tenant.jwt import decode_tenant_access_token
    try:
        payload = decode_tenant_access_token(token)
        tenant_id = int(payload.get("tenant_id") or payload.get("sub"))
        
        # Look up tenant's view_token from database
        tenants = load_tenants()
        tenant = next((t for t in tenants if t.id == tenant_id), None)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        if getattr(tenant, "view_token", "") != view_token:
            raise HTTPException(status_code=403, detail="View token mismatch")
            
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid access token")


@router.post(Routes.TENANT_API_AUTH_LOGIN)
async def auth_login(view_token: str, request: Request, response: Response, payload: LoginRequest):
    """Unchanged - login already receives view_token via path"""
    ip = request.client.host if request.client else "Unknown IP"
    
    with get_conn() as conn:
        tenant = conn.execute(
            "SELECT id, tenantpin, failed_attempts, locked_until FROM tenants WHERE view_token = ?", 
            (payload.view_token,)
        ).fetchone()
        
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
            conn.execute(
                "UPDATE tenants SET failed_attempts = ?, locked_until = ? WHERE id = ?", 
                (failed_attempts, locked_until_str, tenant["id"])
            )
            conn.commit()
            
        raise HTTPException(status_code=401, detail="Incorrect PIN.")
        
    # Reset attempts on success
    if tenant["failed_attempts"] > 0:
        with get_conn() as conn:
            conn.execute(
                "UPDATE tenants SET failed_attempts = 0, locked_until = NULL WHERE id = ?", 
                (tenant["id"],)
            )
            conn.commit()
        
    # Generate Session & Tokens
    session_id, refresh_token = create_tenant_session(tenant["id"], request, payload.remember_me)
    access_token = create_tenant_access_token(tenant["id"], session_id)
    
    # Format cookie value correctly for rotation
    cookie_val = f"{session_id}:{refresh_token}"
    set_tenant_auth_cookies(response, access_token, cookie_val, payload.remember_me, request)
    log_audit(tenant["id"], "Login Success", ip)
    
    return {"status": "success", "message": "Logged in successfully"}


@router.post(Routes.TENANT_API_AUTH_REFRESH)
async def auth_refresh(
    view_token: str = Path(..., description="Tenant view token from URL"),
    request: Request = None, 
    response: Response = None
):
    """Tenant Refresh Token Rotation Flow — now requires view_token in path"""
    # Security: Validate URL view_token matches cookie JWT identity
    _verify_tenant_view_token(request, view_token)
    
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


@router.post(Routes.TENANT_API_AUTH_LOGOUT)
async def auth_logout(
    view_token: str = Path(..., description="Tenant view token from URL"),
    request: Request = None, 
    response: Response = None
):
    """Tenant logout — now requires view_token in path"""
    # Security: Validate URL view_token matches cookie JWT identity
    _verify_tenant_view_token(request, view_token)
    
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


@router.post(Routes.TENANT_API_AUTH_LOGOUT_ALL)
async def auth_logout_all(
    view_token: str = Path(..., description="Tenant view token from URL"),
    request: Request = None,
    principal = Depends(get_current_tenant)
):
    """Logout all devices — now requires view_token in path"""
    # Security: Validate URL view_token matches cookie JWT identity
    _verify_tenant_view_token(request, view_token)
    
    revoke_all_tenant_sessions(principal.id)
    return {"status": "success", "message": "All devices logged out"}
    
# from fastapi import APIRouter, Depends, Request, Response, HTTPException
# from app.models.auth import LoginRequest, ChangePinRequest
# from app.authentication.common.utils import verify_pin, hash_pin
# from app.authentication.tenant.jwt import create_tenant_access_token
# from app.authentication.tenant.sessions import create_tenant_session, get_tenant_session_db, revoke_tenant_session_db, revoke_all_tenant_sessions
# from app.authentication.tenant.cookies import set_tenant_auth_cookies, clear_tenant_auth_cookies
# from app.authentication.tenant.middleware import get_current_tenant
# from app.database.auth_repository import log_audit
# from app.core.db import get_conn

# from app.core.routes_manifest import Routes

# router = APIRouter(tags=["Authentication"])

# @router.post(Routes.TENANT_API_AUTH_LOGIN)
# async def auth_login(view_token: str, request: Request, response: Response, payload: LoginRequest):
#     ip = request.client.host if request.client else "Unknown IP"
    
#     with get_conn() as conn:
#         tenant = conn.execute("SELECT id, tenantpin, failed_attempts, locked_until FROM tenants WHERE view_token = ?", (payload.view_token,)).fetchone()
        
#     if not tenant:
#         raise HTTPException(status_code=404, detail="Invalid profile link.")
        
#     from datetime import datetime, timedelta
#     if tenant["locked_until"]:
#         locked_until = datetime.fromisoformat(tenant["locked_until"])
#         if datetime.utcnow() < locked_until:
#             raise HTTPException(status_code=429, detail="Too many failed attempts. Account locked for 15 minutes.")
        
#     if not verify_pin(payload.pin, tenant["tenantpin"]):
#         log_audit(tenant["id"], "Login Failed - Wrong PIN", ip)
        
#         failed_attempts = tenant["failed_attempts"] + 1
#         locked_until_str = None
#         if failed_attempts >= 5:
#             locked_until_str = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
            
#         with get_conn() as conn:
#             conn.execute("UPDATE tenants SET failed_attempts = ?, locked_until = ? WHERE id = ?", (failed_attempts, locked_until_str, tenant["id"]))
#             conn.commit()
            
#         raise HTTPException(status_code=401, detail="Incorrect PIN.")
        
#     # Reset attempts on success
#     if tenant["failed_attempts"] > 0:
#         with get_conn() as conn:
#             conn.execute("UPDATE tenants SET failed_attempts = 0, locked_until = NULL WHERE id = ?", (tenant["id"],))
#             conn.commit()
        
#     # Generate Session & Tokens
#     session_id, refresh_token = create_tenant_session(tenant["id"], request, payload.remember_me)
#     access_token = create_tenant_access_token(tenant["id"], session_id)
    
#     # Format cookie value correctly for rotation
#     cookie_val = f"{session_id}:{refresh_token}"
#     set_tenant_auth_cookies(response, access_token, cookie_val, payload.remember_me, request)
#     log_audit(tenant["id"], "Login Success", ip)
    
#     return {"status": "success", "message": "Logged in successfully"}

# @router.post(Routes.TENANT_API_AUTH_REFRESH)
# async def auth_refresh(request: Request, response: Response):
#     """Tenant Refresh Token Rotation Flow"""
#     refresh_token = request.cookies.get("tenant_refresh_token")
#     if not refresh_token:
#         raise HTTPException(status_code=401, detail="No refresh token")
        
#     parts = refresh_token.split(":")
#     if len(parts) != 2:
#         raise HTTPException(status_code=401, detail="Malformed refresh token")
    
#     session_id, token_secret = parts[0], parts[1]
    
#     session = get_tenant_session_db(session_id)
#     if not session or not verify_pin(token_secret, session["refresh_token_hash"]):
#         revoke_tenant_session_db(session_id)
#         clear_tenant_auth_cookies(response, request)
#         raise HTTPException(status_code=401, detail="Invalid refresh token")
        
#     # Rotate Refresh Token (Invalidate old, issue new)
#     revoke_tenant_session_db(session_id) 
    
#     # Generate new session & tokens
#     new_session_id, new_refresh_token = create_tenant_session(session["tenant_id"], request, remember_me=True)
#     new_access_token = create_tenant_access_token(session["tenant_id"], new_session_id)
    
#     # Format cookie value correctly
#     new_cookie_val = f"{new_session_id}:{new_refresh_token}"
#     set_tenant_auth_cookies(response, new_access_token, new_cookie_val, remember_me=True, request=request)
    
#     return {"status": "success", "message": "Tokens refreshed silently"}

# @router.post(Routes.TENANT_API_AUTH_LOGOUT)
# async def auth_logout(request: Request, response: Response):
#     token = request.cookies.get("tenant_access_token")
#     if token:
#         try:
#             from app.authentication.tenant.jwt import decode_tenant_access_token
#             payload = decode_tenant_access_token(token)
#             revoke_tenant_session_db(payload.get("sid"))
#             log_audit(int(payload.get("tenant_id") or payload.get("sub")), "Logout Success", request.client.host)
#         except Exception:
#             pass
            
#     clear_tenant_auth_cookies(response, request)
#     return {"status": "success"}

# @router.post(Routes.TENANT_API_AUTH_LOGOUT_ALL)
# async def auth_logout_all(principal = Depends(get_current_tenant)):
#     revoke_all_tenant_sessions(principal.id)
#     return {"status": "success", "message": "All devices logged out"}


