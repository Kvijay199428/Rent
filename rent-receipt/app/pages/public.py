from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.routes import Names, Templates
from app.services.tenant_service import load_tenants, update_tenant, get_occupants
from app.services.billing_service import get_all_receipts
import os

router = APIRouter()

def _calc_arrears(tenant, tenant_receipts):
    tenant.arrears = 0.0
    active_receipts = [r for r in tenant_receipts if r.get("Status") != "ARCHIVED"]
    if active_receipts:
        latest = active_receipts[-1]
        try:
            grand_total = float(latest.get("Total") or 0.0) + float(latest.get("Previous_Arrears") or 0.0)
            amount_received_str = latest.get("Amount_Received", "")
            if amount_received_str in (None, ""):
                amount_received = grand_total
            else:
                amount_received = float(amount_received_str)
            tenant.arrears = grand_total - amount_received
        except ValueError:
            pass

@router.get("/tenant/{tenant_id}", name=Names.TENANT_PROFILE_PAGE, response_class=HTMLResponse)
async def tenant_profile_page(request: Request, tenant_id: int):
    tenants = load_tenants()
    tenant = next((t for t in tenants if t.id == tenant_id), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    if not getattr(tenant, "view_token", None):
        import uuid
        tenant.view_token = str(uuid.uuid4())
        update_tenant(tenant)
        
    receipts = get_all_receipts()
    tenant_receipts = [r for r in receipts if r["Tenant"] == tenant.name]
    _calc_arrears(tenant, tenant_receipts)
    tenant_receipts.reverse()
    
    occupants = get_occupants(tenant.id)
    
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name=Templates.TENANT_PROFILE, context={
            "tenant": tenant,
            "receipts": tenant_receipts,
            "occupants": occupants, 
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )

@router.get("/t/{view_token}", name=Names.PUBLIC_TENANT_PROFILE_GET, response_class=HTMLResponse)
async def public_tenant_profile_get(request: Request, view_token: str):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "view_token", "") == view_token), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")

    theme = getattr(request.state, "theme", "system")
    unlocked = False
    
    # Check session
    token = request.cookies.get("tenant_access_token")
    if token:
        from app.authentication.tenant.jwt import decode_tenant_access_token
        from app.authentication.tenant.sessions import get_tenant_session_db
        try:
            payload = decode_tenant_access_token(token)
            if payload.get("role") == "tenant" and int(payload.get("tenant_id") or payload.get("sub")) == tenant.id:
                session_id = payload.get("sid")
                if get_tenant_session_db(session_id):
                    unlocked = True
        except Exception:
            pass

    if unlocked:
        receipts = get_all_receipts()
        tenant_receipts = [r for r in receipts if r["Tenant"] == tenant.name and r.get("Status") != "ARCHIVED"]
        tenant_receipts.reverse()
        tenant_receipts = tenant_receipts[:config.get("system.limits.public_history_months", 12)]
        occupants = get_occupants(tenant.id)
        
        return templates.TemplateResponse(
            request=request, name=Templates.TENANT_PUBLIC_PROFILE, context={
                "tenant": tenant,
                "receipts": tenant_receipts,
                "occupants": occupants,
                "theme": theme,
                "unlocked": True,
                "view_token": view_token,
                "sys": getattr(request.state, "sys", config.get("system", {}))
            }
        )
    else:
        return templates.TemplateResponse(
            request=request, name=Templates.TENANT_PUBLIC_PROFILE, context={
                "tenant": tenant,
                "theme": theme,
                "unlocked": False,
                "view_token": view_token,
                "sys": getattr(request.state, "sys", config.get("system", {}))
            }
        )

@router.post("/t/{view_token}", name=Names.PUBLIC_TENANT_PROFILE_POST, response_class=HTMLResponse)
async def public_tenant_profile_post(request: Request, view_token: str, pin: str = Form(...)):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "view_token", "") == view_token), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")
        
    theme = getattr(request.state, "theme", "system")
    actual_pin_hash = getattr(tenant, "tenant_pin", None)
    
    from app.authentication.common.utils import verify_pin
    if not actual_pin_hash or not verify_pin(pin, actual_pin_hash):
        return templates.TemplateResponse(
            request=request, name=Templates.TENANT_PUBLIC_PROFILE, context={
                "tenant": tenant,
                "theme": theme,
                "unlocked": False,
                "view_token": view_token,
                "error": "Incorrect PIN",
                "sys": getattr(request.state, "sys", config.get("system", {}))
            }
        )
        
    # Create tenant session and set authentication cookies
    from app.authentication.tenant.sessions import create_tenant_session
    from app.authentication.tenant.jwt import create_tenant_access_token
    from app.authentication.tenant.cookies import set_tenant_auth_cookies
    from fastapi.responses import RedirectResponse
    
    session_id, refresh_token = create_tenant_session(tenant.id, request, remember_me=False)
    access_token = create_tenant_access_token(tenant.id, session_id)
    
    # Redirect to the profile GET page with PRG pattern
    redirect_url = str(request.url_for(Names.PUBLIC_TENANT_PROFILE_GET, view_token=view_token))
    response = RedirectResponse(url=redirect_url, status_code=303)
    
    # Format cookie value correctly
    cookie_val = f"{session_id}:{refresh_token}"
    set_tenant_auth_cookies(response, access_token, cookie_val, remember_me=False, request=request)
    
    return response

@router.get("/favicon.ico", name=Names.FAVICON, include_in_schema=False)
async def favicon():
    file_path = os.path.join("app", "static", "fevicon.svg")
    return FileResponse(file_path, media_type="image/svg+xml") if os.path.exists(file_path) else HTMLResponse(status_code=204)
