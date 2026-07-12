from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config

from app.core.routes_manifest import Routes, Names, Templates

from app.services.billing_service import get_all_receipts

router = APIRouter()

@router.get(Routes.ADMIN_PAGE_ARCHIVE, name=Names.ARCHIVE_PAGE, response_class=HTMLResponse)
async def archive_page(request: Request):
    receipts = get_all_receipts()
    archived_receipts = [r for r in receipts if r.get("Status") == "ARCHIVED"]
    archived_receipts.reverse()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name=Templates.ARCHIVE, context={
            "receipts": archived_receipts,
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )

