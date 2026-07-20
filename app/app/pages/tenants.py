from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config

from app.core.routes_manifest import Routes, Names, Templates

from app.services.tenant_service import load_tenants
from app.services.billing_service import get_all_receipts

router = APIRouter()

@router.get(Routes.ADMINPAGETENANTS, name=Names.TENANTSPAGE, response_class=HTMLResponse)
async def tenants_page(request: Request):
    tenants = load_tenants(include_archived=False)
    receipts = get_all_receipts(include_archived_tenants=False)
    
    for tenant in tenants:
        active_receipts = [r for r in receipts if int(r.get("TenantId", 0) or 0) == tenant.id and r.get("Status") != "ARCHIVED"]
        if active_receipts:
            latest = active_receipts[-1]
            try:
                grandTotal = float(latest.get("Total") or 0.0) + float(latest.get("previousArrears") or 0.0)
                amountReceived_str = latest.get("amountReceived", "")
                if amountReceived_str in (None, ""):
                    amountReceived = grandTotal
                else:
                    amountReceived = float(amountReceived_str)
                tenant.arrears = grandTotal - amountReceived
            except ValueError:
                tenant.arrears = 0.0
        else:
            tenant.arrears = 0.0

    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name=Templates.TENANTS, context={
            "tenants": tenants,
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )

