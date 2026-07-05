from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config
from app.core.routes import Names, Templates

router = APIRouter()

@router.get("/backups", name=Names.BACKUPS_PAGE, response_class=HTMLResponse)
async def backups_page(request: Request):
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name=Templates.BACKUPS, context={
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )
