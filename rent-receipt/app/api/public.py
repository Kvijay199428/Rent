from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from app.core.routes import Names
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder
from app.core.routes import Paths, Names, Prefixes
from typing import Optional
from datetime import datetime
from app.core.paths import KYC_DIR
from app.models.tenant import Tenant
from app.models.receipt import BillRequest, BulkWhatsappRequest, PaymentStatusUpdate
import os, io, re, json
import mimetypes
import uuid
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
from app.services.backup_service import create_full_backup

router = APIRouter()


@router.post("/api/t/{view_token}/kyc", name=Names.PUBLIC_TENANT_KYC_UPLOAD)
async def public_tenant_kyc_upload(
    view_token: str, 
    name: str = Form(...), 
    mobile: str = Form(...),
    aadhaar_front: Optional[UploadFile] = File(None),
    aadhaar_back: Optional[UploadFile] = File(None),
    aadhaar_combined: Optional[UploadFile] = File(None),
    emp_front: Optional[UploadFile] = File(None),
    emp_back: Optional[UploadFile] = File(None)
):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "view_token", "") == view_token), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")
        
    if not aadhaar_combined and not (aadhaar_front and aadhaar_back):
        raise HTTPException(status_code=400, detail="Please upload either a Combined Aadhaar file, or both Front and Back files.")
        
    occupant_uuid = str(uuid.uuid4())
    
    async def save_kyc_img(file_obj: UploadFile, side: str):
        if not file_obj or not file_obj.filename: return ""
        ext = file_obj.filename.split('.')[-1] if '.' in file_obj.filename else 'jpg'
        filename = f"{tenant.id}_{occupant_uuid}_{side}.{ext}"
        os.makedirs(KYC_DIR, exist_ok=True)
        file_path = os.path.join(KYC_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(await file_obj.read())
        return filename

    af_path = await save_kyc_img(aadhaar_front, "aadhaar_front") if aadhaar_front else ""
    ab_path = await save_kyc_img(aadhaar_back, "aadhaar_back") if aadhaar_back else ""
    ac_path = await save_kyc_img(aadhaar_combined, "aadhaar_combined") if aadhaar_combined else ""
    ef_path = await save_kyc_img(emp_front, "emp_front") if emp_front else ""
    eb_path = await save_kyc_img(emp_back, "emp_back") if emp_back else ""
        
    now = datetime.now()
    save_occupant(tenant.id, {
        "uuid": occupant_uuid,
        "Name": name,
        "Mobile": mobile,
        "Status": "Active",
        "Aadhaar Front": af_path,
        "Aadhaar Back": ab_path,
        "Aadhaar Combined": ac_path,
        "Emp Front": ef_path,
        "Emp Back": eb_path,
        "Upload_Date": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "Upload_Month": now.strftime("%B %Y")
    })
    
    return {"status": "success", "message": "KYC uploaded successfully"}

@router.put("/api/t/{view_token}/kyc/{occupant_uuid}/inactive", name=Names.PUBLIC_TENANT_KYC_MARK_INACTIVE)
async def public_tenant_kyc_mark_inactive(view_token: str, occupant_uuid: str):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "view_token", "") == view_token), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid link.")
        
    from app.services.tenant_service import update_occupant_status
    update_occupant_status(occupant_uuid, "Inactive")
    return {"status": "success"}

@router.delete("/api/t/{view_token}/kyc/{occupant_uuid}", name=Names.PUBLIC_TENANT_KYC_DELETE)
async def public_tenant_kyc_delete(view_token: str, occupant_uuid: str):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "view_token", "") == view_token), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")
        
    occupants = get_occupants(tenant.id)
    target = next((o for o in occupants if o.get("Occupant UUID") == occupant_uuid), None)
    
    if target:
        doc_keys = ["Aadhaar Front", "Aadhaar Back", "Aadhaar Combined", "Emp Front", "Emp Back"]
        for key in doc_keys:
            filename = target.get(key)
            if filename:
                file_path = os.path.join(KYC_DIR, filename)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
            
    delete_occupant(occupant_uuid)
    return {"status": "success"}

@router.get("/api/kyc/{filename}", name=Names.GET_KYC_FILE)
async def get_kyc_file(filename: str):
    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = os.path.join(KYC_DIR, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "application/octet-stream"
        
    headers = {
        "Content-Disposition": f'inline; filename="{safe_filename}"'
    }
    return FileResponse(file_path, media_type=mime_type, headers=headers)

