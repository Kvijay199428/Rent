from fastapi import Request, HTTPException
from app.authentication.admin.jwt import decode_admin_access_token
from app.authentication.admin.sessions import get_admin_session_db
from app.authentication.common.principal import AuthPrincipal

async def get_current_admin_page(request: Request) -> AuthPrincipal:
    token = request.cookies.get("admin_access_token")
    if not token:
        login_url = str(request.url_for("adminloginpage"))
        raise HTTPException(status_code=303, headers={"Location": login_url})
        
    try:
        payload = decode_admin_access_token(token)
        if payload.get("role") != "admin":
            login_url = str(request.url_for("adminloginpage"))
            raise HTTPException(status_code=303, headers={"Location": login_url})
            
        session_id = payload.get("sid")
        session = get_admin_session_db(session_id)
        if not session:
            login_url = str(request.url_for("adminloginpage"))
            raise HTTPException(status_code=303, headers={"Location": login_url})
            
        admin_id = int(payload.get("admin_id") or payload.get("sub"))
        return AuthPrincipal(
            authentication_type="admin_page",
            role="admin",
            id=admin_id,
            session_id=session_id,
            admin_id=admin_id
        )
    except Exception:
        login_url = str(request.url_for("adminloginpage"))
        raise HTTPException(status_code=303, headers={"Location": login_url})

async def get_current_admin_api(request: Request) -> AuthPrincipal:
    token = request.cookies.get("admin_access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    try:
        payload = decode_admin_access_token(token)
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
            
        session_id = payload.get("sid")
        session = get_admin_session_db(session_id)
        if not session:
            raise HTTPException(status_code=401, detail="Session revoked")
            
        admin_id = int(payload.get("admin_id") or payload.get("sub"))
        return AuthPrincipal(
            authentication_type="admin_api",
            role="admin",
            id=admin_id,
            session_id=session_id,
            admin_id=admin_id
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized: Token expired or invalid")
