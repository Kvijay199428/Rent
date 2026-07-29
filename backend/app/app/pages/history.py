from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config

from app.core.routes_manifest_landlord import LandlordRoutes as Routes, LandlordNames as Names, LandlordTemplates as Templates

from app.services.billing_service import get_all_receipts

router = APIRouter()

@router.get(Routes.LANDLORDPAGEHISTORY, name=Names.HISTORYPAGE, response_class=HTMLResponse)
async def history_page(request: Request):
    receipts = get_all_receipts(include_archived_tenants=False)
    active_receipts = [r for r in receipts if r.get("Status", "ACTIVE") == "ACTIVE"]
    active_receipts.reverse()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name=Templates.HISTORY, context={
            "receipts": active_receipts,
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )

