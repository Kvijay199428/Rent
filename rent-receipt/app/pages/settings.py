from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config
from app.core.routes import Names, Templates

router = APIRouter()

@router.get("/settings", name=Names.SETTINGS_PAGE, response_class=HTMLResponse)
async def settings_page(request: Request):
    billing_conf = config.get("billing", {})
    landlord_conf = config.get("landlord", {})
    ui_conf = config.get("ui", {})
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name=Templates.SETTINGS, context={
            "billing_config": billing_conf,
            "landlord_config": landlord_conf,
            "ui_config": ui_conf,
            "backup_config": config.get("backup", {}),
            "whatsapp_config": config.get("whatsapp", {}),
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )

# --- REST API ---

