from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.core.routes import Names
from pydantic import BaseModel
import os

from app.core.config_service import config
from app.services.signature_service import save_signature, delete_signature
from app.services.backup_service import create_full_backup

router = APIRouter(tags=["Settings"])

@router.get("/api/config", name=Names.API_GET_CONFIG)
async def api_get_config():
    return {
        "landlord": config.get("landlord", {}),
        "billing": config.get("billing", {}),
        "ui": config.get("ui", {}),
        "backup": config.get("backup", {})
    }

@router.post("/api/settings/signature", name=Names.API_UPLOAD_SIGNATURE)
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
        
    # Update config with just the filename
    filename = os.path.basename(path)
    config.save("landlord", {"signature_image": filename})
    
    return {"status": "success", "path": filename}

@router.delete("/api/settings/signature", name=Names.API_DELETE_SIGNATURE)
async def api_delete_signature():
    delete_signature()
    config.save("landlord", {"signature_image": ""})
    return {"status": "success"}

class ConfigUpdateModel(BaseModel):
    landlord: dict
    billing: dict
    backup: dict = {}

@router.post("/api/config", name=Names.UPDATE_CONFIG)
async def update_config(data: ConfigUpdateModel, background_tasks: BackgroundTasks):
    background_tasks.add_task(create_full_backup, tag="settings_change")
    
    # Merge landlord config to preserve signature_image
    config.save("landlord", data.landlord)
    
    # Merge billing config just in case
    config.save("billing", data.billing)
    if data.backup:
        config.save("backup", data.backup)
    return {"status": "success"}

@router.post("/api/ui/theme", name=Names.UPDATE_THEME)
async def update_theme(data: dict):
    theme = data.get("theme", "system")
    config.save("ui", {"theme": theme})
    return {"status": "success"}
