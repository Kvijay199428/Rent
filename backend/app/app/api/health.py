from fastapi import APIRouter

from app.core.routes_manifest import Names

from app.core.routes_manifest import Routes

from app.core.app_info import APP_INFO
from app.core.config_service import ConfigService
from app.db.connection import check_database


router = APIRouter(tags=["Health"])

@router.get(Routes.HEALTHCHECK, name=Names.HEALTHCHECK)
async def health_check():
    ok, detail = check_database()
    return {
        "status": "ok",
        "application": APP_INFO["name"],
        "version": APP_INFO["version"],
        "schema": APP_INFO["schema"],
        "config_loaded": bool(ConfigService().get("system")),
        "storage_ready": True,
        "database": f"PostgreSQL ({detail})" if ok else f"PostgreSQL (unavailable: {detail})",
        "database_ready": ok,
        "uptime": "N/A",
        "broadcast": ConfigService().get("broadcast", {"enabled": False, "message": "", "type": "info", "dismissible": True})
    }

