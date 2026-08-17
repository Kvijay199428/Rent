from fastapi import APIRouter, Depends, Request, Response, HTTPException, Path
from app.models.auth import LoginRequest, ChangePinRequest
from app.authentication.common.utils import verify_pin, hash_pin
from app.authentication.tenant.jwt import create_access_token
from app.authentication.tenant.sessions import create_tenant_session, get_tenant_session_db, revoke_tenant_session_db, revoke_all_tenant_sessions
from app.authentication.tenant.cookies import set_tenant_auth_cookies, clear_tenant_auth_cookies
from app.authentication.tenant.middleware import get_current_tenant
from app.database.auth_repository import log_audit
from app.core.db import get_conn
from app.services.tenant_service import load_tenants  # ADD THIS

from app.core.routes_manifest_tenant import TenantRoutes, TenantNames

router = APIRouter(tags=["Authentication"])


def _tenant_viewtoken_guard(request: Request, tenantId: int, viewToken: str, propertyId: int, require_token: bool = True):
    """Resolve the tenant whose viewToken matches, verify the requested
    property, and confirm the JWT-cookie identity binds to it. Raises on any
    mismatch so the URL scoping (property → tenant → viewToken → session)
    cannot be crossed.

    When ``require_token`` is False the access-token identity binding is
    skipped for expired/missing tokens; the caller must then bind identity
    another way (e.g. from the refresh-cookie session). The URL-scoping
    checks (tenant exists, viewToken and property match) are always enforced.
    """
    token = request.cookies.get("access_token")
    if token:
        from app.authentication.tenant.jwt import decode_access_token
        try:
            payload = decode_access_token(token)
            cookie_tenant_id = int(payload.get("tenantId") or payload.get("sub"))
        except Exception:
            cookie_tenant_id = None
    else:
        cookie_tenant_id = None

    tenants = load_tenants(include_archived=True)
    tenant = next((t for t in tenants if t.id == tenantId), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if getattr(tenant, "viewToken", "") != viewToken:
        raise HTTPException(status_code=403, detail="View token mismatch")
    if int(getattr(tenant, "propertyId", 0) or 0) != int(propertyId or 0):
        raise HTTPException(status_code=403, detail="Property mismatch")
    if cookie_tenant_id is not None and cookie_tenant_id != tenantId:
        raise HTTPException(status_code=403, detail="Tenant identity mismatch")
    if require_token and cookie_tenant_id is None:
        raise HTTPException(
            status_code=401,
            detail="Access token missing or invalid" if not token else "Invalid access token",
        )
    return tenant


@router.post("/t/{propertyId}/{tenantId}/{viewToken}/api/auth/refresh", include_in_schema=False)
@router.post(TenantRoutes.TENANTAPIAUTHREFRESH)
async def auth_refresh(
    propertyId: int = Path(...),
    tenantId: int = Path(...),
    viewToken: str = Path(..., description="Tenant view token from URL"),
    request: Request = None, 
    response: Response = None
):
    """Tenant Refresh Token Rotation Flow — now requires viewToken in path"""
    # Security: Validate URL property/tenant/viewToken is self-consistent.
    # The access token may already be expired here — identity is bound via the
    # refresh-cookie session below.
    _tenant_viewtoken_guard(request, tenantId, viewToken, propertyId, require_token=False)
    
    refresh_token = request.cookies.get("refresh_token")
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

    if int(session["tenantId"] or 0) != tenantId:
        revoke_tenant_session_db(session_id)
        clear_tenant_auth_cookies(response, request)
        raise HTTPException(status_code=403, detail="Tenant identity mismatch")
        
    # Rotate Refresh Token (Invalidate old, issue new)
    revoke_tenant_session_db(session_id) 
    
    # Generate new session & tokens
    new_session_id, new_refresh_token = create_tenant_session(session["tenantId"], request, remember_me=True)
    new_access_token = create_access_token(session["tenantId"], new_session_id)
    
    # Format cookie value correctly
    new_cookie_val = f"{new_session_id}:{new_refresh_token}"
    set_tenant_auth_cookies(response, new_access_token, new_cookie_val, remember_me=True, request=request)

    ip = request.client.host if request.client else "Unknown"
    log_audit(session["tenantId"], "Token Refreshed", ip)
    
    return {"status": "success", "message": "Tokens refreshed silently"}


@router.post("/t/{propertyId}/{tenantId}/{viewToken}/api/auth/logout", include_in_schema=False)
@router.post(TenantRoutes.TENANTAPIAUTHLOGOUT)
async def auth_logout(
    propertyId: int = Path(...),
    tenantId: int = Path(...),
    viewToken: str = Path(..., description="Tenant view token from URL"),
    request: Request = None, 
    response: Response = None
):
    """Tenant logout — now requires viewToken in path"""
    # Security: Validate URL property/tenant/viewToken is self-consistent.
    # Allow logout with an expired access token so stale sessions can still be
    # cleared; revoke the session from either cookie.
    _tenant_viewtoken_guard(request, tenantId, viewToken, propertyId, require_token=False)
    
    token = request.cookies.get("access_token")
    if token:
        try:
            from app.authentication.tenant.jwt import decode_access_token
            payload = decode_access_token(token)
            revoke_tenant_session_db(payload.get("sid"))
            log_audit(int(payload.get("tenantId") or payload.get("sub")), "Logout Success", request.client.host)
        except Exception:
            pass
    else:
        refresh_cookie = request.cookies.get("refresh_token")
        if refresh_cookie and ":" in refresh_cookie:
            session_id = refresh_cookie.split(":", 1)[0]
            revoke_tenant_session_db(session_id)
            
    clear_tenant_auth_cookies(response, request)
    return {"status": "success"}


@router.post("/t/{propertyId}/{tenantId}/{viewToken}/api/auth/logout-all", include_in_schema=False)
@router.post(TenantRoutes.TENANTAPIAUTHLOGOUTALL)
async def auth_logout_all(
    propertyId: int = Path(...),
    tenantId: int = Path(...),
    viewToken: str = Path(..., description="Tenant view token from URL"),
    request: Request = None,
    principal = Depends(get_current_tenant)
):
    """Logout all devices — now requires viewToken in path"""
    # Security: Validate URL property/tenant/viewToken matches cookie JWT identity
    _tenant_viewtoken_guard(request, tenantId, viewToken, propertyId)
    
    revoke_all_tenant_sessions(principal.id)

    ip = request.client.host if request.client else "Unknown"
    log_audit(principal.id, "Logout All Devices", ip)

    return {"status": "success", "message": "All devices logged out"}
    
# from fastapi import APIRouter, Depends, Request, Response, HTTPException
# from app.models.auth import LoginRequest, ChangePinRequest
# from app.authentication.common.utils import verify_pin, hash_pin
# from app.authentication.tenant.jwt import create_access_token
# from app.authentication.tenant.sessions import create_tenant_session, get_tenant_session_db, revoke_tenant_session_db, revoke_all_tenant_sessions
# from app.authentication.tenant.cookies import set_tenant_auth_cookies, clear_tenant_auth_cookies
# from app.authentication.tenant.middleware import get_current_tenant
# from app.database.auth_repository import log_audit
# from app.core.db import get_conn

# from app.core.routes_manifest import Routes

# router = APIRouter(tags=["Authentication"])

# @router.post(Routes.TENANTAPIAUTHLOGIN)
# async def auth_login(viewToken: str, request: Request, response: Response, payload: LoginRequest):
#     ip = request.client.host if request.client else "Unknown IP"
    
#     with get_conn() as conn:
#         tenant = conn.execute("SELECT id, tenantpin, failed_attempts, locked_until FROM tenants WHERE viewToken = ?", (payload.viewToken,)).fetchone()
        
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
#     access_token = create_access_token(tenant["id"], session_id)
    
#     # Format cookie value correctly for rotation
#     cookie_val = f"{session_id}:{refresh_token}"
#     set_tenant_auth_cookies(response, access_token, cookie_val, payload.remember_me, request)
#     log_audit(tenant["id"], "Login Success", ip)
    
#     return {"status": "success", "message": "Logged in successfully"}

# @router.post(Routes.TENANTAPIAUTHREFRESH)
# async def auth_refresh(request: Request, response: Response):
#     """Tenant Refresh Token Rotation Flow"""
#     refresh_token = request.cookies.get("refresh_token")
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
#     new_session_id, new_refresh_token = create_tenant_session(session["tenantId"], request, remember_me=True)
#     new_access_token = create_access_token(session["tenantId"], new_session_id)
    
#     # Format cookie value correctly
#     new_cookie_val = f"{new_session_id}:{new_refresh_token}"
#     set_tenant_auth_cookies(response, new_access_token, new_cookie_val, remember_me=True, request=request)
    
#     return {"status": "success", "message": "Tokens refreshed silently"}

# @router.post(Routes.TENANTAPIAUTHLOGOUT)
# async def auth_logout(request: Request, response: Response):
#     token = request.cookies.get("access_token")
#     if token:
#         try:
#             from app.authentication.tenant.jwt import decode_access_token
#             payload = decode_access_token(token)
#             revoke_tenant_session_db(payload.get("sid"))
#             log_audit(int(payload.get("tenantId") or payload.get("sub")), "Logout Success", request.client.host)
#         except Exception:
#             pass
            
#     clear_tenant_auth_cookies(response, request)
#     return {"status": "success"}

# @router.post(Routes.TENANTAPIAUTHLOGOUTALL)
# async def auth_logout_all(principal = Depends(get_current_tenant)):
#     revoke_all_tenant_sessions(principal.id)
#     return {"status": "success", "message": "All devices logged out"}


