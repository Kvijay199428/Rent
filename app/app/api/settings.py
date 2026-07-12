# // File: app\app\api\settings.py
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks

from app.core.routes_manifest import Names, Routes

from pydantic import BaseModel
import os

from app.core.config_service import config
from app.services.signature_service import save_signature, delete_signature
from app.services.backup_service import create_full_backup

router = APIRouter(tags=["Settings"])

@router.get(Routes.ADMIN_API_CONFIG_GET, name=Names.API_GET_CONFIG)
async def api_get_config():
    return {
        "landlord": config.get("landlord", {}),
        "billing": config.get("billing", {}),
        "ui": config.get("ui", {}),
        "backup": config.get("backup", {}),
        "whatsapp": config.get("whatsapp", {})
    }

@router.post(Routes.ADMIN_API_SETTINGS_UPLOAD_SIGNATURE, name=Names.API_UPLOAD_SIGNATURE)
async def api_upload_signature(file: UploadFile = File(...)):
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

@router.delete(Routes.ADMIN_API_SETTINGS_DELETE_SIGNATURE, name=Names.API_DELETE_SIGNATURE)
async def api_delete_signature():
    delete_signature()
    config.save("landlord", {"signature_image": ""})
    return {"status": "success"}

class ConfigUpdateModel(BaseModel):
    landlord: dict
    billing: dict
    whatsapp: dict = {}
    backup: dict = {}

@router.post(Routes.ADMIN_API_CONFIG_UPDATE, name=Names.UPDATE_CONFIG)
async def update_config(data: ConfigUpdateModel, background_tasks: BackgroundTasks):
    background_tasks.add_task(create_full_backup, tag="settings_change")

    config.save("landlord", data.landlord)
    config.save("billing", data.billing)

    if data.whatsapp:
        config.save("whatsapp", data.whatsapp)

    if data.backup:
        config.save("backup", data.backup)

    return {"status": "success"}

@router.post(Routes.ADMIN_API_CONFIG_THEME, name=Names.UPDATE_THEME)
async def update_theme(data: dict):
    theme = data.get("theme", "system")
    config.save("ui", {"theme": theme})
    return {"status": "success", "theme": theme, "effective_theme": theme}