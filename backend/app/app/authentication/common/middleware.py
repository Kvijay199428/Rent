from fastapi import Request, HTTPException
from app.authentication.admin.middleware import get_current_admin_api
from app.authentication.tenant.middleware import get_current_tenant
from app.authentication.common.principal import AuthPrincipal

async def get_admin_or_tenant(request: Request) -> AuthPrincipal:
    """Dependency that allows either an Admin or a Tenant. Returns the corresponding AuthPrincipal."""
    # Try Admin first
    try:
        principal = await get_current_admin_api(request)
        return principal
    except HTTPException:
        pass
        
    # Try Tenant next
    try:
        principal = await get_current_tenant(request)
        return principal
    except HTTPException:
        pass
        
    raise HTTPException(status_code=401, detail="Unauthorized: Must be logged in as admin or tenant")

