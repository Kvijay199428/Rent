# // File: app\app\api\settings.py
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends

from app.core.routes_manifest_landlord import LandlordRoutes as Routes, LandlordNames as Names

from pydantic import BaseModel
import os
import datetime

from app.core.config_service import config
from app.core.db import get_conn
from app.services.signature_service import save_signature, delete_signature
from app.services.backup_service import create_full_backup
from app.authentication.landlord.middleware import get_current_landlord_api

router = APIRouter(tags=["Settings"])

@router.get(Routes.LANDLORDAPICONFIGGET, name=Names.APIGETCONFIG)
async def api_get_config(landlordUuid: str, principal=Depends(get_current_landlord_api)):
    return {
        "landlord": config.get("landlord", {}),
        "billing": config.get("billing", {}),
        "ui": config.get("ui", {}),
        "backup": config.get("backup", {}),
        "whatsapp": config.get("whatsapp", {}),
        "system": config.get("system", {}),
        "broadcast": config.get("broadcast", {"enabled": False, "message": "", "type": "info", "dismissible": True})
    }

@router.post(Routes.LANDLORDAPISETTINGSUPLOADSIGNATURE, name=Names.APIUPLOADSIGNATURE)
async def api_upload_signature(landlordUuid: str, file: UploadFile = File(...), principal=Depends(get_current_landlord_api)):
    sys_conf = config.get("system", {})
    max_mb = config.get("system.limits.max_upload_size_mb", 2)
    max_bytes = max_mb * 1024 * 1024

    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large (Max {max_mb}MB)")
    path = save_signature(contents, file.filename)
    if not path:
        raise HTTPException(status_code=500, detail="Failed to process signature image")

    filename = os.path.basename(path)
    config.save("landlord", {"signature_image": filename})

    return {"status": "success", "path": filename}

@router.delete(Routes.LANDLORDAPISETTINGSDELETESIGNATURE, name=Names.APIDELETESIGNATURE)
async def api_delete_signature(landlordUuid: str, principal=Depends(get_current_landlord_api)):
    delete_signature()
    config.save("landlord", {"signature_image": ""})
    return {"status": "success"}

class ConfigUpdateModel(BaseModel):
    landlord: dict
    billing: dict
    whatsapp: dict = {}
    backup: dict = {}
    system: dict | None = None

@router.post(Routes.LANDLORDAPICONFIGUPDATE, name=Names.UPDATECONFIG)
async def update_config(landlordUuid: str, data: ConfigUpdateModel, background_tasks: BackgroundTasks, principal=Depends(get_current_landlord_api)):
    background_tasks.add_task(create_full_backup, tag="settings_change")

    config.save("landlord", data.landlord)
    config.save("billing", data.billing)

    if data.whatsapp:
        config.save("whatsapp", data.whatsapp)

    if data.backup:
        config.save("backup", data.backup)

    if data.system:
        config.save("system", data.system)

    return {"status": "success"}


# ── Per-landlord theme storage ────────────────────────────────────────────────

def _load_landlord_theme(landlord_uuid: str) -> str:
    """Load theme preference for a specific landlord."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT theme FROM landlord_ui_config WHERE landlorduuid = ?",
            (landlord_uuid,),
        ).fetchone()
    return row["theme"] if row else "system"


def _save_landlord_theme(landlord_uuid: str, theme: str) -> None:
    """Save theme preference for a specific landlord (upsert)."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO landlord_ui_config (landlorduuid, theme, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(landlorduuid) DO UPDATE SET theme = ?, updated_at = ?""",
            (landlord_uuid, theme, now, theme, now),
        )
        conn.commit()


@router.get(Routes.LANDLORDAPICONFIGTHEMEGET, name="landlord_get_theme")
async def get_theme(landlordUuid: str, principal=Depends(get_current_landlord_api)):
    """Return the theme preference for the authenticated landlord."""
    theme = _load_landlord_theme(landlordUuid)
    return {"status": "success", "theme": theme}


@router.post(Routes.LANDLORDAPICONFIGTHEME, name=Names.UPDATETHEME)
async def update_theme(landlordUuid: str, data: dict, principal=Depends(get_current_landlord_api)):
    """Save the theme preference for the authenticated landlord."""
    theme = data.get("theme", "system")
    _save_landlord_theme(landlordUuid, theme)
    return {"status": "success", "theme": theme, "effective_theme": theme}
