# // File: app\app\api\backup.py
from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder

from app.core.routes_manifest_landlord import LandlordRoutes as Routes, LandlordNames as Names

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
    get_dashboard_stats, archive_bill, restore_bill, update_paymentStatus
)
from app.services.backup_service import (
    create_full_backup, get_all_backups, create_backup,
    delete_backup, verify_backup_integrity, restore_backup
)
from app.core.paths import BACKUPS_DIR
router = APIRouter()


@router.get(Routes.LANDLORDAPIBACKUPSLIST, name=Names.APIGETBACKUPS)
async def api_get_backups(landlordUuid: str):
    return get_all_backups()

@router.post(Routes.LANDLORDAPIBACKUPSCREATEMANUAL, name=Names.APICREATEMANUALBACKUP)
async def api_create_manual_backup(landlordUuid: str, request: Request, background_tasks: BackgroundTasks):
    from app.authentication.landlord.middleware import extract_landlord_id
    from app.database.landlord_repository import create_landlord_audit_log

    try:
        metadata = create_backup(type_="Manual", subtype="manual")

        landlord_id = extract_landlord_id(request)
        if landlord_id:
            create_landlord_audit_log(
                landlord_id, "backup_created",
                ip_address=request.client.host if request.client else None,
                meta_json=json.dumps({"backup_id": metadata.get("id", "")}),
            )

        return {"status": "success", "data": metadata}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete(Routes.LANDLORDAPIBACKUPSDELETE, name=Names.APIDELETEBACKUP)
async def api_delete_backup(landlordUuid: str, backupId: str):
    if delete_backup(backupId):
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Backup not found")

@router.get(Routes.LANDLORDAPIBACKUPSVERIFY, name=Names.APIVERIFYBACKUP)
async def api_verify_backup(landlordUuid: str, backupId: str):
    try:
        verify_backup_integrity(backupId)
        return {"status": "success", "message": "Backup is fully intact and verified."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post(Routes.LANDLORDAPIBACKUPSRESTORE, name=Names.APIRESTOREBACKUP)
async def api_restore_backup(landlordUuid: str, backupId: str, request: Request):
    from app.authentication.landlord.middleware import extract_landlord_id
    from app.database.landlord_repository import create_landlord_audit_log

    try:
        restore_backup(backupId)

        landlord_id = extract_landlord_id(request)
        if landlord_id:
            create_landlord_audit_log(
                landlord_id, "backup_restored",
                ip_address=request.client.host if request.client else None,
                meta_json=json.dumps({"backup_id": backupId}),
            )

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get(Routes.LANDLORDAPIBACKUPSDOWNLOAD, name=Names.APIDOWNLOADBACKUP)
async def api_download_backup(landlordUuid: str, backupId: str):
    registry = get_all_backups()
    backup_meta = next((b for b in registry["backups"] if b["id"] == backupId), None)
    if not backup_meta:
        raise HTTPException(status_code=404, detail="Backup not found")
        
    abs_path = os.path.join(BACKUPS_DIR, backup_meta["path"])
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Backup file missing")
        
    return FileResponse(abs_path, media_type='application/zip', filename=backup_meta["filename"])

@router.get(Routes.LANDLORDAPIBACKUPSMETADATA, name=Names.APIDOWNLOADMETADATA)
async def api_download_metadata(landlordUuid: str, backupId: str):
    registry = get_all_backups()
    backup_meta = next((b for b in registry["backups"] if b["id"] == backupId), None)
    if not backup_meta:
        raise HTTPException(status_code=404, detail="Backup not found")
        
    return backup_meta
