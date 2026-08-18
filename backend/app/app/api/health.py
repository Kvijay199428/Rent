from fastapi import APIRouter
from app.core.routes_manifest import Names

from app.core.routes_manifest import Routes

from app.core.app_info import APP_INFO
from app.core.config_service import ConfigService



router = APIRouter(tags=["Health"])

@router.get(Routes.HEALTHCHECK, name=Names.HEALTHCHECK)
async def health_check():
    from app.services.cacheservice import cache_stats
    redis_info = cache_stats()
    return {
        "status": "ok",
        "application": APP_INFO["name"],
        "version": APP_INFO["version"],
        "schema": APP_INFO["schema"],
        "config_loaded": bool(ConfigService().get("system")),
        "storage_ready": True,
        "database": "SQLite (rent.db)",
        "database_ready": True,
        "cache": redis_info,
        "uptime": "N/A",
        "broadcast": ConfigService().get("broadcast", {"enabled": False, "message": "", "type": "info", "dismissible": True})
    }

