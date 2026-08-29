from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config

from app.core.routes_manifest_landlord import LandlordRoutes as Routes, LandlordNames as Names, LandlordTemplates as Templates

from app.services.tenant_service import load_tenants
from app.services.payment_service import get_tenant_outstanding_balance

router = APIRouter()

@router.get(Routes.LANDLORDPAGETENANTS, name=Names.TENANTSPAGE, response_class=HTMLResponse)
async def tenants_page(request: Request):
    tenants = load_tenants(include_archived=False)

    for tenant in tenants:
        # Backend is the source of truth: Σ current charges − Σ payments.
        tenant.arrears = get_tenant_outstanding_balance(tenant.id)

    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name=Templates.TENANTS, context={
            "tenants": tenants,
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )

