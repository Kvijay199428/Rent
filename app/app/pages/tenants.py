from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config

from app.core.routes_manifest import Routes, Names, Templates

from app.services.tenant_service import load_tenants
from app.services.billing_service import get_all_receipts

router = APIRouter()

@router.get(Routes.ADMIN_PAGE_TENANTS, name=Names.TENANTS_PAGE, response_class=HTMLResponse)
async def tenants_page(request: Request):
    tenants = load_tenants()
    receipts = get_all_receipts()
    
    for tenant in tenants:
        active_receipts = [r for r in receipts if r["Tenant"] == tenant.name and r.get("Status") != "ARCHIVED"]
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

