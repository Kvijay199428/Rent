# // File: app\app\api\backup.py
from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder

from app.core.routes_manifest import Routes, Names

from typing import Optional
from app.models.tenant import Tenant
from app.models.receipt import BillRequest, PaymentStatusUpdate
import os, io, re, json, datetime
import shutil, logging

from app.services.tenant_service import (
    load_tenants, add_tenant, update_tenant, delete_tenant,
    get_occupants, save_occupant, delete_occupant
)
from app.services.billing_service import (
    get_all_receipts, get_receipt, get_billing_months,
    calculate_charges, create_bill, update_bill, delete_bill,
    get_dashboard_stats, archive_bill, restore_bill, update_payment_status
)
from app.services.backup_service import (
    create_full_backup, get_all_backups, create_backup,
    delete_backup, verify_backup_integrity, restore_backup
)
from app.core.paths import BACKUPS_DIR
router = APIRouter()


@router.get(Routes.ADMIN_API_BACKUPS_LIST, name=Names.API_GET_BACKUPS)
async def api_get_backups():
    return get_all_backups()

@router.post(Routes.ADMIN_API_BACKUPS_CREATE_MANUAL, name=Names.API_CREATE_MANUAL_BACKUP)
async def api_create_manual_backup(background_tasks: BackgroundTasks):
    try:
        metadata = create_backup(type_="Manual", subtype="manual")
        return {"status": "success", "data": metadata}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete(Routes.ADMIN_API_BACKUPS_DELETE, name=Names.API_DELETE_BACKUP)
async def api_delete_backup(backup_id: str):
    if delete_backup(backup_id):
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Backup not found")

@router.get(Routes.ADMIN_API_BACKUPS_VERIFY, name=Names.API_VERIFY_BACKUP)
async def api_verify_backup(backup_id: str):
    try:
        verify_backup_integrity(backup_id)
        return {"status": "success", "message": "Backup is fully intact and verified."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post(Routes.ADMIN_API_BACKUPS_RESTORE, name=Names.API_RESTORE_BACKUP)
async def api_restore_backup(backup_id: str):
    try:
        restore_backup(backup_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get(Routes.ADMIN_API_BACKUPS_DOWNLOAD, name=Names.API_DOWNLOAD_BACKUP)
async def api_download_backup(backup_id: str):
    registry = get_all_backups()
    backup_meta = next((b for b in registry["backups"] if b["id"] == backup_id), None)
    if not backup_meta:
        raise HTTPException(status_code=404, detail="Backup not found")
        
    abs_path = os.path.join(BACKUPS_DIR, backup_meta["path"])
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Backup file missing")
        
    return FileResponse(abs_path, media_type='application/zip', filename=backup_meta["filename"])

@router.get(Routes.ADMIN_API_BACKUPS_METADATA, name=Names.API_DOWNLOAD_METADATA)
async def api_download_metadata(backup_id: str):
    registry = get_all_backups()
    backup_meta = next((b for b in registry["backups"] if b["id"] == backup_id), None)
    if not backup_meta:
        raise HTTPException(status_code=404, detail="Backup not found")
        
    return backup_meta