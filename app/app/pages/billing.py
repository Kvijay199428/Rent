from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config

from app.core.routes_manifest import Routes, Names, Templates

from app.services.tenant_service import load_tenants
from app.services.billing_service import get_all_receipts

router = APIRouter()

@router.get(Routes.ADMINPAGEBILLING, name=Names.BILLINGPAGE, response_class=HTMLResponse)
async def billing_page(request: Request):
    tenants = [t for t in load_tenants() if t.status == "Active"]
    theme = getattr(request.state, "theme", "system")
    receipts_list = get_all_receipts()
    active_receipts = [r for r in receipts_list if r.get("Status", "ACTIVE") == "ACTIVE"]

    return templates.TemplateResponse(
        request=request,
        name=Templates.BILLING,
        context={
            "receipts": active_receipts,
            "tenants": tenants,
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )

