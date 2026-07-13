from fastapi import APIRouter
from app.core.routes_manifest import Names

from app.core.routes_manifest import Routes

from app.core.app_info import APP_INFO
from app.core.config_service import ConfigService



router = APIRouter(tags=["Health"])

@router.get(Routes.HEALTHCHECK, name=Names.HEALTHCHECK)
async def health_check():
    return {
        "status": "ok",
        "application": APP_INFO["name"],
        "version": APP_INFO["version"],
        "schema": APP_INFO["schema"],
        "config_loaded": bool(ConfigService().get("system")),
        "storage_ready": True,  # Monitored at startup
        "database": "SQLite (rent.db)",
        "database_ready": True, 
        "uptime": "N/A" # Trackable if needed
    }

