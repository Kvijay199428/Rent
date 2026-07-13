from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config

from app.core.routes_manifest import Routes, Names, Templates

from app.services.billing_service import get_all_receipts

router = APIRouter()

@router.get(Routes.ADMINPAGEHISTORY, name=Names.HISTORYPAGE, response_class=HTMLResponse)
async def history_page(request: Request):
    receipts = get_all_receipts()
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

