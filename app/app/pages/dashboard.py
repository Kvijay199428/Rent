from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config

from app.core.routes_manifest import Routes, Names, Templates

from app.services.billing_service import get_dashboard_stats

router = APIRouter()

@router.get(Routes.ADMIN_PAGE_ROOT, name=Names.HOME, response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = get_dashboard_stats()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request,
        name=Templates.DASHBOARD,
        context={
            "stats": stats,
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )

