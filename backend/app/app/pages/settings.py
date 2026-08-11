from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config

from app.core.routes_manifest_landlord import LandlordRoutes as Routes, LandlordNames as Names, LandlordTemplates as Templates

router = APIRouter()

@router.get(Routes.LANDLORDPAGESETTINGS, name=Names.SETTINGSPAGE, response_class=HTMLResponse)
async def settings_page(request: Request):
    from app.authentication.landlord.middleware import extract_landlord_id
    from app.services.landlord_config_service import get_effective_landlord_config
    billing_conf = config.get("billing", {})
    landlord_conf = get_effective_landlord_config(extract_landlord_id(request))
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

