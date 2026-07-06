from fastapi import Request, HTTPException
from app.authentication.tenant.jwt import decode_tenant_access_token
from app.authentication.tenant.sessions import get_tenant_session_db
from app.authentication.common.principal import AuthPrincipal

async def get_current_tenant(request: Request) -> AuthPrincipal:
    token = request.cookies.get("tenant_access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Access token missing. Requires refresh.")
    
    try:
        payload = decode_tenant_access_token(token)
        if payload.get("role") != "tenant":
            raise HTTPException(status_code=403, detail="Forbidden: Tenant access required")
            
        session_id = payload.get("sid")
        session = get_tenant_session_db(session_id)
        if not session:
             raise HTTPException(status_code=401, detail="Session revoked")
             
        tenant_id = int(payload.get("tenant_id") or payload.get("sub"))
        return AuthPrincipal(
            authentication_type="tenant_api",
            role="tenant",
            id=tenant_id,
            session_id=session_id,
            tenant_id=tenant_id
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Access token expired. Requires refresh.")
