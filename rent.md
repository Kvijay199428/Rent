```python
// File: api\__init__.py

```

```python
// File: api\backup.py
from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from app.core.routes import Names
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder
from app.core.routes import Paths, Names, Prefixes
from typing import Optional
from app.models.tenant import Tenant
from app.models.receipt import BillRequest, BulkWhatsappRequest, PaymentStatusUpdate
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


@router.get("/api/backups", name=Names.API_GET_BACKUPS)
async def api_get_backups():
    return get_all_backups()

@router.post("/api/backups/manual", name=Names.API_CREATE_MANUAL_BACKUP)
async def api_create_manual_backup(background_tasks: BackgroundTasks):
    try:
        metadata = create_backup(type_="Manual", subtype="manual")
        return {"status": "success", "data": metadata}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/api/backups/{backup_id}", name=Names.API_DELETE_BACKUP)
async def api_delete_backup(backup_id: str):
    if delete_backup(backup_id):
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Backup not found")

@router.get("/api/backups/{backup_id}/verify", name=Names.API_VERIFY_BACKUP)
async def api_verify_backup(backup_id: str):
    try:
        verify_backup_integrity(backup_id)
        return {"status": "success", "message": "Backup is fully intact and verified."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/api/backups/{backup_id}/restore", name=Names.API_RESTORE_BACKUP)
async def api_restore_backup(backup_id: str):
    try:
        restore_backup(backup_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/backups/{backup_id}/download", name=Names.API_DOWNLOAD_BACKUP)
async def api_download_backup(backup_id: str):
    registry = get_all_backups()
    backup_meta = next((b for b in registry["backups"] if b["id"] == backup_id), None)
    if not backup_meta:
        raise HTTPException(status_code=404, detail="Backup not found")
        
    abs_path = os.path.join(BACKUPS_DIR, backup_meta["path"])
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Backup file missing")
        
    return FileResponse(abs_path, media_type='application/zip', filename=backup_meta["filename"])

@router.get("/api/backups/{backup_id}/metadata", name=Names.API_DOWNLOAD_METADATA)
async def api_download_metadata(backup_id: str):
    registry = get_all_backups()
    backup_meta = next((b for b in registry["backups"] if b["id"] == backup_id), None)
    if not backup_meta:
        raise HTTPException(status_code=404, detail="Backup not found")
        
    return backup_meta
```

```python
// File: api\billing.py
from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from app.core.routes import Names
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder
from app.core.routes import Paths, Names, Prefixes
from typing import Optional
from app.models.tenant import Tenant
from app.models.receipt import BillRequest, BulkWhatsappRequest, PaymentStatusUpdate
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
from app.services.backup_service import create_full_backup

router = APIRouter()


@router.get("/api/bills/filter", name=Names.API_FILTER_BILLS)
async def api_filter_bills(status: str = "active"):
    receipts = get_all_receipts()
    if status == "pending":
        filtered = [
            r for r in receipts
            if r.get("Payment_Status", "PENDING") in ["PENDING", "PARTIAL"]
            and r.get("Status") != "ARCHIVED"
        ]
    elif status == "paid":
        filtered = [
            r for r in receipts
            if r.get("Payment_Status", "PENDING") == "PAID"
            and r.get("Status") != "ARCHIVED"
        ]
    elif status == "active":
        filtered = [r for r in receipts if r.get("Status") != "ARCHIVED"]
    else:
        filtered = receipts

    filtered.reverse()
    return filtered

@router.get("/api/billing/months", name=Names.API_BILLING_MONTHS)
async def api_billing_months():
    return get_billing_months()

@router.get("/api/billing/preview", name=Names.API_BILLING_PREVIEW)
async def api_billing_preview(current_reading: float, additional_persons: int):
    return calculate_charges(current_reading, additional_persons)

@router.get("/api/bill/{bill_no}", name=Names.API_GET_SINGLE_BILL)
async def api_get_single_bill(bill_no: str):
    receipt = get_receipt(bill_no)
    if not receipt:
        raise HTTPException(status_code=404, detail="Bill not found")
    return receipt

@router.post("/api/bill", name=Names.API_CREATE_BILL)
async def api_create_bill(request: BillRequest, background_tasks: BackgroundTasks):
    billing_conf = config.get("billing", {})
    prev = float(billing_conf.get("previous_meter_reading", 0.0))
    if request.current_reading < prev:
        raise HTTPException(status_code=400, detail="Current meter reading cannot be less than previous reading.")
        
    try:
        data = create_bill(
            request.tenant,
            request.month,
            request.current_reading,
            request.additional_persons,
            request.tank_water,
            request.maintenance_charge,
            request.maintenance_desc,
            request.previous_arrears,
            request.amount_received,
            request.payment_status
        )
        background_tasks.add_task(create_full_backup, tag="create_bill")
        return {"status": "success", "data": data}
    except ValueError as e:
        msg = str(e)
        if "already exists" in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/edit_bill/{bill_no}", name=Names.API_UPDATE_BILL)
async def api_update_bill(bill_no: str, request: BillRequest, background_tasks: BackgroundTasks):
    receipt = get_receipt(bill_no)
    if not receipt:
        raise HTTPException(status_code=404, detail="Bill not found")
        
    prev = float(receipt["Previous"])
    if request.current_reading < prev:
        raise HTTPException(status_code=400, detail="Current meter reading cannot be less than previous reading.")
        
    try:
        data = update_bill(
            bill_no,
            request.tenant,
            request.month,
            request.current_reading,
            request.additional_persons,
            request.tank_water,
            request.maintenance_charge,
            request.maintenance_desc,
            request.previous_arrears,
            request.amount_received,
            request.payment_status
        )
        background_tasks.add_task(create_full_backup, tag="edit_bill")
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Update PaymentStatusUpdate with amount_received
@router.post("/api/bill/{bill_no}/payment", name=Names.API_UPDATE_PAYMENT)
async def api_update_payment(bill_no: str, data: PaymentStatusUpdate, background_tasks: BackgroundTasks):
    try:
        if data.payment_status not in ["PAID", "PENDING", "PARTIAL", "ADVANCE"]:
            raise ValueError("Invalid payment status")
        update_payment_status(bill_no, data.payment_status, data.amount_received)
        background_tasks.add_task(create_full_backup, tag="payment_status")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/bill/{bill_no}/archive", name=Names.API_ARCHIVE_BILL)
async def api_archive_bill(bill_no: str, background_tasks: BackgroundTasks):
    try:
        archive_bill(bill_no)
        background_tasks.add_task(create_full_backup, tag="archive_bill")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/bill/{bill_no}/restore", name=Names.API_RESTORE_BILL)
async def api_restore_bill(bill_no: str, background_tasks: BackgroundTasks):
    try:
        restore_bill(bill_no)
        background_tasks.add_task(create_full_backup, tag="restore_bill")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/api/archive/{bill_no}", name=Names.API_DELETE_BILL)
async def api_delete_bill(bill_no: str, background_tasks: BackgroundTasks):
    try:
        delete_bill(bill_no)
        background_tasks.add_task(create_full_backup, tag="delete_bill")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

```python
// File: api\health.py
from fastapi import APIRouter
from app.core.routes import Names
from app.core.app_info import APP_INFO
from app.core.config_service import ConfigService

router = APIRouter(tags=["Health"])

@router.get("/health", name=Names.HEALTH_CHECK)
async def health_check():
    return {
        "status": "ok",
        "application": APP_INFO["name"],
        "version": APP_INFO["version"],
        "schema": APP_INFO["schema"],
        "config_loaded": bool(ConfigService.get_config()),
        "storage_ready": True,  # Monitored at startup
        "database_ready": True, # Using flat files
        "uptime": "N/A" # Trackable if needed
    }
```

```python
// File: api\pdf.py
from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from app.core.routes import Names
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder
from app.core.routes import Paths, Names, Prefixes
from typing import Optional
from app.models.tenant import Tenant
from app.models.receipt import BillRequest, BulkWhatsappRequest, PaymentStatusUpdate
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
from app.services.backup_service import create_full_backup

router = APIRouter()


@router.get("/api/pdf/{bill_no}/download", name=Names.PDF_DOWNLOAD)
async def download_pdf(bill_no: str):
    receipt = get_receipt(bill_no)
    if not receipt:
        raise HTTPException(status_code=404, detail="PDF not found")
        
    tenant_name = receipt.get("Tenant", "Unknown").replace(" ", "_")
    try:
        formatted_date = datetime.strptime(receipt.get("Date", ""), "%d %B %Y").strftime("%Y%m%d")
    except:
        formatted_date = receipt.get("Date", "").replace(" ", "")
    custom_filename = f"{tenant_name}_{formatted_date}_{bill_no}.pdf"
        
    from app.services.pdf_service import generate_professional_pdf
    landlord_conf = config.get("landlord", {})
    
    pdf_stream = generate_professional_pdf(receipt, landlord_conf)
    
    response = StreamingResponse(iter([pdf_stream.getvalue()]), media_type='application/pdf')
    response.headers["Content-Disposition"] = f'attachment; filename="{custom_filename}"'
    return response

@router.get("/api/pdf/{bill_no}/view", name=Names.PDF_VIEW)
async def view_pdf(bill_no: str):
    receipt = get_receipt(bill_no)
    if not receipt:
        raise HTTPException(status_code=404, detail="PDF not found")
        
    tenant_name = receipt.get("Tenant", "Unknown").replace(" ", "_")
    try:
        formatted_date = datetime.strptime(receipt.get("Date", ""), "%d %B %Y").strftime("%Y%m%d")
    except:
        formatted_date = receipt.get("Date", "").replace(" ", "")
    custom_filename = f"{tenant_name}_{formatted_date}_{bill_no}.pdf"
        
    from app.services.pdf_service import generate_professional_pdf
    landlord_conf = config.get("landlord", {})
    
    pdf_stream = generate_professional_pdf(receipt, landlord_conf)

    response = StreamingResponse(iter([pdf_stream.getvalue()]), media_type='application/pdf')
    response.headers["Content-Disposition"] = f"inline; filename={custom_filename}"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
```

```python
// File: api\public.py
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
```

```python
// File: api\settings.py
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
```

```python
// File: api\sync.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from app.core.routes import Names
from fastapi.responses import StreamingResponse, FileResponse
from app.core.dependencies import config
from app.models.tenant import Tenant
import os
import io
import json
import datetime
import zipfile
import csv
import uvicorn
import socket

from app.services.tenant_service import load_tenants, add_tenant, update_tenant
from app.services.billing_service import get_all_receipts
from app.services.backup_service import create_full_backup
from app.core.paths import BACKUPS_DIR

import openpyxl
from openpyxl.styles import Font, PatternFill
router = APIRouter()


# ==========================================
# EXCEL IMPORT & EXPORT ENGINE (RELATIONAL)
# ==========================================

PROFILE_HEADERS = [
    "Tenant_ID", "Tenant_Name", "Phone", "Email", "Company", "Address", "Room",
    "Meter_ID", "PIN", "Rent", "Water", "Electricity_Rate", "Additional_Person_Rate",
    "Tank_Water", "Status"
]

RECEIPT_HEADERS = [
    "Bill_No", "Tenant_ID", "Month", "Date", "Previous", "Current", "Units", "Rent",
    "Water", "Electricity", "Additional", "Tank_Water", "Maintenance", "Arrears",
    "Amount_Received", "Total", "Payment_Status", "Receipt_Status"
]

def _build_excel_workbook(tenants_list, receipts_list):
    """Shared helper: builds and returns an openpyxl workbook in memory."""
    wb = openpyxl.Workbook()
    ws_profile = wb.active
    ws_profile.title = "Tenant_Profile"
    ws_profile.append(PROFILE_HEADERS)

    ws_receipts = wb.create_sheet("Rent_Receipts")
    ws_receipts.append(RECEIPT_HEADERS)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    for ws in [ws_profile, ws_receipts]:
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill

    tenant_id_map = {}
    for t in tenants_list:
        t_id_str = f"T{str(t.id).zfill(3)}"
        tenant_id_map[t.name] = t_id_str
        ws_profile.append([
            t_id_str, t.name, str(t.phone), getattr(t, 'email', ''), getattr(t, 'company', ''),
            getattr(t, 'address', ''), getattr(t, 'room_number', ''), getattr(t, 'meter_id', ''),
            getattr(t, 'tenant_pin', '1234'), float(t.rent), float(t.water), float(t.electricity_rate),
            float(t.additional_person_charge), float(getattr(t, 'default_tank_water_charge', 0.0)), t.status
        ])

    for r in receipts_list:
        t_name = r.get("Tenant", "")
        t_id_str = tenant_id_map.get(t_name, "UNKNOWN")
        ws_receipts.append([
            r.get("Bill", ""), t_id_str, r.get("Month", ""), r.get("Date", ""),
            float(r.get("Previous", 0)), float(r.get("Current", 0)), float(r.get("Units", 0)),
            float(r.get("Rent", 0)), float(r.get("Water", 0)), float(r.get("Electricity", 0)),
            float(r.get("Additional", 0)), float(r.get("Tank_Water", 0)),
            float(r.get("Maintenance_Charge", 0)), float(r.get("Previous_Arrears", 0)),
            float(r.get("Amount_Received", 0)), float(r.get("Total", 0)),
            r.get("Payment_Status", "PENDING"), r.get("Status", "ACTIVE")
        ])

    return wb


@router.get("/api/export/csv", name=Names.EXPORT_RECEIPTS_CSV)
async def export_receipts_csv(tenants_list: str = "all"):
    tenants = load_tenants()
    receipts = get_all_receipts()

    if tenants_list != "all":
        selected_ids = [int(x) for x in tenants_list.split(",") if x.isdigit()]
        selected_names = [t.name for t in tenants if t.id in selected_ids]
        receipts = [r for r in receipts if r.get("Tenant") in selected_names]

    stream = io.StringIO()
    if receipts:
        writer = csv.DictWriter(stream, fieldnames=receipts[0].keys())
        writer.writeheader()
        writer.writerows(receipts)
    else:
        stream.write("No data found for selected tenants.")

    date_str = datetime.datetime.now().strftime('%Y%m%d')
    filename = f"receipts_export_{date_str}.csv"
    
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

@router.get("/api/export/zip", name=Names.EXPORT_FULL_ZIP)
async def export_full_zip(tenants_list: str = "all"):
    tenants = load_tenants()
    receipts = get_all_receipts()

    if tenants_list != "all":
        selected_ids = [int(x) for x in tenants_list.split(",") if x.isdigit()]
        selected_names = [t.name for t in tenants if t.id in selected_ids]
        receipts = [r for r in receipts if r.get("Tenant") in selected_names]

    date_str = datetime.datetime.now().strftime('%Y%m%d')
    zip_filename = f"tenant_data_{date_str}.zip"
    zip_path = os.path.join(BACKUPS_DIR, zip_filename)
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    
    from app.services.pdf_service import generate_professional_pdf
    from app.core.config_service import config
    landlord_conf = config.get("landlord", {})

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        stream = io.StringIO()
        if receipts:
            writer = csv.DictWriter(stream, fieldnames=receipts[0].keys())
            writer.writeheader()
            writer.writerows(receipts)
        zipf.writestr("receipts_data.csv", stream.getvalue())

        for r in receipts:
            tenant_name = r.get("Tenant", "Unknown").replace(" ", "_")
            try:
                formatted_date = datetime.strptime(r.get("Date", ""), "%d %B %Y").strftime("%Y%m%d")
            except Exception:
                formatted_date = r.get("Date", "").replace(" ", "")
                
            custom_filename = f"{tenant_name}_{formatted_date}_{r['Bill']}.pdf"
            status = r.get("Status", "ACTIVE")
            folder = "archive" if status == "ARCHIVED" else "active"
            
            try:
                pdf_stream = generate_professional_pdf(r, landlord_conf)
                zipf.writestr(f"PDFs/{folder}/{custom_filename}", pdf_stream.getvalue())
            except Exception as e:
                print(f"Failed to generate PDF for {r['Bill']}: {e}")

    response = FileResponse(zip_path, media_type="application/zip", filename=zip_filename)
    response.headers["Content-Disposition"] = f'attachment; filename="{zip_filename}"'
    return response

@router.get("/api/sync/template", name=Names.DOWNLOAD_EXCEL_TEMPLATE)
async def download_excel_template():
    wb = openpyxl.Workbook()
    ws_profile = wb.active
    ws_profile.title = "Tenant_Profile"
    ws_profile.append(PROFILE_HEADERS)
    ws_receipts = wb.create_sheet("Rent_Receipts")
    ws_receipts.append(RECEIPT_HEADERS)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    for ws in [ws_profile, ws_receipts]:
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill

    # Sample data rows
    ws_profile.append(["T001", "John Doe", "9876543210", "john@gmail.com", "ABC Pvt Ltd", "Delhi", "A101", "MTR001", "1234", 15000, 500, 8.5, 1000, 300, "Active"])
    ws_profile.append(["T002", "Alice Smith", "9988776655", "alice@gmail.com", "XYZ Ltd", "Noida", "B202", "MTR002", "4321", 18000, 600, 9.0, 1200, 400, "Active"])
    ws_receipts.append(["T1-001", "T001", "January 2026", "01 Jan 2026", 120, 150, 30, 15000, 500, 255, 1000, 300, 0, 0, 17055, 17055, "PAID", "ACTIVE"])
    ws_receipts.append(["T2-001", "T002", "January 2026", "01 Jan 2026", 80, 110, 30, 18000, 600, 270, 0, 400, 0, 0, 19270, 19270, "PAID", "ACTIVE"])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    response = StreamingResponse(iter([stream.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Content-Disposition"] = 'attachment; filename="Rent_Data_Template.xlsx"'
    return response

@router.get("/api/sync/export/{format}", name=Names.EXPORT_EXCEL_DATA)
async def export_excel_data(format: str):
    tenants = load_tenants()
    receipts = get_all_receipts()

    # Build workbook entirely in RAM
    wb = _build_excel_workbook(tenants, receipts)
    excel_stream = io.BytesIO()
    wb.save(excel_stream)
    excel_stream.seek(0)

    date_str = datetime.datetime.now().strftime('%Y%m%d')

    if format == "xlsx":
        filename = f"Rent_Data_Export_{date_str}.xlsx"
        response = StreamingResponse(
            iter([excel_stream.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    elif format == "zip":
        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr(f"Rent_Data_Export_{date_str}.xlsx", excel_stream.getvalue())
        zip_stream.seek(0)
        zip_filename = f"Rent_Data_Archive_{date_str}.zip"
        response = StreamingResponse(
            iter([zip_stream.getvalue()]),
            media_type="application/zip"
        )
        response.headers["Content-Disposition"] = f'attachment; filename="{zip_filename}"'
        return response

    raise HTTPException(status_code=400, detail="Unsupported format. Use 'xlsx' or 'zip'.")

def parse_excel_bytes(file_bytes, filename):
    wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), data_only=True)
    if "Tenant_Profile" not in wb.sheetnames or "Rent_Receipts" not in wb.sheetnames:
        raise ValueError(f"File '{filename}' is missing required sheets 'Tenant_Profile' and/or 'Rent_Receipts'.")

    ws_profile = wb["Tenant_Profile"]
    ws_receipts = wb["Rent_Receipts"]

    p_headers = [str(cell.value).strip() if cell.value else f"Col{i}" for i, cell in enumerate(ws_profile[1])]
    r_headers = [str(cell.value).strip() if cell.value else f"Col{i}" for i, cell in enumerate(ws_receipts[1])]

    tenants_dict = {}
    for row in ws_profile.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        row_dict = {p_headers[i]: (str(val).strip() if val is not None else "") for i, val in enumerate(row)}
        t_id = row_dict.get("Tenant_ID", "")
        if t_id:
            tenants_dict[t_id] = {"profile": row_dict, "receipts": []}

    for row in ws_receipts.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        row_dict = {r_headers[i]: (str(val).strip() if val is not None else "") for i, val in enumerate(row)}
        t_id = row_dict.get("Tenant_ID", "")
        if t_id in tenants_dict:
            tenants_dict[t_id]["receipts"].append(row_dict)

    return tenants_dict

@router.post("/api/sync/import/preview", name=Names.IMPORT_PREVIEW_DATA)
async def import_preview_data(file: UploadFile = File(...)):
    preview_data = {}
    content = await file.read()
    try:
        if file.filename.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                for zip_info in z.infolist():
                    if zip_info.filename.endswith('.xlsx'):
                        with z.open(zip_info) as f:
                            preview_data[zip_info.filename] = parse_excel_bytes(f.read(), zip_info.filename)
        elif file.filename.endswith('.xlsx'):
            preview_data[file.filename] = parse_excel_bytes(content, file.filename)
        else:
            raise HTTPException(status_code=400, detail="Only .xlsx or .zip files are supported.")
        return {"status": "success", "files": preview_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/sync/import/execute", name=Names.IMPORT_EXECUTE_DATA)
async def import_execute_data(
    file: UploadFile = File(...),
    selected_targets: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    selected_list = json.loads(selected_targets)
    if not selected_list:
        raise HTTPException(status_code=400, detail="No tenants selected for import.")

    content = await file.read()
    sys_tenants = load_tenants()
    sys_receipts = get_all_receipts()

    background_tasks.add_task(create_full_backup, tag="pre_import_excel")

    def execute_import_for_file(file_bytes, filename):
        parsed_data = parse_excel_bytes(file_bytes, filename)
        for t_id, t_data in parsed_data.items():
            target_key = f"{filename}::{t_id}"
            if target_key not in selected_list:
                continue

            p = t_data["profile"]
            t_name = p.get("Tenant_Name", "").strip()
            if not t_name:
                continue

            t = next((x for x in sys_tenants if x.name.lower() == t_name.lower()), None)
            is_new = False
            if not t:
                t = Tenant(name=t_name, phone=p.get("Phone", ""), rent=0.0, water=0.0, electricity_rate=0.0)
                is_new = True

            t.phone = p.get("Phone", t.phone)
            t.email = p.get("Email", getattr(t, 'email', ''))
            t.company = p.get("Company", getattr(t, 'company', ''))
            t.address = p.get("Address", getattr(t, 'address', ''))
            t.room_number = p.get("Room", getattr(t, 'room_number', ''))
            t.meter_id = p.get("Meter_ID", getattr(t, 'meter_id', ''))
            t.tenant_pin = p.get("PIN", getattr(t, 'tenant_pin', '1234'))
            t.rent = float(p.get("Rent", t.rent) or 0.0)
            t.water = float(p.get("Water", t.water) or 0.0)
            t.electricity_rate = float(p.get("Electricity_Rate", t.electricity_rate) or 0.0)
            t.additional_person_charge = float(p.get("Additional_Person_Rate", getattr(t, 'additional_person_charge', 0.0)) or 0.0)
            t.default_tank_water_charge = float(p.get("Tank_Water", getattr(t, 'default_tank_water_charge', 0.0)) or 0.0)
            t.status = p.get("Status", getattr(t, 'status', 'Active'))

            if is_new:
                add_tenant(t)
                sys_tenants.append(t)
            else:
                update_tenant(t)

            for r in t_data["receipts"]:
                bill_no = r.get("Bill_No", "").strip()
                if not bill_no:
                    continue
                sys_r = next((x for x in sys_receipts if x.get("Bill") == bill_no), None)
                data = {
                    "Bill": bill_no, "Date": r.get("Date", ""), "Month": r.get("Month", ""),
                    "Tenant": t_name, "Previous": r.get("Previous", 0), "Current": r.get("Current", 0),
                    "Units": r.get("Units", 0), "Rent": r.get("Rent", 0), "Additional": r.get("Additional", 0),
                    "Water": r.get("Water", 0), "Tank_Water": r.get("Tank_Water", 0),
                    "Electricity": r.get("Electricity", 0), "Maintenance_Charge": r.get("Maintenance", 0),
                    "Maintenance_Desc": r.get("Maintenance_Desc", ""),
                    "Previous_Arrears": r.get("Arrears", 0), "Amount_Received": r.get("Amount_Received", 0),
                    "Total": r.get("Total", 0), "Payment_Status": r.get("Payment_Status", "PENDING"),
                    "Status": r.get("Receipt_Status", "ACTIVE"), "Receipt_Version": 8, "Generated_By": "Import"
                }
                if sys_r:
                    sys_r.update(data)
                else:
                    sys_receipts.append(data)

    try:
        if file.filename.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                for zip_info in z.infolist():
                    if zip_info.filename.endswith('.xlsx'):
                        with z.open(zip_info) as f:
                            execute_import_for_file(f.read(), zip_info.filename)
        elif file.filename.endswith('.xlsx'):
            execute_import_for_file(content, file.filename)

        from app.services.billing_service import save_all_receipts
        save_all_receipts(sys_receipts)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    sys_conf = config.get("system", {})
    server_host = sys_conf["server"]["host"]
    server_port = sys_conf["server"]["port"]
    is_debug = sys_conf["server"]["debug"]
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()
        
    print(f"\n{'='*50}")
    print(f" {sys_conf['app']['title']} is starting...")
    print(f"{'='*50}")
    print(f" [Local]:   http://127.0.0.1:{server_port}")
    print(f" [Network]: http://{local_ip}:{server_port}")
    print(f" [Note]:    Do NOT click the {server_host} link below")
    print(f"{'='*50}\n")

    uvicorn.run(
        "app:app",
        host=server_host,
        port=server_port,
        reload=is_debug,
        proxy_headers=True,
        forwarded_allow_ips="*",
        access_log=True
    )
```

```python
// File: api\tenants.py
from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from app.core.routes import Names
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder
from app.core.routes import Paths, Names, Prefixes
from typing import Optional
from app.models.tenant import Tenant
from app.models.receipt import BillRequest, BulkWhatsappRequest, PaymentStatusUpdate
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
from app.services.backup_service import create_full_backup

router = APIRouter()


@router.get("/api/tenants", name=Names.API_GET_TENANTS)
async def api_get_tenants():
    return load_tenants()

@router.get("/api/tenants/{tenant_id}", name=Names.API_GET_TENANT)
async def api_get_tenant(tenant_id: int):
    tenants = load_tenants()
    tenant = next((t for t in tenants if t.id == tenant_id), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

@router.get("/api/tenant_receipts/{tenant_name}", name=Names.API_GET_TENANT_RECEIPTS)
async def api_get_tenant_receipts(tenant_name: str):
    receipts = get_all_receipts()
    tenant_receipts = [r for r in receipts if r["Tenant"] == tenant_name]
    tenant_receipts.reverse()
    return tenant_receipts

@router.post("/api/tenants", name=Names.API_ADD_TENANT)
async def api_add_tenant(t: Tenant, background_tasks: BackgroundTasks):
    background_tasks.add_task(create_full_backup, tag="add_tenant")
    return add_tenant(t)

@router.put("/api/tenants/{tenant_id}", name=Names.API_UPDATE_TENANT)
async def api_update_tenant(tenant_id: int, t: Tenant, background_tasks: BackgroundTasks):
    t.id = tenant_id
    background_tasks.add_task(create_full_backup, tag="update_tenant")
    return update_tenant(t)

@router.delete("/api/tenants/{tenant_id}", name=Names.API_DELETE_TENANT)
async def api_delete_tenant(tenant_id: int, action: str = "archive", background_tasks: BackgroundTasks = None):
    if background_tasks:
        background_tasks.add_task(create_full_backup, tag=f"{action}_tenant")
    delete_tenant(tenant_id, action)
    return {"status": "success"}
```

```python
// File: api\whatsapp.py
from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from app.core.routes import Names
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder
from app.core.routes import Paths, Names, Prefixes
from typing import Optional
from urllib.parse import quote
from app.models.tenant import Tenant
from app.models.receipt import BillRequest, BulkWhatsappRequest, PaymentStatusUpdate
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
from app.services.backup_service import create_full_backup

router = APIRouter()


@router.get("/api/whatsapp/single/{bill_no}", name=Names.SEND_WHATSAPP_SINGLE)
async def send_whatsapp_single(request: Request, bill_no: str):
    receipt = get_receipt(bill_no)
    if not receipt:
        raise HTTPException(status_code=404, detail="Bill not found")
        
    tenants = load_tenants()
    tenant = next((t for t in tenants if t.name == receipt.get("Tenant")), None)
    if not tenant or not tenant.phone:
        raise HTTPException(status_code=400, detail="Tenant phone number not found")
        
    landlord_conf = config.get("landlord", {})
    template = landlord_conf.get("whatsapp_template", "Hello {tenant_name}, here is your rent receipt for {month}. Bill No: {bill_no}. Amount: {currency}{total}. View it here: {link}")
    
    if not config.get("system.features.whatsapp_sync", False):
        raise HTTPException(status_code=403, detail="WhatsApp feature is disabled.")

    phone = re.sub(r'\D', '', str(tenant.phone))
    if len(phone) == 10:
        country_code = config.get("system.whatsapp.country_code", "91")
        phone = country_code + phone
        
    token = getattr(tenant, "view_token", "")
    link = str(request.url_for("public_tenant_profile_get", view_token=token))
    
    # Calculate Grand Total for WhatsApp
    grand_total = float(receipt.get("Total", 0)) + float(receipt.get("Previous_Arrears", 0))

    msg = template.format(
        tenant_name=tenant.name,
        month=receipt.get("Month", ""),
        bill_no=bill_no,
        total="{:,.0f}".format(grand_total),
        currency="Rs.",
        link=link
    )
    
    url = f"https://api.whatsapp.com/send?phone={phone}&text={quote(msg)}"
    return {"status": "success", "url": url}

@router.post("/api/whatsapp/bulk", name=Names.SEND_WHATSAPP_BULK)
async def send_whatsapp_bulk(request: Request, data: BulkWhatsappRequest):
    tenants = load_tenants()
    tenant = next((t for t in tenants if t.id == data.tenant_id), None)
    if not tenant or not tenant.phone:
        raise HTTPException(status_code=400, detail="Tenant phone number not found")
        
    receipts = [get_receipt(b) for b in data.bill_numbers]
    receipts = [r for r in receipts if r]
    if not receipts:
        raise HTTPException(status_code=400, detail="No valid bills found")
        
    landlord_conf = config.get("landlord", {})
    template = landlord_conf.get("whatsapp_bulk_template", "Hello {tenant_name}, here are your rent receipts for {bill_list}. Total Amount: {currency}{total_amount}. View them here: {link}")
    
    if not config.get("system.features.whatsapp_sync", False):
        raise HTTPException(status_code=403, detail="WhatsApp feature is disabled.")

    phone = re.sub(r'\D', '', str(tenant.phone))
    if len(phone) == 10:
        country_code = config.get("system.whatsapp.country_code", "91")
        phone = country_code + phone
        
    token = getattr(tenant, "view_token", "")
    link = str(request.url_for("public_tenant_profile_get", view_token=token))
    
    bill_list = ", ".join([r.get("Month", "") for r in receipts])
    
    # Calculate Sum of Grand Totals for Bulk Messages
    total_amount = sum([float(r.get("Total", 0)) + float(r.get("Previous_Arrears", 0)) for r in receipts])
    
    msg = template.format(
        tenant_name=tenant.name,
        bill_list=bill_list,
        total_amount="{:,.0f}".format(total_amount),
        currency="Rs.",
        link=link
    )
    
    url = f"https://api.whatsapp.com/send?phone={phone}&text={quote(msg)}"
    return {"status": "success", "url": url}
```

```python
// File: core\app_info.py
APP_INFO = {
    "name": "Rent Receipt System",
    "version": "3.0.0",
    "schema": 2,
    "environment": "production"
}
```

```python
// File: core\config_defaults.py
DEFAULT_CONFIGS = {
    "billing": {
        "rent": 8000.0,
        "water": 500.0,
        "electricity_rate": 15.0,
        "additional_person_charge": 1000.0,
        "previous_meter_reading": 0.0,
        "next_bill_number": 1
    },
    "landlord": {
        "name": "",
        "phone": "",
        "email": "",
        "address": "",
        "pan": "",
        "bank_account_name": "",
        "bank_account_number": "",
        "bank_name": "",
        "bank_branch": "",
        "bank_ifsc": "",
        "mask_bank_account": True,
        "signature_text": "Authorized Signature",
        "signature_image": "",
        "whatsapp_template": "Hello {tenant_name},\n\nYour rent receipt for {month} has been generated.\n\n*Bill No:* {bill_no}\n*Total Amount:* {currency}{total}\n\nYou can view and download your receipt securely here: {link}\n\nThank you!",
        "whatsapp_bulk_template": "Hello {tenant_name},\n\nHere are your requested rent receipts:\n\n{bill_list}\n*Total Amount:* {currency}{total_amount}\n\nYou can view and download your receipts securely here: {link}\n\nThank you!"
    },
    "ui": {
        "theme": "system",
        "menu": [
            {"name": "Dashboard", "icon": "bi-speedometer2", "type": "internal",
            "route": "home_page"},
            {"name": "Billing", "icon": "bi-receipt", "type": "internal",
            "route": "billing_page"},
            {"name": "History", "icon": "bi-clock-history", "type": "internal",
            "route": "history_page"},
            {"name": "Tenants", "icon": "bi-people", "type": "internal",
            "route": "tenants_page"},
            {"name": "Archive", "icon": "bi-archive", "type": "internal",
            "route": "archive_page"},
            {"name": "Backups", "icon": "bi-database", "type": "internal",
            "route": "backups_page"},
            {"name": "Settings", "icon": "bi-gear", "type": "internal",
            "route": "settings_page"}
        ]
    },
    "schema": {
        "tenant_schema": 2,
        "receipt_schema": 1
    },
    "backup": {
        "enabled": True,
        "frequency": "daily",
        "max_daily": 30,
        "max_weekly": 12,
        "location": "backups",
        "compress": True,
        "verify": True,
        "encrypt": False,
        "create_restore_points": {
            "tenant_update": True,
            "receipt_edit": True,
            "receipt_archive": True,
            "settings_save": True,
            "schema_migration": True
        }
    },
    "system": {
        "server": {
            "host": "0.0.0.0",
            "port": 20081,
            "debug": True
        },
        "app": {
            "title": "Rent Receipt Web Application",
            "short_name": "RRG Suite",
            "currency_symbol": "₹",
            "locale": "en-IN"
        },
        "limits": {
            "max_upload_size_mb": 2,
            "public_history_months": 12
        },
        "whatsapp": {
            "country_code": "91"
        },
        "features": {
            "whatsapp_sync": True
        }
    },
    "tenantProfile": {},
    "rentReceipt": {},
    "payment": {},
    "dashboard": {},
    "archive": {},
    "pdf": {},
    "features": {},
    "theme": {},
    "validation": {}
}
```

```python
// File: core\config_service.py
import json
import os
from typing import Dict, Any, overload
from app.core.paths import CONFIG_DIR
from app.core.config_defaults import DEFAULT_CONFIGS

class ConfigService:
    _instance = None
    _cache: Dict[str, Any] = {}
    
    CONFIG_DIR = CONFIG_DIR

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigService, cls).__new__(cls)
        return cls._instance

    def initialize(self):
        """Must be called after storage directories are ensured."""
        self.reload_all()

    def reload(self, domain: str):
        """Reload a specific configuration domain from disk."""
        self._cache[domain] = self._load_file(domain)

    def _deep_update(self, target_dict: dict, source_dict: dict):
        """Recursively update target_dict with values from source_dict."""
        for k, v in source_dict.items():
            if isinstance(v, dict) and k in target_dict and isinstance(target_dict[k], dict):
                self._deep_update(target_dict[k], v)
            else:
                target_dict[k] = v

    def reload_all(self):
        """Loads all core configs into memory."""
        print(f"Loading configurations from {self.CONFIG_DIR}...")
        
        # Ensure config directory exists
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
        
        # Create missing defaults
        for name, default_data in DEFAULT_CONFIGS.items():
            path = os.path.join(self.CONFIG_DIR, f"{name}.json")
            if not os.path.exists(path):
                print(f"Creating default configuration: {name}.json")
                with open(path, "w", encoding='utf-8') as f:
                    json.dump(default_data, f, indent=4)
        
        # Load all configs
        loaded_count = 0
        for filename in os.listdir(self.CONFIG_DIR):
            if filename.endswith(".json"):
                name = filename[:-5]
                self._cache[name] = self._load_file(name)
                loaded_count += 1
                
        print(f"Successfully loaded {loaded_count} configurations.")

    def _load_file(self, name: str) -> Dict[str, Any]:
        path = os.path.join(self.CONFIG_DIR, f"{name}.json")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Merge with defaults to ensure new keys exist recursively
                if name in DEFAULT_CONFIGS:
                    import copy
                    default_data = copy.deepcopy(DEFAULT_CONFIGS[name])
                    self._deep_update(default_data, data)
                    return default_data
                return data
        except FileNotFoundError:
            default = DEFAULT_CONFIGS.get(name, {})
            with open(path, "w", encoding='utf-8') as f:
                json.dump(default, f, indent=4)
            return default
        except json.JSONDecodeError as e:
            print(f"CRITICAL: Invalid JSON in {name}.json: {e}")
            if os.path.exists(path):
                import shutil
                shutil.copy2(path, f"{path}.invalid")
            default = DEFAULT_CONFIGS.get(name, {})
            with open(path, "w", encoding='utf-8') as f:
                json.dump(default, f, indent=4)
            return default

    def get(self, path: str, subpath: Any = None, default: Any = None) -> Any:
        """
        Fetch a config value using dot notation. 
        Example: config.get("system.app.title", "Default Title")
        Example: config.get("system", "app.title", default="Default Title")
        config.get("ui") returns the full ui config dict.
        """
        if isinstance(subpath, str):
            path = f"{path}.{subpath}" if subpath else path
        elif subpath is not None:
            default = subpath

        parts = path.split('.')
        current = self._cache
        
        for part in parts:
            if not isinstance(current, dict):
                return default
            current = current.get(part)
            if current is None:
                return default
                
        return current
        
    def set(self, path: str, value: Any):
        """
        Set a config value using dot notation in cache only.
        Example: config.set("system.app.title", "New Title")
        """
        parts = path.split('.')
        if len(parts) == 1:
            self._cache[parts[0]] = value
            return
            
        current = self._cache
        for i, part in enumerate(parts[:-1]):
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
            
        current[parts[-1]] = value
        
    def save(self, domain: str, data: dict = None):
        """
        Save a specific domain back to its JSON file.
        If data is None, saves the current cache for that domain.
        """
        if data is not None:
            existing = self._cache.get(domain, {})
            self._deep_update(existing, data)
            self._cache[domain] = existing
            
        path = os.path.join(self.CONFIG_DIR, f"{domain}.json")
        try:
            # Create timestamped backup
            if os.path.exists(path):
                import shutil
                from datetime import datetime
                from app.core.paths import BACKUPS_DIR
                os.makedirs(BACKUPS_DIR, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(BACKUPS_DIR, f"{domain}_{timestamp}.json.bak")
                try:
                    shutil.copy2(path, backup_path)
                except Exception:
                    pass
                    
            # Atomic save
            import tempfile
            with tempfile.NamedTemporaryFile('w', dir=self.CONFIG_DIR, delete=False, encoding='utf-8') as f:
                json.dump(self._cache.get(domain, {}), f, indent=4)
                tmp_name = f.name
            os.replace(tmp_name, path)
        except Exception as e:
            print(f"Error saving {domain}.json: {e}")

# Initialize a global instance to be imported across the app
config = ConfigService()
```

```python
// File: core\db.py
import os
import sqlite3
from app.core.paths import DBDIR

DB_PATH = os.path.join(DBDIR, "rent.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn
```

```python
// File: core\dependencies.py
from fastapi import Request
from fastapi.templating import Jinja2Templates
from app.core.config_service import config
from app.core.paths import TEMPLATES_DIR
from app.core.route_builder import RouteBuilder
from app.core.routes import Names


def _normalize_base_path(path: str | None) -> str:
    if not path or path == "/":
        return ""
    normalized = path.strip()
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized.rstrip("/")


def app_base(request: Request | None = None) -> str:
    if request is None:
        return ""
    return _normalize_base_path(
        request.scope.get("root_path") or getattr(request.state, "base_path", "")
    )


def static_url(request: Request, path: str) -> str:
    clean_path = path if path.startswith("/") else f"/{path}"
    return f"{app_base(request)}/static{clean_path}"


templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals["config"] = config
templates.env.globals["route"] = RouteBuilder.build
templates.env.globals["Names"] = Names
templates.env.globals["sys"] = config.get("system", {})
templates.env.globals["APP_BASE"] = app_base
templates.env.globals["STATIC_URL"] = static_url

async def get_config(request: Request):
    return request.state.sys

async def get_theme(request: Request):
    return getattr(request.state, 'theme', 'system')
```

```python
// File: core\paths.py
import os

# Set the base storage directory. 
# Defaults to a local "storage" folder, but can be overridden by an environment variable.
STORAGE_DIR = os.environ.get("RENT_STORAGE_DIR", r"d:\VEGA\RENT\storage")

# Define organized subdirectories
CONFIG_DIR = os.path.join(STORAGE_DIR, "config")
DB_DIR = os.path.join(STORAGE_DIR, "database")
RECEIPTS_DIR = os.path.join(STORAGE_DIR, "receipts")
BACKUPS_DIR = os.path.join(STORAGE_DIR, "backups")
UPLOADS_DIR = os.path.join(STORAGE_DIR, "uploads")
KYC_DIR = os.path.join(UPLOADS_DIR, "kyc")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

def ensure_storage_dirs():
    """Creates all necessary directories if they don't exist."""
    directories = [CONFIG_DIR, DB_DIR, RECEIPTS_DIR, BACKUPS_DIR, UPLOADS_DIR, KYC_DIR]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
```

```python
// File: core\route_builder.py
from app.core.routes import Names

class RouteBuilder:
    @staticmethod
    def build(request, name: str, **kwargs):
        return request.url_for(name, **kwargs)

    @staticmethod
    def static(request, path: str):
        return request.url_for("static", path=path)

    @staticmethod
    def pdf(request, bill_no: str):
        return request.url_for(Names.PDF_VIEW, bill_no=bill_no)

    @staticmethod
    def public_tenant(request, token: str):
        return request.url_for(Names.PUBLIC, view_token=token)
```

```python
// File: core\router_registry.py
from fastapi import FastAPI

# API Routers
from app.api.billing import router as billing_api_router
from app.api.tenants import router as tenants_api_router
from app.api.settings import router as settings_api_router
from app.api.backup import router as backup_api_router
from app.api.pdf import router as pdf_api_router
from app.api.whatsapp import router as whatsapp_api_router
from app.api.sync import router as sync_api_router
from app.api.public import router as public_api_router
from app.api.health import router as health_api_router

# Page Routers
from app.pages.dashboard import router as dashboard_page_router
from app.pages.billing import router as billing_page_router
from app.pages.history import router as history_page_router
from app.pages.archive import router as archive_page_router
from app.pages.settings import router as settings_page_router
from app.pages.tenants import router as tenants_page_router
from app.pages.backups import router as backups_page_router
from app.pages.public import router as public_page_router
from app.pages.errors import register_exception_handlers

PAGE_ROUTERS = [
    dashboard_page_router,
    billing_page_router,
    history_page_router,
    archive_page_router,
    settings_page_router,
    tenants_page_router,
    backups_page_router,
    public_page_router
]

API_ROUTERS = [
    billing_api_router,
    tenants_api_router,
    settings_api_router,
    backup_api_router,
    pdf_api_router,
    whatsapp_api_router,
    sync_api_router,
    public_api_router,
    health_api_router
]

def register_all_routers(app: FastAPI):
    for router in PAGE_ROUTERS:
        app.include_router(router)
    for router in API_ROUTERS:
        app.include_router(router)
    register_exception_handlers(app)
```

```python
// File: core\routes.py
class Paths:
    HOME = "/"
    BILLING = "/billing"
    HISTORY = "/history"
    TENANTS = "/tenants"
    SETTINGS = "/settings"
    ARCHIVE = "/archive"
    BACKUPS = "/backups"
    TENANT = "/tenant"
    PUBLIC = "/t"

class Names:
    # Pages
    HOME = "home_page"
    BILLING_PAGE = "billing_page"
    HISTORY_PAGE = "history_page"
    TENANTS_PAGE = "tenants_page"
    SETTINGS_PAGE = "settings_page"
    ARCHIVE_PAGE = "archive_page"
    BACKUPS_PAGE = "backups_page"
    TENANT_PROFILE_PAGE = "tenant_profile_page"
    PUBLIC_TENANT_PROFILE_GET = "public_tenant_profile_get"
    PUBLIC_TENANT_PROFILE_POST = "public_tenant_profile_post"
    FAVICON = "favicon"
    
    # API - Backups
    API_GET_BACKUPS = "api_get_backups"
    API_CREATE_MANUAL_BACKUP = "api_create_manual_backup"
    API_DELETE_BACKUP = "api_delete_backup"
    API_VERIFY_BACKUP = "api_verify_backup"
    API_RESTORE_BACKUP = "api_restore_backup"
    API_DOWNLOAD_BACKUP = "api_download_backup"
    API_DOWNLOAD_METADATA = "api_download_metadata"
    
    # API - Billing
    API_FILTER_BILLS = "api_filter_bills"
    API_BILLING_MONTHS = "api_billing_months"
    API_BILLING_PREVIEW = "api_billing_preview"
    API_GET_SINGLE_BILL = "api_get_single_bill"
    API_CREATE_BILL = "api_create_bill"
    API_UPDATE_BILL = "api_update_bill"
    API_UPDATE_PAYMENT = "api_update_payment"
    API_ARCHIVE_BILL = "api_archive_bill"
    API_RESTORE_BILL = "api_restore_bill"
    API_DELETE_BILL = "api_delete_bill"
    
    # API - PDF
    PDF_DOWNLOAD = "download_pdf"
    PDF_VIEW = "view_pdf"
    
    # API - Public / KYC
    PUBLIC_TENANT_KYC_UPLOAD = "public_tenant_kyc_upload"
    PUBLIC_TENANT_KYC_MARK_INACTIVE = "public_tenant_kyc_mark_inactive"
    PUBLIC_TENANT_KYC_DELETE = "public_tenant_kyc_delete"
    GET_KYC_FILE = "get_kyc_file"
    
    # API - Settings
    API_GET_CONFIG = "api_get_config"
    API_UPLOAD_SIGNATURE = "api_upload_signature"
    API_DELETE_SIGNATURE = "api_delete_signature"
    UPDATE_CONFIG = "update_config"
    UPDATE_THEME = "update_theme"
    
    # API - Sync
    EXPORT_RECEIPTS_CSV = "export_receipts_csv"
    EXPORT_FULL_ZIP = "export_full_zip"
    DOWNLOAD_EXCEL_TEMPLATE = "download_excel_template"
    EXPORT_EXCEL_DATA = "export_excel_data"
    IMPORT_PREVIEW_DATA = "import_preview_data"
    IMPORT_EXECUTE_DATA = "import_execute_data"
    
    # API - Tenants
    API_GET_TENANTS = "api_get_tenants"
    API_GET_TENANT = "api_get_tenant"
    API_GET_TENANT_RECEIPTS = "api_get_tenant_receipts"
    API_ADD_TENANT = "api_add_tenant"
    API_UPDATE_TENANT = "api_update_tenant"
    API_DELETE_TENANT = "api_delete_tenant"
    
    # API - Whatsapp
    SEND_WHATSAPP_SINGLE = "send_whatsapp_single"
    SEND_WHATSAPP_BULK = "send_whatsapp_bulk"
    
    # API - Health
    HEALTH_CHECK = "health_check"

class Prefixes:
    API = "/api"
    STATIC = "/static"
    UPLOADS = "/static/uploads"

class Templates:
    DASHBOARD = "dashboard.html"
    BILLING = "billing.html"
    HISTORY = "history.html"
    SETTINGS = "settings.html"
    TENANTS = "tenants.html"
    ARCHIVE = "archive.html"
    BACKUPS = "backups.html"
    ERROR = "error.html"
    TENANT_PROFILE = "tenant_profile.html"
    TENANT_PUBLIC_PROFILE = "tenant_public_profile.html"
```

```python
// File: core\startup.py
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config_service import ConfigService
from app.core.paths import UPLOADS_DIR, STATIC_DIR, ensure_storage_dirs

class StartupManager:
    @staticmethod
    def initialize(app: FastAPI):
        StartupManager.initialize_storage()
        StartupManager.initialize_config()
        StartupManager.mount_static(app)
        StartupManager.register_middlewares(app)
        StartupManager.register_events(app)

    @staticmethod
    def initialize_storage():
        ensure_storage_dirs()

    @staticmethod
    def initialize_config():
        ConfigService().initialize()

    @staticmethod
    def mount_static(app: FastAPI):
        if not os.path.isdir(STATIC_DIR):
            raise RuntimeError(f"Static asset directory not found: {STATIC_DIR}")
        app.mount("/static/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @staticmethod
    def register_middlewares(app: FastAPI):
        # We will add middlewares here if needed
        pass

    @staticmethod
    def register_events(app: FastAPI):
        @app.on_event("startup")
        async def startup_event():
            print("==================================================")
            print("  Rent Receipt System Initialization Complete")
            print("==================================================")
            print("Registered Routes:")
            print(f"{'METHOD':<10} | {'PATH':<40} | {'NAME':<35} | {'TAGS'}")
            print("-" * 100)
            for route in app.routes:
                if hasattr(route, 'methods'):
                    methods = ",".join(route.methods)
                    name = getattr(route, 'name', 'N/A')
                    tags = getattr(route, 'tags', [])
                    print(f"{methods:<10} | {route.path:<40} | {name:<35} | {tags}")
            print("==================================================")
```

```python
// File: main.py
import os
import time
from fastapi import FastAPI, Request
from starlette.types import ASGIApp, Receive, Scope, Send
from app.core.startup import StartupManager
from app.core.router_registry import register_all_routers
from app.core.app_info import APP_INFO


def normalize_base_path(path: str | None) -> str:
    if not path or path == "/":
        return ""
    normalized = path.strip()
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized.rstrip("/")


class ProxyContextMiddleware:
    """
    Pure ASGI middleware that correctly handles proxy prefixes for Starlette.
    Starlette's routing ALWAYS assumes that scope["path"] starts with scope["root_path"].
    If Nginx strips the prefix (e.g. proxy_pass http://upstream/), scope["path"] will not
    contain the prefix. We must prepend root_path to scope["path"] if it's missing,
    otherwise nested mounts (like StaticFiles) will fail to strip root_path correctly
    and return 404.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope.get("headers", []))

            forwarded_proto = headers.get(b"x-forwarded-proto", b"").decode("latin1")
            forwarded_prefix = headers.get(b"x-forwarded-prefix", b"").decode("latin1")

            if forwarded_proto:
                scope["scheme"] = forwarded_proto.split(",")[0].strip()

            root_path = normalize_base_path(forwarded_prefix or os.getenv("APP_BASE_PATH"))

            if root_path:
                scope["root_path"] = root_path
                # PREPEND root_path to path if it was stripped by Nginx.
                # Starlette explicitly requires path to contain root_path.
                current_path = scope.get("path", "")
                if not current_path.startswith(root_path):
                    scope["path"] = root_path + current_path

                # Keep raw_path in sync
                raw_prefix = root_path.encode("ascii")
                raw_path = scope.get("raw_path", b"")
                if not raw_path.startswith(raw_prefix):
                    scope["raw_path"] = raw_prefix + raw_path

        await self.app(scope, receive, send)


# ── Build the application ────────────────────────────────────────────────────

app = FastAPI(title=APP_INFO["name"], version=APP_INFO["version"])

# Initialize Storage, Config, Static mounts
StartupManager.initialize_storage()
StartupManager.initialize_config()
StartupManager.mount_static(app)
StartupManager.register_middlewares(app)

# Register all modular routers
register_all_routers(app)

# Register events after routers are registered so startup diagnostics show all routes
StartupManager.register_events(app)

# Add proxy middleware — must be added AFTER routes so it sits outermost in the stack
app.add_middleware(ProxyContextMiddleware)  # type: ignore[arg-type]


# Request timing / logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    path = request.scope.get("path", "?")
    print(f"[{response.status_code}] {request.method} {path} - {duration:.4f}s")
    return response


if __name__ == "__main__":
    import uvicorn
    # Local dev mode
    uvicorn.run("app.main:app", host="127.0.0.1", port=20081, reload=True)
```

```python
// File: models\receipt.py
from pydantic import BaseModel
from typing import Optional

class Receipt(BaseModel):
    bill_no: str
    date: str
    month: str
    tenant_name: str
    previous_reading: float
    current_reading: float
    units_consumed: float
    rent: float
    additional_charge: float
    water_charge: float
    electricity_charge: float
    total: float
    pdf_filename: str

class BillRequest(BaseModel):
    tenant: str
    month: str
    current_reading: float
    additional_persons: int
    tank_water: float = 0.0
    maintenance_charge: float = 0.0
    maintenance_desc: str = ""
    previous_arrears: float = 0.0
    amount_received: Optional[float] = None
    payment_status: str = "PENDING"

class PaymentStatusUpdate(BaseModel):
    payment_status: str
    amount_received: Optional[float] = None

class BulkWhatsappRequest(BaseModel):
    bill_nos: list[str]
```

```python
// File: models\tenant.py
from pydantic import BaseModel
from typing import Optional

class Tenant(BaseModel):
    id: Optional[int] = None
    
    # General Info
    name: str
    company: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    room_number: Optional[str] = ""
    occupation: Optional[str] = ""
    notes: Optional[str] = ""
    status: str = "Active" # Active or Inactive

    # Billing Profile
    rent: float = 0.0
    water: float = 0.0
    default_tank_water_charge: float = 0.0
    electricity_rate: float = 0.0
    previous_meter: float = 0.0
    additional_person_charge: float = 0.0
    
    # Security Profile
    security_deposit: float = 0.0
    
    # Utilities
    meter_id: Optional[str] = ""
    
    # NEW: Secure access token for public QR profiles
    view_token: Optional[str] = ""
    
    # NEW: Security PIN for Tenant Portal (Default to 1234)
    tenant_pin: str = "1234"
    
    # NEW: Current arrears (balance due)
    arrears: float = 0.0
```

```python
// File: pages\__init__.py

```

```python
// File: pages\archive.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config
from app.core.routes import Names, Templates
from app.services.billing_service import get_all_receipts

router = APIRouter()

@router.get("/archive", name=Names.ARCHIVE_PAGE, response_class=HTMLResponse)
async def archive_page(request: Request):
    receipts = get_all_receipts()
    archived_receipts = [r for r in receipts if r.get("Status") == "ARCHIVED"]
    archived_receipts.reverse()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name=Templates.ARCHIVE, context={
            "receipts": archived_receipts,
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )
```

```python
// File: pages\backups.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config
from app.core.routes import Names, Templates

router = APIRouter()

@router.get("/backups", name=Names.BACKUPS_PAGE, response_class=HTMLResponse)
async def backups_page(request: Request):
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name=Templates.BACKUPS, context={
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )
```

```python
// File: pages\billing.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config
from app.core.routes import Names, Templates
from app.services.tenant_service import load_tenants
from app.services.billing_service import get_all_receipts

router = APIRouter()

@router.get("/billing", name=Names.BILLING_PAGE, response_class=HTMLResponse)
async def billing_page(request: Request):
    tenants = [t for t in load_tenants() if t.status == "Active"]
    theme = getattr(request.state, "theme", "system")
    receipts_list = get_all_receipts()
    active_receipts = [r for r in receipts_list if r.get("Status", "ACTIVE") == "ACTIVE"]

    return templates.TemplateResponse(
        request=request,
        name=Templates.BILLING,
        context={
            "receipts": active_receipts,
            "tenants": tenants,
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )
```

```python
// File: pages\dashboard.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config
from app.core.routes import Paths, Names, Templates
from app.services.billing_service import get_dashboard_stats

router = APIRouter()

@router.get(Paths.HOME, name=Names.HOME, response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = get_dashboard_stats()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request,
        name=Templates.DASHBOARD,
        context={
            "stats": stats,
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )
```

```python
// File: pages\errors.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.dependencies import templates
from app.core.routes import Templates
from app.core.config_service import config  # Import the configuration service

def register_exception_handlers(app: FastAPI):
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return templates.TemplateResponse(
                request=request,
                name=Templates.ERROR,
                context={
                    "request": request, 
                    "status_code": exc.status_code, 
                    "detail": exc.detail,
                    "sys": config.get("system", {})  # Provide system config context
                },
                status_code=exc.status_code
            )
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return templates.TemplateResponse(
                request=request,
                name=Templates.ERROR,
                context={
                    "request": request, 
                    "status_code": 500, 
                    "detail": "Internal Server Error",
                    "sys": config.get("system", {})  # Provide system config context
                },
                status_code=500
            )
        return JSONResponse({"detail": "Internal Server Error"}, status_code=500)
```

```python
// File: pages\history.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config
from app.core.routes import Names, Templates
from app.services.billing_service import get_all_receipts

router = APIRouter()

@router.get("/history", name=Names.HISTORY_PAGE, response_class=HTMLResponse)
async def history_page(request: Request):
    receipts = get_all_receipts()
    active_receipts = [r for r in receipts if r.get("Status", "ACTIVE") == "ACTIVE"]
    active_receipts.reverse()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name=Templates.HISTORY, context={
            "receipts": active_receipts,
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )
```

```python
// File: pages\public.py
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.routes import Names, Templates
from app.services.tenant_service import load_tenants, update_tenant, get_occupants
from app.services.billing_service import get_all_receipts
import os

router = APIRouter()


def _calc_arrears(tenant, tenant_receipts):
    tenant.arrears = 0.0
    active_receipts = [r for r in tenant_receipts if r.get("Status") != "ARCHIVED"]
    if active_receipts:
        # Before reverse, active_receipts[-1] is the latest
        latest = active_receipts[-1]
        try:
            grand_total = float(latest.get("Total") or 0.0) + float(latest.get("Previous_Arrears") or 0.0)
            amount_received_str = latest.get("Amount_Received", "")
            if amount_received_str in (None, ""):
                amount_received = grand_total
            else:
                amount_received = float(amount_received_str)
            tenant.arrears = grand_total - amount_received
        except ValueError:
            pass

@router.get("/tenant/{tenant_id}", name=Names.TENANT_PROFILE_PAGE, response_class=HTMLResponse)
async def tenant_profile_page(request: Request, tenant_id: int):
    tenants = load_tenants()
    tenant = next((t for t in tenants if t.id == tenant_id), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    if not getattr(tenant, "view_token", None):
        import uuid
        tenant.view_token = str(uuid.uuid4())
        update_tenant(tenant)
        
    receipts = get_all_receipts()
    tenant_receipts = [r for r in receipts if r["Tenant"] == tenant.name]
    _calc_arrears(tenant, tenant_receipts)
    tenant_receipts.reverse()
    
    occupants = get_occupants(tenant.id)
    
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name=Templates.TENANT_PROFILE, context={
            "tenant": tenant,
            "receipts": tenant_receipts,
            "occupants": occupants, 
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )

@router.get("/t/{view_token}", name=Names.PUBLIC_TENANT_PROFILE_GET, response_class=HTMLResponse)
async def public_tenant_profile_get(request: Request, view_token: str):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "view_token", "") == view_token), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")

    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name=Templates.TENANT_PUBLIC_PROFILE, context={
            "tenant": tenant,
            "theme": theme,
            "unlocked": False,
            "view_token": view_token,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )

@router.get("/favicon.ico", name=Names.FAVICON, include_in_schema=False)
async def favicon():
    file_path = os.path.join("app", "static", "fevicon.svg")
    return FileResponse(file_path, media_type="image/svg+xml") if os.path.exists(file_path) else HTMLResponse(status_code=204)



@router.post("/t/{view_token}", name=Names.PUBLIC_TENANT_PROFILE_POST, response_class=HTMLResponse)
async def public_tenant_profile_post(request: Request, view_token: str, pin: str = Form(...)):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "view_token", "") == view_token), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")
        
    theme = getattr(request.state, "theme", "system")
    
    actual_pin = getattr(tenant, "tenant_pin", "1234")
    if pin != actual_pin:
        return templates.TemplateResponse(
            request=request, name=Templates.TENANT_PUBLIC_PROFILE, context={
                "tenant": tenant,
                "theme": theme,
                "unlocked": False,
                "view_token": view_token,
                "error": "Incorrect PIN",
                "sys": getattr(request.state, "sys", config.get("system", {}))
            }
        )
        
    receipts = get_all_receipts()
    tenant_receipts = [r for r in receipts if r["Tenant"] == tenant.name and r.get("Status") != "ARCHIVED"]
    tenant_receipts.reverse()
    sys_conf = config.get("system", {})
    tenant_receipts = tenant_receipts[:config.get("system.limits.public_history_months", 12)] 
    
    occupants = get_occupants(tenant.id)

    return templates.TemplateResponse(
        request=request, name=Templates.TENANT_PUBLIC_PROFILE, context={
            "tenant": tenant,
            "receipts": tenant_receipts,
            "occupants": occupants,
            "theme": theme,
            "unlocked": True,
            "view_token": view_token,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )
```

```python
// File: pages\settings.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config
from app.core.routes import Names, Templates

router = APIRouter()

@router.get("/settings", name=Names.SETTINGS_PAGE, response_class=HTMLResponse)
async def settings_page(request: Request):
    billing_conf = config.get("billing", {})
    landlord_conf = config.get("landlord", {})
    ui_conf = config.get("ui", {})
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name=Templates.SETTINGS, context={
            "billing_config": billing_conf,
            "landlord_config": landlord_conf,
            "ui_config": ui_conf,
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )

# --- REST API ---
```

```python
// File: pages\tenants.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config
from app.core.routes import Names, Templates
from app.services.tenant_service import load_tenants
from app.services.billing_service import get_all_receipts

router = APIRouter()

@router.get("/tenants", name=Names.TENANTS_PAGE, response_class=HTMLResponse)
async def tenants_page(request: Request):
    tenants = load_tenants()
    receipts = get_all_receipts()
    
    for tenant in tenants:
        active_receipts = [r for r in receipts if r["Tenant"] == tenant.name and r.get("Status") != "ARCHIVED"]
        if active_receipts:
            latest = active_receipts[-1]
            try:
                grand_total = float(latest.get("Total") or 0.0) + float(latest.get("Previous_Arrears") or 0.0)
                amount_received_str = latest.get("Amount_Received", "")
                if amount_received_str in (None, ""):
                    amount_received = grand_total
                else:
                    amount_received = float(amount_received_str)
                tenant.arrears = grand_total - amount_received
            except ValueError:
                tenant.arrears = 0.0
        else:
            tenant.arrears = 0.0

    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name=Templates.TENANTS, context={
            "tenants": tenants,
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )
```

```python
// File: services\backup_service.py
import os
import json
import shutil
import hashlib
from datetime import datetime
import platform

from app.core.config_service import config
from app.core.paths import BACKUPS_DIR as BACKUP_DIR, DB_DIR, CONFIG_DIR, RECEIPTS_DIR, UPLOADS_DIR

# Map new storage directories to their legacy names for zip structure compatibility
DIR_MAPPING = {
    DB_DIR: "database",
    CONFIG_DIR: "config",
    RECEIPTS_DIR: "receipts",
    UPLOADS_DIR: "static/uploads/signatures"
}

REGISTRY_FILE = os.path.join(BACKUP_DIR, "registry.json")
LOG_FILE = os.path.join(BACKUP_DIR, "backup.jsonl")

# Ensure subdirectories
for sub in ["automatic/daily", "automatic/weekly", "automatic/monthly", "manual", "restore_points", "emergency"]:
    os.makedirs(os.path.join(BACKUP_DIR, sub), exist_ok=True)

def _log(operation, type_, status, duration_ms, details=None):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        "type": type_,
        "status": status,
        "duration_ms": duration_ms
    }
    if details:
        log_entry["details"] = details
        
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except:
        pass

def load_registry():
    if not os.path.exists(REGISTRY_FILE):
        return {"version": 1, "backups": []}
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"version": 1, "backups": []}

def save_registry(registry):
    try:
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=4)
    except Exception as e:
        print(f"Error saving registry: {e}")

def hash_file(filepath):
    h = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
    except Exception:
        return ""
    return h.hexdigest()

def hash_directory(dirpath):
    h = hashlib.sha256()
    if not os.path.exists(dirpath):
        return h.hexdigest()
        
    for root, dirs, files in os.walk(dirpath):
        for names in sorted(files):
            filepath = os.path.join(root, names)
            try:
                with open(filepath, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        h.update(chunk)
            except Exception:
                pass
    return h.hexdigest()

def create_manifest(backup_id, backup_type, timestamp_str):
    schema_conf = config.get("schema", {})
    return {
        "application": "Rent Receipt System",
        "version": "3.0.0",
        "schema": schema_conf.get("receipt_schema", 4),
        "created": timestamp_str,
        "platform": platform.system(),
        "backup_type": backup_type,
        "backup_id": backup_id
    }

def get_db_stats():
    # Count receipts, tenants, PDFs
    import csv
    receipt_count = 0
    archived_count = 0
    tenant_count = 0
    inactive_tenant_count = 0
    pdf_count = 0
    
    if os.path.exists(os.path.join(DB_DIR, "receipts.csv")):
        try:
            with open(os.path.join(DB_DIR, "receipts.csv"), "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    receipt_count += 1
                    if r.get("Status") == "ARCHIVED":
                        archived_count += 1
        except:
            pass
            
    if os.path.exists(os.path.join(DB_DIR, "tenants.csv")):
        try:
            with open(os.path.join(DB_DIR, "tenants.csv"), "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    tenant_count += 1
                    if r.get("Status") == "Inactive":
                        inactive_tenant_count += 1
        except:
            pass
            
    for root, dirs, files in os.walk(RECEIPTS_DIR):
        for f in files:
            if f.endswith(".pdf"):
                pdf_count += 1
                
    return receipt_count, archived_count, tenant_count, inactive_tenant_count, pdf_count

def create_metadata(backup_id, backup_type, timestamp_str):
    schema_conf = config.get("schema", {})
    ui_conf = config.get("ui", {})
    r_count, arc_count, t_count, it_count, p_count = get_db_stats()
    
    metadata = {
        "id": backup_id,
        "type": backup_type,
        "date": timestamp_str,
        "application_version": "3.0.0",
        "schema_version": schema_conf.get("receipt_schema", 4),
        "created_by": "System",
        "machine_name": platform.node(),
        "os": platform.system(),
        "receipt_count": r_count,
        "archived_receipt_count": arc_count,
        "tenant_count": t_count,
        "inactive_tenant_count": it_count,
        "pdf_count": p_count,
        "theme": ui_conf.get("theme", "system"),
        "checksums": {
            "database": hash_directory(DB_DIR),
            "config": hash_directory(CONFIG_DIR),
            "receipts": hash_directory(RECEIPTS_DIR)
        },
        "verified": True,
        "compressed": True,
        "password_protected": False
    }
    return metadata

def create_backup(type_="Manual", subtype="manual", tag=""):
    """
    type_: 'Manual', 'Automatic', 'Restore Point', 'Emergency'
    subtype: 'manual', 'daily', 'weekly', 'monthly', 'before_edit', etc.
    """
    start_time = datetime.now()
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    timestamp_iso = start_time.isoformat()
    backup_id = f"BKP-{start_time.strftime('%Y%m%d-%H%M%S')}"
    
    if type_ == "Restore Point":
        dest_folder = "restore_points"
        filename = f"{subtype}_{timestamp}.zip"
    elif type_ == "Automatic":
        dest_folder = f"automatic/{subtype}"
        filename = f"{subtype}_{timestamp}.zip"
    elif type_ == "Emergency":
        dest_folder = "emergency"
        filename = f"emergency_{timestamp}.zip"
    else:
        dest_folder = "manual"
        filename = f"manual_{timestamp}.zip"
        
    rel_path = f"{dest_folder}/{filename}"
    abs_path = os.path.join(BACKUP_DIR, dest_folder, filename)
    
    temp_dir = os.path.join(BACKUP_DIR, "temp_backup_staging")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Copy dirs mapping real paths to internal zip structure
        for real_path, legacy_name in DIR_MAPPING.items():
            if os.path.exists(real_path):
                shutil.copytree(real_path, os.path.join(temp_dir, legacy_name))
                
        # Generate manifest & metadata
        manifest = create_manifest(backup_id, type_, timestamp_iso)
        with open(os.path.join(temp_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=4)
            
        metadata = create_metadata(backup_id, type_, timestamp_iso)
        if tag:
            metadata["notes"] = tag
            
        with open(os.path.join(temp_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=4)
            
        # Zip
        zip_base = abs_path.replace(".zip", "")
        shutil.make_archive(zip_base, 'zip', temp_dir)
        
        # Calculate size and zip checksum
        size_bytes = os.path.getsize(abs_path)
        size_mb = f"{size_bytes / (1024 * 1024):.1f} MB"
        metadata["size"] = size_mb
        metadata["filename"] = filename
        metadata["path"] = rel_path
        metadata["zip_sha256"] = hash_file(abs_path)
        
        # Update registry
        registry = load_registry()
        registry["backups"].insert(0, metadata) # Add at top
        save_registry(registry)
        
        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        _log("Backup", type_, "Success", duration, {"backup_id": backup_id, "path": rel_path})
        
        # Cleanup old backups depending on type (implement later in 14B)
        
        return metadata
    except Exception as e:
        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        _log("Backup", type_, "Failed", duration, {"error": str(e)})
        raise e
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

def create_full_backup(tag="auto"):
    # Wrapper for existing calls in app.py
    # Decipher tag
    if tag == "auto" or not tag:
        return create_backup(type_="Automatic", subtype="daily")
    elif tag.startswith("settings_change"):
        return create_backup(type_="Restore Point", subtype="before_settings", tag="Settings Change")
    elif tag.startswith("create_bill"):
        return create_backup(type_="Restore Point", subtype="before_receipt", tag="Receipt Creation")
    elif tag.startswith("edit_bill"):
        return create_backup(type_="Restore Point", subtype="before_edit", tag="Receipt Edit")
    elif tag.startswith("archive_bill"):
        return create_backup(type_="Restore Point", subtype="before_archive", tag="Receipt Archive")
    elif tag.startswith("restore_bill"):
        return create_backup(type_="Restore Point", subtype="before_restore", tag="Receipt Restore")
    elif tag.startswith("delete_bill"):
        return create_backup(type_="Restore Point", subtype="before_delete", tag="Receipt Delete")
    elif tag.startswith("add_tenant") or tag.startswith("update_tenant") or tag.startswith("delete_tenant"):
        return create_backup(type_="Restore Point", subtype="before_tenant_update", tag="Tenant Update")
    else:
        return create_backup(type_="Manual", subtype="manual", tag=tag)

def get_all_backups():
    return load_registry()

def verify_backup_integrity(backup_id):
    registry = load_registry()
    backup_meta = next((b for b in registry["backups"] if b["id"] == backup_id), None)
    if not backup_meta:
        raise Exception("Backup not found in registry")
        
    abs_path = os.path.join(BACKUP_DIR, backup_meta["path"])
    if not os.path.exists(abs_path):
        raise Exception("Backup ZIP file is missing")
        
    current_hash = hash_file(abs_path)
    if current_hash != backup_meta.get("zip_sha256"):
        raise Exception("Backup ZIP checksum mismatch (corrupted)")
        
    return True

def restore_backup(backup_id):
    start_time = datetime.now()
    try:
        verify_backup_integrity(backup_id)
        
        registry = load_registry()
        backup_meta = next((b for b in registry["backups"] if b["id"] == backup_id))
        abs_path = os.path.join(BACKUP_DIR, backup_meta["path"])
        
        # 1. Create Temporary Backup (Rollback Point)
        temp_backup = create_backup(type_="Emergency", subtype="before_restore", tag=f"Before restoring {backup_id}")
        temp_abs_path = os.path.join(BACKUP_DIR, temp_backup["path"])
        
        # 2. Extract Backup to staging
        staging_dir = os.path.join(BACKUP_DIR, "restore_staging")
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir, ignore_errors=True)
        os.makedirs(staging_dir, exist_ok=True)
        
        shutil.unpack_archive(abs_path, staging_dir, 'zip')
        
        # 3. Validation
        if not os.path.exists(os.path.join(staging_dir, "database")) or not os.path.exists(os.path.join(staging_dir, "config")):
            raise Exception("Invalid backup archive structure")
            
        # 4. Replacement
        for real_path, legacy_name in DIR_MAPPING.items():
            src = os.path.join(staging_dir, legacy_name)
            dst = real_path
            if os.path.exists(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst)
                
        # 5. Cleanup Staging
        shutil.rmtree(staging_dir, ignore_errors=True)
        
        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        _log("Restore", "Full", "Success", duration, {"backup_id": backup_id})
        return True
        
    except Exception as e:
        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        _log("Restore", "Full", "Failed", duration, {"error": str(e), "backup_id": backup_id})
        raise e

def delete_backup(backup_id):
    registry = load_registry()
    for i, b in enumerate(registry["backups"]):
        if b["id"] == backup_id:
            abs_path = os.path.join(BACKUP_DIR, b["path"])
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except:
                    pass
            registry["backups"].pop(i)
            save_registry(registry)
            return True
    return False
```

```python
// File: services\billing_service.py
import csv
import os
import shutil
from datetime import datetime
from app.core.config_service import config
from app.services.tenant_service import load_tenants, update_tenant
from app.services.pdf_service import generate_professional_pdf

from app.core.paths import DB_DIR, BACKUPS_DIR as BACKUP_DIR, RECEIPTS_DIR

RECEIPTS_CSV = os.path.join(DB_DIR, "receipts.csv")

HEADERS = [
    "Bill", "Date", "Month", "Tenant", "Previous", "Current", 
    "Units", "Rent", "Additional", "Water", "Tank_Water", "Electricity", "Total", "PDF",
    "Tenant_Phone", "Tenant_Company", "Tenant_Address", "Rate",
    "Status", "Archived_Date", "Archived_By", "Deleted_Date",
    "Additional_Persons", "Additional_Person_Rate", "Receipt_Version", "Generated_By",
    "Payment_Status", "Maintenance_Charge", "Maintenance_Desc",
    "Previous_Arrears", "Amount_Received" # --- NEW COLUMNS ---
]

def migrate_receipts_schema():
    schema_conf = config.get("schema", {})
    current_version = schema_conf.get("receipt_schema", 1)
    
    if current_version < 2:
        # V1 to V2 Migration: Add lifecycle columns
        print("Migrating receipts.csv from V1 to V2...")
        if os.path.exists(RECEIPTS_CSV):
            receipts = []
            try:
                with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["Status"] = "ACTIVE"
                        row["Archived_Date"] = ""
                        row["Archived_By"] = ""
                        row["Deleted_Date"] = ""
                        receipts.append(row)
                
                backup_path = os.path.join(BACKUP_DIR, "receipts_v1_migration.bak")
                shutil.copy2(RECEIPTS_CSV, backup_path)
                
                with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(receipts)
                    
                print("Migrating PDFs to active directory structure...")
                for row in receipts:
                    try:
                        year_str = row["Month"].split()[-1]
                    except Exception:
                        year_str = datetime.now().strftime("%Y")
                    
                    old_pdf_path = os.path.join(RECEIPTS_DIR, year_str, row["PDF"])
                    new_dir = os.path.join(RECEIPTS_DIR, "active", year_str)
                    new_pdf_path = os.path.join(new_dir, row["PDF"])
                    
                    if os.path.exists(old_pdf_path):
                        os.makedirs(new_dir, exist_ok=True)
                        shutil.move(old_pdf_path, new_pdf_path)
            except Exception as e:
                print(f"Error migrating receipts to V2: {e}")
        
        schema_conf["receipt_schema"] = 2
        config.save("schema", schema_conf)

    if current_version < 3:
        # V2 to V3 Migration: Add Additional_Persons, Additional_Person_Rate, Receipt_Version
        print("Migrating receipts.csv from V2 to V3...")
        if os.path.exists(RECEIPTS_CSV):
            receipts = []
            try:
                with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["Additional_Persons"] = "0"
                        row["Additional_Person_Rate"] = "0.0"
                        row["Receipt_Version"] = "3"
                        receipts.append(row)
                        
                backup_path = os.path.join(BACKUP_DIR, "receipts_v2_migration.bak")
                shutil.copy2(RECEIPTS_CSV, backup_path)
                
                with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(receipts)
            except Exception as e:
                print(f"Error migrating receipts to V3: {e}")
                
        schema_conf["receipt_schema"] = 3
        config.save("schema", schema_conf)
        current_version = 3

    if current_version < 4:
        # V3 to V4 Migration: Add Tank_Water and Generated_By
        print("Migrating receipts.csv from V3 to V4...")
        if os.path.exists(RECEIPTS_CSV):
            receipts = []
            try:
                with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["Tank_Water"] = "0.0"
                        row["Generated_By"] = "Admin"
                        row["Receipt_Version"] = "4"
                        receipts.append(row)
                        
                backup_path = os.path.join(BACKUP_DIR, "receipts_v3_migration.bak")
                shutil.copy2(RECEIPTS_CSV, backup_path)
                
                with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(receipts)
            except Exception as e:
                print(f"Error migrating receipts to V4: {e}")
                
        schema_conf["receipt_schema"] = 4
        config.save("schema", schema_conf)
        current_version = 4

    if current_version < 5:
        # V4 to V5 Migration: Bump Receipt_Version for Bank Details layout
        print("Migrating receipts.csv from V4 to V5...")
        if os.path.exists(RECEIPTS_CSV):
            receipts = []
            try:
                with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["Receipt_Version"] = "5"
                        receipts.append(row)
                        
                backup_path = os.path.join(BACKUP_DIR, "receipts_v4_migration.bak")
                shutil.copy2(RECEIPTS_CSV, backup_path)
                
                with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(receipts)
            except Exception as e:
                print(f"Error migrating receipts to V5: {e}")
                
        schema_conf["receipt_schema"] = 5
        config.save("schema", schema_conf)
        current_version = 5

    if current_version < 6:
        # V5 to V6 Migration: Add Payment_Status column
        print("Migrating receipts.csv from V5 to V6...")
        if os.path.exists(RECEIPTS_CSV):
            receipts = []
            try:
                with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["Payment_Status"] = "PENDING"
                        receipts.append(row)
                        
                backup_path = os.path.join(BACKUP_DIR, "receipts_v5_migration.bak")
                shutil.copy2(RECEIPTS_CSV, backup_path)
                
                with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(receipts)
            except Exception as e:
                print(f"Error migrating receipts to V6: {e}")
                
        schema_conf["receipt_schema"] = 6
        config.save("schema", schema_conf)
        current_version = 6

    if current_version < 7:
        # V6 to V7 Migration: Add Maintenance_Charge and Maintenance_Desc
        print("Migrating receipts.csv from V6 to V7...")
        if os.path.exists(RECEIPTS_CSV):
            receipts = []
            try:
                with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["Maintenance_Charge"] = "0.0"
                        row["Maintenance_Desc"] = ""
                        receipts.append(row)
                        
                backup_path = os.path.join(BACKUP_DIR, "receipts_v6_migration.bak")
                shutil.copy2(RECEIPTS_CSV, backup_path)
                
                with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(receipts)
            except Exception as e:
                print(f"Error migrating receipts to V7: {e}")
                
        schema_conf["receipt_schema"] = 7
        config.save("schema", schema_conf)
        current_version = 7

    if current_version < 8:
        # V7 to V8 Migration: Add Previous_Arrears and Amount_Received columns
        print("Migrating receipts.csv from V7 to V8 (Arrears & Payments)...")
        if os.path.exists(RECEIPTS_CSV):
            receipts = []
            try:
                with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["Previous_Arrears"] = "0.0"
                        # Assume historically that all total bills were fully received.
                        row["Amount_Received"] = row.get("Total", "0.0")
                        row["Receipt_Version"] = "8"
                        receipts.append(row)
                        
                backup_path = os.path.join(BACKUP_DIR, "receipts_v7_migration.bak")
                shutil.copy2(RECEIPTS_CSV, backup_path)
                
                with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(receipts)
            except Exception as e:
                print(f"Error migrating receipts to V8: {e}")
                
        schema_conf["receipt_schema"] = 8
        config.save("schema", schema_conf)
        current_version = 8

def init_csv():
    if not os.path.exists(RECEIPTS_CSV):
        with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)

def get_bill_details(bill_no):
    init_csv()
    with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Bill"] == bill_no:
                return row
    return None

def resolve_payment_state(current_total, previous_arrears=0.0, amount_received=None):
    current_total = float(current_total or 0)
    previous_arrears = float(previous_arrears or 0)
    grand_total = round(current_total + previous_arrears, 2)
    received = round(float(amount_received or 0), 2)

    if received <= 0:
        return {
            "payment_status": "PENDING",
            "grand_total": grand_total,
            "amount_received": 0.0,
            "balance_due": max(grand_total, 0.0),
            "advance_amount": max(-grand_total, 0.0) if grand_total < 0 else 0.0
        }

    if received < grand_total:
        return {
            "payment_status": "PARTIAL",
            "grand_total": grand_total,
            "amount_received": received,
            "balance_due": round(grand_total - received, 2),
            "advance_amount": 0.0
        }

    if received == grand_total:
        return {
            "payment_status": "PAID",
            "grand_total": grand_total,
            "amount_received": received,
            "balance_due": 0.0,
            "advance_amount": 0.0
        }

    return {
        "payment_status": "ADVANCE",
        "grand_total": grand_total,
        "amount_received": received,
        "balance_due": 0.0,
        "advance_amount": round(received - grand_total, 2)
    }

def update_payment_status(bill_no, requested_status, amount_received=None):
    receipts = get_all_receipts()
    receipt = next((r for r in receipts if r.get("Bill") == bill_no), None)
    if not receipt:
        raise ValueError("Bill not found")

    grand_total = round(
        float(receipt.get("Total", 0) or 0) +
        float(receipt.get("Previous_Arrears", 0) or 0), 2
    )

    if requested_status == "PENDING":
        receipt["Payment_Status"] = "PENDING"
        receipt["Amount_Received"] = 0.0
        save_all_receipts(receipts)
        return receipt

    resolved = resolve_payment_state(
        current_total=float(receipt.get("Total", 0) or 0),
        previous_arrears=float(receipt.get("Previous_Arrears", 0) or 0),
        amount_received=amount_received
    )

    receipt["Payment_Status"] = resolved["payment_status"]
    receipt["Amount_Received"] = resolved["amount_received"]
    save_all_receipts(receipts)
    return receipt

def get_all_receipts():
    init_csv()
    migrate_receipts_schema()
    receipts = []
    try:
        with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                receipts.append(row)
    except Exception as e:
        print(f"Error loading receipts: {e}")
    return receipts

def get_receipt(bill_no):
    receipts = get_all_receipts()
    for r in receipts:
        if r["Bill"] == bill_no:
            return r
    return None

def save_all_receipts(receipts_list):
    init_csv()
    if os.path.exists(RECEIPTS_CSV):
        backup_path = os.path.join(BACKUP_DIR, "receipts.csv.bak")
        try:
            shutil.copy2(RECEIPTS_CSV, backup_path)
        except Exception:
            pass
            
    try:
        with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            writer.writeheader()
            writer.writerows(receipts_list)
    except Exception as e:
        print(f"Error saving receipts: {e}")

def get_billing_months():
    now = datetime.now()
    current_year = now.year
    current_month_idx = now.month 
    
    months_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    
    months_list = []
    for i in range(current_month_idx):
        months_list.append(f"{months_names[i]} {current_year}")
        
    return {
        "currentMonth": f"{months_names[current_month_idx - 1]} {current_year}",
        "months": months_list
    }

def calculate_charges(current_reading, additional_persons, prev_reading, rent, water, tank_water, maintenance_charge, rate, add_person_charge):
    units = max(0.0, current_reading - prev_reading)
    electricity = units * rate
    additional = additional_persons * add_person_charge
    total = rent + additional + water + tank_water + maintenance_charge + electricity
    
    return {
        "rent": rent,
        "water": water,
        "tank_water": tank_water,
        "maintenance_charge": maintenance_charge,
        "rate": rate,
        "additional": additional,
        "units": units,
        "electricity": electricity,
        "total": total,
        "previous": prev_reading
    }

def create_bill(tenant_name, month, current_reading, additional_persons, tank_water, maintenance_charge, maintenance_desc, previous_arrears=0.0, amount_received=None, payment_status="PENDING"):
    receipts = get_all_receipts()
    for r in receipts:
        if r["Tenant"] == tenant_name and r["Month"] == month and r.get("Status", "ACTIVE") == "ACTIVE":
            raise ValueError(f"A receipt for '{tenant_name}' for '{month}' already exists (Bill #{r['Bill']}). Please edit the existing bill instead.")
            
    billing_conf = config.get("billing", {})
    tenants = load_tenants()
    
    tenant_details = next((t for t in tenants if t.name == tenant_name), None)
    if not tenant_details:
        raise ValueError("Tenant not found")
        
    t_phone = tenant_details.phone
    t_company = tenant_details.company
    t_address = tenant_details.address
    
    charges = calculate_charges(
        current_reading, 
        additional_persons,
        prev_reading=tenant_details.previous_meter,
        rent=tenant_details.rent,
        water=tenant_details.water,
        tank_water=tank_water,
        maintenance_charge=maintenance_charge,
        rate=tenant_details.electricity_rate,
        add_person_charge=tenant_details.additional_person_charge
    )
    
    tenant_receipts = [r for r in receipts if r["Tenant"] == tenant_name]
    max_seq = 0
    for r in tenant_receipts:
        try:
            bill_str = r["Bill"]
            seq = int(bill_str.split('-')[-1]) if '-' in bill_str else int(bill_str)
            max_seq = max(max_seq, seq)
        except ValueError:
            pass
            
    bill_no = f"T{tenant_details.id}-{str(max_seq + 1).zfill(3)}"
    date_str = datetime.now().strftime("%d %B %Y")
    
    try:
        year_str = month.split()[-1]
    except Exception:
        year_str = datetime.now().strftime("%Y")
        
    pdf_filename = f"{bill_no}.pdf"
    
    grand_total = charges["total"] + previous_arrears
    if amount_received is None:
        amount_received = grand_total if payment_status == "PAID" else 0.0
        
    resolved = resolve_payment_state(
        current_total=charges["total"],
        previous_arrears=previous_arrears,
        amount_received=amount_received
    )
    payment_status = resolved["payment_status"]
    amount_received = resolved["amount_received"]
    
    data_dict = {
        "Bill": bill_no,
        "Date": date_str,
        "Month": month,
        "Tenant": tenant_name,
        "Previous": charges["previous"],
        "Current": current_reading,
        "Units": charges["units"],
        "Rent": charges["rent"],
        "Additional": charges["additional"],
        "Water": charges["water"],
        "Tank_Water": charges["tank_water"],
        "Electricity": charges["electricity"],
        "Total": charges["total"],
        "PDF": pdf_filename,
        "Tenant_Phone": t_phone,
        "Tenant_Company": t_company,
        "Tenant_Address": t_address,
        "Rate": charges["rate"],
        "Status": "ACTIVE",
        "Archived_Date": "",
        "Archived_By": "",
        "Deleted_Date": "",
        "Additional_Persons": additional_persons,
        "Additional_Person_Rate": tenant_details.additional_person_charge,
        "Receipt_Version": 8,
        "Generated_By": "Admin",
        "Payment_Status": payment_status,
        "Maintenance_Charge": maintenance_charge,
        "Maintenance_Desc": maintenance_desc,
        "Previous_Arrears": previous_arrears,
        "Amount_Received": amount_received
    }
    
    init_csv()
    receipts = get_all_receipts()
    receipts.append(data_dict)
    save_all_receipts(receipts)
    
    config.save("billing", billing_conf)
    
    tenant_details.previous_meter = float(current_reading)
    update_tenant(tenant_details)
    
    return data_dict

def update_bill(bill_no, tenant_name, month, current_reading, additional_persons, tank_water, maintenance_charge, maintenance_desc, previous_arrears=0.0, amount_received=None, payment_status="PENDING"):
    receipts = get_all_receipts()
    receipt = next((r for r in receipts if r["Bill"] == bill_no), None)
    if not receipt:
        raise ValueError("Receipt not found")
        
    tenants = load_tenants()
    tenant_details = next((t for t in tenants if t.name == tenant_name), None)
    
    prev_reading = float(receipt["Previous"])
    snap_rent = float(receipt.get("Rent", 0.0))
    snap_water = float(receipt.get("Water", 0.0))
    snap_tank_water = float(receipt.get("Tank_Water", 0.0))
    snap_rate = float(receipt.get("Rate", 0.0))
    
    snap_add_rate = float(receipt.get("Additional_Person_Rate", 0.0))
    if snap_add_rate == 0.0 and int(receipt.get("Receipt_Version", 2)) < 3 and tenant_details:
        snap_add_rate = tenant_details.additional_person_charge
    
    charges = calculate_charges(
        current_reading, 
        additional_persons, 
        prev_reading=prev_reading,
        rent=snap_rent,
        water=snap_water,
        tank_water=tank_water,
        maintenance_charge=maintenance_charge,
        rate=snap_rate,
        add_person_charge=snap_add_rate
    )
    
    pdf_filename = receipt.get("PDF", f"{bill_no}.pdf")
    status = receipt.get("Status", "ACTIVE")
    
    grand_total = charges["total"] + previous_arrears
    if amount_received is None:
        amount_received = grand_total if payment_status == "PAID" else 0.0
        
    resolved = resolve_payment_state(
        current_total=charges["total"],
        previous_arrears=previous_arrears,
        amount_received=amount_received
    )
    payment_status = resolved["payment_status"]
    amount_received = resolved["amount_received"]
    
    updated_dict = {
        "Bill": bill_no,
        "Date": receipt["Date"],
        "Month": month,
        "Tenant": tenant_name,
        "Previous": prev_reading,
        "Current": current_reading,
        "Units": charges["units"],
        "Rent": charges["rent"],
        "Additional": charges["additional"],
        "Water": charges["water"],
        "Tank_Water": charges["tank_water"],
        "Electricity": charges["electricity"],
        "Total": charges["total"],
        "PDF": pdf_filename,
        "Tenant_Phone": receipt.get("Tenant_Phone", ""),
        "Tenant_Company": receipt.get("Tenant_Company", ""),
        "Tenant_Address": receipt.get("Tenant_Address", ""),
        "Rate": charges["rate"],
        "Status": status,
        "Archived_Date": receipt.get("Archived_Date", ""),
        "Archived_By": receipt.get("Archived_By", ""),
        "Deleted_Date": receipt.get("Deleted_Date", ""),
        "Additional_Persons": receipt.get("Additional_Persons", 0),
        "Additional_Person_Rate": receipt.get("Additional_Person_Rate", 0.0),
        "Receipt_Version": receipt.get("Receipt_Version", 8),
        "Generated_By": receipt.get("Generated_By", "Admin"),
        "Payment_Status": payment_status,
        "Maintenance_Charge": maintenance_charge,
        "Maintenance_Desc": maintenance_desc,
        "Previous_Arrears": previous_arrears,
        "Amount_Received": amount_received
    }
    
    for idx, item in enumerate(receipts):
        if item["Bill"] == bill_no:
            receipts[idx] = updated_dict
            break
    save_all_receipts(receipts)
    
    return updated_dict

def archive_bill(bill_no):
    receipts = get_all_receipts()
    receipt = next((r for r in receipts if r["Bill"] == bill_no), None)
    if not receipt:
        raise ValueError("Receipt not found")
        
    if receipt.get("Status") == "ARCHIVED":
        return receipt

    for idx, r in enumerate(receipts):
        if r["Bill"] == bill_no:
            receipts[idx]["Status"] = "ARCHIVED"
            receipts[idx]["Archived_Date"] = datetime.now().strftime("%Y-%m-%d")
            receipts[idx]["Archived_By"] = "Admin"
            break
            
    save_all_receipts(receipts)
    return receipt

def restore_bill(bill_no):
    receipts = get_all_receipts()
    receipt = next((r for r in receipts if r["Bill"] == bill_no), None)
    if not receipt:
        raise ValueError("Receipt not found")
        
    if receipt.get("Status") == "ACTIVE":
        return receipt

    for idx, r in enumerate(receipts):
        if r["Bill"] == bill_no:
            receipts[idx]["Status"] = "ACTIVE"
            receipts[idx]["Archived_Date"] = ""
            receipts[idx]["Archived_By"] = ""
            break
            
    save_all_receipts(receipts)
    return receipt

def delete_bill(bill_no):
    receipts = get_all_receipts()
    receipt = next((r for r in receipts if r["Bill"] == bill_no), None)
    if not receipt:
        raise ValueError("Receipt not found")
        
    if receipt.get("Status") != "ARCHIVED":
        raise ValueError("Only archived receipts can be permanently deleted.")
        
    receipts = [r for r in receipts if r["Bill"] != bill_no]
    save_all_receipts(receipts)

def get_dashboard_stats():
    billing_conf = config.get("billing", {})
    receipts = get_all_receipts()
    tenants = load_tenants()
    
    next_bill = str(billing_conf.get("next_bill_number", 1)).zfill(3)
    
    now = datetime.now()
    current_year = now.year
    current_month_idx = now.month
    months_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    current_month_str = f"{months_names[current_month_idx - 1]} {current_year}"
    
    if current_month_idx == 1:
        prev_month_idx = 12
        prev_year = current_year - 1
    else:
        prev_month_idx = current_month_idx - 1
        prev_year = current_year
    prev_month_str = f"{months_names[prev_month_idx - 1]} {prev_year}"
    
    active_tenants = len([t for t in tenants if t.status == "Active"])
    inactive_tenants = len([t for t in tenants if t.status == "Inactive"])
    total_tenants = len(tenants)
    
    active_receipts = [r for r in receipts if r.get("Status", "ACTIVE") == "ACTIVE"]
    archived_receipts = [r for r in receipts if r.get("Status") == "ARCHIVED"]
    total_active_receipts = len(active_receipts)
    total_archived_receipts = len(archived_receipts)
    total_receipts_all = total_active_receipts + total_archived_receipts
    
    monthly_revenue = 0.0
    prev_monthly_revenue = 0.0
    pending_payments_count = 0
    pending_amount = 0.0
    amount_collected = 0.0
    electricity_consumed_this_month = 0.0
    highest_meter_reading = 0.0
    paid_bills_count = 0
    
    for r in active_receipts:
        try:
            current_reading = float(r.get("Current", 0.0))
            if current_reading > highest_meter_reading:
                highest_meter_reading = current_reading
        except ValueError:
            pass
            
        status = r.get("Payment_Status", "PENDING")
        gross_amount = float(r.get("Total", 0) or 0) + float(r.get("Previous_Arrears", 0) or 0)

        raw_recv = r.get("Amount_Received")
        received = float(raw_recv) if raw_recv not in (None, "") else (gross_amount if status == "PAID" else 0.0)
        outstanding = max(gross_amount - received, 0.0)

        is_paid = status == "PAID"
        is_partial = status == "PARTIAL"
        is_due = status in ["PENDING", "PARTIAL"]

        amount_collected += received

        if r.get("Month") == current_month_str:
            monthly_revenue += received

        if r.get("Month") == prev_month_str:
            prev_monthly_revenue += received

        if is_due:
            pending_payments_count += 1
            if outstanding > 0:
                pending_amount += outstanding

        if is_paid:
            paid_bills_count += 1
            

            
        if r.get("Month") == current_month_str:
            try:
                electricity_consumed_this_month += float(r.get("Units", 0.0))
            except ValueError:
                pass
            
    revenue_change_str = ""
    if prev_monthly_revenue == 0.0:
        revenue_change_str = "New Month"
    else:
        diff = monthly_revenue - prev_monthly_revenue
        pct = (diff / prev_monthly_revenue) * 100
        sign = "+" if diff > 0 else ""
        revenue_change_str = f"{sign}{pct:.2f}%"
        
    collection_rate = 0.0
    if total_active_receipts > 0:
        collection_rate = (paid_bills_count / total_active_receipts) * 100
        
    recent_bills = []
    for r in reversed(active_receipts[-5:]):
        recent_bills.append({
            "bill_no": r["Bill"],
            "tenant_name": r["Tenant"],
            "total": float(r.get("Total", 0)) + float(r.get("Previous_Arrears", 0)),
            "amount_received": float(r.get("Amount_Received", 0) or 0),
            "month": r["Month"],
            "payment_status": r.get("Payment_Status", "PENDING")
        })
        
    revenue_chart_data = {m: 0.0 for m in months_names}
    electricity_chart_data = {m: 0.0 for m in months_names}
    
    for r in active_receipts:
        try:
            r_month, r_year = r["Month"].split()
            if r_year == str(current_year) and r_month in revenue_chart_data:
                revenue_chart_data[r_month] += float(r.get("Amount_Received", r.get("Total", 0)))
                electricity_chart_data[r_month] += float(r.get("Units", 0.0))
        except Exception:
            pass
            
    chart_months = [m for m in months_names if revenue_chart_data[m] > 0 or electricity_chart_data[m] > 0]
    if not chart_months:
        chart_months = months_names[:current_month_idx]
        
    revenue_list = [revenue_chart_data[m] for m in chart_months]
    electricity_list = [electricity_chart_data[m] for m in chart_months]
    
    return {
        "next_bill": next_bill,
        "current_month": current_month_str,
        "monthly_revenue": monthly_revenue,
        "prev_monthly_revenue": prev_monthly_revenue,
        "revenue_change_str": revenue_change_str,
        "total_active_receipts": total_active_receipts,
        "total_archived_receipts": total_archived_receipts,
        "total_receipts_all": total_receipts_all,
        "active_tenants": active_tenants,
        "inactive_tenants": inactive_tenants,
        "total_tenants": total_tenants,
        "highest_meter_reading": highest_meter_reading,
        "electricity_consumed": electricity_consumed_this_month,
        "pending_payments_count": pending_payments_count,
        "pending_amount": pending_amount,
        "amount_collected": amount_collected,
        "collection_rate": collection_rate,
        "recent_bills": recent_bills,
        "chart_labels": chart_months,
        "chart_revenue": revenue_list,
        "chart_electricity": electricity_list
    }
```

```python
// File: services\pdf_service.py
import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from num2words import num2words
from datetime import datetime
import sys
from app.core.paths import UPLOADS_DIR
from app.services.tenant_service import load_tenants
from app.core.config_service import config

font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'fonts')

try:
    pdfmetrics.registerFont(TTFont('NotoSans', os.path.join(font_dir, 'NotoSans-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('NotoSans-Bold', os.path.join(font_dir, 'NotoSans-Bold.ttf')))
    pdfmetrics.registerFont(TTFont('NotoSans-Italic', os.path.join(font_dir, 'NotoSans-Italic.ttf')))
except Exception as e:
    print(f"WARNING: Missing custom fonts in {font_dir}. PDFs may generate without the ₹ symbol. Error: {e}", file=sys.stderr)

def _safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def generate_professional_pdf(data, landlord_config, output_path=None):
    # Live Tenant Sync Engine: Override PDF with the most current tenant attributes
    tenants = load_tenants()
    tenant_name = data.get('Tenant', 'Unknown')
    current_tenant = next((t for t in tenants if t.name == tenant_name), None)
    if current_tenant:
        data['Tenant_Phone'] = current_tenant.phone
        data['Tenant_Company'] = current_tenant.company
        data['Tenant_Address'] = current_tenant.address

    is_stream = False
    if output_path is None:
        output_path = io.BytesIO()
        is_stream = True
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    tenant_name = data.get('Tenant', 'Unknown')
    bill_no = data.get('Bill', '000')
    date_str = data.get('Date', '')
    try:
        date_obj = datetime.strptime(date_str, "%d %B %Y")
        formatted_date = date_obj.strftime("%Y%m%d")
    except Exception:
        formatted_date = date_str.replace(" ", "")

    safe_tenant_name = tenant_name.replace(" ", "_")
    pdf_title = f"{safe_tenant_name}_{formatted_date}_{bill_no}"
    c.setTitle(pdf_title)
    
    c.setLineWidth(1)
    c.rect(30, 30, width - 60, height - 60)
    
    c.setFont("NotoSans-Bold", 24)
    c.drawCentredString(width / 2.0, height - 70, "RENT RECEIPT")
    
    c.setLineWidth(2)
    c.line(40, height - 85, width - 40, height - 85)
    
    c.setFont("NotoSans", 11)
    y = height - 105
    c.drawString(50, y, f"Receipt No: {data['Bill']}")
    c.drawCentredString(width / 2.0, y, f"Billing Month: {data['Month']}")
    c.drawRightString(width - 50, y, f"Date: {data['Date']}")
    y -= 15
    
    
    c.setLineWidth(1)
    y -= 10
    c.line(40, y, width - 40, y)
    
    y -= 15 
    styles = getSampleStyleSheet()
    style_normal = styles["Normal"]
    style_normal.fontName = "NotoSans"
    style_normal.fontSize = 10
    style_normal.leading = 14
    
    style_heading = ParagraphStyle('Heading', parent=style_normal, fontName='NotoSans-Bold', fontSize=12, spaceAfter=8)
    
    landlord_html = f"<b>Name:</b> {landlord_config.get('name', '')}<br/>" \
                    f"<b>Phone:</b> {landlord_config.get('phone', '')}<br/>" \
                    f"<b>Email:</b> {landlord_config.get('email', '')}<br/>" \
                    f"<b>Address:</b> {landlord_config.get('address', '')}<br/>" \
                    
    tenant_html = f"<b>Name:</b> {data.get('Tenant', '')}<br/>" \
                  f"<b>Phone:</b> {data.get('Tenant_Phone', '')}<br/>"
    company = data.get('Tenant_Company', '')
    if company:
        tenant_html += f"<b>Company:</b> {company}<br/>"
    tenant_html += f"<b>Address:</b> {data.get('Tenant_Address', '')}"
    
    p_landlord_title = Paragraph("LANDLORD", style_heading)
    p_landlord_body = Paragraph(landlord_html, style_normal)
    
    p_tenant_title = Paragraph("TENANT", style_heading)
    p_tenant_body = Paragraph(tenant_html, style_normal)
    
    card_width = (width - 100 - 20) / 2.0 
    
    table = Table([[ [p_landlord_title, p_landlord_body], "", [p_tenant_title, p_tenant_body] ]], 
                  colWidths=[card_width, 20, card_width])
                  
    table.setStyle(TableStyle([
        ('BOX', (0,0), (0,0), 1, colors.black),
        ('BOX', (2,0), (2,0), 1, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    
    tw, th = table.wrapOn(c, width, height)
    y -= th
    table.drawOn(c, 50, y)
    
    y -= 25
    c.setLineWidth(1)
    c.line(40, y, width - 40, y)
    
    y -= 25
    c.setFont("NotoSans-Bold", 12)
    c.drawString(60, y, "DESCRIPTION")
    c.drawRightString(width - 60, y, "AMOUNT")
    
    y -= 10
    c.line(50, y, width - 50, y)
    
    items = []
    
    rent = _safe_float(data.get('Rent'))
    items.append(("Rent", "", rent))
        
    add_charge = _safe_float(data.get('Additional'))
    add_count = _safe_int(data.get("Additional_Persons"))
    add_rate = _safe_float(data.get("Additional_Person_Rate"))
    items.append(("Additional Person Charges", f"{add_count} Persons x ₹{add_rate:,.2f}", add_charge))
            
    water = _safe_float(data.get('Water'))
    items.append(("Water Charges", "", water))
        
    tank_water = _safe_float(data.get('Tank_Water'))
    items.append(("Tank Water Charges", "", tank_water))
        
    maintenance = _safe_float(data.get('Maintenance_Charge'))
    if maintenance > 0:
        desc = data.get('Maintenance_Desc', '')
        items.append(("Maintenance Charges", desc, maintenance))
        
    electricity = _safe_float(data.get('Electricity'))
    units = _safe_float(data.get('Units'))
    rate = _safe_float(data.get('Rate'))
    prev = data.get('Previous', '')
    curr = data.get('Current', '')
    
    if prev == '' and curr == '':
        items.append(("Electricity Charges", f"{units:g} Units x ₹{rate:,.2f}", electricity))
    else:
        items.append(("Electricity Charges", f"{prev}-{curr} = {units:g} Units x ₹{rate:,.2f}", electricity))

    for title, subtitle, amt in items:
        y -= 20
        c.setFont("NotoSans", 11)
        c.drawString(60, y, title)
        c.drawRightString(width - 60, y, f"     {amt:,.2f}")
        if subtitle:
            y -= 15
            c.setFont("NotoSans", 10)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.drawString(60, y, subtitle)
            c.setFillColorRGB(0, 0, 0)
        
    y -= 15
    c.line(50, y, width - 50, y)
    
    curr_total = _safe_float(data.get('Total'))
    prev_arr = _safe_float(data.get('Previous_Arrears'))
    grand_total = curr_total + prev_arr
    amt_recv = _safe_float(data.get('Amount_Received'), grand_total)
    balance = grand_total - amt_recv

    y -= 20
    c.setFont("NotoSans", 11)
    c.drawString(60, y, "CURRENT MONTH TOTAL")
    c.drawRightString(width - 60, y, f"     {curr_total:,.2f}")

    if prev_arr != 0:
        y -= 15
        c.setFont("NotoSans", 11)
        c.drawString(60, y, "PREVIOUS ARREARS" if prev_arr > 0 else "PREVIOUS ADVANCE")
        c.drawRightString(width - 60, y, f"     {abs(prev_arr):,.2f}")

    y -= 15
    c.line(40, y, width - 40, y)

    y -= 20
    c.setFont("NotoSans-Bold", 12)
    c.drawString(60, y, "GRAND TOTAL")
    c.drawRightString(width - 60, y, f"     {grand_total:,.2f}")

    if amt_recv != grand_total:
        y -= 15
        c.setFont("NotoSans", 11)
        c.drawString(60, y, "AMOUNT RECEIVED")
        c.drawRightString(width - 60, y, f"     {amt_recv:,.2f}")
        
        y -= 15
        c.setFont("NotoSans-Bold", 11)
        if balance > 0:
            c.drawString(60, y, "BALANCE DUE")
            c.drawRightString(width - 60, y, f"     {balance:,.2f}")
        elif balance < 0:
            c.drawString(60, y, "ADVANCE AMOUNT")
            c.drawRightString(width - 60, y, f"     {abs(balance):,.2f}")

    y -= 15
    c.line(40, y, width - 40, y)
    
    y -= 25
    c.setFont("NotoSans-Bold", 11)
    c.drawString(50, y, "Amount in Words:")
    c.setFont("NotoSans-Italic", 11)
    try:
        total_float = grand_total
        words = num2words(total_float, lang='en_IN').replace(',', '').title()
        
        amount_style = ParagraphStyle('Amount', parent=style_normal, fontName='NotoSans-Italic', fontSize=11)
        p_amount = Paragraph(f"Rupees {words} Only", amount_style)
        pw, ph = p_amount.wrapOn(c, width - 200, height)
        y -= ph - 11 
        p_amount.drawOn(c, 160, y)
    except Exception:
        c.drawString(160, y, f"{total_float}")
        
    bank_acc_no = landlord_config.get("bank_account_number", "").strip()
    # pyrefly: ignore [bad-keyword-argument]
    if bank_acc_no and config.get("receipt", "toggles.show_bank_details", default=True):
        y -= 25
        if landlord_config.get("mask_bank_account", True):
            if len(bank_acc_no) > 4:
                masked_no = "X" * (len(bank_acc_no) - 4) + bank_acc_no[-4:]
            else:
                masked_no = "XXXX"
        else:
            masked_no = bank_acc_no
            
        box_y = y - 90
        box_width = 320
        c.setLineWidth(1)
        c.rect(50, box_y, box_width, 90)
        
        c.setFont("NotoSans-Bold", 10)
        c.drawString(60, box_y + 75, "PAYMENT DETAILS")
        c.line(50, box_y + 70, 50 + box_width, box_y + 70)
        
        c.setFont("NotoSans", 10)
        c.drawString(60, box_y + 53, f"Account Holder    : {landlord_config.get('bank_account_name', '')}")
        c.drawString(60, box_y + 38, f"Account Number : {masked_no}")
        c.drawString(60, box_y + 23, f"Bank Name           : {landlord_config.get('bank_name', '')}")
        
        branch = landlord_config.get('bank_branch', '')
        ifsc = landlord_config.get('bank_ifsc', '')
        branch_ifsc = []
        if branch: branch_ifsc.append(branch)
        if ifsc: branch_ifsc.append(ifsc)
        
        c.drawString(60, box_y + 8, f"Branch & IFSC      : {' - '.join(branch_ifsc)}")
        
        y = box_y
        
    # Move down for the signature, but clamp 'y' to a minimum of 90 
    # to prevent overlapping the footer (y=40) and outer border (y=30)
    y -= 50
    if y < 90:
        y = 90
    
    sig_filename = landlord_config.get('signature_image', '')
    # pyrefly: ignore [bad-keyword-argument]
    if sig_filename and config.get("receipt", "toggles.show_signature", default=True):
        sig_img_path = os.path.join(UPLOADS_DIR, sig_filename)
        
        if os.path.exists(sig_img_path):
            try:
                from reportlab.lib.utils import ImageReader
                from PIL import Image
                
                pil_img = Image.open(sig_img_path).convert("RGBA")
                background = Image.new('RGBA', pil_img.size, (255, 255, 255, 255))
                alpha_composite = Image.alpha_composite(background, pil_img)
                final_img = alpha_composite.convert('RGB')
                
                img = ImageReader(final_img)
                max_w, max_h = 160, 60
                img_w, img_h = img.getSize()
                
                aspect = img_w / float(img_h)
                if (max_w / aspect) <= max_h:
                    new_w = max_w
                    new_h = max_w / aspect
                else:
                    new_h = max_h
                    new_w = max_h * aspect
                    
                c.drawImage(img, width - 60 - new_w, y, width=new_w, height=new_h, preserveAspectRatio=True)
                y -= 15
            except Exception as e:
                print(f"Error drawing signature image: {e}")
                c.setFont("NotoSans", 11)
                c.drawRightString(width - 60, y, "________________________")
                y -= 15
        else:
            print(f"Warning: Signature image configured but not found at {sig_img_path}")
            c.setFont("NotoSans", 11)
            c.drawRightString(width - 60, y, "________________________")
            y -= 15
    else:
        c.setFont("NotoSans", 11)
        c.drawRightString(width - 60, y, "________________________")
        y -= 15
        
    c.setFont("NotoSans", 11)
    sig_text = landlord_config.get('signature_text', '')
    if sig_text:
        c.drawRightString(width - 60, y, sig_text)
    else:
        c.drawRightString(width - 60, y, "Authorized Signature")
        
    y -= 15
    c.setFont("NotoSans-Bold", 11)
    c.drawRightString(width - 60, y, landlord_config.get('name', ''))
    
    status = data.get('Status', 'ACTIVE')
    
    c.setFont("NotoSans", 9)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(40, 40, f"Receipt Status : {status}")
    if status == 'ARCHIVED':
        archived_date = data.get('Archived_Date', '')
        c.drawString(160, 40, f"Archived : {archived_date}")
        
    gen_date = data.get("Date", "")
    c.drawRightString(width / 2.0 + 30, 40, f"Generated : {gen_date}")
    c.drawRightString(width - 40, 40, f"Receipt No : {data['Bill']}")
    
    c.showPage()
    c.save()
    
    if is_stream:
        output_path.seek(0)
        return output_path
        
    return output_path
```

```python
// File: services\signature_service.py
import os
from PIL import Image, ImageOps
import io
import shutil

from app.core.paths import UPLOADS_DIR as SIGNATURE_DIR

def flatten_signature(input_path, output_path):
    """
    Removes white background, converts to transparent PNG, 
    and crops excess whitespace.
    """
    try:
        # Open image and ensure it has an alpha channel
        img = Image.open(input_path).convert("RGBA")
        
        # Get data
        data = img.getdata()
        
        new_data = []
        for item in data:
            # Change all white (also shades of white)
            # to transparent. 
            # A simple heuristic: if R, G, B are all > 220, it's white-ish.
            if item[0] > 200 and item[1] > 200 and item[2] > 200:
                new_data.append((255, 255, 255, 0)) # transparent
            else:
                new_data.append(item)
                
        img.putdata(new_data)
        
        # Crop to bounding box of non-transparent pixels
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
            
        # Save as PNG
        img.save(output_path, "PNG")
        return True
    except Exception as e:
        print(f"Error processing signature: {e}")
        return False

def save_signature(file_bytes: bytes, filename: str) -> str:
    """
    Saves the uploaded signature and processes it.
    Returns the path to the flattened signature.
    """
    temp_path = os.path.join(SIGNATURE_DIR, "temp_" + filename)
    flattened_path = os.path.join(SIGNATURE_DIR, "landlord_signature_flattened.png")
    
    with open(temp_path, "wb") as f:
        f.write(file_bytes)
        
    success = flatten_signature(temp_path, flattened_path)
    
    # Remove temp file
    if os.path.exists(temp_path):
        os.remove(temp_path)
        
    if success:
        return flattened_path
    return ""

def delete_signature():
    """
    Deletes the saved signature.
    """
    flattened_path = os.path.join(SIGNATURE_DIR, "landlord_signature_flattened.png")
    if os.path.exists(flattened_path):
        try:
            os.remove(flattened_path)
        except Exception:
            pass
```

```python
// File: services\tenant_service.py
import csv
import os
import shutil
from app.models.tenant import Tenant
from app.core.config_service import config
from app.core.paths import DB_DIR, BACKUPS_DIR as BACKUP_DIR

TENANTS_CSV = os.path.join(DB_DIR, "tenants.csv")

HEADERS_V1 = [
    "ID", "Tenant Name", "Company", "Phone", "Email", 
    "Permanent Address", "Room Number", "Occupation", "Notes", "Status"
]

HEADERS_V2 = HEADERS_V1 + [
    "Rent", "Water", "Electricity Rate", "Previous Meter", 
    "Additional Person", "Security Deposit"
]

HEADERS_V3 = HEADERS_V2 + [
    "Default Tank Water"
]

HEADERS_V4 = HEADERS_V3 + [
    "Meter ID"
]

HEADERS_V5 = HEADERS_V4 + [
    "View Token"
]

HEADERS_V6 = HEADERS_V5 + [
    "Tenant PIN"
]

CURRENT_HEADERS = HEADERS_V6

def init_csv():
    if not os.path.exists(TENANTS_CSV):
        with open(TENANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CURRENT_HEADERS)

def _migrate_database():
    if not os.path.exists(TENANTS_CSV):
        return
        
    v1_needs_migration = False
    v2_needs_migration = False
    v3_needs_migration = False
    v4_needs_migration = False
    v5_needs_migration = False
    with open(TENANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
            if "Rent" not in headers:
                v1_needs_migration = True
            if "Default Tank Water" not in headers:
                v2_needs_migration = True
            if "Meter ID" not in headers:
                v3_needs_migration = True
            if "View Token" not in headers:
                v4_needs_migration = True
            if "Tenant PIN" not in headers:
                v5_needs_migration = True
        except StopIteration:
            return

    if v1_needs_migration or v2_needs_migration or v3_needs_migration or v4_needs_migration or v5_needs_migration:
        print("Migrating tenants database schema...")
        old_rows = []
        with open(TENANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_rows.append(row)
                
        billing_conf = config.get("billing", {})
        
        def safe_float(val):
            try:
                return float(str(val).strip() or 0.0)
            except:
                return 0.0
                
        default_rent = safe_float(billing_conf.get("rent", 0.0) or billing_conf.get("default_rent", 0.0))
        default_water = safe_float(billing_conf.get("water", 0.0) or billing_conf.get("default_water", 0.0))
        default_rate = safe_float(billing_conf.get("electricity_rate", 0.0) or billing_conf.get("default_rate", 0.0))
        default_prev = safe_float(billing_conf.get("previous_meter_reading", 0.0) or 0.0)
        default_add = safe_float(billing_conf.get("additional_person_charge", 0.0) or billing_conf.get("default_additional_person_charge", 0.0))
        
        backup_path = os.path.join(BACKUP_DIR, "tenants_migration.csv.bak")
        try:
            shutil.copy2(TENANTS_CSV, backup_path)
        except Exception:
            pass
            
        with open(TENANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CURRENT_HEADERS)
            writer.writeheader()
            for row in old_rows:
                if v1_needs_migration:
                    row["Rent"] = default_rent
                    row["Water"] = default_water
                    row["Electricity Rate"] = default_rate
                    row["Previous Meter"] = default_prev
                    row["Additional Person"] = default_add
                    row["Security Deposit"] = 0.0
                if v2_needs_migration:
                    row["Default Tank Water"] = 0.0
                if v3_needs_migration:
                    row["Meter ID"] = ""
                if v4_needs_migration:
                    row["View Token"] = ""
                if v5_needs_migration:
                    row["Tenant PIN"] = "1234"
                writer.writerow(row)
                
        print("Migration complete.")

def load_tenants():
    init_csv()
    _migrate_database()
    
    tenants = []
    try:
        with open(TENANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                def safe_float(val):
                    try:
                        return float(str(val).strip() or 0.0)
                    except:
                        return 0.0
                        
                t = Tenant(
                    id=int(row["ID"]) if row.get("ID") else None,
                    name=row.get("Tenant Name", ""),
                    company=row.get("Company", ""),
                    phone=row.get("Phone", ""),
                    email=row.get("Email", ""),
                    address=row.get("Permanent Address", ""),
                    room_number=row.get("Room Number", ""),
                    occupation=row.get("Occupation", ""),
                    notes=row.get("Notes", ""),
                    status=row.get("Status", "Active"),
                    rent=safe_float(row.get("Rent")),
                    water=safe_float(row.get("Water")),
                    electricity_rate=safe_float(row.get("Electricity Rate")),
                    previous_meter=safe_float(row.get("Previous Meter")),
                    additional_person_charge=safe_float(row.get("Additional Person")),
                    security_deposit=safe_float(row.get("Security Deposit")),
                    default_tank_water_charge=safe_float(row.get("Default Tank Water")),
                    meter_id=row.get("Meter ID", ""),
                    view_token=row.get("View Token", ""),
                    tenant_pin=row.get("Tenant PIN", "1234")
                )
                tenants.append(t)
    except Exception as e:
        print(f"Error loading tenants: {e}")
    return tenants

def save_all_tenants(tenants_list):
    init_csv()
    if os.path.exists(TENANTS_CSV):
        backup_path = os.path.join(BACKUP_DIR, "tenants.csv.bak")
        try:
            shutil.copy2(TENANTS_CSV, backup_path)
        except Exception:
            pass
            
    try:
        with open(TENANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CURRENT_HEADERS)
            writer.writeheader()
            for t in tenants_list:
                row = {
                    "ID": t.id,
                    "Tenant Name": t.name,
                    "Company": t.company,
                    "Phone": t.phone,
                    "Email": t.email,
                    "Permanent Address": t.address,
                    "Room Number": t.room_number,
                    "Occupation": t.occupation,
                    "Notes": t.notes,
                    "Status": t.status,
                    "Rent": t.rent,
                    "Water": t.water,
                    "Electricity Rate": t.electricity_rate,
                    "Previous Meter": t.previous_meter,
                    "Additional Person": t.additional_person_charge,
                    "Security Deposit": t.security_deposit,
                    "Default Tank Water": t.default_tank_water_charge,
                    "Meter ID": t.meter_id,
                    "View Token": getattr(t, "view_token", ""),
                    "Tenant PIN": getattr(t, "tenant_pin", "1234")
                }
                writer.writerow(row)
    except Exception as e:
        print(f"Error saving tenants: {e}")

def add_tenant(t: Tenant):
    tenants = load_tenants()
    next_id = 1
    if tenants:
        next_id = max(x.id for x in tenants if x.id is not None) + 1
    t.id = next_id
    
    # --- NEW: Auto-generate Meter ID if left blank ---
    if not t.meter_id:
        t.meter_id = f"MTR - F - {str(next_id).zfill(2)}"
        
    tenants.append(t)
    save_all_tenants(tenants)
    return t

def update_tenant(t: Tenant):
    tenants = load_tenants()
    for idx, item in enumerate(tenants):
        if item.id == t.id:
            tenants[idx] = t
            break
    save_all_tenants(tenants)
    return t

def delete_tenant(tenant_id: int, action: str = "archive"):
    tenants = load_tenants()
    target_tenant = next((t for t in tenants if t.id == tenant_id), None)
    if not target_tenant:
        return
        
    from app.services.billing_service import get_all_receipts, archive_bill, delete_bill
    receipts = get_all_receipts()
    tenant_receipts = [r for r in receipts if r["Tenant"] == target_tenant.name]
    
    if action == "archive":
        target_tenant.status = "Inactive"
        update_tenant(target_tenant)
        # Archive all associated receipts
        for r in tenant_receipts:
            if r.get("Status") != "ARCHIVED":
                try:
                    archive_bill(r["Bill"])
                except Exception:
                    pass
                    
    elif action == "delete":
        # Force delete all associated receipts
        for r in tenant_receipts:
            # We must archive it first to bypass the safety check in delete_bill
            if r.get("Status") != "ARCHIVED":
                try:
                    archive_bill(r["Bill"])
                except Exception:
                    pass
            try:
                delete_bill(r["Bill"])
            except Exception:
                pass
        
        # Remove tenant completely
        tenants = [t for t in tenants if t.id != tenant_id]
        save_all_tenants(tenants)

# --- OCCUPANT / KYC MANAGEMENT ---
OCCUPANTS_CSV = os.path.join(DB_DIR, "occupants.csv")
OCC_HEADERS = [
    "Tenant ID", "Occupant UUID", "Name", "Mobile", "Status",
    "Aadhaar Front", "Aadhaar Back", "Aadhaar Combined", "Emp Front", "Emp Back",
    "Upload_Date", "Upload_Month"
]

def init_occupants_csv():
    if not os.path.exists(OCCUPANTS_CSV):
        with open(OCCUPANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(OCC_HEADERS)

def get_occupants(tenant_id: int):
    init_occupants_csv()
    occupants = []
    try:
        with open(OCCUPANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if str(row["Tenant ID"]) == str(tenant_id):
                    if not row.get("Upload_Month"):
                        row["Upload_Month"] = "Legacy Uploads"
                    occupants.append(row)
    except Exception as e:
        print(f"Error loading occupants: {e}")
    return occupants

def save_occupant(tenant_id: int, occ_data: dict):
    init_occupants_csv()
    all_rows = []
    updated = False
    
    with open(OCCUPANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Occupant UUID"] == occ_data["uuid"]:
                for key in occ_data:
                    if key in OCC_HEADERS or key in row:
                        row[key] = occ_data[key]
                updated = True
            all_rows.append(row)
            
    if not updated:
        new_row = {
            "Tenant ID": tenant_id,
            "Occupant UUID": occ_data["uuid"],
            "Name": occ_data["Name"],
            "Mobile": occ_data["Mobile"],
            "Status": occ_data.get("Status", "Active"),
            "Aadhaar Front": occ_data.get("Aadhaar Front", ""),
            "Aadhaar Back": occ_data.get("Aadhaar Back", ""),
            "Aadhaar Combined": occ_data.get("Aadhaar Combined", ""),
            "Emp Front": occ_data.get("Emp Front", ""),
            "Emp Back": occ_data.get("Emp Back", ""),
            "Upload_Date": occ_data.get("Upload_Date", ""),
            "Upload_Month": occ_data.get("Upload_Month", "")
        }
        all_rows.append(new_row)
        
    with open(OCCUPANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=OCC_HEADERS)
        writer.writeheader()
        writer.writerows(all_rows)

def update_occupant_status(occupant_uuid: str, status: str):
    init_occupants_csv()
    all_rows = []
    with open(OCCUPANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Occupant UUID"] == occupant_uuid:
                row["Status"] = status
            all_rows.append(row)
            
    with open(OCCUPANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=OCC_HEADERS)
        writer.writeheader()
        writer.writerows(all_rows)

def delete_occupant(occupant_uuid: str):
    init_occupants_csv()
    all_rows = []
    with open(OCCUPANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Occupant UUID"] != occupant_uuid:
                all_rows.append(row)
                
    with open(OCCUPANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=OCC_HEADERS)
        writer.writeheader()
        writer.writerows(all_rows)
```

```css
// File: static\css\style.css
/* Modern SaaS Design System */

:root {
    --border-radius-base: 16px;
    --border-radius-card: 20px;
    --border-radius-btn: 50rem; /* Pill shape */
    --transition-speed: 200ms;
}

body {
    font-size: 16px; /* Base 16px to prevent zoom on iOS and ensure readability */
    background-color: var(--bs-body-bg);
}

/* Form Standardization */
.form-floating > label {
    padding-left: 1rem;
    padding-right: 1rem;
}
.form-floating > .form-control:focus ~ label, 
.form-floating > .form-control:not(:placeholder-shown) ~ label, 
.form-floating > .form-select ~ label {
    /* Prevent clipping in dark mode by wrapping the label text */
    background-color: transparent !important;
}
.form-floating > .form-control:focus ~ label::after, 
.form-floating > .form-control:not(:placeholder-shown) ~ label::after, 
.form-floating > .form-select ~ label::after {
    /* Create a proper solid background behind the scaled label to mask the border */
    position: absolute;
    inset: 1rem 0.5rem;
    z-index: -1;
    height: 1.5em;
    content: "";
    background-color: var(--bs-body-bg);
    border-radius: 4px;
}
.form-control, .form-select {
    font-size: 16px; /* 16px minimum for forms */
}

/* Sidebar & Layout */
.sidebar {
    position: fixed;
    top: 56px; /* Below sticky header */
    bottom: 0;
    left: 0;
    z-index: 100;
    width: 250px;
    box-shadow: inset -1px 0 0 rgba(0, 0, 0, .05);
}

@media (min-width: 768px) {
    main {
        margin-left: 250px !important;
        width: calc(100% - 250px) !important;
    }
}

@media (max-width: 767.98px) {
    .menu-toggle {
        display: block;
        background: none;
        border: none;
        color: var(--bs-body-color);
        cursor: pointer;
    }

    .sidebar {
        position: fixed;
        top: 0;
        left: -280px;
        width: 260px;
        height: 100vh !important;
        z-index: 1040;
        transition: left 0.3s ease;
        box-shadow: 2px 0 10px rgba(0,0,0,0.1);
        display: flex !important;
    }

    .sidebar.open {
        left: 0;
    }

    .sidebar-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        opacity: 0;
        visibility: hidden;
        transition: opacity 0.3s ease, visibility 0.3s ease;
        z-index: 1030;
    }

    .sidebar-overlay.show {
        opacity: 1;
        visibility: visible;
    }

    body.sidebar-open {
        overflow: hidden;
    }

    main {
        margin-left: 0 !important;
        width: 100% !important;
    }
}

.sidebar .nav-link {
    font-weight: 500;
    color: var(--bs-body-color);
    border-radius: var(--border-radius-base);
    padding: 0.75rem 1rem;
    transition: background-color var(--transition-speed) ease, color var(--transition-speed) ease;
}

.sidebar .nav-link:hover {
    background-color: var(--bs-secondary-bg);
}

.sidebar .nav-link.active {
    color: #fff;
    background-color: var(--bs-primary);
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

/* Cards */
.card {
    border-radius: var(--border-radius-card);
    border: none;
    transition: transform var(--transition-speed) ease, box-shadow var(--transition-speed) ease;
}

.card-hover:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 20px rgba(0,0,0,0.08) !important;
}

/* Buttons */
.btn {
    border-radius: var(--border-radius-btn);
    transition: all var(--transition-speed) ease;
}

/* Typography Utilities */
.fs-7 { font-size: 0.75rem; }
.fs-8 { font-size: 0.65rem; }
.tracking-wider { letter-spacing: 0.05em; }

/* Dark Mode specific */
[data-bs-theme="dark"] .sidebar {
    box-shadow: inset -1px 0 0 rgba(255, 255, 255, .05);
}

/* Accordion modifications for History */
.accordion-item {
    border-radius: var(--border-radius-base) !important;
    margin-bottom: 0.5rem;
    border: 1px solid var(--bs-border-color);
    overflow: hidden;
}

.accordion-button {
    border-radius: var(--border-radius-base) !important;
    font-weight: 600;
}

/* ==========================================
   GLOBAL LOADING & SYNC OVERLAY
   ========================================== */
#globalSyncOverlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    z-index: 99999;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.3s ease, visibility 0.3s ease;
    cursor: wait;
}

#globalSyncOverlay.active {
    opacity: 1;
    visibility: visible;
}

.sync-spinner {
    width: 60px;
    height: 60px;
    position: relative;
    animation: sync-spin 2s infinite linear;
    margin-bottom: 20px;
}
.sync-spinner .dot {
    width: 100%;
    height: 100%;
    position: absolute;
    left: 0;
    top: 0;
}
.sync-spinner .dot::before {
    content: '';
    display: block;
    width: 25%;
    height: 25%;
    background-color: #ffffff;
    border-radius: 100%;
    animation: sync-bounce 2s infinite ease-in-out both;
}
.sync-spinner .dot:nth-child(1) { transform: rotate(0deg); }
.sync-spinner .dot:nth-child(2) { transform: rotate(90deg); }
.sync-spinner .dot:nth-child(3) { transform: rotate(180deg); }
.sync-spinner .dot:nth-child(4) { transform: rotate(270deg); }

.sync-spinner .dot:nth-child(1)::before { animation-delay: -1.1s; background-color: #0d6efd; }
.sync-spinner .dot:nth-child(2)::before { animation-delay: -1.0s; background-color: #198754; }
.sync-spinner .dot:nth-child(3)::before { animation-delay: -0.9s; background-color: #ffc107; }
.sync-spinner .dot:nth-child(4)::before { animation-delay: -0.8s; background-color: #dc3545; }

@keyframes sync-spin { 100% { transform: rotate(360deg); } }
@keyframes sync-bounce {
    0%, 100% { transform: scale(0.0); }
    50% { transform: scale(1.0); }
}

.sync-text {
    color: white;
    font-weight: 600;
    font-size: 1.2rem;
    letter-spacing: 1px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.5);
}
```

```javascript
// File: static\js\alerts.js
// SweetAlert2 Global Wrappers

const Toast = Swal.mixin({
    toast: true,
    position: 'top-end',
    showConfirmButton: false,
    timer: 3000,
    timerProgressBar: true,
    didOpen: (toast) => {
        toast.addEventListener('mouseenter', Swal.stopTimer)
        toast.addEventListener('mouseleave', Swal.resumeTimer)
    }
});

function showToast(icon, title) {
    Toast.fire({
        icon: icon,
        title: title
    });
}

function showSuccess(title, text, html = null) {
    return Swal.fire({
        icon: 'success',
        title: title,
        text: text,
        html: html,
        confirmButtonColor: '#198754',
        showClass: { popup: 'animate__animated animate__fadeInDown animate__faster' },
        hideClass: { popup: 'animate__animated animate__fadeOutUp animate__faster' }
    });
}

function showError(title, text) {
    return Swal.fire({
        icon: 'error',
        title: title,
        text: text,
        confirmButtonColor: '#dc3545',
        showClass: { popup: 'animate__animated animate__shakeX animate__faster' }
    });
}

function confirmAction(title, text, confirmBtnText = 'Confirm', confirmColor = '#dc3545') {
    return Swal.fire({
        title: title,
        text: text,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: confirmColor,
        cancelButtonColor: '#6c757d',
        confirmButtonText: confirmBtnText,
        showClass: { popup: 'animate__animated animate__fadeIn animate__faster' }
    });
}
```

```javascript
// File: static\js\loading.js
// Fullscreen Loading Overlay

function showLoadingOverlay(text = "Please wait...") {
    if (document.getElementById('global-loading-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'global-loading-overlay';
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100vw';
    overlay.style.height = '100vh';
    overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
    overlay.style.zIndex = '9999';
    overlay.style.display = 'flex';
    overlay.style.flexDirection = 'column';
    overlay.style.justifyContent = 'center';
    overlay.style.alignItems = 'center';
    overlay.style.color = '#fff';
    overlay.style.backdropFilter = 'blur(4px)';

    overlay.innerHTML = `
        <div class="spinner-border text-light mb-3" role="status" style="width: 3rem; height: 3rem;">
            <span class="visually-hidden">Loading...</span>
        </div>
        <h4 class="fw-bold tracking-wider">${text}</h4>
    `;

    document.body.appendChild(overlay);
    document.body.style.overflow = 'hidden';
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('global-loading-overlay');
    if (overlay) {
        overlay.remove();
        document.body.style.overflow = '';
    }
}
```

```javascript
// File: static\js\main.js
// Main JS functionality (Theme, Sidebar, Setup)

document.addEventListener("DOMContentLoaded", () => {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

    // Sidebar Mobile Drawer Toggle
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    const toggle = document.getElementById("menuToggle");
    const closeBtn = document.getElementById("sidebarCloseBtn");

    function closeSidebar(){
        if(sidebar) sidebar.classList.remove("open");
        if(overlay) overlay.classList.remove("show");
        document.body.classList.remove("sidebar-open");
    }

    if(toggle) {
        toggle.addEventListener("click", () => {
            sidebar.classList.toggle("open");
            overlay.classList.toggle("show");
            document.body.classList.toggle("sidebar-open");
        });
    }

    if(overlay) overlay.addEventListener("click", closeSidebar);
    if(closeBtn) closeBtn.addEventListener("click", closeSidebar);

    document.querySelectorAll(".sidebar a").forEach(link => {
        link.addEventListener("click", closeSidebar);
    });
});

// --- Smooth DOM Update Engine ---
async function smoothUpdate(selectors) {
    try {
        const res = await fetch(window.location.href);
        const htmlText = await res.text();
        const doc = new DOMParser().parseFromString(htmlText, 'text/html');
        
        selectors.forEach(selector => {
            const currentElements = document.querySelectorAll(selector);
            const newElements = doc.querySelectorAll(selector);
            
            // Replace the HTML of the target containers
            currentElements.forEach((el, index) => {
                if (newElements[index]) {
                    el.innerHTML = newElements[index].innerHTML;
                }
            });
        });
        
        // Re-trigger visual scripts if they exist on the page
        if (typeof calculateYearStats === 'function') calculateYearStats();
        if (typeof searchTenants === 'function') searchTenants();
    } catch(e) {
        console.error("Smooth update failed", e);
        window.location.reload(); // Safe fallback
    }
}

// Global UI Updater mapping
async function updateUI() {
    const path = window.location.pathname;
    if (path === '/') {
        await smoothUpdate(['.row-cols-1', '.table-responsive', '.d-md-none']); // Updates Dashboard Cards & Tables
    } else if (path.includes('/history')) {
        await smoothUpdate(['#historyAccordion']); // Updates History Accordion
    } else if (path.includes('/archive')) {
        await smoothUpdate(['#archiveAccordion', '.row.g-4.mb-4']); // Updates Archive Accordion & Stats
    } else if (path.includes('/tenants')) {
        await smoothUpdate(['#tenantsTable']); // Updates Tenants Table
    } else if (path.startsWith('/tenant/')) {
        await smoothUpdate(['.col-xl-4', '.col-xl-8']); // Updates Tenant Profile columns
    } else {
        window.location.reload();
    }
}

// --- Instant Theme Handler ---
async function setTheme(themeName) {
    try {
        const res = await fetch(window.APP.API + "/ui/theme", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ theme: themeName })
        });
        if (res.ok) {
            // Apply theme instantly without reloading
            const targetTheme = themeName === 'system' 
                ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') 
                : themeName;
            document.documentElement.setAttribute('data-bs-theme', targetTheme);
        }
    } catch (e) {
        showError("Theme Error", "Failed to switch theme.");
    }
}

// --- Smooth Payment Status Toggle with Arrears Logic ---
async function togglePaymentStatus(billNo, currentStatus, grandTotal, currentReceived = 0) {
    if (currentStatus === "PAID" || currentStatus === "PARTIAL" || currentStatus === "ADVANCE") {
        const reset = await confirmAction("Reset Status?", "Reset this bill to PENDING?", "Yes, Reset");
        if (!reset.isConfirmed) return;

        try {
            await fetch(`${window.APP.BASE}/api/bill/${billNo}/payment`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    payment_status: "PENDING",
                    amount_received: 0
                })
            });
            await updateUI();
        } catch (e) {
            showError("Network Error", "Could not reach server");
        }
        return;
    }

    const defaultAmount = parseFloat(currentReceived) > 0 ? parseFloat(currentReceived) : parseFloat(grandTotal);

    const { value: input } = await Swal.fire({
        title: 'Amount Received',
        text: `Total Bill: ₹${parseFloat(grandTotal).toFixed(2)}`,
        input: 'number',
        inputValue: defaultAmount.toFixed(2),
        showCancelButton: true,
        confirmButtonText: 'Update',
        confirmButtonColor: '#198754',
        didOpen: () => {
            const swalInput = Swal.getInput();
            if (swalInput) {
                swalInput.select();
            }
        },
        inputValidator: (value) => {
            if (!value && value !== '0') {
                return 'Please enter an amount!';
            }
            if (parseFloat(value) < 0) {
                return 'Amount cannot be negative!';
            }
        }
    });

    if (input === undefined || input === null) return;

    const amount = parseFloat(input);
    if (Number.isNaN(amount) || amount < 0) {
        showError("Invalid Amount", "Please enter a valid non-negative amount.");
        return;
    }

    try {
        const res = await fetch(`${window.APP.BASE}/api/bill/${billNo}/payment`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                payment_status: "PAID",
                amount_received: amount
            })
        });

        const result = await res.json();
        if (!res.ok) {
            showError("Payment Update Failed", result.detail || "Could not update payment.");
            return;
        }

        if (typeof showToast === 'function') {
            showToast('success', `Bill #${billNo} payment updated!`);
        }
        await updateUI();
    } catch (e) {
        showError("Network Error", "Could not reach server");
    }
}

// Secure Download wrapper to bypass browser HTTP download warnings
async function secureDownload(url, filename) {
    if (typeof showLoading === 'function') {
        showLoading('Preparing download...');
    }
    try {
        const response = await fetch(window.APP.BASE + "/" + url);
        if (!response.ok) throw new Error('Download failed');
        const blob = await response.blob();
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(blobUrl);
        a.remove();
    } catch (e) {
        console.error('Download error:', e);
        if (typeof showError === 'function') {
            showError('Download Error', 'Could not download the file securely.');
        } else {
            alert('Could not download the file.');
        }
    } finally {
        if (typeof hideLoading === 'function') {
            hideLoading();
        }
    }
}


// --- Global PDF Preview Handler ---

/**
 * Opens Chrome's native PDF viewer in a global modal overlay.
 * @param {string} billNo - The receipt bill number to preview.
 */
function openGlobalPDFPreview(billNo) {
    const iframe = document.getElementById('globalPdfIframe');
    const modalEl = document.getElementById('globalPdfModal');
    
    if (!iframe || !modalEl) {
        console.error("Global PDF Modal elements not found in the DOM.");
        if (typeof showError === 'function') showError("UI Error", "Cannot find PDF viewer components.");
        return;
    }

    // Point the iframe directly to your existing FastAPI PDF endpoint
    iframe.src = window.APP.API + `/pdf/${billNo}/view`;
    
    // Initialize and show the Bootstrap modal
    const pdfModal = new bootstrap.Modal(modalEl);
    pdfModal.show();
}

// Memory & UX Cleanup: Clear the iframe when the modal closes
document.addEventListener('DOMContentLoaded', () => {
    const modalEl = document.getElementById('globalPdfModal');
    if (modalEl) {
        modalEl.addEventListener('hidden.bs.modal', () => {
            const iframe = document.getElementById('globalPdfIframe');
            if (iframe) iframe.src = "";
        });
    }
});

// --- Live Global Search Engine ---
document.addEventListener('DOMContentLoaded', () => {
    const globalSearch = document.getElementById('globalSearchBar');
    const dropdown = document.getElementById('globalSearchDropdown');

    if (globalSearch && dropdown) {
        let searchTimeout;

        globalSearch.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim().toLowerCase();
            
            if (query.length < 2) {
                dropdown.style.display = 'none';
                return;
            }

            // Debounce the API call to prevent spamming the backend
            searchTimeout = setTimeout(async () => {
                try {
                    const [tRes, rRes] = await Promise.all([
                        fetch(window.APP.API + "/tenants"),
                        fetch(window.APP.API + "/bills/filter?status=all")
                    ]);
                    const tenants = await tRes.json();
                    const bills = await rRes.json();
                    
                    let html = '';
                    
                    // Filter Tenants
                    const matchT = tenants.filter(t => t.name.toLowerCase().includes(query) || `t${t.id}`.includes(query) || (t.company && t.company.toLowerCase().includes(query)));
                    if (matchT.length > 0) {
                        html += `<li><h6 class="dropdown-header text-primary fw-bold">Tenants</h6></li>`;
                        matchT.slice(0, 3).forEach(t => {
                            html += `<li><a class="dropdown-item" href="tenant/${t.id}">
                                <div class="d-flex align-items-center"><i class="bi bi-person bg-primary-subtle text-primary p-1 rounded me-2"></i> 
                                <div><div class="fw-semibold">${t.name} (T${t.id})</div>
                                <div class="text-muted" style="font-size: 0.7rem;">${t.company || 'Individual'}</div></div></div></a></li>`;
                        });
                    }
                    
                    // Filter Bills
                    const matchB = bills.filter(b => b.Tenant.toLowerCase().includes(query) || b.Bill.toLowerCase().includes(query) || String(b.Total).includes(query));
                    if (matchB.length > 0) {
                        if (html) html += `<li><hr class="dropdown-divider"></li>`;
                        html += `<li><h6 class="dropdown-header text-success fw-bold">Receipts</h6></li>`;
                        matchB.slice(0, 5).forEach(b => {
                            html += `<li><a class="dropdown-item" href="javascript:void(0)" onclick="dropdownPreview('${b.Bill}')">
                                <div class="d-flex justify-content-between align-items-center">
                                <div><i class="bi bi-receipt bg-success-subtle text-success p-1 rounded me-2"></i><span class="fw-semibold">#${b.Bill}</span></div>
                                <span class="text-muted fs-7">${b.Tenant}</span></div></a></li>`;
                        });
                    }
                    
                    if (!html) {
                        html = `<li><span class="dropdown-item text-muted py-3 text-center"><i class="bi bi-search d-block fs-4 mb-2"></i>No results found for "${query}"</span></li>`;
                    }
                    
                    dropdown.innerHTML = html;
                    dropdown.style.display = 'block';
                } catch (e) {
                    console.error("Live search failed", e);
                }
            }, 300); // 300ms debounce
        });

        // Hide dropdown on click outside
        document.addEventListener('click', (e) => {
            if (!globalSearch.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = 'none';
            }
        });

        // Keep the Enter key to redirect
        globalSearch.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                dropdown.style.display = 'none';
                const query = this.value.trim().toUpperCase();
                if (query.startsWith('T') && !isNaN(query.substring(1))) {
                    window.location.href = window.APP.BASE + `/tenant/${query.substring(1)}`;
                } else {
                    window.location.href = window.APP.BASE + `/history?q=${query}`;
                }
            }
        });
    }
});

// Helper for live dropdown PDF preview
window.dropdownPreview = function(billNo) {
    document.getElementById('globalSearchDropdown').style.display = 'none';
    openGlobalPDFPreview(billNo);
};

// --- Global Sync Overlay Controls ---
function showSyncOverlay(message = "Processing Data...") {
    const overlay = document.getElementById('globalSyncOverlay');
    const textEl = document.getElementById('syncOverlayText');
    if (overlay) {
        if(textEl) textEl.innerText = message;
        overlay.classList.add('active');
        document.activeElement.blur(); 
    }
}

function hideSyncOverlay() {
    const overlay = document.getElementById('globalSyncOverlay');
    if (overlay) overlay.classList.remove('active');
}

window.showLoadingOverlay = showSyncOverlay;
window.hideLoadingOverlay = hideSyncOverlay;

async function executeExport(format) {
    showSyncOverlay(`Generating ${format === 'template' ? 'Template' : format.toUpperCase() + ' Backup'}...`);
    
    try {
        const endpoint = format === 'template' ? window.APP.BASE + '/api/sync/template' : window.APP.API + `/sync/export/${format}`;
        const response = await fetch(endpoint);
        if (!response.ok) throw new Error("Failed to generate export file.");
        
        const disposition = response.headers.get('Content-Disposition');
        let filename = `Rent_Data_Export.${format}`;
        if (disposition && disposition.includes('filename="')) {
            filename = disposition.split('filename="')[1].split('"')[0];
        }

        const blob = await response.blob();
        const blobUrl = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        window.URL.revokeObjectURL(blobUrl);
        a.remove();
        
        setTimeout(() => {
            hideSyncOverlay();
            if (typeof showToast === 'function') showToast('success', `${format === 'template' ? 'Template' : format.toUpperCase() + ' Export'} completed successfully!`);
        }, 500);
    } catch (e) {
        hideSyncOverlay();
        if (typeof showError === 'function') {
            showError("Export Failed", e.message);
        } else {
            alert("Failed to export data.");
        }
    }
}
// Secure Download wrapper to bypass browser HTTP download warnings
async function secureDownload(url, filename) {
    if (typeof showLoading === 'function') {
        showLoading('Preparing download...');
    }
    try {
        const response = await fetch(window.APP.BASE + "/" + url);
        if (!response.ok) throw new Error('Download failed');
        const blob = await response.blob();
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(blobUrl);
        a.remove();
    } catch (e) {
        console.error('Download error:', e);
        if (typeof showError === 'function') {
            showError('Download Error', 'Could not download the file securely.');
        } else {
            alert('Could not download the file.');
        }
    } finally {
        if (typeof hideLoading === 'function') {
            hideLoading();
        }
    }
}


// --- Global PDF Preview Handler ---

/**
 * Opens Chrome's native PDF viewer in a global modal overlay.
 * @param {string} billNo - The receipt bill number to preview.
 */
function openGlobalPDFPreview(billNo) {
    const iframe = document.getElementById('globalPdfIframe');
    const modalEl = document.getElementById('globalPdfModal');
    
    if (!iframe || !modalEl) {
        console.error("Global PDF Modal elements not found in the DOM.");
        if (typeof showError === 'function') showError("UI Error", "Cannot find PDF viewer components.");
        return;
    }

    // Point the iframe directly to your existing FastAPI PDF endpoint
    iframe.src = window.APP.API + `/pdf/${billNo}/view`;
    
    // Initialize and show the Bootstrap modal
    const pdfModal = new bootstrap.Modal(modalEl);
    pdfModal.show();
}

// Memory & UX Cleanup: Clear the iframe when the modal closes
document.addEventListener('DOMContentLoaded', () => {
    const modalEl = document.getElementById('globalPdfModal');
    if (modalEl) {
        modalEl.addEventListener('hidden.bs.modal', () => {
            const iframe = document.getElementById('globalPdfIframe');
            if (iframe) iframe.src = "";
        });
    }
});

// --- Live Global Search Engine ---
document.addEventListener('DOMContentLoaded', () => {
    const globalSearch = document.getElementById('globalSearchBar');
    const dropdown = document.getElementById('globalSearchDropdown');

    if (globalSearch && dropdown) {
        let searchTimeout;

        globalSearch.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim().toLowerCase();
            
            if (query.length < 2) {
                dropdown.style.display = 'none';
                return;
            }

            // Debounce the API call to prevent spamming the backend
            searchTimeout = setTimeout(async () => {
                try {
                    const [tRes, rRes] = await Promise.all([
                        fetch(window.APP.API + "/tenants"),
                        fetch(window.APP.API + "/bills/filter?status=all")
                    ]);
                    const tenants = await tRes.json();
                    const bills = await rRes.json();
                    
                    let html = '';
                    
                    // Filter Tenants
                    const matchT = tenants.filter(t => t.name.toLowerCase().includes(query) || `t${t.id}`.includes(query) || (t.company && t.company.toLowerCase().includes(query)));
                    if (matchT.length > 0) {
                        html += `<li><h6 class="dropdown-header text-primary fw-bold">Tenants</h6></li>`;
                        matchT.slice(0, 3).forEach(t => {
                            html += `<li><a class="dropdown-item" href="tenant/${t.id}">
                                <div class="d-flex align-items-center"><i class="bi bi-person bg-primary-subtle text-primary p-1 rounded me-2"></i> 
                                <div><div class="fw-semibold">${t.name} (T${t.id})</div>
                                <div class="text-muted" style="font-size: 0.7rem;">${t.company || 'Individual'}</div></div></div></a></li>`;
                        });
                    }
                    
                    // Filter Bills
                    const matchB = bills.filter(b => b.Tenant.toLowerCase().includes(query) || b.Bill.toLowerCase().includes(query) || String(b.Total).includes(query));
                    if (matchB.length > 0) {
                        if (html) html += `<li><hr class="dropdown-divider"></li>`;
                        html += `<li><h6 class="dropdown-header text-success fw-bold">Receipts</h6></li>`;
                        matchB.slice(0, 5).forEach(b => {
                            html += `<li><a class="dropdown-item" href="javascript:void(0)" onclick="dropdownPreview('${b.Bill}')">
                                <div class="d-flex justify-content-between align-items-center">
                                <div><i class="bi bi-receipt bg-success-subtle text-success p-1 rounded me-2"></i><span class="fw-semibold">#${b.Bill}</span></div>
                                <span class="text-muted fs-7">${b.Tenant}</span></div></a></li>`;
                        });
                    }
                    
                    if (!html) {
                        html = `<li><span class="dropdown-item text-muted py-3 text-center"><i class="bi bi-search d-block fs-4 mb-2"></i>No results found for "${query}"</span></li>`;
                    }
                    
                    dropdown.innerHTML = html;
                    dropdown.style.display = 'block';
                } catch (e) {
                    console.error("Live search failed", e);
                }
            }, 300); // 300ms debounce
        });

        // Hide dropdown on click outside
        document.addEventListener('click', (e) => {
            if (!globalSearch.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = 'none';
            }
        });

        // Keep the Enter key to redirect
        globalSearch.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                dropdown.style.display = 'none';
                const query = this.value.trim().toUpperCase();
                if (query.startsWith('T') && !isNaN(query.substring(1))) {
                    window.location.href = window.APP.BASE + `/tenant/${query.substring(1)}`;
                } else {
                    window.location.href = window.APP.BASE + `/history?q=${query}`;
                }
            }
        });
    }
});

// Helper for live dropdown PDF preview
window.dropdownPreview = function(billNo) {
    document.getElementById('globalSearchDropdown').style.display = 'none';
    openGlobalPDFPreview(billNo);
};

// --- Global Sync Overlay Controls ---
function showSyncOverlay(message = "Processing Data...") {
    const overlay = document.getElementById('globalSyncOverlay');
    const textEl = document.getElementById('syncOverlayText');
    if (overlay) {
        if(textEl) textEl.innerText = message;
        overlay.classList.add('active');
        document.activeElement.blur(); 
    }
}

function hideSyncOverlay() {
    const overlay = document.getElementById('globalSyncOverlay');
    if (overlay) overlay.classList.remove('active');
}

window.showLoadingOverlay = showSyncOverlay;
window.hideLoadingOverlay = hideSyncOverlay;

async function executeExport(format) {
    showSyncOverlay(`Generating ${format === 'template' ? 'Template' : format.toUpperCase() + ' Backup'}...`);
    
    try {
        const endpoint = format === 'template' ? window.APP.BASE + '/api/sync/template' : window.APP.API + `/sync/export/${format}`;
        const response = await fetch(endpoint);
        if (!response.ok) throw new Error("Failed to generate export file.");
        
        const disposition = response.headers.get('Content-Disposition');
        let filename = `Rent_Data_Export.${format}`;
        if (disposition && disposition.includes('filename="')) {
            filename = disposition.split('filename="')[1].split('"')[0];
        }

        const blob = await response.blob();
        const blobUrl = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        window.URL.revokeObjectURL(blobUrl);
        a.remove();
        
        setTimeout(() => {
            hideSyncOverlay();
            if (typeof showToast === 'function') showToast('success', `${format === 'template' ? 'Template' : format.toUpperCase() + ' Export'} completed successfully!`);
        }, 500);
    } catch (e) {
        hideSyncOverlay();
        if (typeof showError === 'function') {
            showError("Export Failed", e.message);
        } else {
            alert("Failed to export data.");
        }
    }
}

async function updatePaymentStatus(billNo, newStatus, amountReceived) {
    if (newStatus === 'PARTIAL' && amountReceived === undefined) {
        const amount = prompt("Enter the partial amount received:");
        if (!amount) return; // User cancelled
        amountReceived = parseFloat(amount);
    }
    
    try {
        const response = await fetch(window.APP.API + `/bills/${billNo}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                payment_status: newStatus,
                amount_received: amountReceived
            })
        });
        
        if (response.ok) {
            showToast('success', `Bill #${billNo} marked as ${newStatus}!`);
            await updateUI();
        } else {
            showError('Error', 'Failed to update payment status');
        }
    } catch (error) {
        showError('Network Error', 'Could not reach server');
    }
}

// Global fix for Chrome aria-hidden focus warning on Bootstrap modals
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('hide.bs.modal', function () {
            if (document.activeElement) {
                document.activeElement.blur();
            }
        });
    });
});
```

```javascript
// File: static\js\search.js
function initializeSharedSearch(searchInputId, containerSelector, rowSelector) {
    const searchInput = document.getElementById(searchInputId);
    if (!searchInput) return;

    searchInput.addEventListener('keyup', function() {
        const query = this.value.toLowerCase();
        const containers = document.querySelectorAll(containerSelector);

        containers.forEach(container => {
            const rows = container.querySelectorAll(rowSelector);
            let visibleInContainer = 0;

            rows.forEach(row => {
                // Fetch attributes
                const tenant = (row.getAttribute('data-tenant') || "").toLowerCase();
                const month = (row.getAttribute('data-month') || "").toLowerCase();
                const year = (row.getAttribute('data-year') || "").toLowerCase();
                const bill = (row.getAttribute('data-bill') || "").toLowerCase();
                const company = (row.getAttribute('data-company') || "").toLowerCase();
                const amount = parseFloat(row.getAttribute('data-total') || "0");
                
                // Allow amount range searching like "> 5000" or simple match
                let amountMatches = false;
                if (query.startsWith(">") || query.startsWith("<")) {
                    const num = parseFloat(query.substring(1).trim());
                    if (!isNaN(num)) {
                        if (query.startsWith(">") && amount > num) amountMatches = true;
                        if (query.startsWith("<") && amount < num) amountMatches = true;
                    }
                } else if (amount.toString().includes(query)) {
                    amountMatches = true;
                }

                if (
                    tenant.includes(query) || 
                    month.includes(query) || 
                    year.includes(query) || 
                    bill.includes(query) ||
                    company.includes(query) ||
                    amountMatches
                ) {
                    row.style.display = "";
                    visibleInContainer++;
                } else {
                    row.style.display = "none";
                }
            });

            // Container visibility logic (specifically for accordion year groups)
            if (container.classList.contains('year-group')) {
                if (visibleInContainer === 0) {
                    container.style.display = "none";
                } else {
                    container.style.display = "";
                    const collapseTarget = container.querySelector('.accordion-collapse');
                    if (collapseTarget && query.length > 0) {
                        collapseTarget.classList.add('show');
                    }
                }
            }
        });
    });
}
```

```html
// File: templates\archive.html
{% extends "base.html" %}

{% block title %}Archived Receipts | Rent Receipt System{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pb-3 mb-4 border-bottom">
    <h1 class="h2 mb-0 fw-bold">Archived Receipts</h1>
    
    <!-- Global Search for Archive -->
    <div class="input-group ms-auto mt-3 mt-md-0 shadow-sm" style="max-width: 400px;">
        <span class="input-group-text bg-white border-end-0 rounded-start-pill"><i class="bi bi-search text-muted"></i></span>
        <input type="text" class="form-control border-start-0 rounded-end-pill" id="globalSearch" placeholder="Search Tenant, Company, Amount...">
    </div>
</div>

<!-- Dashboard Summary Cards -->
<div class="row g-4 mb-4">
    <div class="col-md-4">
        <div class="card shadow-sm h-100 bg-primary text-white border-0 card-hover">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 class="card-title mb-0 fw-bold opacity-75">Archived Receipts</h6>
                    <div class="bg-white bg-opacity-25 rounded p-2 d-flex align-items-center justify-content-center" style="width: 40px; height: 40px;">
                        <i class="bi bi-archive fs-5"></i>
                    </div>
                </div>
                <h2 class="display-6 fw-bold mb-0" id="totalArchivedCount">{{ receipts|length }}</h2>
            </div>
        </div>
    </div>
    
    <div class="col-md-4">
        <div class="card shadow-sm h-100 border-0 card-hover">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 class="card-title mb-0 fw-bold text-muted">Archived Years</h6>
                    <div class="bg-primary-subtle text-primary rounded p-2 d-flex align-items-center justify-content-center" style="width: 40px; height: 40px;">
                        <i class="bi bi-calendar3 fs-5"></i>
                    </div>
                </div>
                {% set unique_years = [] %}
                {% for r in receipts %}
                    {% set y = (r.Month.split(' ')[1]) if (r.Month.split(' ')|length > 1) else 'Unknown' %}
                    {% if y not in unique_years %}{% set _ = unique_years.append(y) %}{% endif %}
                {% endfor %}
                <h2 class="display-6 fw-bold mb-0 text-dark">{{ unique_years|length }}</h2>
            </div>
        </div>
    </div>

    <div class="col-md-4">
        <div class="card shadow-sm h-100 border-0 card-hover">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 class="card-title mb-0 fw-bold text-muted">Total Archived Revenue</h6>
                    <div class="bg-success-subtle text-success rounded p-2 d-flex align-items-center justify-content-center" style="width: 40px; height: 40px;">
                        <i class="bi bi-currency-rupee fs-5"></i>
                    </div>
                </div>
                {% set total_revenue = 0 %}
                {% for r in receipts %}
                    {% set total_revenue = total_revenue + r.Total|float %}
                {% endfor %}
                <h2 class="display-6 fw-bold mb-0 text-dark">₹{{ "{:,.2f}".format(total_revenue) }}</h2>
            </div>
        </div>
    </div>
</div>

<div class="accordion" id="archiveAccordion">
    {% set current_year = '' %}
    {% set current_month = '' %}
    
    {% for r in receipts %}
        {% set parts = r.Month.split(' ') %}
        {% set m = parts[0] %}
        {% set y = parts[1] if parts|length > 1 else 'Unknown' %}
        
        {% if y != current_year %}
            {% if current_year != '' %}
                    </div> <!-- End Accordion Body -->
                </div> <!-- End Collapse -->
            </div> <!-- End Accordion Item -->
            {% endif %}
            
            <div class="accordion-item mb-4 shadow-sm border-0 year-group" data-year="{{ y }}">
                <h2 class="accordion-header" id="heading-{{ y }}">
                    <button class="accordion-button bg-body-tertiary fw-bold fs-5" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-{{ y }}" aria-expanded="true" aria-controls="collapse-{{ y }}">
                        <i class="bi bi-calendar3 me-3 text-primary"></i> {{ y }}
                        
                        <!-- Year Summary Stats injected via JS -->
                        <div class="ms-auto me-3 d-none d-md-flex gap-4 text-muted fs-7 fw-normal">
                            <span><i class="bi bi-archive"></i> <span class="year-bills-count">0</span> Archived</span>
                        </div>
                    </button>
                </h2>
                <div id="collapse-{{ y }}" class="accordion-collapse collapse show" aria-labelledby="heading-{{ y }}">
                    <div class="accordion-body p-0">
            {% set current_year = y %}
            {% set current_month = '' %}
        {% endif %}
        
        {% if m != current_month %}
            <div class="bg-light p-2 px-4 border-bottom fw-bold text-secondary month-header">
                <i class="bi bi-chevron-down me-2 fs-7"></i> {{ m }}
            </div>
            {% set current_month = m %}
        {% endif %}
        
        <!-- Receipt Row -->
        <div class="p-3 px-4 border-bottom d-flex flex-column flex-md-row justify-content-between align-items-md-center receipt-row transition-hover" 
             data-tenant="{{ r.Tenant|lower }}" data-company="{{ r.Tenant_Company|lower }}" data-month="{{ m|lower }}" data-year="{{ y }}" data-bill="{{ r.Bill }}" data-total="{{ r.Total }}">
            {% set curr_total = r.Total|default(0,true)|float %}
            {% set prev_arr = r.Previous_Arrears|default(0,true)|float %}
            {% set grand_total = curr_total + prev_arr %}
            {% set amt_recv = r.Amount_Received|default(0, true)|float %}
            {% set balance = grand_total - amt_recv %}
            {% set advance_amount = 0 - balance if balance < 0 else 0 %}
            
            <div class="d-flex align-items-center mb-3 mb-md-0">
                <div class="bg-secondary-subtle text-secondary rounded-circle d-flex align-items-center justify-content-center me-3" style="width: 48px; height: 48px;">
                    <i class="bi bi-archive fs-5"></i>
                </div>
                <div>
                    <h6 class="fw-bold mb-1">{{ r.Tenant }}</h6>
                    <div class="text-muted fs-7">
                        <span class="badge bg-secondary-subtle text-secondary me-2">#{{ r.Bill }}</span>
                        {% if r.Archived_Date %}
                        <i class="bi bi-clock-history me-1"></i> Archived on {{ r.Archived_Date }}
                        {% else %}
                        <i class="bi bi-calendar-event me-1"></i> {{ r.Date }}
                        {% endif %}
                    </div>
                </div>
            </div>
            
            <div class="d-flex flex-column flex-md-row align-items-md-center gap-3 gap-md-5">
                <div class="d-flex flex-row flex-md-column align-items-center align-items-md-end justify-content-between gap-2">
                    <div class="text-md-end">
                        <div class="fs-7 text-muted mb-1">Total Payable</div>
                        <div class="fw-bold text-dark fs-5">₹{{ "{:,.2f}".format(grand_total) }}</div>
                        <div class="text-success fs-7">Paid: ₹{{ "{:,.2f}".format(amt_recv) }}</div>
                        {% if balance > 0 %}
                        <div class="text-danger fw-semibold fs-7">Due: ₹{{ "{:,.2f}".format(balance) }}</div>
                        {% elif balance < 0 %}
                        <div class="text-info fw-semibold fs-7">Advance: ₹{{ "{:,.2f}".format(advance_amount) }}</div>
                        {% endif %}
                    </div>
                        <div>
                            {% if r.Payment_Status == "PAID" %}
                                <span class="badge bg-success rounded-pill px-3"><i class="bi bi-circle-fill fs-9 me-1"></i> Paid</span>
                            {% elif r.Payment_Status == "PARTIAL" %}
                                <span class="badge bg-warning text-dark rounded-pill px-3"><i class="bi bi-circle-fill fs-9 me-1"></i> Partial</span>
                            {% elif r.Payment_Status == "ADVANCE" %}
                                <span class="badge bg-info text-dark rounded-pill px-3"><i class="bi bi-circle-fill fs-9 me-1"></i> Advance</span>
                            {% else %}
                                <span class="badge bg-danger rounded-pill px-3"><i class="bi bi-circle-fill fs-9 me-1"></i> Pending</span>
                            {% endif %}
                        </div>
                </div>
                
                <div class="btn-group shadow-sm rounded-pill mt-3 mt-md-0">
                    {% if r.Payment_Status in ['PAID', 'PARTIAL', 'ADVANCE'] %}
                    <button class="btn btn-sm btn-light border" onclick="togglePaymentStatus('{{ r.Bill }}', '{{ r.Payment_Status }}', '{{ grand_total }}', '{{ amt_recv }}')" title="Mark Pending">
                        <i class="bi bi-arrow-counterclockwise text-secondary"></i>
                    </button>
                    {% else %}
                    <button class="btn btn-sm btn-light border" onclick="togglePaymentStatus('{{ r.Bill }}', 'PENDING', '{{ grand_total }}', '0')" title="Mark Paid">
                        <i class="bi bi-check2 text-success"></i>
                    </button>
                    {% endif %}
                    <button class="btn btn-sm btn-light border text-success" onclick="sendWhatsApp('{{ r.Bill }}')" title="Send via WhatsApp">
                        <i class="bi bi-whatsapp"></i>
                    </button>
                    <button class="btn btn-sm btn-light border" onclick="openGlobalPDFPreview('{{ r.Bill }}')" title="View PDF">
                        <i class="bi bi-eye"></i>
                    <span class="d-none d-lg-inline ms-1">View</span></button>
                    <button class="btn btn-sm btn-light border" onclick="restoreBill('{{ r.Bill }}')" title="Restore">
                        <i class="bi bi-arrow-counterclockwise text-primary"></i> <span class="d-none d-lg-inline ms-1">Restore</span>
                    </button>
                    <a href="javascript:void(0)" onclick="secureDownload('api/pdf/{{ r.Bill }}/download', 'Receipt_{{ r.Bill }}.pdf')" class="btn btn-sm btn-light border" title="Download PDF">
                        <i class="bi bi-download text-success"></i> <span class="d-none d-lg-inline ms-1">DL</span>
                    </a>
                    <button class="btn btn-sm btn-light border" onclick="permanentlyDeleteBill('{{ r.Bill }}')" title="Delete Permanently">
                        <i class="bi bi-trash text-danger"></i> <span class="d-none d-lg-inline ms-1">Delete</span>
                    </button>
                </div>
            </div>
        </div>
        
    {% endfor %}
    
    {% if current_year != '' %}
            </div> <!-- End Accordion Body -->
        </div> <!-- End Collapse -->
    </div> <!-- End Accordion Item -->
    {% else %}
    <div class="text-center py-5 text-muted">
        <i class="bi bi-box-seam fs-1 d-block mb-3 opacity-50"></i>
        <h5>No Archived Receipts</h5>
        <p class="fs-7">Receipts you archive will appear here.</p>
    </div>
    {% endif %}
</div>

{% endblock %}

{% block scripts %}
<style>
    .transition-hover { transition: background-color 0.2s ease; }
    .transition-hover:hover { background-color: var(--bs-secondary-bg); }
</style>
<script src="{{ STATIC_URL(request, '/js/search.js') }}"></script>
<script>
    document.addEventListener("DOMContentLoaded", function() {
        calculateYearStats();
        initializeSharedSearch('globalSearch', '.year-group', '.receipt-row');
    });

    function calculateYearStats() {
        const yearGroups = document.querySelectorAll('.year-group');
        yearGroups.forEach(group => {
            const rows = group.querySelectorAll('.receipt-row');
            let count = rows.length;
            const countEl = group.querySelector('.year-bills-count');
            if(countEl) countEl.innerText = count;
        });
    }



    function restoreBill(billNo) {
        confirmAction(
            "Restore Receipt?", 
            `Receipt #${billNo} will be restored to active bills.`,
            "Restore",
            "#0d6efd"
        ).then(async (result) => {
            if (result.isConfirmed) {
                try {
                    const res = await fetch(`api/bill/${billNo}/restore`, { method: "POST" });
                    if (res.ok) {
                        showSuccess("Restored!", "The receipt has been restored.").then(async () => {
                            await updateUI(); // Smooth refresh
                        });
                    } else {
                        showError("Failed", "Could not restore the receipt.");
                    }
                } catch(e) {
                    showError("Network Error", "An error occurred.");
                }
            }
        });
    }

    function permanentlyDeleteBill(billNo) {
        confirmAction(
            "Delete Permanently?", 
            `This action cannot be undone. Receipt #${billNo} will be permanently removed.`,
            "Delete",
            "#dc3545"
        ).then(async (result) => {
            if (result.isConfirmed) {
                try {
                    const res = await fetch(`api/archive/${billNo}`, { method: "DELETE" });
                    if (res.ok) {
                        showSuccess("Deleted!", "The receipt has been permanently deleted.").then(async () => {
                            await updateUI(); // Smooth refresh
                        });
                    } else {
                        showError("Failed", "Could not delete the receipt.");
                    }
                } catch(e) {
                    showError("Network Error", "An error occurred.");
                }
            }
        });
    }
</script>
{% endblock %}
```

```html
// File: templates\backups.html
{% extends "base.html" %}

{% block title %}Backup Manager | Rent Receipt System{% endblock %}

{% block content %}
<div class="row mb-4 align-items-center">
    <div class="col">
        <h3 class="fw-bold mb-0">Disaster Recovery & Backups</h3>
        <p class="text-muted mb-0">Manage, verify, and restore system snapshots safely.</p>
    </div>
    <div class="col-auto">
        <button class="btn btn-primary fw-bold rounded-pill px-4 shadow-sm" onclick="createManualBackup()">
            <i class="bi bi-shield-plus me-2"></i>Create Manual Backup
        </button>
    </div>
</div>

<!-- Filters -->
<div class="card shadow-sm border-0 mb-4 rounded-4">
    <div class="card-body p-3">
        <ul class="nav nav-pills nav-fill gap-2" id="backup-filters">
            <li class="nav-item">
                <button class="nav-link active rounded-pill fw-bold" data-filter="all">All Backups</button>
            </li>
            <li class="nav-item">
                <button class="nav-link rounded-pill fw-bold" data-filter="Automatic">Automatic</button>
            </li>
            <li class="nav-item">
                <button class="nav-link rounded-pill fw-bold" data-filter="Manual">Manual</button>
            </li>
            <li class="nav-item">
                <button class="nav-link rounded-pill fw-bold" data-filter="Restore Point">Restore Points</button>
            </li>
            <li class="nav-item">
                <button class="nav-link rounded-pill fw-bold" data-filter="Emergency">Emergency</button>
            </li>
        </ul>
    </div>
</div>

<div class="row g-4" id="backup-container">
    <!-- Loaded dynamically -->
</div>

<!-- Restore Wizard Modal -->
<div class="modal fade" id="restoreWizardModal" tabindex="-1" data-bs-backdrop="static">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content border-0 shadow-lg rounded-4">
            <div class="modal-header border-bottom-0 bg-primary bg-gradient text-white rounded-top-4">
                <h5 class="modal-title fw-bold"><i class="bi bi-arrow-counterclockwise me-2"></i>Restore System</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body p-4">
                
                <!-- Wizard Steps -->
                <div id="wizard-step-1" class="text-center py-4">
                    <i class="bi bi-shield-exclamation text-warning" style="font-size: 4rem;"></i>
                    <h4 class="fw-bold mt-3">Confirm Restore</h4>
                    <p class="text-muted">You are about to restore the system to:<br><strong id="restore-target-name" class="text-dark"></strong></p>
                    
                    <div class="alert alert-info text-start fs-7">
                        <i class="bi bi-info-circle me-2"></i>A temporary restore point will be created automatically before the rollback.
                    </div>
                </div>

                <div id="wizard-step-2" class="d-none text-center py-5">
                    <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <h5 class="fw-bold mt-3">Validating Backup...</h5>
                    <p class="text-muted fs-7">Checking checksums and archive integrity.</p>
                </div>
                
                <div id="wizard-step-3" class="d-none">
                    <h5 class="fw-bold mb-3 text-center">Compatibility Check</h5>
                    <div class="card bg-body-tertiary border-0 mb-3">
                        <div class="card-body">
                            <div class="d-flex justify-content-between mb-2">
                                <span class="text-muted">Schema Compatibility:</span>
                                <span class="fw-bold text-success" id="compat-schema"><i class="bi bi-check-circle-fill me-1"></i>YES</span>
                            </div>
                            <div class="d-flex justify-content-between mb-2">
                                <span class="text-muted">Receipts:</span>
                                <span class="fw-bold" id="compat-receipts"></span>
                            </div>
                            <div class="d-flex justify-content-between">
                                <span class="text-muted">Tenants:</span>
                                <span class="fw-bold" id="compat-tenants"></span>
                            </div>
                        </div>
                    </div>
                    <div class="alert alert-warning fs-7 mb-0">
                        <i class="bi bi-exclamation-triangle-fill me-2"></i><strong>Warning:</strong> Restoring will completely overwrite the current database and configuration.
                    </div>
                </div>
                
                <div id="wizard-step-4" class="d-none text-center py-5">
                    <div class="spinner-border text-success" role="status" style="width: 3rem; height: 3rem;">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <h5 class="fw-bold mt-3">Restoring System...</h5>
                    <p class="text-muted fs-7" id="restore-progress-text">Extracting files and safely replacing database.</p>
                </div>

            </div>
            <div class="modal-footer border-top-0 pt-0 pb-4 px-4 justify-content-center gap-2">
                <button type="button" class="btn btn-light border rounded-pill px-4" data-bs-dismiss="modal" id="btn-cancel">Cancel</button>
                <button type="button" class="btn btn-primary rounded-pill px-4 fw-bold shadow-sm" id="btn-next">Continue</button>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    let allBackups = [];
    let currentFilter = 'all';
    let targetBackup = null;

    document.addEventListener("DOMContentLoaded", function() {
        loadBackups();
        
        // Filter logic
        document.querySelectorAll('#backup-filters .nav-link').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('#backup-filters .nav-link').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                currentFilter = e.target.getAttribute('data-filter');
                renderBackups();
            });
        });
        
        // Wizard logic
        document.getElementById('btn-next').addEventListener('click', handleWizardNext);
    });

    async function loadBackups() {
        try {
            const res = await fetch('api/backups');
            if (res.ok) {
                const data = await res.json();
                allBackups = data.backups || [];
                renderBackups();
            }
        } catch(e) {
            showToast('error', 'Failed to load backups.');
        }
    }

    function renderBackups() {
        const container = document.getElementById('backup-container');
        container.innerHTML = '';
        
        let filtered = allBackups;
        if (currentFilter !== 'all') {
            filtered = allBackups.filter(b => b.type === currentFilter);
        }
        
        if (filtered.length === 0) {
            container.innerHTML = `<div class="col-12 text-center py-5"><h5 class="text-muted">No backups found in this category.</h5></div>`;
            return;
        }
        
        filtered.forEach(b => {
            let badgeClass = "bg-primary";
            let icon = "bi-archive";
            
            if (b.type === "Automatic") { badgeClass = "bg-info"; icon = "bi-clock-history"; }
            if (b.type === "Restore Point") { badgeClass = "bg-warning text-dark"; icon = "bi-pin-angle"; }
            if (b.type === "Emergency") { badgeClass = "bg-danger"; icon = "bi-exclamation-triangle"; }
            
            const dateStr = new Date(b.date).toLocaleString();
            
            const card = `
                <div class="col-md-6 col-lg-4">
                    <div class="card h-100 shadow-sm border-0 rounded-4 backup-card">
                        <div class="card-body p-4">
                            <div class="d-flex justify-content-between align-items-start mb-3">
                                <span class="badge ${badgeClass} rounded-pill px-3 py-2"><i class="bi ${icon} me-1"></i>${b.type}</span>
                                ${b.verified ? '<span class="text-success" title="Verified Integrity"><i class="bi bi-shield-check fs-5"></i></span>' : '<span class="text-warning"><i class="bi bi-shield-exclamation fs-5"></i></span>'}
                            </div>
                            
                            <h6 class="fw-bold text-truncate mb-1" title="${b.id}">${b.notes || b.id}</h6>
                            <p class="text-muted fs-7 mb-3"><i class="bi bi-calendar3 me-1"></i>${dateStr}</p>
                            
                            <div class="row g-2 fs-7 mb-4 bg-body-tertiary p-2 rounded-3 text-center mx-0">
                                <div class="col-4 border-end">
                                    <div class="text-muted">Size</div>
                                    <div class="fw-bold">${b.size || '-'}</div>
                                </div>
                                <div class="col-4 border-end">
                                    <div class="text-muted">Receipts</div>
                                    <div class="fw-bold">${b.receipt_count || 0}</div>
                                </div>
                                <div class="col-4">
                                    <div class="text-muted">Tenants</div>
                                    <div class="fw-bold">${b.tenant_count || 0}</div>
                                </div>
                            </div>
                            
                            <div class="d-flex justify-content-between align-items-center mt-auto border-top pt-3">
                                <button class="btn btn-sm btn-outline-success rounded-pill fw-bold" onclick="startRestore('${b.id}')">
                                    <i class="bi bi-arrow-counterclockwise me-1"></i>Restore
                                </button>
                                <div class="btn-group rounded-pill shadow-sm">
                                    <a href="javascript:void(0)" onclick="secureDownload('api/backups/${b.id}/download', '${b.filename}')" class="btn btn-sm btn-light border py-1" title="Download ZIP">
                                        <i class="bi bi-download text-primary"></i>
                                    </a>
                                    <button class="btn btn-sm btn-light border py-1" onclick="verifyBackup('${b.id}')" title="Verify Integrity">
                                        <i class="bi bi-shield-check text-info"></i>
                                    </button>
                                    <button class="btn btn-sm btn-light border py-1" onclick="deleteBackup('${b.id}')" title="Delete">
                                        <i class="bi bi-trash text-danger"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            container.innerHTML += card;
        });
    }

    async function createManualBackup() {
        showLoadingOverlay("Creating Manual Backup...");
        try {
            const res = await fetch('api/backups/manual', { method: 'POST' });
            hideLoadingOverlay();
            if (res.ok) {
                showToast('success', 'Backup created successfully!');
                loadBackups();
            } else {
                showError('Error', 'Failed to create backup.');
            }
        } catch(e) {
            hideLoadingOverlay();
            showError('Network Error', 'Failed to communicate with server.');
        }
    }
    
    async function deleteBackup(id) {
        confirmAction("Delete Backup?", "This action cannot be undone.", "Delete", "#dc3545").then(async (result) => {
            if(result.isConfirmed) {
                try {
                    const res = await fetch(`api/backups/${id}`, { method: 'DELETE' });
                    if(res.ok) {
                        showToast('success', 'Backup deleted.');
                        loadBackups();
                    } else {
                        showError('Error', 'Failed to delete backup.');
                    }
                } catch(e) {
                    showError('Error', 'Network error.');
                }
            }
        });
    }

    async function verifyBackup(id) {
        showLoadingOverlay("Verifying Backup Integrity...");
        try {
            const res = await fetch(`api/backups/${id}/verify`);
            const data = await res.json();
            hideLoadingOverlay();
            if (res.ok && data.status === 'success') {
                Swal.fire('Verified', data.message, 'success');
            } else {
                Swal.fire('Integrity Error', data.message, 'error');
            }
        } catch(e) {
            hideLoadingOverlay();
            showError('Error', 'Verification failed.');
        }
    }

    // --- RESTORE WIZARD ---
    let wizardStep = 1;
    let restoreModal;

    function startRestore(id) {
        targetBackup = allBackups.find(b => b.id === id);
        if(!targetBackup) return;
        
        wizardStep = 1;
        document.getElementById('restore-target-name').innerText = targetBackup.notes || targetBackup.id;
        showWizardStep(1);
        
        document.getElementById('btn-next').innerText = "Validate Integrity";
        document.getElementById('btn-next').className = "btn btn-primary rounded-pill px-4 fw-bold shadow-sm";
        document.getElementById('btn-next').disabled = false;
        document.getElementById('btn-cancel').disabled = false;
        
        restoreModal = new bootstrap.Modal(document.getElementById('restoreWizardModal'));
        restoreModal.show();
    }

    function showWizardStep(step) {
        for(let i=1; i<=4; i++) {
            document.getElementById(`wizard-step-${i}`).classList.add('d-none');
        }
        document.getElementById(`wizard-step-${step}`).classList.remove('d-none');
    }

    async function handleWizardNext() {
        if (wizardStep === 1) {
            // Move to Step 2: Validation
            wizardStep = 2;
            showWizardStep(2);
            document.getElementById('btn-next').disabled = true;
            document.getElementById('btn-cancel').disabled = true;
            
            try {
                const res = await fetch(`api/backups/${targetBackup.id}/verify`);
                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    // Success, move to Step 3
                    setTimeout(() => {
                        wizardStep = 3;
                        showWizardStep(3);
                        
                        document.getElementById('compat-receipts').innerText = `${targetBackup.receipt_count || 0}`;
                        document.getElementById('compat-tenants').innerText = `${targetBackup.tenant_count || 0}`;
                        
                        document.getElementById('btn-next').innerText = "Execute Restore";
                        document.getElementById('btn-next').className = "btn btn-danger rounded-pill px-4 fw-bold shadow-sm";
                        document.getElementById('btn-next').disabled = false;
                        document.getElementById('btn-cancel').disabled = false;
                    }, 800);
                } else {
                    restoreModal.hide();
                    Swal.fire('Validation Failed', data.message, 'error');
                }
            } catch(e) {
                restoreModal.hide();
                showError('Error', 'Validation process failed.');
            }
        } 
        else if (wizardStep === 3) {
            // Move to Step 4: Execute
            wizardStep = 4;
            showWizardStep(4);
            document.getElementById('btn-next').disabled = true;
            document.getElementById('btn-cancel').disabled = true;
            
            try {
                const res = await fetch(`api/backups/${targetBackup.id}/restore`, { method: 'POST' });
                if (res.ok) {
                    document.getElementById('restore-progress-text').innerText = "Success! Reloading system...";
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    const data = await res.json();
                    restoreModal.hide();
                    Swal.fire('Restore Failed', data.detail || 'An error occurred during restoration.', 'error');
                }
            } catch(e) {
                restoreModal.hide();
                showError('Error', 'Network error during restore.');
            }
        }
    }

</script>
{% endblock %}
```

```html
// File: templates\base.html
<!DOCTYPE html>
<html lang="en" data-bs-theme="{% if theme == 'dark' %}dark{% elif theme == 'light' %}light{% else %}auto{% endif %}">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Rent Receipt System{% endblock %}</title>
    <link rel="icon" type="image/svg+xml" href="{{ STATIC_URL(request, '/fevicon.svg') }}">
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
    <!-- SweetAlert2 -->
    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css" />
    <!-- Custom CSS -->
    <link href="{{ STATIC_URL(request, '/css/style.css?v=2') }}" rel="stylesheet">

    <!-- Early Theme Script to prevent flash -->
    <script>
        function applySystemTheme() {
            const theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
            document.documentElement.setAttribute('data-bs-theme', theme);
        }
        const currentTheme = "{{ theme }}";
        if (currentTheme === 'system') {
            applySystemTheme();
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applySystemTheme);
        }
    </script>
    {% block head %}{% endblock %}
    <script>
        window.RouteManifest = {
            pages: {
                dashboard: "{{ route(request, Names.HOME) }}",
                billing: "{{ route(request, Names.BILLING_PAGE) }}",
                history: "{{ route(request, Names.HISTORY_PAGE) }}",
                tenants: "{{ route(request, Names.TENANTS_PAGE) }}",
                archive: "{{ route(request, Names.ARCHIVE_PAGE) }}",
                settings: "{{ route(request, Names.SETTINGS_PAGE) }}",
                backups: "{{ route(request, Names.BACKUPS_PAGE) }}"
            },
            api: {
                billing: "{{ route(request, Names.API_FILTER_BILLS) }}",
                tenants: "{{ route(request, Names.API_GET_TENANTS) }}",
                pdf: "{{ route(request, Names.PDF_DOWNLOAD, bill_no='REPLACE') }}".replace('REPLACE', '')
            },
            static: {
                base: "{{ STATIC_URL(request, '/') }}"
            }
        };
        window.APP_BASE = "{{ APP_BASE(request) }}";
        // Legacy compat alias
        window.APP = {
            BASE: window.APP_BASE,
            API: window.APP_BASE + "/api",
            STATIC: window.RouteManifest.static.base
        };
    </script>
</head>

<body>

    <!-- Sticky Header -->
    <header class="navbar sticky-top bg-body-tertiary border-bottom shadow-sm flex-md-nowrap p-0 py-2">
        <div class="d-flex align-items-center w-100 px-3">
            <!-- Mobile Toggle -->
            <button id="menuToggle" class="menu-toggle d-md-none me-3" type="button" aria-label="Toggle navigation">
                <i class="bi bi-list fs-4"></i>
            </button>

            <a class="navbar-brand col-md-3 col-lg-2 me-0 px-3 fs-5 fw-bold text-primary d-none d-md-flex align-items-center"
                href="{{ route(request, Names.HOME) }}">
                <!-- <i class="bi bi-receipt-cutoff me-2"></i>{{ sys.app.short_name }} -->
                <i class="bi bi-receipt-cutoff me-2"></i>{{ config.get('system.app.short_name') }}
            </a>

            <!-- Global Search Placeholder -->
            <div class="w-100 me-3 d-flex align-items-center position-relative" id="globalSearchContainer">
                <div class="input-group input-group-sm" style="max-width: 400px;">
                    <span class="input-group-text bg-body border-end-0"><i class="bi bi-search text-muted"></i></span>
                    <input class="form-control border-start-0 bg-body" id="globalSearchBar" type="text"
                        placeholder="Search T1, bills, tenants..." aria-label="Search" autocomplete="off">
                </div>
                <ul class="dropdown-menu shadow w-100" id="globalSearchDropdown"
                    style="max-width: 400px; max-height: 350px; overflow-y: auto; top: 100%; left: 0; position: absolute; display: none; z-index: 1050;">
                </ul>
            </div>

            <!-- Right Icons -->
            <div class="d-flex align-items-center gap-3">
                <a class="nav-link" href="#" data-bs-toggle="tooltip" title="Notifications"><i
                        class="bi bi-bell fs-5"></i></a>

                <div class="dropdown">
                    <button
                        class="btn btn-sm btn-light dropdown-toggle d-flex align-items-center rounded-pill px-3 shadow-sm"
                        type="button" data-bs-toggle="dropdown" aria-expanded="false">
                        <i class="bi bi-circle-half me-2"></i> Theme
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end">
                        <li><button class="dropdown-item d-flex align-items-center" onclick="setTheme('light')"><i
                                    class="bi bi-sun-fill me-2"></i> Light</button></li>
                        <li><button class="dropdown-item d-flex align-items-center" onclick="setTheme('dark')"><i
                                    class="bi bi-moon-stars-fill me-2"></i> Dark</button></li>
                        <li><button class="dropdown-item d-flex align-items-center" onclick="setTheme('system')"><i
                                    class="bi bi-laptop me-2"></i> System</button></li>
                    </ul>
                </div>
            </div>
        </div>
    </header>

    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar -->
            <aside id="sidebar" class="sidebar border-end col-md-3 col-lg-2 p-0 bg-body-tertiary d-flex flex-column"
                style="height: calc(100vh - 60px); overflow-y: auto; overflow-x: hidden;">
                <div
                    class="sidebar-header border-bottom d-md-none p-3 d-flex justify-content-between align-items-center">
                    <h5 class="m-0 text-primary fw-bold"><i class="bi bi-receipt-cutoff me-2"></i>{{
                        config.get('system.app.short_name') }}</h5>
                    <button type="button" class="btn-close" id="sidebarCloseBtn" aria-label="Close"></button>
                </div>

                <div class="sidebar-body d-flex flex-column p-0 pt-lg-3 overflow-y-auto flex-grow-1">
                    <ul class="nav flex-column gap-2 px-3 mt-3 mt-md-0">
                        {% for item in config.get('ui.menu', []) %}
                        {% if item.type == 'external' %}
                        {% set item_url = item.url %}
                        {% set target = '_blank' %}
                        {% else %}
                        {% set item_url = route(request, item.route)|string %}
                        {% set target = '_self' %}
                        {% endif %}
                        <li class="nav-item">
                            <a class="nav-link {% if (request.url|string).split('?')[0] == item_url %}active{% endif %}"
                                href="{{ item_url }}" target="{{ target }}">
                                <i class="bi {{ item.icon }} me-2"></i> {{ item.name }}
                            </a>
                        </li>
                        {% endfor %}
                    </ul>
                </div>

                <!-- Sidebar Footer -->
                <div class="mt-auto p-3 border-top bg-body text-center">
                    <div class="d-flex align-items-center justify-content-center gap-2 mb-1">
                        <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center"
                            style="width: 32px; height: 32px; font-weight: bold;">
                            A
                        </div>
                        <span class="fw-semibold text-muted">Admin User</span>
                    </div>
                    <small class="text-secondary fs-8">Version 3.0.0</small>
                </div>
            </aside>

            <div id="sidebarOverlay" class="sidebar-overlay d-md-none"></div>

            <!-- Main Content -->
            <main class="col-md-9 ms-sm-auto col-lg-10 px-md-4 py-4 bg-body">
                {% block content %}{% endblock %}
            </main>
        </div>
    </div>

    <!-- Global PDF Preview Modal -->
    <div class="modal fade" id="globalPdfModal" tabindex="-1">
        <div class="modal-dialog modal-xl modal-dialog-centered">
            <div class="modal-content border-0 shadow-lg" style="border-radius: 16px; overflow: hidden;">
                <div class="modal-header bg-light border-bottom-0 py-2">
                    <h5 class="modal-title fw-bold fs-6">
                        <i class="bi bi-file-pdf text-danger me-2"></i>Receipt Preview
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body p-0 bg-secondary" style="height: 80vh;">
                    <iframe id="globalPdfIframe" src="" width="100%" height="100%" style="border: none;"></iframe>
                </div>
            </div>
        </div>
    </div>

    <div class="modal fade" id="globalEditBillModal" tabindex="-1" data-bs-backdrop="static">
        <div class="modal-dialog modal-lg modal-dialog-centered">
            <div class="modal-content border-0 shadow-lg rounded-4">
                <div class="modal-header bg-warning text-dark border-bottom-0 py-3 rounded-top-4">
                    <h5 class="modal-title fw-bold">
                        <i class="bi bi-pencil-square me-2"></i>Edit Receipt <span id="edit_bill_number_display"
                            class="badge bg-dark text-white ms-2"></span>
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body p-4 bg-body">
                    <form id="editReceiptForm">
                        <input type="hidden" id="edit_bill_no">

                        <div class="row g-3 mb-4">
                            <div class="col-md-6">
                                <label class="form-label fw-semibold">Tenant Name</label>
                                <select class="form-select" id="edit_tenant" required></select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-semibold">Billing Month</label>
                                <select class="form-select" id="edit_month" required></select>
                            </div>
                        </div>

                        <h6 class="fw-bold mb-3 border-bottom pb-2 text-secondary">Electricity Readings</h6>
                        <div class="row g-3 mb-4">
                            <div class="col-sm-6">
                                <label class="form-label text-primary">Current Meter Reading</label>
                                <input type="number" class="form-control border-primary fw-bold"
                                    id="edit_current_reading" step="0.1" required oninput="calculateEditLiveTotal()">
                            </div>
                            <div class="col-sm-6">
                                <label class="form-label">Previous Meter Reading</label>
                                <input type="text" class="form-control bg-body-tertiary" id="edit_prev_reading"
                                    readonly>
                            </div>
                            <div class="col-12 mt-2">
                                <div class="bg-primary-subtle text-primary rounded px-3 py-2 d-inline-block">
                                    <i class="bi bi-lightning-charge-fill me-1"></i> Consumed Units: <strong
                                        id="edit_consumed_units_label">0.0</strong>
                                    <span class="ms-2 fs-8">(at ₹<span id="edit_rate_display">0.00</span>/unit)</span>
                                </div>
                            </div>
                        </div>

                        <h6 class="fw-bold mb-3 border-bottom pb-2 text-secondary">Other Charges</h6>
                        <div class="row g-3 mb-3">
                            <div class="col-sm-6">
                                <label class="form-label">Tank Water Charge (₹)</label>
                                <input type="number" class="form-control" id="edit_tank_water_val" step="0.1"
                                    oninput="calculateEditLiveTotal()">
                            </div>
                            <div class="col-sm-6">
                                <label class="form-label">Additional Persons</label>
                                <input type="number" class="form-control" id="edit_additional_persons"
                                    placeholder="Blank if none" min="0" oninput="calculateEditLiveTotal()">
                                <div class="form-text fs-8">Rate: ₹<span id="edit_add_rate_display">0.00</span>/person
                                </div>
                            </div>
                        </div>
                        <div class="row g-3 mb-4">
                            <div class="col-sm-4">
                                <label class="form-label text-info fw-bold">Maintenance (₹)</label>
                                <input type="number" class="form-control border-info" id="edit_maintenance_val"
                                    step="0.1" oninput="calculateEditLiveTotal(); toggleEditMaintenanceDesc();">
                            </div>
                            <div class="col-sm-8">
                                <label class="form-label">Maintenance Description</label>
                                <input type="text" class="form-control" id="edit_maintenance_desc"
                                    placeholder="e.g. Building Maintenance">
                            </div>
                        </div>

                        <h6 class="fw-bold mb-3 border-bottom pb-2 text-secondary">Arrears & Payments</h6>
                        <div class="row g-3 mb-4">
                            <div class="col-sm-4">
                                <label class="form-label text-warning-emphasis fw-bold">Prev Arrears (₹)</label>
                                <input type="number" class="form-control border-warning" id="edit_previous_arrears"
                                    step="0.1" value="0" oninput="calculateEditLiveTotal()">
                            </div>
                            <div class="col-sm-4">
                                <label class="form-label fw-bold">Status</label>
                                <select class="form-select border-secondary fw-bold" id="edit_payment_status"
                                    onchange="calculateEditLiveTotal()">
                                    <option value="PENDING">Pending</option>
                                    <option value="PARTIAL">Partial</option>
                                    <option value="PAID">Paid</option>
                                    <option value="ADVANCE">Advance</option>
                                </select>
                            </div>
                            <div class="col-sm-4">
                                <label class="form-label text-success fw-bold">Received (₹)</label>
                                <input type="number" class="form-control border-success" id="edit_amount_received"
                                    step="0.1" oninput="calculateEditLiveTotal()">
                                <div class="form-text fs-8 text-muted mt-1">Leave empty to auto-calculate.
                                </div>
                            </div>
                        </div>

                        <div class="card bg-light-subtle border mb-4">
                            <div class="card-body p-3">
                                <div class="row text-muted fs-7 mb-2">
                                    <div class="col-6 d-flex justify-content-between"><span>Rent:</span> <span
                                            class="fw-bold text-dark">₹<span id="edit_live_rent">0.00</span></span>
                                    </div>
                                    <div class="col-6 d-flex justify-content-between"><span>Water:</span> <span
                                            class="fw-bold text-dark">₹<span id="edit_live_water">0.00</span></span>
                                    </div>
                                    <div class="col-6 d-flex justify-content-between"><span>Tank Water:</span> <span
                                            class="fw-bold text-dark">₹<span
                                                id="edit_live_tank_water">0.00</span></span></div>
                                    <div class="col-6 d-flex justify-content-between"><span>Additional:</span> <span
                                            class="fw-bold text-dark">₹<span
                                                id="edit_live_additional">0.00</span></span></div>
                                    <div class="col-6 d-flex justify-content-between"><span>Maintenance:</span> <span
                                            class="fw-bold text-info">₹<span
                                                id="edit_live_maintenance">0.00</span></span></div>
                                    <div class="col-6 d-flex justify-content-between"><span>Electricity:</span> <span
                                            class="fw-bold text-dark">₹<span
                                                id="edit_live_electricity">0.00</span></span></div>
                                </div>
                                <hr class="my-2">
                                <div class="row text-muted fs-7 mb-2">
                                    <div class="col-12 d-flex justify-content-between"><span>Current Bill Total:</span>
                                        <span class="fw-bold text-dark">₹<span
                                                id="edit_live_current_total">0.00</span></span>
                                    </div>
                                    <div class="col-12 d-flex justify-content-between"><span
                                            class="text-warning" id="edit_label_prev_arrears">Previous Arrears:</span> <span
                                            class="fw-bold text-warning">₹<span
                                                id="edit_live_prev_arrears">0.00</span></span></div>
                                </div>
                                <div class="d-flex justify-content-between align-items-center border-top pt-2">
                                    <span class="fw-bold fs-6">GRAND TOTAL:</span>
                                    <span class="fw-bold fs-4 text-success">₹<span
                                            id="edit_live_grand_total">0.00</span></span>
                                </div>
                                <div class="d-flex justify-content-between mt-2 align-items-center">
                                    <span class="fs-7 text-muted">Amount Received</span>
                                    <span class="fs-6 fw-bold">₹<span id="edit_live_amount_received">0.00</span></span>
                                </div>
                                <div class="d-flex justify-content-between mt-1 align-items-center">
                                    <span class="fs-7 text-info fw-bold" id="edit_label_balance_due">Balance Due</span>
                                    <span class="fs-6 fw-bold text-info">₹<span
                                            id="edit_live_balance_due">0.00</span></span>
                                </div>
                            </div>
                        </div>

                        <button type="submit" class="btn btn-warning btn-lg w-100 rounded-pill fw-bold shadow-sm"
                            id="editSubmitBtn">
                            <i class="bi bi-save me-2"></i>Update Receipt
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </div>

    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ STATIC_URL(request, '/js/alerts.js') }}"></script>
    <script src="{{ STATIC_URL(request, '/js/loading.js') }}"></script>
    <script src="{{ STATIC_URL(request, '/js/main.js?v=3') }}"></script>
    {% block scripts %}{% endblock %}
    <script>
        // --- Global Edit Bill Logic ---
        let editState = {
            prevMeter: 0, rent: 0, water: 0, rate: 0,
            originalAdditional: 0, addPersonRate: 0
        };

        async function openEditBillModal(billNo) {
            if (typeof showLoadingOverlay === 'function') showLoadingOverlay("Fetching details...");

            try {
                const [billRes, tenantsRes, monthsRes] = await Promise.all([
                    fetch(window.APP.API + `/bill/${billNo}`),
                    fetch(window.APP.API + `/tenants`),
                    fetch(window.APP.API + `/billing/months`)
                ]);

                if (!billRes.ok) throw new Error("Could not fetch bill details.");

                const receipt = await billRes.json();
                const tenants = await tenantsRes.json();
                const monthsData = await monthsRes.json();

                // Populate Tenants Dropdown
                const tenantSelect = document.getElementById('edit_tenant');
                tenantSelect.innerHTML = '';
                tenants.forEach(t => {
                    tenantSelect.add(new Option(t.name, t.name, false, t.name === receipt.Tenant));
                });
                if (!tenants.find(t => t.name === receipt.Tenant)) {
                    tenantSelect.add(new Option(receipt.Tenant, receipt.Tenant, true, true));
                }

                // Populate Months Dropdown
                const monthSelect = document.getElementById('edit_month');
                monthSelect.innerHTML = `<option value="${receipt.Month}" selected>${receipt.Month}</option>`;
                monthsData.months.forEach(m => {
                    if (m !== receipt.Month) monthSelect.add(new Option(m, m));
                });

                // Set Form Values
                document.getElementById('edit_bill_no').value = receipt.Bill;
                document.getElementById('edit_bill_number_display').innerText = receipt.Bill;
                document.getElementById('edit_current_reading').value = receipt.Current;
                document.getElementById('edit_prev_reading').value = receipt.Previous;
                document.getElementById('edit_tank_water_val').value = receipt.Tank_Water || 0;
                document.getElementById('edit_maintenance_val').value = receipt.Maintenance_Charge || 0;
                document.getElementById('edit_maintenance_desc').value = receipt.Maintenance_Desc || "";
                document.getElementById('edit_additional_persons').value = receipt.Additional_Persons > 0 ? receipt.Additional_Persons : "";

                document.getElementById('edit_previous_arrears').value = receipt.Previous_Arrears || 0;
                const originalGrandTotal = parseFloat(receipt.Total) + parseFloat(receipt.Previous_Arrears || 0);
                document.getElementById('edit_amount_received').value = (receipt.Amount_Received !== null && receipt.Amount_Received !== undefined) ? receipt.Amount_Received : originalGrandTotal;

                // Pre-select payment status
                const paymentStatus = receipt.Payment_Status || "PENDING";
                const selectEl = document.getElementById('edit_payment_status');
                if (selectEl) selectEl.value = paymentStatus;

                // Set Snapshot State for Calculations
                editState.prevMeter = parseFloat(receipt.Previous) || 0;
                editState.rent = parseFloat(receipt.Rent) || 0;
                editState.water = parseFloat(receipt.Water) || 0;
                editState.rate = parseFloat(receipt.Rate) || 0;
                editState.originalAdditional = parseFloat(receipt.Additional) || 0;

                editState.addPersonRate = parseFloat(receipt.Additional_Person_Rate) || 0;
                if (editState.addPersonRate === 0) {
                    const currentTenant = tenants.find(t => t.name === receipt.Tenant);
                    if (currentTenant) editState.addPersonRate = currentTenant.additional_person_charge || 0;
                }

                document.getElementById('edit_rate_display').innerText = editState.rate.toFixed(2);
                document.getElementById('edit_add_rate_display').innerText = editState.addPersonRate.toFixed(2);

                toggleEditMaintenanceDesc();
                calculateEditLiveTotal();

                if (typeof hideLoadingOverlay === 'function') hideLoadingOverlay();

                const modal = new bootstrap.Modal(document.getElementById('globalEditBillModal'));
                modal.show();

            } catch (error) {
                if (typeof hideLoadingOverlay === 'function') hideLoadingOverlay();
                if (typeof showError === 'function') showError("Error", error.message);
                else alert(error.message);
            }
        }

        function calculateEditLiveTotal() {
            const currentVal = parseFloat(document.getElementById('edit_current_reading').value) || 0;
            const addPersons = parseInt(document.getElementById('edit_additional_persons').value) || 0;
            const tankWater = parseFloat(document.getElementById('edit_tank_water_val').value) || 0;
            const maintenance = parseFloat(document.getElementById('edit_maintenance_val').value) || 0;
            const previousArrears = parseFloat(document.getElementById('edit_previous_arrears').value) || 0;

            let consumed = Math.max(0, currentVal - editState.prevMeter);
            let electricity = consumed * editState.rate;
            let additional = addPersons > 0 ? (addPersons * editState.addPersonRate) : editState.originalAdditional;
            let currentTotal = editState.rent + editState.water + tankWater + maintenance + additional + electricity;

            let grandTotal = currentTotal + previousArrears;
            let status = document.getElementById('edit_payment_status').value;
            let amountReceivedInput = document.getElementById('edit_amount_received').value;
            let amountReceived;
            if (amountReceivedInput !== "") {
                amountReceived = parseFloat(amountReceivedInput);
            } else {
                amountReceived = status === "PAID" ? grandTotal : (status === "PENDING" ? 0 : 0);
            }
            let balanceDue = grandTotal - amountReceived;
            
            // Auto-update status based on amount received (if amount was entered)
            if (amountReceivedInput !== "") {
                if (amountReceived === 0) status = "PENDING";
                else if (amountReceived < grandTotal) status = "PARTIAL";
                else if (amountReceived === grandTotal) status = "PAID";
                else status = "ADVANCE";
                document.getElementById('edit_payment_status').value = status;
            }

            document.getElementById('edit_label_prev_arrears').innerText = previousArrears < 0 ? "Previous Advance:" : "Previous Arrears:";
            document.getElementById('edit_label_balance_due').innerText = balanceDue < 0 ? "Advance Amount" : "Balance Due";

            document.getElementById('edit_consumed_units_label').innerText = consumed.toFixed(1);
            document.getElementById('edit_live_rent').innerText = editState.rent.toFixed(2);
            document.getElementById('edit_live_water').innerText = editState.water.toFixed(2);
            document.getElementById('edit_live_tank_water').innerText = tankWater.toFixed(2);
            document.getElementById('edit_live_maintenance').innerText = maintenance.toFixed(2);
            document.getElementById('edit_live_additional').innerText = additional.toFixed(2);
            document.getElementById('edit_live_electricity').innerText = electricity.toFixed(2);

            document.getElementById('edit_live_current_total').innerText = currentTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            document.getElementById('edit_live_prev_arrears').innerText = Math.abs(previousArrears).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            document.getElementById('edit_live_grand_total').innerText = grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            document.getElementById('edit_live_amount_received').innerText = amountReceived.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            document.getElementById('edit_live_balance_due').innerText = Math.abs(balanceDue).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }

        function toggleEditMaintenanceDesc() {
            const val = parseFloat(document.getElementById('edit_maintenance_val').value) || 0;
            const descField = document.getElementById('edit_maintenance_desc');
            if (val > 0) {
                descField.disabled = false;
                descField.classList.remove("bg-body-tertiary");
            } else {
                descField.disabled = true;
                descField.classList.add("bg-body-tertiary");
                descField.value = "";
            }
        }

        // Handle Edit Form Submission
        document.getElementById('editReceiptForm').addEventListener('submit', async function (e) {
            e.preventDefault();

            const billNo = document.getElementById('edit_bill_no').value;
            const currentVal = parseFloat(document.getElementById('edit_current_reading').value) || 0;
            const previousArrears = parseFloat(document.getElementById('edit_previous_arrears').value) || 0;
            const amountReceivedInput = document.getElementById('edit_amount_received').value;

            if (currentVal < editState.prevMeter) {
                if (typeof showError === 'function') showError("Validation Error", `Current reading (${currentVal}) cannot be less than previous (${editState.prevMeter}).`);
                return;
            }

            const btn = document.getElementById('editSubmitBtn');
            const originalBtnHtml = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Updating...';

            const payload = {
                tenant: document.getElementById('edit_tenant').value,
                month: document.getElementById('edit_month').value,
                current_reading: currentVal,
                additional_persons: parseInt(document.getElementById('edit_additional_persons').value) || 0,
                tank_water: parseFloat(document.getElementById('edit_tank_water_val').value) || 0,
                maintenance_charge: parseFloat(document.getElementById('edit_maintenance_val').value) || 0,
                maintenance_desc: document.getElementById('edit_maintenance_desc').value || "",
                previous_arrears: previousArrears,
                amount_received: amountReceivedInput !== "" ? parseFloat(amountReceivedInput) : null,
                payment_status: document.getElementById("edit_payment_status") ? document.getElementById("edit_payment_status").value : "PENDING"
            };

            try {
                const res = await fetch(window.APP.API + `/edit_bill/${billNo}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                const result = await res.json();

                btn.disabled = false;
                btn.innerHTML = originalBtnHtml;

                if (res.ok) {
                    bootstrap.Modal.getInstance(document.getElementById('globalEditBillModal')).hide();
                    if (typeof showSuccess === 'function') {
                        showSuccess("Updated!", `Receipt #${billNo} has been updated.`).then(() => {
                            if (typeof updateUI === 'function') updateUI(); else window.location.reload();
                        });
                    } else {
                        alert("Updated successfully!");
                        window.location.reload();
                    }
                } else {
                    if (typeof showError === 'function') showError("Update Failed", result.detail || "An error occurred.");
                }
            } catch (error) {
                btn.disabled = false;
                btn.innerHTML = originalBtnHtml;
                if (typeof showError === 'function') showError("Network Error", "Could not reach the server.");
            }
        });
    </script>
    <script>
        async function sendWhatsApp(billNo) {
            if (typeof showLoadingOverlay === 'function') showLoadingOverlay("Generating WhatsApp link...");
            try {
                const res = await fetch(window.APP.API + `/whatsapp/single/${billNo}`);
                const data = await res.json();
                if (typeof hideLoadingOverlay === 'function') hideLoadingOverlay();

                if (res.ok) {
                    window.open(data.url, '_blank');
                } else {
                    if (typeof showError === 'function') showError('Cannot Send', data.detail);
                    else alert(data.detail);
                }
            } catch (e) {
                if (typeof hideLoadingOverlay === 'function') hideLoadingOverlay();
                if (typeof showError === 'function') showError('Error', 'Failed to generate WhatsApp link.');
            }
        }
    </script>

    <div id="globalSyncOverlay">
        <div class="sync-spinner">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>
        <div class="sync-text" id="syncOverlayText">Processing Data...</div>
    </div>

</body>

</html>
```

```html
// File: templates\billing.html
{% extends "base.html" %}

{% block title %}New Receipt | Rent Receipt System{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-8 col-md-10 col-12 mb-5">
        <div class="card shadow-sm border-0">
            <div class="card-header bg-primary bg-gradient text-white py-3 px-4 d-flex align-items-center">
                <i class="bi bi-file-earmark-plus fs-4 me-3"></i>
                <h4 class="mb-0 fw-bold tracking-wider">Generate New Receipt <span id="bill_no_display" class="badge bg-white text-primary ms-2 fs-6 align-middle d-none"></span></h4>
            </div>
            <div class="card-body px-4 px-md-5 py-4">
                <form id="receiptForm">
                    <!-- Tenant Selection -->
                    <div class="form-floating mb-4">
                        <select class="form-select form-select-lg" id="tenant" required onchange="onTenantChange()">
                            <option value="" data-id="" disabled selected>Select Tenant...</option>
                            {% for t in tenants %}
                            {% if t.status == 'Active' %}
                            <option value="{{ t.name }}" data-id="{{ t.id }}">{{ t.name }} {% if t.room_number %}(Room
                                {{ t.room_number }}){% endif %}</option>
                            {% endif %}
                            {% endfor %}
                        </select>
                        <label for="tenant"><i class="bi bi-person me-2"></i>Tenant Name</label>
                    </div>

                    <!-- Billing Month -->
                    <div class="form-floating mb-4">
                        <select class="form-select form-select-lg" id="month" required>
                        </select>
                        <label for="month"><i class="bi bi-calendar-event me-2"></i>Billing Month</label>
                    </div>

                    <h5 class="fw-bold mb-3 mt-4 text-secondary border-bottom pb-2">Fixed Charges</h5>
                    <div class="row g-3">
                        <div class="col-sm-4">
                            <div class="form-floating">
                                <input type="text" class="form-control bg-body-tertiary" id="rent_val" value=""
                                    placeholder="0.00" readonly>
                                <label for="rent_val">Monthly Rent (₹)</label>
                            </div>
                        </div>
                        <div class="col-sm-4">
                            <div class="form-floating">
                                <input type="text" class="form-control bg-body-tertiary" id="water_val" value=""
                                    placeholder="0.00" readonly>
                                <label for="water_val">Water Charge (₹)</label>
                            </div>
                        </div>
                        <div class="col-sm-4">
                            <div class="form-floating">
                                <input type="number" class="form-control" id="tank_water_val" step="0.1" value="0.00"
                                    oninput="calculateLiveTotal()">
                                <label for="tank_water_val">Tank Water Charge (₹)</label>
                            </div>
                        </div>
                    </div>

                    <h5 class="fw-bold mb-3 mt-4 text-secondary border-bottom pb-2">Maintenance & Other Charges</h5>
                    <div class="row g-3">
                        <div class="col-sm-4">
                            <div class="form-floating">
                                <input type="number" class="form-control border-info" id="maintenance_val" step="0.1"
                                    value="0.00" oninput="calculateLiveTotal(); toggleMaintenanceDesc();">
                                <label for="maintenance_val" class="text-info fw-bold">Amount (₹)</label>
                            </div>
                        </div>
                        <div class="col-sm-8">
                            <div class="form-floating">
                                <input type="text" class="form-control bg-body-tertiary" id="maintenance_desc"
                                    placeholder="e.g. Building Maintenance" disabled>
                                <label for="maintenance_desc">Description (Optional)</label>
                            </div>
                        </div>
                    </div>

                    <h5 class="fw-bold mb-3 mt-4 text-secondary border-bottom pb-2">Electricity</h5>
                    <div class="row g-3 mb-2">
                        <div class="col-sm-4">
                            <div class="form-floating">
                                <input type="text" class="form-control bg-body-tertiary" id="prev_reading" value=""
                                    placeholder="0.0" readonly>
                                <label for="prev_reading">Previous Reading</label>
                            </div>
                        </div>
                        <div class="col-sm-4">
                            <div class="form-floating">
                                <input type="number" class="form-control border-primary fw-bold" id="current_reading"
                                    step="0.1" placeholder="0.0" required oninput="calculateLiveTotal()">
                                <label for="current_reading" class="text-primary">Current Reading</label>
                            </div>
                        </div>
                        <div class="col-sm-4">
                            <div class="form-floating">
                                <input type="text" class="form-control bg-body-tertiary fw-bold" id="rate_display_input"
                                    value="₹0.00" readonly>
                                <label for="rate_display_input">Electricity Rate</label>
                            </div>
                        </div>
                    </div>
                    <div
                        class="d-flex align-items-center bg-primary-subtle text-primary rounded-3 px-3 py-2 mb-4 d-inline-block w-auto">
                        <i class="bi bi-lightning-charge-fill me-2"></i>
                        <span>Consumed Units: <strong id="consumed_units_label" class="fs-5 ms-1">0.0</strong></span>
                    </div>

                    <h5 class="fw-bold mb-3 mt-4 text-secondary border-bottom pb-2">Occupancy</h5>
                    <div class="row g-3 mb-4">
                        <div class="col-sm-6">
                            <div class="form-floating">
                                <input type="number" class="form-control border-primary" id="additional_persons"
                                    placeholder="Blank if none" min="0" oninput="calculateLiveTotal()">
                                <label for="additional_persons" class="text-primary">Additional Persons</label>
                            </div>
                            <div class="form-text fs-8 text-muted mt-1">Number of extra people.</div>
                        </div>
                        <div class="col-sm-6">
                            <div class="form-floating">
                                <input type="text" class="form-control bg-body-tertiary" id="add_rate_display_input"
                                    value="₹0.00" readonly>
                                <label for="add_rate_display_input">Rate per person (₹)</label>
                            </div>
                        </div>
                    </div>

                    <h5 class="fw-bold mb-3 mt-4 text-secondary border-bottom pb-2">Arrears & Payments</h5>
                    <div class="row g-3 mb-4">
                        <div class="col-sm-6">
                            <div class="form-floating">
                                <input type="number" class="form-control border-warning fw-bold text-warning-emphasis"
                                    id="previous_arrears" step="0.1" placeholder="0.00" value="0.00"
                                    oninput="calculateLiveTotal()">
                                <label for="previous_arrears" class="text-warning-emphasis">Previous Arrears (₹)</label>
                            </div>
                            <div class="form-text fs-8 text-muted mt-1">Automatically carries over balance from the last
                                bill.</div>
                        </div>
                        <div class="col-sm-6">
                            <div class="form-floating">
                                <input type="number" class="form-control border-success fw-bold text-success"
                                    id="amount_received" step="0.1" placeholder="Leave empty for full payment"
                                    oninput="calculateLiveTotal()">
                                <label for="amount_received" class="text-success">Amount Received (₹)</label>
                            </div>
                            <div class="form-text fs-8 text-muted mt-1">Leave empty to assume full payment.</div>
                        </div>
                    </div>

                    <!-- Live Total Details Area -->
                    <div class="card bg-success bg-gradient text-white border-0 shadow-sm mb-4">
                        <div class="card-body p-4">
                            <h6 class="text-uppercase fw-semibold text-white-50 mb-3 fs-8 tracking-wider">Live Breakdown
                            </h6>

                            <div class="d-flex justify-content-between mb-2">
                                <span class="text-white-50">Rent:</span>
                                <span class="fw-bold">₹<span id="live_rent">0.00</span></span>
                            </div>
                            <div class="d-flex justify-content-between mb-2">
                                <span class="text-white-50">Water:</span>
                                <span class="fw-bold">₹<span id="live_water">0.00</span></span>
                            </div>
                            <div class="d-flex justify-content-between mb-2">
                                <span class="text-white-50">Tank Water:</span>
                                <span class="fw-bold">₹<span id="live_tank_water">0.00</span></span>
                            </div>
                            <div class="d-flex justify-content-between mb-2">
                                <span class="text-white-50">Maintenance:</span>
                                <span class="fw-bold text-info">₹<span id="live_maintenance">0.00</span></span>
                            </div>
                            <div class="d-flex justify-content-between mb-2">
                                <span class="text-white-50">Additional:</span>
                                <span class="fw-bold">₹<span id="live_additional">0.00</span></span>
                            </div>
                            <div class="d-flex justify-content-between mb-3">
                                <span class="text-white-50">Electricity:</span>
                                <span class="fw-bold">₹<span id="live_electricity">0.00</span></span>
                            </div>
                            <hr class="border-white opacity-25 my-2">

                            <div class="d-flex justify-content-between mb-2 border-top border-white pt-2"
                                style="--bs-border-opacity: 0.5;">
                                <span class="text-white-50">Current Bill Total:</span>
                                <span class="fw-bold">₹<span id="live_current_total">0.00</span></span>
                            </div>
                            <div class="d-flex justify-content-between mb-2">
                                <span class="text-warning fw-bold" id="live_prev_arrears_label">Previous Arrears:</span>
                                <span class="fw-bold text-warning">₹<span id="live_prev_arrears">0.00</span></span>
                            </div>
                            <div class="d-flex justify-content-between align-items-center mt-3 pt-2 border-top border-white"
                                style="--bs-border-opacity: 0.5;">
                                <span class="fs-5 fw-bold">GRAND TOTAL</span>
                                <span class="fs-4 fw-bold">₹<span id="live_grand_total">0.00</span></span>
                            </div>

                        </div>
                    </div>




                    <button type="submit" class="btn btn-success btn-lg rounded-pill w-100 py-3 shadow-sm fw-bold fs-5"
                        id="submitBtn">
                        <i class="bi bi-check2-circle me-2"></i>Generate Receipt
                    </button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    let defaultRent = 0;
    let defaultWater = 0;
    let prevMeterVal = 0;
    let electricityRate = 0;
    let additionalPersonCharge = 0;
    let defaultTankWater = 0;
    let calculatedArrearsVal = 0;

    document.addEventListener("DOMContentLoaded", function () {
        loadMonths();
    });

    async function onTenantChange() {
        const select = document.getElementById("tenant");
        const option = select.options[select.selectedIndex];
        const tenantId = option.getAttribute("data-id");
        const tenantName = select.value;

        if (!tenantId) return;

        try {
            const [tRes, recRes] = await Promise.all([
                fetch(`api/tenants/${tenantId}`),
                fetch(`api/tenant_receipts/${encodeURIComponent(tenantName)}`)
            ]);

            if (tRes.ok) {
                const t = await tRes.json();
                defaultRent = t.rent || 0;
                defaultWater = t.water || 0;
                prevMeterVal = t.previous_meter || 0;
                electricityRate = t.electricity_rate || 0;
                additionalPersonCharge = t.additional_person_charge || 0;
                defaultTankWater = t.default_tank_water_charge || 0;

                document.getElementById("rent_val").value = defaultRent > 0 ? defaultRent.toFixed(2) : "";
                document.getElementById("water_val").value = defaultWater > 0 ? defaultWater.toFixed(2) : "";
                document.getElementById("prev_reading").value = prevMeterVal > 0 ? prevMeterVal.toFixed(1) : "";
                document.getElementById("additional_persons").value = "";
                document.getElementById("rate_display_input").value = `₹${electricityRate.toFixed(2)}`;
                document.getElementById("add_rate_display_input").value = `₹${additionalPersonCharge.toFixed(2)}`;
                document.getElementById("tank_water_val").value = defaultTankWater.toFixed(2);

                let calculatedArrears = 0;
                let maxSeq = 0;
                if (recRes.ok) {
                    const receipts = await recRes.json();
                    
                    receipts.forEach(r => {
                        let bStr = r.Bill;
                        if (bStr) {
                            let parts = bStr.split('-');
                            let seq = parts.length > 1 ? parseInt(parts[parts.length - 1]) : parseInt(bStr);
                            if (!isNaN(seq)) {
                                maxSeq = Math.max(maxSeq, seq);
                            }
                        }
                    });

                    if (receipts.length > 0) {
                        const last = receipts[0];
                        const lastTotal = parseFloat(last.Total) || 0;
                        const lastPrevArr = parseFloat(last.Previous_Arrears) || 0;
                        const grandTotal = lastTotal + lastPrevArr;
                        const lastRecv = (last.Amount_Received !== null && last.Amount_Received !== undefined) ? parseFloat(last.Amount_Received) : grandTotal;

                        if (!isNaN(lastRecv)) {
                            calculatedArrears = grandTotal - lastRecv;
                        }
                    }
                }

                calculatedArrearsVal = calculatedArrears;
                const nextBillNo = "T" + tenantId + "-" + String(maxSeq + 1).padStart(3, '0');
                const billDisplay = document.getElementById("bill_no_display");
                if (billDisplay) {
                    billDisplay.innerText = "#" + nextBillNo;
                    billDisplay.classList.remove("d-none");
                }

                calculateLiveTotal();
            }
        } catch (e) {
            console.error(e);
            showToast("error", "Failed to load tenant billing profile");
        }
    }

    async function loadMonths() {
        try {
            const res = await fetch("api/billing/months");
            if (res.ok) {
                const data = await res.json();
                const select = document.getElementById("month");
                select.innerHTML = "";

                data.months.forEach(m => {
                    let option = document.createElement("option");
                    option.value = m;
                    option.text = m;
                    if (m === data.currentMonth) {
                        option.selected = true;
                    }
                    select.appendChild(option);
                });
            }
        } catch (e) {
            console.error("Failed to load month list", e);
            showToast('error', 'Failed to load billing months');
        }
    }

    function calculateLiveTotal() {
        const currentVal = parseFloat(document.getElementById("current_reading").value) || 0;
        const addPersons = parseInt(document.getElementById("additional_persons").value) || 0;

        let consumed = Math.max(0, currentVal - prevMeterVal);
        let electricity = consumed * electricityRate;
        let additional = addPersons * additionalPersonCharge;
        let tankWater = parseFloat(document.getElementById("tank_water_val").value) || 0;
        let maintenance = parseFloat(document.getElementById("maintenance_val").value) || 0;
        let currentTotal = defaultRent + defaultWater + tankWater + maintenance + additional + electricity;

        let previousArrears = calculatedArrearsVal;
        let grandTotal = currentTotal + previousArrears;

        // Update Labels
        document.getElementById("consumed_units_label").innerText = consumed.toFixed(1);
        document.getElementById("live_rent").innerText = defaultRent.toFixed(2);
        document.getElementById("live_water").innerText = defaultWater.toFixed(2);
        document.getElementById("live_tank_water").innerText = tankWater.toFixed(2);
        document.getElementById("live_maintenance").innerText = maintenance.toFixed(2);
        document.getElementById("live_additional").innerText = additional.toFixed(2);
        document.getElementById("live_electricity").innerText = electricity.toFixed(2);

        document.getElementById("live_current_total").innerText = currentTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        document.getElementById("live_prev_arrears_label").innerText = previousArrears < 0 ? "Previous Advance:" : "Previous Arrears:";
        document.getElementById("live_prev_arrears").innerText = Math.abs(previousArrears).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        document.getElementById("live_grand_total").innerText = grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function toggleMaintenanceDesc() {
        const val = parseFloat(document.getElementById("maintenance_val").value) || 0;
        const descField = document.getElementById("maintenance_desc");
        if (val > 0) {
            descField.disabled = false;
            descField.classList.remove("bg-body-tertiary");
        } else {
            descField.disabled = true;
            descField.classList.add("bg-body-tertiary");
            descField.value = "";
        }
    }

    document.getElementById("receiptForm").addEventListener("submit", async function (e) {
        e.preventDefault();

        const tenant = document.getElementById("tenant").value;
        const month = document.getElementById("month").value;
        const currentVal = parseFloat(document.getElementById("current_reading").value);
        const addPersons = parseInt(document.getElementById("additional_persons").value) || 0;
        const previousArrears = calculatedArrearsVal;
        const amountReceivedInput = "";
        const paymentStatus = "PENDING";

        if (currentVal < prevMeterVal) {
            showError("Invalid Meter Reading", `Current reading (${currentVal}) cannot be less than the previous reading (${prevMeterVal}).`);
            return;
        }

        const submitBtn = document.querySelector('#receiptForm button[type="submit"]');
        if (submitBtn) submitBtn.disabled = true;

        showLoadingOverlay("Generating Receipt...");

        try {
            const res = await fetch("api/bill", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    tenant: tenant,
                    month: month,
                    current_reading: currentVal,
                    additional_persons: addPersons,
                    tank_water: parseFloat(document.getElementById("tank_water_val").value) || 0,
                    maintenance_charge: parseFloat(document.getElementById("maintenance_val").value) || 0,
                    maintenance_desc: document.getElementById("maintenance_desc").value || "",
                    previous_arrears: previousArrears,
                    amount_received: amountReceivedInput !== "" ? parseFloat(amountReceivedInput) : null,
                    payment_status: paymentStatus
                })
            });
            const result = await res.json();
            hideLoadingOverlay();

            if (res.ok) {
                const successHtml = `
                    <div class="mt-3">
                        <h4 class="fw-bold text-success mb-1">₹${document.getElementById("live_grand_total").innerText}</h4>
                        <p class="text-muted mb-4">Receipt #${result.data.Bill}</p>
                        <hr>
                        <div class="d-flex flex-column gap-2 text-start">
                            <button type="button" onclick="Swal.close(); openGlobalPDFPreview('${result.data.Bill}')" class="btn btn-outline-primary text-start">
                                <i class="bi bi-eye me-2"></i> Preview Receipt
                            </button>
                            <a href="javascript:void(0)" onclick="secureDownload('api/pdf/${result.data.Bill}/download', 'Receipt_${result.data.Bill}.pdf')" class="btn btn-outline-secondary text-start">
                                <i class="bi bi-download me-2"></i> Download PDF
                            </a>
                            <a href="{{ APP_BASE(request) }}/history" class="btn btn-outline-secondary text-start">
                                <i class="bi bi-clock-history me-2"></i> Receipt History
                            </a>
                        </div>
                    </div>
                `;

                Swal.fire({
                    icon: 'success',
                    title: 'Receipt Generated',
                    html: successHtml,
                    showConfirmButton: true,
                    confirmButtonText: '<i class="bi bi-plus-lg me-1"></i> Generate Another',
                    confirmButtonColor: '#198754',
                    allowOutsideClick: false
                }).then((result) => {
                    if (result.isConfirmed) {
                        window.location.reload();
                    }
                });

            } else {
                const detail = result.detail || "Failed to create receipt.";
                const match = detail.match(/Bill\s+#?([A-Z0-9-]+)/i);
                
                if (res.status === 409 || detail.includes("already exists")) {
                    if (match) {
                        const existingBillNo = match[1];
                        Swal.fire({
                            icon: 'error',
                            title: 'Bill already exists',
                            text: `This month already has a bill (${existingBillNo}).`,
                            showCancelButton: true,
                            confirmButtonText: '<i class="bi bi-pencil me-1"></i> Edit Existing Bill',
                            cancelButtonText: 'Close',
                            confirmButtonColor: '#ffc107',
                            cancelButtonColor: '#6c757d'
                        }).then((result) => {
                            if (result.isConfirmed) {
                                if (typeof openEditBillModal === 'function') {
                                    openEditBillModal(existingBillNo);
                                }
                            }
                        });
                        return;
                    }
                }
                showError("Generation Failed", detail);
            }
        } catch (err) {
            hideLoadingOverlay();
            showError("Network Error", "A connection error occurred while generating the receipt.");
        } finally {
            const submitBtn = document.querySelector('#receiptForm button[type="submit"]');
            if (submitBtn) submitBtn.disabled = false;
        }
    });
</script>
{% endblock %}
```

```html
// File: templates\dashboard.html
{% extends "base.html" %}

{% block title %}Dashboard | Rent Receipt System{% endblock %}

{% block head %}
<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pb-3 mb-4 border-bottom">
    <div>
        <h1 class="h2 mb-1 fw-bold">Dashboard</h1>
        <div class="text-muted fs-6">
            <i class="bi bi-calendar3 me-2"></i>Today is <span id="currentDate" class="fw-medium"></span> &nbsp;|&nbsp;
            <i class="bi bi-clock-history me-2"></i>Billing Month: <span class="fw-bold text-primary">{{
                stats.current_month }}</span>
        </div>
    </div>
    <div class="btn-toolbar mb-2 mb-md-0 gap-2">
        <a href="{{ route(request, Names.BILLING_PAGE) }}" class="btn btn-primary rounded-pill px-4 shadow-sm">
            <i class="bi bi-plus-lg me-2"></i>New Receipt
        </a>
        <a href="{{ APP_BASE(request) }}/settings" class="btn btn-outline-secondary rounded-pill shadow-sm">
            <i class="bi bi-gear"></i>
        </a>
    </div>
</div>

<!-- Stats Cards -->
<div class="row row-cols-1 row-cols-sm-2 row-cols-xl-5 g-4 mb-5">
    <!-- Card 1: Monthly Revenue -->
    <div class="col">
        <div
            class="card h-100 shadow-sm border-0 bg-primary bg-gradient text-white card-hover overflow-hidden position-relative">
            <div class="position-absolute end-0 top-0 mt-3 me-3 opacity-25">
                <i class="bi bi-currency-rupee" style="font-size: 3rem;"></i>
            </div>
            <div class="card-body py-4 z-1">
                <h6 class="text-white-50 text-uppercase fw-semibold tracking-wider mb-2" style="font-size: 0.75rem;">
                    Monthly Revenue</h6>
                <h3 class="fw-bold mb-1">₹{{ "{:,.0f}".format(stats.monthly_revenue) }}</h3>
                <span class="text-white-50 fs-8 d-block mt-1">Received this month</span>
            </div>
        </div>
    </div>

    <!-- Card 2: Previous Month Revenue -->
    <div class="col">
        <div
            class="card h-100 shadow-sm border-0 bg-secondary bg-gradient text-white card-hover overflow-hidden position-relative">
            <div class="position-absolute end-0 top-0 mt-3 me-3 opacity-25">
                <i class="bi bi-graph-up" style="font-size: 3rem;"></i>
            </div>
            <div class="card-body py-4 z-1">
                <h6 class="text-white-50 text-uppercase fw-semibold tracking-wider mb-2" style="font-size: 0.75rem;">
                    Prev Month Revenue</h6>
                <h3 class="fw-bold mb-1">₹{{ "{:,.0f}".format(stats.prev_monthly_revenue) }}</h3>
                {% if stats.revenue_change_str == "New Month" %}
                <span class="badge bg-white text-dark rounded-pill fw-bold fs-8 mt-1">New Month</span>
                {% else %}
                <span class="badge bg-white text-dark rounded-pill fw-bold fs-8 mt-1">{{ stats.revenue_change_str
                    }}</span>
                {% endif %}
            </div>
        </div>
    </div>

    <!-- Card 3: Bills Generated -->
    <div class="col" style="cursor: pointer;" onclick="openDashboardModal('paid', 'Paid Bills')">
        <div
            class="card h-100 shadow-sm border-0 bg-info bg-gradient text-white card-hover overflow-hidden position-relative">
            <div class="position-absolute end-0 top-0 mt-3 me-3 opacity-25">
                <i class="bi bi-receipt" style="font-size: 3rem;"></i>
            </div>
            <div class="card-body py-4 z-1">
                <h6 class="text-white-50 text-uppercase fw-semibold tracking-wider mb-2" style="font-size: 0.75rem;">
                    Paid Bills</h6>
                <h3 class="fw-bold mb-1">{{ stats.paid_bills_count }} <span
                        class="fs-6 fw-normal text-white-50">Bills</span></h3>
                <span class="text-white-50 fs-8 d-block mt-1">Paid receipts count</span>
            </div>
        </div>
    </div>

    <!-- Card 4: Due Payments -->
    <div class="col" style="cursor: pointer;" onclick="openDashboardModal('pending', 'Due Payments')">
        <div
            class="card h-100 shadow-sm border-0 bg-danger bg-gradient text-white card-hover overflow-hidden position-relative">
            <div class="position-absolute end-0 top-0 mt-3 me-3 opacity-25">
                <i class="bi bi-exclamation-circle" style="font-size: 3rem;"></i>
            </div>
            <div class="card-body py-4 z-1">
                <h6 class="text-white-50 text-uppercase fw-semibold tracking-wider mb-2" style="font-size: 0.75rem;">
                    Due Payments</h6>
                <h3 class="fw-bold mb-1">{{ stats.pending_payments_count }} <span
                        class="fs-6 fw-normal text-white-50">Due</span></h3>
                <span class="text-white-50 fs-8 d-block mt-1">Due receipts count</span>
            </div>
        </div>
    </div>

    <!-- Card 5: Pending Amount -->
    <div class="col">
        <div class="card h-100 shadow-sm border-0 bg-danger bg-gradient text-white card-hover overflow-hidden position-relative"
            style="--bs-bg-opacity: 0.8;">
            <div class="position-absolute end-0 top-0 mt-3 me-3 opacity-25">
                <i class="bi bi-cash-stack" style="font-size: 3rem;"></i>
            </div>
            <div class="card-body py-4 z-1">
                <h6 class="text-white-50 text-uppercase fw-semibold tracking-wider mb-2" style="font-size: 0.75rem;">
                    Pending Amount</h6>
                <h3 class="fw-bold mb-1">₹{{ "{:,.0f}".format(stats.pending_amount) }}</h3>
                <span class="text-white-50 fs-8 d-block mt-1">To be collected</span>
            </div>
        </div>
    </div>

    <!-- Card 6: Amount Collected -->
    <div class="col">
        <div
            class="card h-100 shadow-sm border-0 bg-success bg-gradient text-white card-hover overflow-hidden position-relative">
            <div class="position-absolute end-0 top-0 mt-3 me-3 opacity-25">
                <i class="bi bi-piggy-bank" style="font-size: 3rem;"></i>
            </div>
            <div class="card-body py-4 z-1">
                <h6 class="text-white-50 text-uppercase fw-semibold tracking-wider mb-2" style="font-size: 0.75rem;">
                    Amount Collected</h6>
                <h3 class="fw-bold mb-1">₹{{ "{:,.0f}".format(stats.amount_collected) }}</h3>
                <span class="text-white-50 fs-8 d-block mt-1">Sum of paid receipts</span>
            </div>
        </div>
    </div>

    <!-- Card 7: Active Tenants -->
    <div class="col">
        <div class="card h-100 shadow-sm border-0 bg-primary bg-gradient text-white card-hover overflow-hidden position-relative"
            style="--bs-bg-opacity: 0.8;">
            <div class="position-absolute end-0 top-0 mt-3 me-3 opacity-25">
                <i class="bi bi-people" style="font-size: 3rem;"></i>
            </div>
            <div class="card-body py-4 z-1">
                <h6 class="text-white-50 text-uppercase fw-semibold tracking-wider mb-2" style="font-size: 0.75rem;">
                    Active Tenants</h6>
                <h3 class="fw-bold mb-1">{{ stats.active_tenants }} <span
                        class="fs-6 fw-normal text-white-50">Active</span></h3>
                <span class="text-white-50 fs-8 d-block mt-1">{{ stats.inactive_tenants }} Inactive</span>
            </div>
        </div>
    </div>

    <!-- Card 8: Last Meter Reading -->
    <div class="col">
        <div
            class="card h-100 shadow-sm border-0 bg-warning bg-gradient text-dark card-hover overflow-hidden position-relative">
            <div class="position-absolute end-0 top-0 mt-3 me-3 opacity-25">
                <i class="bi bi-speedometer2" style="font-size: 3rem;"></i>
            </div>
            <div class="card-body py-4 z-1">
                <h6 class="text-dark-50 text-uppercase fw-semibold tracking-wider mb-2"
                    style="opacity: 0.7; font-size: 0.75rem;">Last Meter Reading</h6>
                <h3 class="fw-bold mb-1">{{ "{:,.0f}".format(stats.highest_meter_reading) }} <span
                        class="fs-6 fw-normal text-dark-50" style="opacity: 0.7;">Units</span></h3>
                <span class="text-dark-50 fs-8 d-block mt-1" style="opacity: 0.7;">Highest current meter</span>
            </div>
        </div>
    </div>

    <!-- Card 9: Electricity Consumed -->
    <div class="col">
        <div class="card h-100 shadow-sm border-0 bg-warning bg-gradient text-dark card-hover overflow-hidden position-relative"
            style="--bs-bg-opacity: 0.8;">
            <div class="position-absolute end-0 top-0 mt-3 me-3 opacity-25">
                <i class="bi bi-lightning-charge" style="font-size: 3rem;"></i>
            </div>
            <div class="card-body py-4 z-1">
                <h6 class="text-dark-50 text-uppercase fw-semibold tracking-wider mb-2"
                    style="opacity: 0.7; font-size: 0.75rem;">Electricity Consumed</h6>
                <h3 class="fw-bold mb-1">{{ "{:,.0f}".format(stats.electricity_consumed) }} <span
                        class="fs-6 fw-normal text-dark-50" style="opacity: 0.7;">Units</span></h3>
                <span class="text-dark-50 fs-8 d-block mt-1" style="opacity: 0.7;">Current month</span>
            </div>
        </div>
    </div>

    <!-- Card 10: Collection Rate -->
    <div class="col">
        <div class="card h-100 shadow-sm border-0 bg-success bg-gradient text-white card-hover overflow-hidden position-relative"
            style="--bs-bg-opacity: 0.8;">
            <div class="position-absolute end-0 top-0 mt-3 me-3 opacity-25">
                <i class="bi bi-pie-chart" style="font-size: 3rem;"></i>
            </div>
            <div class="card-body py-4 z-1">
                <h6 class="text-white-50 text-uppercase fw-semibold tracking-wider mb-2" style="font-size: 0.75rem;">
                    Collection Rate</h6>
                <h3 class="fw-bold mb-1">{{ "{:.0f}".format(stats.collection_rate) }}%</h3>
                <span class="text-white-50 fs-8 d-block mt-1">Paid / Generated</span>
            </div>
        </div>
    </div>
</div>

<div class="row g-4 mb-4">
    <!-- Chart: Monthly Revenue -->
    <div class="col-xl-6">
        <div class="card shadow-sm h-100 border-0">
            <div class="card-header bg-transparent border-0 pt-4 pb-0 px-4">
                <h5 class="fw-bold mb-0"><i class="bi bi-graph-up-arrow me-2 text-success"></i>Revenue Trends</h5>
            </div>
            <div class="card-body p-4">
                <canvas id="revenueChart" style="max-height: 250px;"></canvas>
            </div>
        </div>
    </div>

    <!-- Chart: Electricity Consumption -->
    <div class="col-xl-6">
        <div class="card shadow-sm h-100 border-0">
            <div class="card-header bg-transparent border-0 pt-4 pb-0 px-4">
                <h5 class="fw-bold mb-0"><i class="bi bi-lightning-charge-fill me-2 text-warning"></i>Electricity
                    Consumption</h5>
            </div>
            <div class="card-body p-4">
                <canvas id="electricityChart" style="max-height: 250px;"></canvas>
            </div>
        </div>
    </div>
</div>

<div class="row g-4">
    <!-- Recent Bills -->
    <div class="col-xl-8">
        <div class="card shadow-sm border-0 h-100">
            <div
                class="card-header bg-transparent border-0 pt-4 pb-3 px-4 d-flex justify-content-between align-items-center">
                <h5 class="fw-bold mb-0"><i class="bi bi-list-stars me-2 text-primary"></i>Recent Bills</h5>
                <a href="{{ APP_BASE(request) }}/history" class="btn btn-sm btn-link text-decoration-none">View All</a>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive d-none d-md-block">
                    <table class="table table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th class="ps-4" style="width: 60px;">S.No</th>
                                <th>Bill #</th>
                                <th>Tenant</th>
                                <th>Month</th>
                                <th>Total</th>
                                <th>Payment</th>
                                <th class="text-end pe-4">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for b in stats.recent_bills %}
                            <tr>
                                <td class="ps-4 text-muted fw-semibold">{{ loop.index }}</td>
                                <td><span class="badge bg-secondary">{{ b.bill_no }}</span></td>
                                <td class="fw-semibold text-primary">{{ b.tenant_name }}</td>
                                <td>{{ b.month }}</td>
                                <td class="text-dark fw-bold">₹{{ "{:,.2f}".format(b.total|float) }}</td>
                                <td>
                                    {% set grand_total = (b.total|float) + (b.previous_arrears|default(0, true)|float) %}
                                    {% set amount_received = b.get("amount_received")|default(0, true)|float %}
                                    {% set balance_due = grand_total - amount_received %}
                                    {% set advance_amount = 0 - balance_due if balance_due < 0 else 0 %}

                                    {% if b.payment_status == "PAID" %}
                                        <span class="badge bg-success rounded-pill px-3"><i class="bi bi-circle-fill fs-9 me-1"></i> Paid</span>
                                    {% elif b.payment_status == "PARTIAL" %}
                                        <span class="badge bg-warning text-dark rounded-pill px-3"><i class="bi bi-circle-fill fs-9 me-1"></i> Partial</span>
                                    {% elif b.payment_status == "ADVANCE" %}
                                        <span class="badge bg-info text-dark rounded-pill px-3"><i class="bi bi-circle-fill fs-9 me-1"></i> Advance</span>
                                    {% else %}
                                        <span class="badge bg-danger rounded-pill px-3"><i class="bi bi-circle-fill fs-9 me-1"></i> Pending</span>
                                    {% endif %}
                                    <div class="small text-muted mt-1">Recv: ₹{{ "{:,.2f}".format(amount_received) }}</div>
                                    {% if balance_due > 0 %}
                                    <div class="small text-danger fw-semibold">Rem: ₹{{ "{:,.2f}".format(balance_due) }}</div>
                                    {% elif balance_due < 0 %}
                                    <div class="small text-info fw-semibold">Adv: ₹{{ "{:,.2f}".format(advance_amount) }}</div>
                                    {% endif %}
                                </td>
                                <td class="text-end pe-4">
                                    <div class="btn-group gap-1">
                                        {% if b.payment_status in ['PAID', 'PARTIAL', 'ADVANCE'] %}
                                        <button
                                            onclick="togglePaymentStatus('{{ b.bill_no }}', '{{ b.payment_status }}', '{{ grand_total }}', '{{ amount_received }}')"
                                            class="btn btn-sm btn-outline-secondary rounded-pill px-2 shadow-sm"
                                            title="Mark Pending">
                                            <i class="bi bi-arrow-counterclockwise"></i>
                                        </button>
                                        {% else %}
                                        <button
                                            onclick="togglePaymentStatus('{{ b.bill_no }}', 'PENDING', '{{ grand_total }}', '0')"
                                            class="btn btn-sm btn-outline-success rounded-pill px-2 shadow-sm"
                                            title="Mark Paid">
                                            <i class="bi bi-check2"></i> <span class="d-none d-xl-inline">Paid</span>
                                        </button>
                                        {% endif %}
                                        <button onclick="openGlobalPDFPreview('{{ b.bill_no }}')"
                                            class="btn btn-sm btn-light border rounded-pill px-3 shadow-sm"
                                            title="View PDF">
                                            <i class="bi bi-eye"></i> View
                                        </button>
                                        <a href="javascript:void(0)"
                                            onclick="secureDownload('api/pdf/{{ b.bill_no }}/download', 'Receipt_{{ b.bill_no }}.pdf')"
                                            class="btn btn-sm btn-light border rounded-pill px-3 shadow-sm"
                                            title="Download PDF">
                                            <i class="bi bi-download"></i> DL
                                        </a>
                                        {% if config.get('system', 'features.whatsapp_sync') %}
                                        <button class="btn btn-sm btn-light border text-success"
                                            onclick="sendWhatsApp('{{ b.bill_no }}')" title="Send via WhatsApp">
                                            <i class="bi bi-whatsapp"></i>
                                        </button>
                                        {% endif %}
                                        <button onclick="openEditBillModal('{{ b.bill_no }}')"
                                            class="btn btn-sm btn-light border rounded-pill px-3 shadow-sm text-warning"
                                            title="Edit Bill">
                                            <i class="bi bi-pencil"></i>
                                        </button>
                                    </div>
                                </td>
                            </tr>
                            {% endfor %}
                            {% if not stats.recent_bills %}
                            <tr>
                                <td colspan="5" class="text-center py-5 text-muted">
                                    <i class="bi bi-receipt fs-1 d-block mb-3 opacity-50"></i>
                                    <h5>No Receipts Yet</h5>
                                    <p class="fs-7">Generate your first receipt to see it here.</p>
                                    <a href="{{ APP_BASE(request) }}/billing"
                                        class="btn btn-primary rounded-pill mt-2">Generate Receipt</a>
                                </td>
                            </tr>
                            {% endif %}
                        </tbody>
                    </table>
                </div>
                <!-- Mobile Card View -->
                <div class="d-md-none p-3">
                    <div class="d-flex flex-column gap-3">
                        {% for b in stats.recent_bills %}
                        <div class="card shadow-sm border-0 bg-body-secondary">
                            <div class="card-body p-3">
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <div>
                                        <span class="badge bg-light text-dark border me-1">{{ loop.index }}</span>
                                        <span class="badge bg-secondary">{{ b.bill_no }}</span>
                                    </div>
                                    <span class="text-dark fw-bold fs-5">₹{{ "{:,.2f}".format(b.total|float) }}</span>
                                </div>
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    {% set grand_total = (b.total|float) + (b.previous_arrears|default(0, true)|float) %}
                                    {% set amount_received = b.get("amount_received")|default(0, true)|float %}
                                    {% set balance_due = grand_total - amount_received %}
                                    {% set advance_amount = 0 - balance_due if balance_due < 0 else 0 %}
                                    <h6 class="fw-bold text-primary mb-0">{{ b.tenant_name }}</h6>
                                    {% if b.payment_status == "PAID" %}
                                        <span class="badge bg-success rounded-pill"><i class="bi bi-circle-fill fs-9 me-1"></i> Paid</span>
                                    {% elif b.payment_status == "PARTIAL" %}
                                        <span class="badge bg-warning text-dark rounded-pill"><i class="bi bi-circle-fill fs-9 me-1"></i> Partial</span>
                                    {% elif b.payment_status == "ADVANCE" %}
                                        <span class="badge bg-info text-dark rounded-pill"><i class="bi bi-circle-fill fs-9 me-1"></i> Advance</span>
                                    {% else %}
                                        <span class="badge bg-danger rounded-pill"><i class="bi bi-circle-fill fs-9 me-1"></i> Pending</span>
                                    {% endif %}
                                </div>
                                <div class="d-flex justify-content-between mb-3">
                                    <p class="text-muted fs-7 mb-0"><i class="bi bi-calendar3 me-1"></i> {{ b.month }}</p>
                                    <div class="text-end">
                                        <div class="small text-muted" style="font-size: 0.75rem;">Recv: ₹{{ "{:,.2f}".format(amount_received) }}</div>
                                        {% if balance_due > 0 %}
                                        <div class="small text-danger fw-semibold" style="font-size: 0.75rem;">Rem: ₹{{ "{:,.2f}".format(balance_due) }}</div>
                                        {% elif balance_due < 0 %}
                                        <div class="small text-info fw-semibold" style="font-size: 0.75rem;">Adv: ₹{{ "{:,.2f}".format(advance_amount) }}</div>
                                        {% endif %}
                                    </div>
                                </div>
                                <div class="d-flex flex-wrap gap-2">
                                    {% if b.payment_status in ['PAID', 'PARTIAL', 'ADVANCE'] %}
                                    <button onclick="togglePaymentStatus('{{ b.bill_no }}', '{{ b.payment_status }}', '{{ grand_total }}', '{{ amount_received }}')"
                                        class="btn btn-sm btn-outline-secondary rounded-pill flex-grow-1 shadow-sm"><i
                                            class="bi bi-arrow-counterclockwise"></i> Undo</button>
                                    {% else %}
                                    <button onclick="togglePaymentStatus('{{ b.bill_no }}', 'PENDING', '{{ grand_total }}', '0')"
                                        class="btn btn-sm btn-outline-success rounded-pill flex-grow-1 shadow-sm"><i
                                            class="bi bi-check2"></i> Mark Paid</button>
                                    {% endif %}
                                    <button onclick="openGlobalPDFPreview('{{ b.bill_no }}')"
                                        class="btn btn-sm btn-light border rounded-pill flex-grow-1 shadow-sm"><i
                                            class="bi bi-eye"></i> View</button>
                                    {% if config.get('system', 'features.whatsapp_sync') %}
                                    <button class="btn btn-sm btn-light border text-success flex-grow-1"
                                        onclick="sendWhatsApp('{{ b.bill_no }}')" title="Send via WhatsApp"><i
                                            class="bi bi-whatsapp"></i></button>
                                    {% endif %}
                                    <button onclick="openEditBillModal('{{ b.bill_no }}')"
                                        class="btn btn-sm btn-light border rounded-pill flex-grow-1 shadow-sm text-warning"><i
                                            class="bi bi-pencil"></i> Edit</button>
                                </div>
                            </div>
                        </div>
                        {% endfor %}
                        {% if not stats.recent_bills %}
                        <div class="text-center py-5 text-muted">
                            <i class="bi bi-receipt fs-1 d-block mb-3 opacity-50"></i>
                            <h5>No Receipts Yet</h5>
                            <p class="fs-7">Generate your first receipt to see it here.</p>
                            <a href="{{ APP_BASE(request) }}/billing" class="btn btn-primary rounded-pill mt-2">Generate
                                Receipt</a>
                        </div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Recent Activity -->
    <div class="col-xl-4">
        <div class="card shadow-sm border-0 h-100">
            <div class="card-header bg-transparent border-0 pt-4 pb-3 px-4">
                <h5 class="fw-bold mb-0"><i class="bi bi-activity me-2 text-danger"></i>Recent Activity</h5>
            </div>
            <div class="card-body px-4 pt-0">
                <div class="position-relative mt-3">
                    <!-- Placeholder Activity Feed -->
                    <div class="d-flex mb-4">
                        <div class="flex-shrink-0">
                            <div class="bg-success-subtle text-success rounded-circle d-flex align-items-center justify-content-center"
                                style="width: 40px; height: 40px;">
                                <i class="bi bi-file-earmark-check fs-5"></i>
                            </div>
                        </div>
                        <div class="ms-3 flex-grow-1 border-bottom pb-3">
                            <h6 class="mb-1 fw-bold">Receipt Generated</h6>
                            <p class="text-muted fs-7 mb-0">System automatically saved receipt #001 for L T Elevator.
                            </p>
                            <small class="text-secondary fs-8">2 hours ago</small>
                        </div>
                    </div>

                    <div class="d-flex mb-4">
                        <div class="flex-shrink-0">
                            <div class="bg-primary-subtle text-primary rounded-circle d-flex align-items-center justify-content-center"
                                style="width: 40px; height: 40px;">
                                <i class="bi bi-person-plus fs-5"></i>
                            </div>
                        </div>
                        <div class="ms-3 flex-grow-1 border-bottom pb-3">
                            <h6 class="mb-1 fw-bold">Tenant Added</h6>
                            <p class="text-muted fs-7 mb-0">New tenant profile created.</p>
                            <small class="text-secondary fs-8">Yesterday</small>
                        </div>
                    </div>

                    <div class="d-flex">
                        <div class="flex-shrink-0">
                            <div class="bg-warning-subtle text-warning rounded-circle d-flex align-items-center justify-content-center"
                                style="width: 40px; height: 40px;">
                                <i class="bi bi-gear fs-5"></i>
                            </div>
                        </div>
                        <div class="ms-3 flex-grow-1">
                            <h6 class="mb-1 fw-bold">Settings Updated</h6>
                            <p class="text-muted fs-7 mb-0">Billing configuration modified.</p>
                            <small class="text-secondary fs-8">3 days ago</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script id="chart-data" type="application/json">
{
    "labels": {{ stats.chart_labels | tojson }},
    "revenue": {{ stats.chart_revenue | tojson }},
    "electricity": {{ stats.chart_electricity | tojson }}
}
</script>
<script>
    // Set Current Date
    document.getElementById('currentDate').innerText = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

    // Config Chart.js color based on bootstrap theme
    const themeAttr = document.documentElement.getAttribute('data-bs-theme');
    const isDark = themeAttr === 'dark' || (themeAttr === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    const textColor = isDark ? '#adb5bd' : '#495057';
    const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';

    const chartData = JSON.parse(document.getElementById('chart-data').textContent);
    const labels = chartData.labels;
    const revenueData = chartData.revenue;
    const electricityData = chartData.electricity;

    // Revenue Chart (Gradient Fill)
    const revCtx = document.getElementById('revenueChart').getContext('2d');
    let gradientRev = revCtx.createLinearGradient(0, 0, 0, 400);
    gradientRev.addColorStop(0, 'rgba(25, 135, 84, 0.5)');
    gradientRev.addColorStop(1, 'rgba(25, 135, 84, 0.05)');

    new Chart(revCtx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Revenue (₹)',
                data: revenueData,
                backgroundColor: gradientRev,
                borderColor: 'rgb(25, 135, 84)',
                borderWidth: 2,
                fill: true,
                tension: 0.3,
                pointBackgroundColor: 'rgb(25, 135, 84)',
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { grid: { color: gridColor }, ticks: { color: textColor } },
                x: { grid: { display: false }, ticks: { color: textColor } }
            },
            plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
            interaction: { mode: 'nearest', axis: 'x', intersect: false }
        }
    });

    // Electricity Chart
    const elecCtx = document.getElementById('electricityChart').getContext('2d');
    let gradientElec = elecCtx.createLinearGradient(0, 0, 0, 400);
    gradientElec.addColorStop(0, 'rgba(255, 193, 7, 0.5)');
    gradientElec.addColorStop(1, 'rgba(255, 193, 7, 0.05)');

    new Chart(elecCtx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Electricity (Units)',
                data: electricityData,
                backgroundColor: gradientElec,
                borderColor: 'rgb(255, 193, 7)',
                borderWidth: 2,
                fill: true,
                tension: 0.3,
                pointBackgroundColor: 'rgb(255, 193, 7)',
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { grid: { color: gridColor }, ticks: { color: textColor } },
                x: { grid: { display: false }, ticks: { color: textColor } }
            },
            plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
            interaction: { mode: 'nearest', axis: 'x', intersect: false }
        }
    });
</script>
<div class="modal fade" id="dashboardDetailsModal" tabindex="-1">
    <div class="modal-dialog modal-xl modal-dialog-centered">
        <div class="modal-content border-0 shadow-lg rounded-4 overflow-hidden" style="height: 85vh;">
            <div class="modal-header border-bottom bg-light py-2">
                <h5 class="modal-title fw-bold" id="dashboardModalTitle">Details</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body p-0 d-flex flex-column flex-lg-row h-100">
                <div class="col-lg-5 col-xl-4 border-end bg-white d-flex flex-column h-100">
                    <div class="table-responsive flex-grow-1" style="overflow-y: auto;">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="table-light sticky-top">
                                <tr>
                                    <th class="ps-3">Bill & Status</th>
                                    <th>Tenant Details</th>
                                    <th class="text-end pe-3">Total</th>
                                </tr>
                            </thead>
                            <tbody id="dashboardModalBody">
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="col-lg-7 col-xl-8 bg-secondary position-relative h-100">
                    <div id="pdfPlaceholder"
                        class="position-absolute top-50 start-50 translate-middle text-center text-white-50 w-100">
                        <i class="bi bi-file-earmark-pdf" style="font-size: 4rem;"></i>
                        <p class="mt-2 fs-5">Select a bill from the list to preview</p>
                    </div>
                    <iframe id="dashboardPdfIframe" src="" width="100%" height="100%"
                        style="border: none; position: relative; z-index: 1; display: none;"></iframe>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
    async function openDashboardModal(statusType, title) {
        document.getElementById('dashboardModalTitle').innerText = title;
        const tbody = document.getElementById('dashboardModalBody');

        // Reset right panel
        document.getElementById('dashboardPdfIframe').style.display = 'none';
        document.getElementById('dashboardPdfIframe').src = '';
        document.getElementById('pdfPlaceholder').style.display = 'block';

        tbody.innerHTML = '<tr><td colspan="3" class="text-center py-5"><div class="spinner-border text-primary"></div></td></tr>';

        const modal = new bootstrap.Modal(document.getElementById('dashboardDetailsModal'));
        modal.show();

        try {
            const res = await fetch(`api/bills/filter?status=${statusType}`);
            const bills = await res.json();

            tbody.innerHTML = '';
            if (bills.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3" class="text-center py-5 text-muted">No records found.</td></tr>';
                return;
            }

            bills.forEach(b => {
                let badge = '';
                if (b.Payment_Status === 'PAID') {
                    badge = `<span class="badge bg-success rounded-pill px-2">Paid</span>`;
                } else if (b.Payment_Status === 'PARTIAL') {
                    badge = `<span class="badge bg-warning text-dark rounded-pill px-2">Partial</span>`;
                } else if (b.Payment_Status === 'ADVANCE') {
                    badge = `<span class="badge bg-info text-dark rounded-pill px-2">Advance</span>`;
                } else {
                    badge = `<span class="badge bg-danger rounded-pill px-2">Pending</span>`;
                }

                let grandTotal = parseFloat(b.Total) + (parseFloat(b.Previous_Arrears) || 0);
                let amountReceived = b.Amount_Received !== undefined && b.Amount_Received !== null ? parseFloat(b.Amount_Received) : (b.Payment_Status === 'PAID' ? grandTotal : 0);
                let balanceDue = grandTotal - amountReceived;
                let advanceAmount = balanceDue < 0 ? Math.abs(balanceDue) : 0;
                
                let detailsHtml = `<div class="small text-muted mt-1">Recv: ₹${amountReceived.toLocaleString('en-IN', {maximumFractionDigits: 0})}</div>`;
                if (balanceDue > 0) {
                    detailsHtml += `<div class="small text-danger">Rem: ₹${balanceDue.toLocaleString('en-IN', {maximumFractionDigits: 0})}</div>`;
                } else if (balanceDue < 0) {
                    detailsHtml += `<div class="small text-info">Adv: ₹${advanceAmount.toLocaleString('en-IN', {maximumFractionDigits: 0})}</div>`;
                }

                tbody.innerHTML += `
                    <tr style="cursor: pointer;" onclick="previewInSplitModal('${b.Bill}', this)" class="split-row transition-hover">
                        <td class="ps-3">
                            <span class="badge bg-secondary mb-1">#${b.Bill}</span><br>
                            ${badge}
                            ${detailsHtml}
                        </td>
                        <td>
                            <div class="fw-bold fs-7 text-primary text-truncate" style="max-width: 150px;">${b.Tenant}</div>
                            <div class="text-muted fs-8">${b.Month}</div>
                        </td>
                        <td class="text-end pe-3">
                            <div class="text-success fw-bold fs-7">₹${grandTotal.toLocaleString('en-IN', {maximumFractionDigits: 0})}</div>
                            <button class="btn btn-sm btn-light border rounded-pill mt-1" style="font-size: 0.7rem;"><i class="bi bi-eye"></i> View</button>
                        </td>
                    </tr>
                `;
            });

            // Auto-preview the first bill in the list
            if (bills.length > 0) {
                setTimeout(() => {
                    const firstRow = tbody.querySelector('tr');
                    if (firstRow) firstRow.click();
                }, 100);
            }

        } catch (e) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center py-4 text-danger">Failed to load data.</td></tr>';
        }
    }

    function previewInSplitModal(billNo, rowElement) {
        // Highlight selected row
        const rows = document.querySelectorAll('.split-row');
        rows.forEach(r => r.classList.remove('bg-primary-subtle'));
        if (rowElement) rowElement.classList.add('bg-primary-subtle');

        // Show iframe, hide placeholder
        document.getElementById('pdfPlaceholder').style.display = 'none';
        const iframe = document.getElementById('dashboardPdfIframe');
        iframe.style.display = 'block';
        iframe.src = `api/pdf/${billNo}/view`;
    }
</script>
{% endblock %}
```

```html
// File: templates\error.html
{% extends "base.html" %}

{% block content %}
<div class="container text-center my-5 py-5">
    <h1 class="display-1 fw-bold text-danger">{{ status_code }}</h1>
    <h2 class="mb-4">An error occurred</h2>
    <p class="lead mb-4">{{ detail }}</p>
    <a href="{{ route(request, Names.HOME) }}" class="btn btn-primary">Return Home</a>
</div>
{% endblock %}
```

```html
// File: templates\history.html
{% extends "base.html" %}

{% block title %}Receipt History | Rent Receipt System{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pb-3 mb-4 border-bottom">
    <h1 class="h2 mb-0 fw-bold">Receipt History</h1>

    <!-- Global Search for History -->
    <div class="input-group ms-auto mt-3 mt-md-0 shadow-sm" style="max-width: 400px;">
        <span class="input-group-text bg-white border-end-0 rounded-start-pill"><i
                class="bi bi-search text-muted"></i></span>
        <input type="text" class="form-control border-start-0 rounded-end-pill" id="globalSearch"
            placeholder="Search Tenant, Company, Amount...">
    </div>
</div>

<div class="accordion" id="historyAccordion">
    {% set current_year = '' %}
    {% set current_month = '' %}

    {% for r in receipts %}
    {% set parts = r.Month.split(' ') %}
    {% set m = parts[0] %}
    {% set y = parts[1] if parts|length > 1 else 'Unknown' %}

    {% if y != current_year %}
    {% if current_year != '' %}
</div> <!-- End Accordion Body -->
</div> <!-- End Collapse -->
</div> <!-- End Accordion Item -->
{% endif %}

<div class="accordion-item mb-4 shadow-sm border-0 year-group" data-year="{{ y }}">
    <h2 class="accordion-header" id="heading-{{ y }}">
        <button class="accordion-button bg-body-tertiary fw-bold fs-5" type="button" data-bs-toggle="collapse"
            data-bs-target="#collapse-{{ y }}" aria-expanded="true" aria-controls="collapse-{{ y }}">
            <i class="bi bi-calendar3 me-3 text-primary"></i> {{ y }}

            <!-- Year Summary Stats injected via JS -->
            <div class="ms-auto me-3 d-none d-md-flex gap-4 text-muted fs-7 fw-normal">
                <span><i class="bi bi-receipt"></i> <span class="year-bills-count">0</span> Bills</span>
                <span><i class="bi bi-currency-rupee"></i> <span class="year-revenue">0.00</span></span>
            </div>
        </button>
    </h2>
    <div id="collapse-{{ y }}" class="accordion-collapse collapse show" aria-labelledby="heading-{{ y }}">
        <div class="accordion-body p-0">
            {% set current_year = y %}
            {% set current_month = '' %}
            {% endif %}

            {% if m != current_month %}
            <div class="bg-light p-2 px-4 border-bottom fw-bold text-secondary month-header">
                <i class="bi bi-chevron-down me-2 fs-7"></i> {{ m }}
            </div>
            {% set current_month = m %}
            {% endif %}

            <!-- Receipt Row -->
            <div class="p-3 px-4 border-bottom d-flex flex-column flex-md-row justify-content-between align-items-md-center receipt-row transition-hover"
                data-tenant="{{ r.Tenant|lower }}" data-company="{{ r.Tenant_Company|lower }}"
                data-month="{{ m|lower }}" data-year="{{ y }}" data-bill="{{ r.Bill }}" data-total="{{ r.Total }}">
                {% set curr_total = r.Total|default(0,true)|float %}
                {% set prev_arr = r.Previous_Arrears|default(0,true)|float %}
                {% set grand_total = curr_total + prev_arr %}
                {% set amt_recv = r.Amount_Received|default(0, true)|float %}
                {% set balance = grand_total - amt_recv %}
                {% set advance_amount = 0 - balance if balance < 0 else 0 %}

                <div class="d-flex align-items-center mb-3 mb-md-0">
                    <div class="bg-primary-subtle text-primary rounded-circle d-flex align-items-center justify-content-center me-3"
                        style="width: 48px; height: 48px;">
                        <i class="bi bi-receipt fs-5"></i>
                    </div>
                    <div>
                        <h6 class="fw-bold mb-1">{{ r.Tenant }}</h6>
                        <div class="text-muted fs-7">
                            <span class="badge bg-secondary-subtle text-secondary me-2">#{{ r.Bill }}</span>
                            <i class="bi bi-calendar-event me-1"></i> {{ r.Date }}
                        </div>
                    </div>
                </div>

                <div class="d-flex flex-column flex-md-row align-items-md-center gap-3 gap-md-5">
                    <div
                        class="d-flex flex-row flex-md-column align-items-center align-items-md-end justify-content-between gap-2">
                        <div class="text-md-end">
                            <div class="fs-7 text-muted mb-1">Total Payable</div>
                            <div class="fw-bold text-dark fs-5">₹{{ "{:,.2f}".format(grand_total) }}</div>
                            <div class="text-success fs-7">Paid: ₹{{ "{:,.2f}".format(amt_recv) }}</div>
                            {% if balance > 0 %}
                            <div class="text-danger fw-semibold fs-7">Due: ₹{{ "{:,.2f}".format(balance) }}</div>
                            {% elif balance < 0 %}
                            <div class="text-info fw-semibold fs-7">Advance: ₹{{ "{:,.2f}".format(advance_amount) }}</div>
                            {% endif %}
                        </div>
                        <div>
                            {% if r.Payment_Status == "PAID" %}
                                <span class="badge bg-success rounded-pill px-3"><i class="bi bi-circle-fill fs-9 me-1"></i> Paid</span>
                            {% elif r.Payment_Status == "PARTIAL" %}
                                <span class="badge bg-warning text-dark rounded-pill px-3"><i class="bi bi-circle-fill fs-9 me-1"></i> Partial</span>
                            {% elif r.Payment_Status == "ADVANCE" %}
                                <span class="badge bg-info text-dark rounded-pill px-3"><i class="bi bi-circle-fill fs-9 me-1"></i> Advance</span>
                            {% else %}
                                <span class="badge bg-danger rounded-pill px-3"><i class="bi bi-circle-fill fs-9 me-1"></i> Pending</span>
                            {% endif %}
                        </div>
                    </div>

                    <div class="btn-group shadow-sm rounded-pill">
                        {% if r.Payment_Status in ['PAID', 'PARTIAL', 'ADVANCE'] %}
                        <button class="btn btn-sm btn-light border"
                            onclick="togglePaymentStatus('{{ r.Bill }}', '{{ r.Payment_Status }}', '{{ grand_total }}', '{{ amt_recv }}')" title="Mark Pending">
                            <i class="bi bi-arrow-counterclockwise text-secondary"></i>
                        </button>
                        {% else %}
                        <button class="btn btn-sm btn-light border"
                            onclick="togglePaymentStatus('{{ r.Bill }}', 'PENDING', '{{ grand_total }}', '0')" title="Mark Paid">
                            <i class="bi bi-check2 text-success"></i>
                        </button>
                        {% endif %}
                        <button class="btn btn-sm btn-light border text-success" onclick="sendWhatsApp('{{ r.Bill }}')" title="Send via WhatsApp">
                            <i class="bi bi-whatsapp"></i>
                        </button>
                        <button class="btn btn-sm btn-light border" onclick="openGlobalPDFPreview('{{ r.Bill }}')"
                            title="View PDF">
                            <i class="bi bi-eye text-primary"></i> <span class="d-none d-lg-inline ms-1">View</span>
                        </button>
                        <button onclick="openEditBillModal('{{ r.Bill }}')" class="btn btn-sm btn-light border" title="Edit Bill">
                            <i class="bi bi-pencil text-warning"></i> <span class="d-none d-lg-inline ms-1">Edit</span>
                        </button>
                        <button class="btn btn-sm btn-light border" onclick="archiveBill('{{ r.Bill }}')"
                            title="Archive/Delete">
                            <i class="bi bi-archive text-danger"></i>
                        </button>
                    </div>
                </div>
            </div>

            {% endfor %}

            {% if current_year != '' %}
        </div> <!-- End Accordion Body -->
    </div> <!-- End Collapse -->
</div> <!-- End Accordion Item -->
{% else %}
<div class="text-center py-5 text-muted">
    <i class="bi bi-inbox fs-1 d-block mb-3 opacity-50"></i>
    <h5>No Receipts Found</h5>
    <p class="fs-7">Receipts you generate will appear here.</p>
    <a href="{{ APP_BASE(request) }}/billing" class="btn btn-primary rounded-pill mt-2">Generate Receipt</a>
</div>
{% endif %}
</div>

{% endblock %}

{% block scripts %}
<style>
    .transition-hover {
        transition: background-color 0.2s ease;
    }

    .transition-hover:hover {
        background-color: var(--bs-secondary-bg);
    }
</style>
<script src="{{ STATIC_URL(request, '/js/search.js') }}"></script>
<script>
    document.addEventListener("DOMContentLoaded", function () {
        calculateYearStats();
        initializeSharedSearch('globalSearch', '.year-group', '.receipt-row');
        
        // Auto-fill and trigger search if coming from the Top Nav search bar
        const urlParams = new URLSearchParams(window.location.search);
        const q = urlParams.get('q');
        if (q) {
            const searchInput = document.getElementById('globalSearch');
            if (searchInput) {
                searchInput.value = q;
                searchInput.dispatchEvent(new Event('keyup'));
            }
        }
    });

    function calculateYearStats() {
        const yearGroups = document.querySelectorAll('.year-group');
        yearGroups.forEach(group => {
            const rows = group.querySelectorAll('.receipt-row');
            let totalRev = 0;
            let count = rows.length;

            rows.forEach(row => {
                totalRev += parseFloat(row.getAttribute('data-total') || 0);
            });

            const countEl = group.querySelector('.year-bills-count');
            const revEl = group.querySelector('.year-revenue');
            if (countEl) countEl.innerText = count;
            if (revEl) revEl.innerText = totalRev.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        });
    }



    function archiveBill(billNo) {
        confirmAction(
            "Archive Receipt?",
            `Receipt #${billNo} will be moved to Archived Receipts.`,
            "Archive",
            "#dc3545"
        ).then(async (result) => {
            if (result.isConfirmed) {
                try {
                    const res = await fetch(`api/bill/${billNo}/archive`, { method: "POST" });
                    if (res.ok) {
                        showSuccess("Archived!", "The receipt has been archived.").then(async () => {
                            await updateUI(); // Smooth refresh
                        });
                    } else {
                        showError("Failed", "Could not archive the receipt.");
                    }
                } catch (e) {
                    showError("Network Error", "An error occurred.");
                }
            }
        });
    }
</script>
{% endblock %}
```

```html
// File: templates\index.html
{% extends "base.html" %}

{% block content %}
<div class="row text-center mb-5">
    <div class="col-12">
        <h2 class="display-5">Dashboard</h2>
        <p class="text-muted">Welcome to the Rent Receipt Generator</p>
    </div>
</div>

<div class="row mb-4">
    <div class="col-md-4 mb-3">
        <div class="card text-bg-light h-100 text-center">
            <div class="card-body">
                <h5 class="card-title">Next Bill Number</h5>
                <h2 class="display-4 text-primary">{{ next_bill_number }}</h2>
            </div>
        </div>
    </div>
    <div class="col-md-4 mb-3">
        <div class="card text-bg-light h-100 text-center">
            <div class="card-body">
                <h5 class="card-title">Last Meter Reading</h5>
                <h2 class="display-4 text-primary">{{ last_meter_reading }}</h2>
            </div>
        </div>
    </div>
    <div class="col-md-4 mb-3">
        <div class="card text-bg-light h-100 text-center">
            <div class="card-body">
                <h5 class="card-title">Total Tenants</h5>
                <h2 class="display-4 text-primary">{{ total_tenants }}</h2>
            </div>
        </div>
    </div>
</div>

<div class="row text-center">
    <div class="col-md-4 mb-3">
        <a href="{{ APP_BASE(request) }}/billing" class="btn btn-primary btn-lg w-100">New Bill</a>
    </div>
    <div class="col-md-4 mb-3">
        <a href="{{ APP_BASE(request) }}/history" class="btn btn-secondary btn-lg w-100">History</a>
    </div>
    <div class="col-md-4 mb-3">
        <a href="{{ APP_BASE(request) }}/settings" class="btn btn-outline-secondary btn-lg w-100">Settings</a>
    </div>
</div>
{% endblock %}
```

```html
// File: templates\settings.html
{% extends "base.html" %}

{% block title %}Settings | Rent Receipt System{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pb-3 mb-4 border-bottom">
    <h1 class="h2 mb-0 fw-bold">Settings</h1>
</div>

<div class="row">
    <!-- Left Navigation Tabs -->
    <div class="col-md-3 mb-4">
        <div class="card shadow-sm border-0">
            <div class="card-body p-2">
                <div class="nav flex-column nav-pills" id="settingsTabs" role="tablist" aria-orientation="vertical">
                    <button class="nav-link text-start active fw-semibold py-3 px-4 mb-1" id="billing-tab" data-bs-toggle="pill" data-bs-target="#billing" type="button" role="tab">
                        <i class="bi bi-receipt-cutoff me-3"></i>Billing Defaults
                    </button>
                    <button class="nav-link text-start fw-semibold py-3 px-4 mb-1" id="landlord-tab" data-bs-toggle="pill" data-bs-target="#landlord" type="button" role="tab">
                        <i class="bi bi-person-badge me-3"></i>Landlord Info
                    </button>
                    <button class="nav-link text-start fw-semibold py-3 px-4 mb-1" id="appearance-tab" data-bs-toggle="pill" data-bs-target="#appearance" type="button" role="tab">
                        <i class="bi bi-palette me-3"></i>Appearance
                    </button>
                    <button class="nav-link text-start fw-semibold py-3 px-4" id="backup-tab" data-bs-toggle="pill" data-bs-target="#backup" type="button" role="tab">
                        <i class="bi bi-cloud-download me-3"></i>Backup & Data
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Right Content Area -->
    <div class="col-md-9">
        <div class="card shadow-sm border-0 h-100">
            <div class="card-body p-4 p-md-5">
                <form id="settingsForm">
                    <div class="tab-content" id="settingsTabContent">
                        
                        <!-- Billing Settings -->
                        <div class="tab-pane fade show active" id="billing" role="tabpanel" aria-labelledby="billing-tab">
                            <h4 class="fw-bold mb-4 border-bottom pb-2">Application Billing Defaults</h4>
                            <p class="text-muted mb-4">These values will be automatically assigned to <strong>newly created tenants</strong>. Existing tenants will not be affected.</p>
                            
                            <div class="row g-3">
                                <div class="col-sm-6">
                                    <div class="form-floating mb-3">
                                        <input type="number" class="form-control" id="b_rent" value="{{ billing_config.rent }}" required>
                                        <label for="b_rent">Default Rent (₹)</label>
                                    </div>
                                </div>
                                <div class="col-sm-6">
                                    <div class="form-floating mb-3">
                                        <input type="number" class="form-control" id="b_water" value="{{ billing_config.water }}" required>
                                        <label for="b_water">Default Water (₹)</label>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row g-3">
                                <div class="col-sm-6">
                                    <div class="form-floating mb-3">
                                        <input type="number" class="form-control" id="b_elec_rate" step="0.1" value="{{ billing_config.electricity_rate }}" required>
                                        <label for="b_elec_rate">Electricity Rate (₹/unit)</label>
                                    </div>
                                </div>
                                <div class="col-sm-6">
                                    <div class="form-floating mb-3">
                                        <input type="number" class="form-control" id="b_prev_meter" step="0.1" value="{{ billing_config.previous_meter_reading }}" required>
                                        <label for="b_prev_meter">Default Meter Reading</label>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="form-floating mb-3">
                                <input type="number" class="form-control" id="b_add_person" value="{{ billing_config.additional_person_charge }}">
                                <label for="b_add_person">Additional Person Charge (₹)</label>
                            </div>
                        </div>

                        <!-- Landlord Settings -->
                        <div class="tab-pane fade" id="landlord" role="tabpanel" aria-labelledby="landlord-tab">
                            <h4 class="fw-bold mb-4 border-bottom pb-2">Landlord Information</h4>
                            <p class="text-muted mb-4">This information will be printed on the generated PDF receipts.</p>
                            
                            <div class="form-floating mb-3">
                                <input type="text" class="form-control" id="l_name" value="{{ landlord_config.name }}" required>
                                <label for="l_name">Landlord Name</label>
                            </div>
                            
                            <div class="row g-3">
                                <div class="col-sm-6">
                                    <div class="form-floating mb-3">
                                        <input type="tel" class="form-control" id="l_phone" value="{{ landlord_config.phone }}">
                                        <label for="l_phone">Phone Number</label>
                                    </div>
                                </div>
                                <div class="col-sm-6">
                                    <div class="form-floating mb-3">
                                        <input type="email" class="form-control" id="l_email" value="{{ landlord_config.email }}">
                                        <label for="l_email">Email Address</label>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="form-floating mb-3">
                                <textarea class="form-control" id="l_address" style="height: 100px" required>{{ landlord_config.address }}</textarea>
                                <label for="l_address">Property Address</label>
                            </div>
                            
                            <div class="row g-3">
                                <div class="col-sm-6">
                                    <div class="form-floating mb-3">
                                        <input type="text" class="form-control" id="l_pan" value="{{ landlord_config.pan }}">
                                        <label for="l_pan">PAN Number</label>
                                    </div>
                                </div>
                                <div class="col-sm-6">
                                    <div class="form-floating mb-3">
                                        <input type="text" class="form-control" id="l_sign" value="{{ landlord_config.signature_text }}">
                                        <label for="l_sign">Signature Text</label>
                                    </div>
                                </div>
                            </div>

                            <h5 class="fw-bold mb-3 mt-4 border-bottom pb-2">Bank Details <span class="badge bg-secondary ms-2 fw-normal fs-8">Optional</span></h5>
                            <p class="text-muted mb-4 fs-7">If provided, payment instructions will be added to your receipts.</p>
                            
                            <div class="row g-3">
                                <div class="col-sm-6">
                                    <div class="form-floating mb-3">
                                        <input type="text" class="form-control" id="l_bank_acc_name" value="{{ landlord_config.bank_account_name }}">
                                        <label for="l_bank_acc_name">Account Holder Name</label>
                                    </div>
                                </div>
                                <div class="col-sm-6">
                                    <div class="form-floating mb-3">
                                        <input type="text" class="form-control" id="l_bank_acc_no" value="{{ landlord_config.bank_account_number }}">
                                        <label for="l_bank_acc_no">Account Number</label>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row g-3">
                                <div class="col-sm-5">
                                    <div class="form-floating mb-3">
                                        <input type="text" class="form-control" id="l_bank_name" value="{{ landlord_config.bank_name }}">
                                        <label for="l_bank_name">Bank Name</label>
                                    </div>
                                </div>
                                <div class="col-sm-4">
                                    <div class="form-floating mb-3">
                                        <input type="text" class="form-control" id="l_bank_branch" value="{{ landlord_config.bank_branch }}">
                                        <label for="l_bank_branch">Branch</label>
                                    </div>
                                </div>
                                <div class="col-sm-3">
                                    <div class="form-floating mb-3">
                                        <input type="text" class="form-control" id="l_bank_ifsc" value="{{ landlord_config.bank_ifsc }}" style="text-transform: uppercase;">
                                        <label for="l_bank_ifsc">IFSC Code</label>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="form-check form-switch mb-4">
                                <input class="form-check-input" type="checkbox" role="switch" id="l_mask_bank" {% if landlord_config.mask_bank_account %}checked{% endif %}>
                                <label class="form-check-label" for="l_mask_bank">Mask account number on printed receipts</label>
                            </div>

                            <h5 class="fw-bold mb-3 mt-4 border-bottom pb-2">Digital Signature</h5>
                            <div class="row g-3 mb-4">
                                <div class="col-12">
                                    <div class="card bg-body-tertiary border-0">
                                        <div class="card-body p-4 text-center">
                                            <div id="signaturePreviewContainer" class="mb-3 {% if landlord_config.signature_image %}d-block{% else %}d-none{% endif %}">
                                                <img id="signaturePreview" src="{% if landlord_config.signature_image %}{{ APP_BASE(request) }}/static/uploads/{{ landlord_config.signature_image }}{% endif %}" alt="Landlord Signature" class="img-fluid border rounded bg-white p-2" style="max-height: 100px;">
                                                <div class="mt-2">
                                                    <button type="button" class="btn btn-sm btn-outline-danger rounded-pill px-3" onclick="removeSignature()">
                                                        <i class="bi bi-trash me-1"></i>Remove Signature
                                                    </button>
                                                </div>
                                            </div>
                                            
                                            <div id="signatureUploadContainer" class="p-4 rounded-3 bg-body {% if landlord_config.signature_image %}d-none{% else %}d-block{% endif %}" onclick="document.getElementById('signatureFile').click()">
                                                <i class="bi bi-cloud-arrow-up text-primary mb-2 d-block" style="font-size: 2.5rem;"></i>
                                                <h6 class="fw-bold">Drag & Drop Signature</h6>
                                                <p class="text-muted fs-7 mb-3">Or click to browse. Accepted: PNG, JPG, WEBP. Max size: 2MB.<br>The background will be automatically removed.</p>
                                                <input type="file" class="form-control d-none" id="signatureFile" accept="image/png, image/jpeg, image/webp" onchange="uploadSignature()">
                                                <button type="button" class="btn btn-outline-primary rounded-pill px-4" onclick="event.stopPropagation(); document.getElementById('signatureFile').click()">
                                                    <i class="bi bi-upload me-2"></i>Select Image
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <h5 class="fw-bold mb-3 mt-4 border-bottom pb-2">WhatsApp Templates</h5>
                            <p class="text-muted fs-7 mb-3">Customize the messages sent to tenants. You can use the following variables:<br>
                            <code>{tenant_name}</code>, <code>{month}</code>, <code>{bill_no}</code>, <code>{total}</code>, <code>{currency}</code>, <code>{link}</code></p>
                            
                            <div class="form-floating mb-3">
                                <textarea class="form-control" id="l_wa_template" style="height: 150px" required>{{ landlord_config.whatsapp_template }}</textarea>
                                <label for="l_wa_template">Single Receipt Message Template</label>
                            </div>
                            
                            <div class="form-floating mb-4">
                                <textarea class="form-control" id="l_wa_bulk_template" style="height: 150px" required>{{ landlord_config.whatsapp_bulk_template }}</textarea>
                                <label for="l_wa_bulk_template">Bulk Receipts Message Template</label>
                                <div class="form-text fs-8">Use <code>{bill_list}</code> and <code>{total_amount}</code> instead of single bill variables here.</div>
                            </div>

                        </div>

                        <!-- Appearance Settings -->
                        <div class="tab-pane fade" id="appearance" role="tabpanel" aria-labelledby="appearance-tab">
                            <h4 class="fw-bold mb-4 border-bottom pb-2">Appearance</h4>
                            
                            <h6 class="fw-semibold mb-3">Base Theme</h6>
                            <div class="d-flex gap-3 mb-5">
                                <button type="button" class="btn btn-outline-secondary px-4 py-3 rounded-3 {% if theme == 'light' %}active border-primary{% endif %}" onclick="setTheme('light')">
                                    <i class="bi bi-sun-fill fs-4 d-block mb-2 text-warning"></i> Light
                                </button>
                                <button type="button" class="btn btn-outline-secondary px-4 py-3 rounded-3 {% if theme == 'dark' %}active border-primary{% endif %}" onclick="setTheme('dark')">
                                    <i class="bi bi-moon-stars-fill fs-4 d-block mb-2 text-primary"></i> Dark
                                </button>
                                <button type="button" class="btn btn-outline-secondary px-4 py-3 rounded-3 {% if theme == 'system' %}active border-primary{% endif %}" onclick="setTheme('system')">
                                    <i class="bi bi-laptop fs-4 d-block mb-2 text-secondary"></i> System
                                </button>
                            </div>
                            
                            <h6 class="fw-semibold mb-3">Accent Color <span class="badge bg-secondary-subtle text-secondary ms-2 fw-normal fs-8">Coming Soon</span></h6>
                            <div class="d-flex gap-2 mb-3">
                                <div class="rounded-circle bg-primary" style="width: 32px; height: 32px; cursor: pointer; border: 2px solid white; outline: 2px solid var(--bs-primary);"></div>
                                <div class="rounded-circle bg-success" style="width: 32px; height: 32px; cursor: not-allowed; opacity: 0.5;"></div>
                                <div class="rounded-circle" style="background-color: #6f42c1; width: 32px; height: 32px; cursor: not-allowed; opacity: 0.5;"></div>
                                <div class="rounded-circle bg-danger" style="width: 32px; height: 32px; cursor: not-allowed; opacity: 0.5;"></div>
                            </div>
                            <p class="text-muted fs-7">Custom accent colors are currently in development.</p>
                        </div>
                        
                        <!-- Backup Settings -->
                        <div class="tab-pane fade" id="backup" role="tabpanel" aria-labelledby="backup-tab">
                            <div class="card shadow-sm border-0 mb-4 rounded-4">
                                <div class="card-header bg-success bg-gradient text-white py-3 px-4 d-flex align-items-center rounded-top-4">
                                    <i class="bi bi-file-earmark-spreadsheet fs-5 me-3"></i>
                                    <h5 class="mb-0 fw-bold">Excel Import & Export (Relational)</h5>
                                </div>
                                <div class="card-body p-4">
                                    <p class="text-muted mb-4 fs-7">
                                        Manage your tenants and receipts using a highly organized Excel format (.xlsx). The workbook separates Tenant Profiles and Receipts into distinct sheets to prevent duplication and make editing easier.
                                    </p>
                            
                                    <div class="row g-3">
                                        <div class="col-md-4">
                                            <button onclick="executeExport('template')" type="button" class="btn btn-outline-success w-100 py-2 fw-bold text-start rounded-3 shadow-sm d-flex align-items-center justify-content-between">
                                                <span><i class="bi bi-grid-3x3 me-2 text-success"></i> Blank Excel Template</span>
                                                <i class="bi bi-download"></i>
                                            </button>
                                        </div>
                                        <div class="col-md-4">
                                            <button onclick="executeExport('xlsx')" type="button" class="btn btn-outline-primary w-100 py-2 fw-bold text-start rounded-3 shadow-sm d-flex align-items-center justify-content-between">
                                                <span><i class="bi bi-file-excel-fill me-2 text-primary"></i> Export to Excel (.xlsx)</span>
                                                <i class="bi bi-box-arrow-up-right"></i>
                                            </button>
                                        </div>
                                        <div class="col-md-4">
                                            <button onclick="executeExport('zip')" type="button" class="btn btn-outline-primary w-100 py-2 fw-bold text-start rounded-3 shadow-sm d-flex align-items-center justify-content-between">
                                                <span><i class="bi bi-file-zip-fill me-2 text-primary"></i> Export as ZIP Archive</span>
                                                <i class="bi bi-box-arrow-up-right"></i>
                                            </button>
                                        </div>
                                    </div>
                                    
                                    <hr class="my-4 text-muted">
                                    
                                    <div class="d-flex align-items-center justify-content-between bg-primary-subtle p-3 rounded-3 border border-primary">
                                        <div>
                                            <h6 class="fw-bold text-primary mb-1">Import Excel Data</h6>
                                            <div class="fs-8 text-muted">Select an .xlsx file or a .zip containing multiple .xlsx files.</div>
                                        </div>
                                        <div>
                                            <input type="file" id="importExcelFile" accept=".xlsx, .zip" class="d-none" onchange="handleExcelImport(this)">
                                            <button type="button" onclick="document.getElementById('importExcelFile').click()" class="btn btn-primary fw-bold shadow-sm rounded-pill px-4">
                                                <i class="bi bi-cloud-arrow-up-fill me-2"></i> Select File to Import
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>
                    
                    <!-- Save Button Area -->
                    <div class="mt-4 pt-4 border-top">
                        <button type="submit" class="btn btn-primary btn-lg rounded-pill px-5 shadow-sm fw-bold" id="saveBtn">
                            <i class="bi bi-save me-2"></i>Save All Settings
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
<div class="modal fade" id="importPreviewModal" tabindex="-1" data-bs-backdrop="static">
    <div class="modal-dialog modal-dialog-centered" style="max-width: 95vw; width: 95vw;">
        <div class="modal-content border-0 shadow-lg rounded-4 overflow-hidden" style="height: 85vh;">
            <div class="modal-header bg-dark text-white border-bottom-0 py-2">
                <h5 class="modal-title fw-bold fs-6">
                    <i class="bi bi-file-excel me-2 text-success"></i> Data Import Preview
                </h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            
            <div class="modal-body p-0 d-flex flex-row h-100" style="overflow: hidden;">
                
                <div class="border-end bg-body-tertiary d-flex flex-column h-100" style="width: 20%; min-width: 250px;">
                    <div class="p-2 border-bottom bg-light d-flex justify-content-between align-items-center shadow-sm z-1">
                        <h6 class="fw-bold mb-0 text-secondary fs-7 px-2">Select Tenants</h6>
                    </div>
                    
                    <div class="overflow-auto flex-grow-1 p-2" id="importTreeList">
                        </div>
                </div>

                <div class="bg-body d-flex flex-column h-100" style="width: 80%;">
                    
                    <div class="p-3 border-bottom bg-primary-subtle shadow-sm z-1 d-none" id="previewProfileCard">
                        <div class="row align-items-center">
                            <div class="col-md-4">
                                <h5 class="fw-bold text-primary mb-0" id="prev_t_name">Tenant Name</h5>
                                <div class="fs-7 text-muted" id="prev_t_id">T001</div>
                            </div>
                            <div class="col-md-8">
                                <div class="row fs-7 text-dark fw-semibold">
                                    <div class="col-4"><i class="bi bi-telephone me-1"></i> <span id="prev_t_phone"></span></div>
                                    <div class="col-4"><i class="bi bi-building me-1"></i> <span id="prev_t_company"></span></div>
                                    <div class="col-4">Rent: ₹<span id="prev_t_rent"></span></div>
                                    <div class="col-4"><i class="bi bi-lightning-charge me-1"></i> ₹<span id="prev_t_rate"></span>/unit</div>
                                    <div class="col-4">Water: ₹<span id="prev_t_water"></span></div>
                                    <div class="col-4"><span class="badge bg-success" id="prev_t_status"></span></div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="px-3 py-2 border-bottom bg-light d-flex justify-content-between align-items-center" id="previewHeaderBar">
                        <h6 class="fw-bold mb-0 text-secondary" id="previewTableName">Select a tenant on the left to preview receipts</h6>
                        <span class="badge bg-secondary" id="previewTableRowsCount">0 Receipts</span>
                    </div>
                    
                    <div class="table-responsive flex-grow-1 p-0 m-0 bg-white" style="overflow-y: auto;">
                        <table class="table table-hover table-sm fs-8 m-0 border-top-0" id="previewTable">
                            <thead class="table-dark sticky-top" id="previewTableHead"></thead>
                            <tbody id="previewTableBody">
                                <tr><td colspan="100%" class="text-center text-muted py-5 mt-5"><i class="bi bi-inboxes d-block fs-1 mb-3 opacity-50"></i>No preview available</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

            </div>
            
            <div class="modal-footer bg-light border-top-0 py-2">
                <button type="button" class="btn btn-outline-secondary fw-bold rounded-pill px-4" data-bs-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-success fw-bold rounded-pill px-5 shadow-sm" id="btnExecuteImport" onclick="executeExcelImport()">
                    <i class="bi bi-cloud-check-fill me-2"></i> Import Selected Tenants
                </button>
            </div>
        </div>
    </div>
</div>

{% endblock %}

{% block scripts %}
<style>
    #signatureUploadContainer {
        border: 2px dashed #dee2e6;
        transition: all 0.2s ease-in-out;
        cursor: pointer;
    }
    #signatureUploadContainer.drag-over {
        border-color: var(--bs-primary);
        background-color: var(--bs-primary-bg-subtle) !important;
    }
</style>
<script>
    document.getElementById("settingsForm").addEventListener("submit", async function(e) {
        e.preventDefault();
        
        // Because "Appearance" and "Backup" don't have form fields to save,
        // we only gather Landlord and Billing fields.
        const landlordData = {
            name: document.getElementById("l_name").value,
            phone: document.getElementById("l_phone").value,
            email: document.getElementById("l_email").value,
            address: document.getElementById("l_address").value,
            pan: document.getElementById("l_pan").value,
            bank_account_name: document.getElementById("l_bank_acc_name").value,
            bank_account_number: document.getElementById("l_bank_acc_no").value,
            bank_name: document.getElementById("l_bank_name").value.trim(),
            bank_branch: document.getElementById("l_bank_branch").value.trim(),
            bank_ifsc: document.getElementById("l_bank_ifsc").value.toUpperCase(),
            mask_bank_account: document.getElementById("l_mask_bank").checked,
            signature_text: document.getElementById("l_sign").value,
            whatsapp_template: document.getElementById("l_wa_template").value,
            whatsapp_bulk_template: document.getElementById("l_wa_bulk_template").value
        };
        
        // Bank Validation
        if (landlordData.bank_account_name || landlordData.bank_account_number || landlordData.bank_name || landlordData.bank_branch || landlordData.bank_ifsc) {
            if (!landlordData.bank_account_number) {
                showError("Validation Error", "Account Number is required if bank details are provided.");
                return;
            }
            if (landlordData.bank_ifsc && !/^[A-Z]{4}0[A-Z0-9]{6}$/.test(landlordData.bank_ifsc)) {
                showError("Validation Error", "Invalid IFSC Code format. Example: SBIN0001234");
                return;
            }
        }
        
        const billingData = {
            rent: parseFloat(document.getElementById("b_rent").value),
            water: parseFloat(document.getElementById("b_water").value),
            electricity_rate: parseFloat(document.getElementById("b_elec_rate").value),
            previous_meter_reading: parseFloat(document.getElementById("b_prev_meter").value),
            additional_person_charge: parseFloat(document.getElementById("b_add_person").value) || 0
        };
        
        const saveBtn = document.getElementById("saveBtn");
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Saving...';
        
        try {
            const res = await fetch("api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    landlord: landlordData,
                    billing: billingData
                })
            });
            if (res.ok) {
                showToast('success', 'Settings Saved Successfully');
                setTimeout(() => window.location.reload(), 1500);
            } else {
                showError('Error', 'Failed to save settings.');
                resetSaveBtn(saveBtn);
            }
        } catch (e) {
            showError('Network Error', 'A connection error occurred.');
            resetSaveBtn(saveBtn);
        }
    });

    function resetSaveBtn(btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-save me-2"></i>Save All Settings';
    }

    let importExcelCache = {};
    let currentExcelFileObj = null;

    async function handleExcelImport(inputEl) {
        if (!inputEl.files || inputEl.files.length === 0) return;
        
        currentExcelFileObj = inputEl.files[0];
        const formData = new FormData();
        formData.append("file", currentExcelFileObj);
        
        showSyncOverlay("Parsing Excel structure...");
        
        try {
            const res = await fetch("api/sync/import/preview", { method: "POST", body: formData });
            hideSyncOverlay();
            
            if (!res.ok) {
                const data = await res.json();
                showError("Parse Error", data.detail || "Unable to read file contents.");
                inputEl.value = '';
                return;
            }
            
            const data = await res.json();
            importExcelCache = data.files; // Format: { "Rent_Data.xlsx": { "T001": { profile: {}, receipts: [] } } }
            
            renderImportTreeList();
            
            // Hide right side preview initially
            document.getElementById('previewProfileCard').classList.add('d-none');
            document.getElementById('previewTableBody').innerHTML = '<tr><td colspan="100%" class="text-center text-muted py-5 mt-5"><i class="bi bi-inboxes d-block fs-1 mb-3 opacity-50"></i>Select a tenant on the left to preview data.</td></tr>';
            document.getElementById('previewTableHead').innerHTML = '';
            
            const modal = new bootstrap.Modal(document.getElementById('importPreviewModal'));
            modal.show();
            
        } catch(e) {
            hideSyncOverlay();
            showError("Network Error", "Could not reach the server.");
        }
        inputEl.value = ''; // reset input
    }

    function renderImportTreeList() {
        const listContainer = document.getElementById('importTreeList');
        listContainer.innerHTML = '';
        
        let isFirst = true;

        // Loop over files (Will be 1 if just .xlsx, multiple if .zip)
        for (const [filename, tenantsObj] of Object.entries(importExcelCache)) {
            
            // File Header
            const fileGroup = document.createElement('div');
            fileGroup.className = "mb-3 border rounded-3 bg-white overflow-hidden shadow-sm";
            
            const fileHeader = document.createElement('div');
            fileHeader.className = "bg-body-tertiary p-2 border-bottom d-flex align-items-center justify-content-between";
            fileHeader.innerHTML = `
                <div class="fw-bold fs-7 text-dark text-truncate" title="${filename}">
                    <i class="bi bi-file-earmark-excel-fill text-success me-1"></i> ${filename}
                </div>
                <input type="checkbox" class="form-check-input file-group-checkbox" checked onchange="toggleFileGroup(this, '${filename.replace(/[^a-zA-Z0-9]/g, '_')}')" title="Select All in File">
            `;
            fileGroup.appendChild(fileHeader);
            
            const tenantList = document.createElement('div');
            tenantList.className = "list-group list-group-flush";
            tenantList.id = `group_${filename.replace(/[^a-zA-Z0-9]/g, '_')}`;
            
            // Loop over Tenants inside this file
            for (const [tenantId, data] of Object.entries(tenantsObj)) {
                const tName = data.profile.Tenant_Name || "Unknown Tenant";
                const receiptCount = data.receipts.length;
                
                const tItem = document.createElement('div');
                tItem.className = `list-group-item list-group-item-action d-flex align-items-center gap-2 py-2 px-3 border-bottom-0 tenant-select-item ${isFirst ? 'bg-primary-subtle' : ''}`;
                tItem.style.cursor = "pointer";
                
                // Handle clicking the row to preview
                tItem.onclick = (e) => {
                    if(e.target.type === 'checkbox') return;
                    
                    document.querySelectorAll('.tenant-select-item').forEach(el => el.classList.remove('bg-primary-subtle'));
                    tItem.classList.add('bg-primary-subtle');
                    
                    renderRightSidePreview(filename, tenantId);
                };
                
                tItem.innerHTML = `
                    <input class="form-check-input import-tenant-checkbox" type="checkbox" value="${filename}::${tenantId}" checked>
                    <div class="d-flex flex-column w-100" style="overflow: hidden;">
                        <div class="fw-bold fs-7 text-truncate" title="${tName}">${tName}</div>
                        <div class="d-flex justify-content-between">
                            <span class="fs-8 text-muted">${tenantId}</span>
                            <span class="fs-8 badge bg-secondary rounded-pill">${receiptCount} Bills</span>
                        </div>
                    </div>
                `;
                
                tenantList.appendChild(tItem);
                
                if (isFirst) {
                    renderRightSidePreview(filename, tenantId);
                    isFirst = false;
                }
            }
            
            fileGroup.appendChild(tenantList);
            listContainer.appendChild(fileGroup);
        }
    }

    // Must attach toggleFileGroup to window to work with inline onchange
    window.toggleFileGroup = function(checkbox, groupId) {
        const group = document.getElementById(`group_${groupId}`);
        if (group) {
            group.querySelectorAll('.import-tenant-checkbox').forEach(cb => cb.checked = checkbox.checked);
        }
    };

    function renderRightSidePreview(filename, tenantId) {
        const data = importExcelCache[filename][tenantId];
        
        // 1. Render Profile Summary Card
        document.getElementById('previewProfileCard').classList.remove('d-none');
        
        const p = data.profile;
        document.getElementById('prev_t_name').innerText = p.Tenant_Name || "-";
        document.getElementById('prev_t_id').innerText = tenantId;
        document.getElementById('prev_t_phone').innerText = p.Phone || "-";
        document.getElementById('prev_t_company').innerText = p.Company || "-";
        document.getElementById('prev_t_rent').innerText = p.Rent || "0";
        document.getElementById('prev_t_rate').innerText = p.Electricity_Rate || "0";
        document.getElementById('prev_t_water').innerText = p.Water || "0";
        document.getElementById('prev_t_status').innerText = p.Status || "Active";
        
        // 2. Render Receipts Table
        document.getElementById('previewTableName').innerText = `Receipt History`;
        document.getElementById('previewTableRowsCount').innerText = `${data.receipts.length} Receipts`;
        
        const thead = document.getElementById('previewTableHead');
        const tbody = document.getElementById('previewTableBody');
        
        if (data.receipts.length === 0) {
            thead.innerHTML = "";
            tbody.innerHTML = `<tr><td colspan="100%" class="text-center text-muted py-5"><i class="bi bi-inbox d-block fs-1 mb-2 opacity-50"></i>No receipts found for this tenant.</td></tr>`;
            return;
        }
        
        // Extract headers from first receipt object keys dynamically
        const headers = Object.keys(data.receipts[0]);
        
        let trHead = '<tr>';
        headers.forEach(h => { trHead += `<th class="text-nowrap">${h}</th>`; });
        trHead += '</tr>';
        thead.innerHTML = trHead;
        
        let trBody = '';
        data.receipts.forEach(row => {
            trBody += '<tr>';
            headers.forEach(h => {
                const val = row[h] || '-';
                
                // Color code statuses visually for preview
                let styledVal = val;
                if (h === 'Payment_Status') {
                    styledVal = val === 'PAID' ? `<span class="text-success fw-bold">${val}</span>` : `<span class="text-danger fw-bold">${val}</span>`;
                }
                
                trBody += `<td class="text-nowrap">${styledVal}</td>`;
            });
            trBody += '</tr>';
        });
        tbody.innerHTML = trBody;
    }

    async function executeExcelImport() {
        const checkboxes = document.querySelectorAll('.import-tenant-checkbox:checked');
        const selectedTargets = Array.from(checkboxes).map(cb => cb.value); // ["RentData.xlsx::T001", ...]
        
        if (selectedTargets.length === 0) {
            showError("Selection Required", "Please check at least one tenant from the list on the left to import.");
            return;
        }
        
        const btn = document.getElementById('btnExecuteImport');
        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Importing...';
        
        document.activeElement.blur(); // Remove focus to prevent ARIA hidden warnings
        bootstrap.Modal.getInstance(document.getElementById('importPreviewModal')).hide(); // Hide the modal first
        showSyncOverlay("Importing & Syncing Data...");
        
        const formData = new FormData();
        formData.append("file", currentExcelFileObj);
        formData.append("selected_targets", JSON.stringify(selectedTargets));
        
        try {
            const res = await fetch("api/sync/import/execute", { method: "POST", body: formData });
            hideSyncOverlay();
            
            btn.disabled = false;
            btn.innerHTML = originalHtml;
            
            if (res.ok) {
                Swal.fire({
                    icon: 'success',
                    title: 'Excel Data Synced',
                    text: 'Your relational tenant profiles and receipts have been successfully merged into the system.',
                    confirmButtonColor: '#198754'
                }).then(() => {
                    window.location.reload();
                });
            } else {
                const errData = await res.json();
                showError("Import Failed", errData.detail || "An error occurred while merging Excel data.");
            }
            
        } catch(e) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
            hideSyncOverlay();
            showError("Network Error", "Could not reach the server.");
        }
    }

    async function uploadSignature() {
        const fileInput = document.getElementById('signatureFile');
        const file = fileInput.files[0];
        if (!file) return;
        
        if (file.size > 2 * 1024 * 1024) {
            showError('Error', 'File is too large. Max 2MB allowed.');
            fileInput.value = '';
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        showLoadingOverlay('Uploading and processing signature...');
        try {
            const res = await fetch('api/settings/signature', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            hideLoadingOverlay();
            
            if (res.ok) {
                showToast('success', 'Signature uploaded and processed successfully.');
                document.getElementById('signaturePreview').src = "static/uploads/" + data.path + "?t=" + new Date().getTime();
                document.getElementById('signaturePreviewContainer').style.display = 'block';
                document.getElementById('signatureUploadContainer').style.display = 'none';
            } else {
                showError('Upload Failed', data.detail || 'An error occurred');
            }
        } catch (e) {
            hideLoadingOverlay();
            showError('Network Error', 'Failed to upload signature.');
        }
        fileInput.value = '';
    }

    async function removeSignature() {
        confirmAction("Remove Signature?", "This will delete the uploaded signature.", "Remove", "#dc3545").then(async (result) => {
            if (result.isConfirmed) {
                try {
                    const res = await fetch('api/settings/signature', { method: 'DELETE' });
                    if (res.ok) {
                        showToast('success', 'Signature removed.');
                        document.getElementById('signaturePreviewContainer').style.display = 'none';
                        document.getElementById('signatureUploadContainer').style.display = 'block';
                        document.getElementById('signaturePreview').src = "";
                    } else {
                        showError('Error', 'Failed to remove signature.');
                    }
                } catch(e) {
                    showError('Error', 'Network error.');
                }
            }
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        const dropZone = document.getElementById('signatureUploadContainer');
        const fileInput = document.getElementById('signatureFile');

        // Prevent default behaviors for all drag events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        // Add highlight class when dragging over
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.add('drag-over');
            }, false);
        });

        // Remove highlight class when dragging leaves
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove('drag-over');
            }, false);
        });

        // Handle dropped files
        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;

            if (files.length > 0) {
                fileInput.files = files; // Assign the dropped file to the hidden input
                uploadSignature();       // Trigger the existing upload function
            }
        });
    });
</script>

{% endblock %}
```

```html
// File: templates\tenant_profile.html
{% extends "base.html" %}

{% block title %}{{ tenant.name }} | Tenant Profile{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pb-3 mb-4 border-bottom">
    <div class="d-flex align-items-center">
        <a href="{{ APP_BASE(request) }}/tenants" class="btn btn-sm btn-outline-secondary rounded-pill me-3"><i class="bi bi-arrow-left"></i>
            Back</a>
        <h1 class="h2 mb-0 fw-bold">Tenant Profile</h1>
    </div>
    <div class="d-flex align-items-center gap-2">
        {% if tenant.arrears > 0 %}
        <span class="badge bg-danger fs-6 px-3 py-2 rounded-pill shadow-sm me-2">Due: ₹{{ "%.2f"|format(tenant.arrears) }}</span>
        {% endif %}
        <button onclick="openKycModal()" class="btn btn-info text-white rounded-pill shadow-sm">
            <i class="bi bi-person-vcard me-2"></i>Occupants List
        </button>
        
        <button onclick="showQRCode('{{ tenant.view_token }}')" class="btn btn-dark rounded-pill shadow-sm">
            <i class="bi bi-qr-code-scan me-2"></i>Tenant QR
        </button>

        <button
            onclick="window.open(window.APP_BASE + '/t/{{ tenant.view_token }}', '_blank')"
            class="btn btn-primary rounded-pill shadow-sm">
            <i class="bi bi-box-arrow-up-right me-2"></i>Tenant Portal
        </button>

        <span class="badge bg-primary fs-5 px-3 py-2 rounded-pill shadow-sm">ID: T{{ tenant.id }}</span>
    </div>
</div>

<div class="row g-4">
    <div class="col-xl-4 col-lg-5">
        <div class="card shadow-sm border-0 mb-4 rounded-4 position-relative overflow-hidden">
            <div class="bg-primary bg-gradient position-absolute top-0 w-100" style="height: 100px;"></div>
            <div class="card-body px-4 pt-5 text-center mt-3">
                <div class="bg-white text-primary rounded-circle shadow d-flex align-items-center justify-content-center mx-auto mb-3"
                    style="width: 80px; height: 80px; font-size: 2rem; font-weight: bold; border: 4px solid white; position: relative; z-index: 1;">
                    {{ tenant.name[:1]|upper }}
                </div>
                <h4 class="fw-bold mb-1">{{ tenant.name }}</h4>
                <p class="text-muted mb-3">{{ tenant.company or "Individual Tenant" }}</p>

                <div class="d-flex justify-content-center gap-2 mb-4">
                    {% if tenant.status == 'Active' %}
                    <span class="badge bg-success rounded-pill px-3 py-2"><i
                            class="bi bi-check-circle me-1"></i>Active</span>
                    {% else %}
                    <span class="badge bg-danger rounded-pill px-3 py-2"><i
                            class="bi bi-dash-circle me-1"></i>Inactive</span>
                    {% endif %}
                </div>

                <div class="text-start border-top pt-3">
                    <div class="mb-3 d-flex align-items-start">
                        <i class="bi bi-telephone text-primary me-3 mt-1"></i>
                        <div><strong class="d-block text-muted fs-8 text-uppercase">Phone</strong> {{ tenant.phone or
                            "-" }}</div>
                    </div>
                    <div class="mb-3 d-flex align-items-start">
                        <i class="bi bi-envelope text-primary me-3 mt-1"></i>
                        <div><strong class="d-block text-muted fs-8 text-uppercase">Email</strong> {{ tenant.email or
                            "-" }}</div>
                    </div>
                    <div class="mb-3 d-flex align-items-start">
                        <i class="bi bi-geo-alt text-primary me-3 mt-1"></i>
                        <div><strong class="d-block text-muted fs-8 text-uppercase">Address</strong> {{ tenant.address
                            or "-" }}</div>
                    </div>
                    <div class="mb-3 d-flex align-items-start">
                        <i class="bi bi-key text-primary me-3 mt-1"></i>
                        <div><strong class="d-block text-muted fs-8 text-uppercase">Portal PIN</strong> <span
                                class="badge bg-secondary font-monospace">{{ tenant.tenant_pin }}</span></div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card shadow-sm border-0 rounded-4 mb-4">
            <div class="card-body p-4">
                <h6 class="fw-bold text-muted border-bottom pb-2 mb-3"><i class="bi bi-receipt me-2"></i>Billing Profile
                </h6>

                <div
                    class="d-flex justify-content-between align-items-center border-bottom pb-2 mb-2 bg-light rounded p-2">
                    <span class="text-muted"><i class="bi bi-speedometer2 text-warning me-2"></i>Meter ID:</span>
                    <span class="fw-bold text-dark">{{ tenant.meter_id or 'Unassigned' }}</span>
                </div>

                <div class="d-flex justify-content-between mb-2 mt-3">
                    <span class="text-muted">Monthly Rent:</span>
                    <span class="fw-bold">₹{{ "{:,.0f}".format(tenant.rent) }}</span>
                </div>
                <div class="d-flex justify-content-between mb-2">
                    <span class="text-muted">Electricity Rate:</span>
                    <span class="fw-bold">₹{{ tenant.electricity_rate }}/unit</span>
                </div>
                <div class="d-flex justify-content-between mb-2">
                    <span class="text-muted">Last Meter Read:</span>
                    <span class="fw-bold text-warning">{{ tenant.previous_meter }}</span>
                </div>
                <div class="d-flex justify-content-between">
                    <span class="text-muted">Security Deposit:</span>
                    <span class="fw-bold">₹{{ "{:,.0f}".format(tenant.security_deposit) }}</span>
                </div>
            </div>
        </div>
    </div>

    <div class="col-xl-8 col-lg-7">
        <div class="card shadow-sm border-0 rounded-4 h-100">
            <div
                class="card-header bg-transparent border-0 pt-4 pb-3 px-4 d-flex justify-content-between align-items-center">
                <h5 class="fw-bold mb-0"><i class="bi bi-clock-history me-2 text-primary"></i>Receipt History</h5>
                <div class="d-flex gap-2">
                    {% if config.get('system', 'features.whatsapp_sync') %}
                    <button class="btn btn-sm btn-outline-success rounded-pill" onclick="sendBulkWhatsApp()">
                        <i class="bi bi-whatsapp me-1"></i>Bulk Send
                    </button>
                    {% endif %}
                    <a href="{{ APP_BASE(request) }}/billing" class="btn btn-sm btn-primary rounded-pill"><i class="bi bi-plus-lg me-1"></i>New
                        Bill</a>
                </div>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th class="ps-4" style="width: 40px;">
                                    <input class="form-check-input" type="checkbox" id="selectAllBills"
                                        onclick="toggleAllBills(this)">
                                </th>
                                <th>Bill #</th>
                                <th>Month</th>
                                <th>Total</th>
                                <th>Status</th>
                                <th class="text-end pe-4">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for r in receipts %}
                            {% set curr_total = r.Total|default(0,true)|float %}
                            {% set prev_arr = r.Previous_Arrears|default(0,true)|float %}
                            {% set grand_total = curr_total + prev_arr %}
                            {% set amt_recv = r.Amount_Received|default(0, true)|float %}
                            {% set balance = grand_total - amt_recv %}
                            {% set advance_amount = 0 - balance if balance < 0 else 0 %}
                            <tr>
                                <td class="ps-4">
                                    <input class="form-check-input bill-checkbox" type="checkbox" value="{{ r.Bill }}">
                                </td>
                                <td><span class="badge bg-secondary">{{ r.Bill }}</span></td>
                                <td class="fw-semibold">{{ r.Month }}</td>
                                <td>
                                    <div class="fw-bold text-dark">₹{{ "{:,.2f}".format(grand_total) }}</div>
                                    <div class="text-success fs-7">Paid: ₹{{ "{:,.2f}".format(amt_recv) }}</div>
                                    {% if balance > 0 %}
                                    <div class="text-danger fw-semibold fs-7">Due: ₹{{ "{:,.2f}".format(balance) }}
                                    </div>
                                    {% elif balance < 0 %}
                                    <div class="text-info fw-semibold fs-7">Adv: ₹{{ "{:,.2f}".format(advance_amount) }}
                                    </div>
                                    {% endif %}
                                    {% if prev_arr > 0 %}
                                    <div class="text-warning-emphasis fs-8">Arr: ₹{{ "{:,.2f}".format(prev_arr) }}</div>
                                    {% elif prev_arr < 0 %}
                                    <div class="text-info-emphasis fs-8">Adv: ₹{{ "{:,.2f}".format(prev_arr|abs) }}</div>
                                    {% endif %}
                                </td>
                                <td>
                                    {% if r.Payment_Status == "PAID" %}
                                        <span class="badge bg-success rounded-pill px-2"><i class="bi bi-check2"></i> Paid</span>
                                    {% elif r.Payment_Status == "PARTIAL" %}
                                        <span class="badge bg-warning text-dark rounded-pill px-2">Partial</span>
                                    {% elif r.Payment_Status == "ADVANCE" %}
                                        <span class="badge bg-info text-dark rounded-pill px-2">Advance</span>
                                    {% else %}
                                        <span class="badge bg-danger rounded-pill px-2">Pending</span>
                                    {% endif %}

                                    {% if r.Status == 'ARCHIVED' %}
                                    <span class="badge bg-warning text-dark rounded-pill ms-1 px-2"><i
                                            class="bi bi-archive"></i></span>
                                    {% endif %}
                                </td>
                                <td class="text-end pe-4">
                                    <div class="btn-group gap-1 rounded-pill shadow-sm">
                                        {% if r.Payment_Status in ['PAID', 'PARTIAL', 'ADVANCE'] %}
                                        <button
                                            onclick="togglePaymentStatus('{{ r.Bill }}', '{{ r.Payment_Status }}', '{{ grand_total }}', '{{ amt_recv }}')"
                                            class="btn btn-sm btn-light border py-1" title="Mark Pending"><i
                                                class="bi bi-arrow-counterclockwise text-secondary"></i></button>
                                        {% else %}
                                        <button
                                            onclick="togglePaymentStatus('{{ r.Bill }}', 'PENDING', '{{ grand_total }}', '0')"
                                            class="btn btn-sm btn-light border py-1" title="Mark Paid"><i
                                                class="bi bi-check2 text-success"></i></button>
                                        {% endif %}
                                        {% if config.get('system', 'features.whatsapp_sync') %}
                                        <button class="btn btn-sm btn-light border py-1 text-success"
                                            onclick="sendWhatsApp('{{ r.Bill }}')" title="Send via WhatsApp"><i
                                                class="bi bi-whatsapp"></i></button>
                                        {% endif %}
                                        <button class="btn btn-sm btn-light border py-1"
                                            onclick="openGlobalPDFPreview('{{ r.Bill }}')" title="View PDF"><i
                                                class="bi bi-eye text-primary"></i></button>
                                        <button onclick="openEditBillModal('{{ r.Bill }}')"
                                            class="btn btn-sm btn-light border py-1 text-warning" title="Edit Bill"><i
                                                class="bi bi-pencil"></i></button>
                                    </div>
                                </td>
                            </tr>
                            {% endfor %}
                            {% if not receipts %}
                            <tr>
                                <td colspan="5" class="text-center py-5 text-muted">
                                    <i class="bi bi-inbox fs-1 d-block mb-3 opacity-50"></i>
                                    <h5>No Receipts Found</h5>
                                    <p class="fs-7">Generate the first receipt for {{ tenant.name }}.</p>
                                </td>
                            </tr>
                            {% endif %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>


    </div>
</div>

<div id="printQrArea" class="d-none">
    <div style="border: 4px solid #000; border-radius: 20px; padding: 40px; max-width: 500px; margin: auto;">
        <h1 style="font-size: 2.5rem; margin-bottom: 10px; font-weight: bold;">Scan to View Bills</h1>
        <h3 style="color: #555; margin-bottom: 30px;">{{ tenant.name }}</h3>

        <div id="printQrcode" style="display: flex; justify-content: center; margin-bottom: 30px;"></div>

        <p style="font-size: 1.2rem; color: #777;">
            Point your smartphone camera here to view your live rent profile, latest bills, and payment status.
        </p>
        {% if tenant.room_number %}
        <div
            style="margin-top: 20px; padding-top: 20px; border-top: 2px dashed #ccc; font-size: 1.5rem; font-weight: bold;">
            Room: {{ tenant.room_number }}
        </div>
        {% endif %}
    </div>
</div>

<div class="modal fade" id="qrModal" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered modal-sm">
        <div class="modal-content border-0 shadow-lg rounded-4 text-center p-4">
            <h5 class="fw-bold mb-1">Tenant Access QR</h5>
            <p class="text-muted fs-7 mb-4">Scan to view the latest 12 months of bills</p>
            <div id="qrcode" class="d-flex justify-content-center mb-4 p-3 bg-white border rounded-3"></div>

            <div class="d-flex gap-2">
                <button type="button" class="btn btn-primary rounded-pill w-100 fw-bold shadow-sm"
                    onclick="window.print()">
                    <i class="bi bi-printer me-2"></i>Print
                </button>
                <button type="button" class="btn btn-light rounded-pill w-100 fw-bold border"
                    data-bs-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>

<script id="occupantsData" type="application/json">
    {{ occupants | tojson | safe }}
</script>

<div class="modal fade" id="kycSplitModal" tabindex="-1">
    <div class="modal-dialog modal-xl modal-dialog-centered">
        <div class="modal-content border-0 shadow-lg rounded-4 overflow-hidden" style="height: 85vh;">
            <div class="modal-header border-bottom bg-light py-3">
                <h5 class="modal-title fw-bold text-primary">
                    <i class="bi bi-person-vcard me-2"></i>Occupant KYC Documents
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>

            <div class="modal-body p-0 d-flex flex-column flex-lg-row h-100">
                <div class="col-lg-5 border-end bg-body-tertiary d-flex flex-column h-100">
                    <div class="p-3 border-bottom bg-white">
                        <h6 class="fw-bold mb-0 text-muted">Occupants Directory</h6>
                    </div>
                    <div class="flex-grow-1 p-0" style="overflow-y: auto;" id="kycOccupantList">
                    </div>
                </div>

                <div class="col-lg-7 bg-white position-relative d-flex flex-column h-100">

                    <div id="kycPreviewPlaceholder"
                        class="position-absolute top-50 start-50 translate-middle text-center text-muted w-100"
                        style="z-index: 2;">
                        <i class="bi bi-file-earmark-person" style="font-size: 4rem; opacity: 0.5;"></i>
                        <h5 class="mt-3">Select an occupant</h5>
                        <p class="fs-7">Choose an occupant from the left to view their KYC details.</p>
                    </div>

                    <div id="kycPreviewContent" class="d-none d-flex flex-column h-100 w-100" style="z-index: 1;">
                        <div class="p-3 border-bottom bg-light">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <div>
                                    <h5 class="fw-bold mb-1" id="previewOccName">Name</h5>
                                    <span class="badge bg-secondary" id="previewOccStatus">Status</span>
                                    <span class="text-muted fs-8 ms-2" id="previewOccDates"></span>
                                </div>
                                <div class="btn-group shadow-sm rounded-pill">
                                    <button class="btn btn-sm btn-light border text-warning d-none" id="btnMarkInactive"
                                        title="Mark Inactive">
                                        <i class="bi bi-person-down"></i> Inactive
                                    </button>
                                    <button class="btn btn-sm btn-light border text-danger" id="btnDeleteOcc"
                                        title="Delete Record">
                                        <i class="bi bi-trash"></i> Delete
                                    </button>
                                </div>
                            </div>
                            <div class="d-flex gap-2 flex-wrap" id="documentToggles">
                            </div>
                        </div>

                        <div class="flex-grow-1 bg-secondary position-relative p-0" id="documentViewerContainer"
                            style="overflow: hidden; min-height: 400px;">
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<style>
    /* Print-specific styling for the QR Poster */
    @media print {
        body * {
            visibility: hidden;
        }

        #printQrArea,
        #printQrArea * {
            visibility: visible;
        }

        #printQrArea {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            display: flex !important;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }

        /* Hide the modal when printing */
        .modal {
            display: none !important;
        }

        .modal-backdrop {
            display: none !important;
        }
    }
</style>
<script>
    // Parse the JSON securely injected by Jinja
    const occupantsRaw = JSON.parse(document.getElementById('occupantsData').textContent || '[]');
    const viewToken = '{{ tenant.view_token }}'; // Need this for admin actions

    function toggleAllBills(source) {
        const checkboxes = document.querySelectorAll('.bill-checkbox');
        checkboxes.forEach(cb => cb.checked = source.checked);
    }

    async function sendBulkWhatsApp() {
        const checkboxes = document.querySelectorAll('.bill-checkbox:checked');
        if (checkboxes.length === 0) {
            showError("No Selection", "Please select at least one bill to send.");
            return;
        }

        const billNumbers = Array.from(checkboxes).map(cb => cb.value);

        try {
            showLoading("Generating Link...");
            const response = await fetch(window.APP.API + '/whatsapp/bulk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: parseInt('{{ tenant.id }}'),
                    bill_numbers: billNumbers
                })
            });
            const data = await response.json();
            hideLoading();

            if (data.status === 'success') {
                window.open(data.url, '_blank');
            } else {
                showError("Failed", data.message || data.detail);
            }
        } catch (e) {
            hideLoading();
            showError("Network Error", "Could not connect to the server.");
        }
    }

    function openKycModal() {
        renderOccupantList();
        resetPreviewPane();
        const modal = new bootstrap.Modal(document.getElementById('kycSplitModal'));
        modal.show();
    }

    function renderOccupantList() {
        const listContainer = document.getElementById('kycOccupantList');
        listContainer.innerHTML = '';

        if (occupantsRaw.length === 0) {
            listContainer.innerHTML = `
                <div class="text-center p-5 text-muted">
                    <i class="bi bi-inbox fs-2 mb-2 d-block opacity-50"></i>
                    <p>No occupants registered.</p>
                </div>`;
            return;
        }

        // Group by Status instead of Date
        const grouped = { 'Active': [], 'Inactive': [] };
        occupantsRaw.forEach(occ => {
            const status = occ['Status'] === 'Active' ? 'Active' : 'Inactive';
            grouped[status].push(occ);
        });

        // Render Groups
        for (const [statusGroup, occs] of Object.entries(grouped)) {
            if (occs.length === 0) continue; // Skip empty groups

            // Group Header
            const icon = statusGroup === 'Active' ? 'bi-person-check' : 'bi-person-slash';
            const color = statusGroup === 'Active' ? 'text-success' : 'text-secondary';

            listContainer.innerHTML += `
                <div class="bg-body-secondary p-2 px-3 fw-bold ${color} fs-8 text-uppercase sticky-top border-bottom" style="z-index: 10;">
                    <i class="bi ${icon} me-2"></i>${statusGroup} Occupants
                </div>
            `;

            // Occupant Rows
            occs.forEach(o => {
                const docsAvailable = (o['Aadhaar Combined'] || o['Aadhaar Front'] || o['Aadhaar Back'] || o['Emp Front'])
                    ? '<i class="bi bi-file-earmark-check text-success fs-7"></i>'
                    : '<i class="bi bi-exclamation-circle text-warning fs-7"></i>';

                const encodedData = encodeURIComponent(JSON.stringify(o));

                listContainer.innerHTML += `
                    <div class="p-3 border-bottom bg-white transition-hover kyc-list-item" style="cursor: pointer;" onclick="selectOccupant(this, '${encodedData}')">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <div class="fw-bold text-primary mb-1">${o['Name']}</div>
                                <div class="text-muted fs-8"><i class="bi bi-telephone me-1"></i>${o['Mobile'] || 'N/A'}</div>
                            </div>
                            <div>${docsAvailable}</div>
                        </div>
                    </div>
                `;
            });
        }
    }

    function selectOccupant(element, encodedData) {
        // UI Highlight
        document.querySelectorAll('.kyc-list-item').forEach(el => el.classList.remove('bg-primary-subtle'));
        element.classList.add('bg-primary-subtle');

        // Parse Data
        const occ = JSON.parse(decodeURIComponent(encodedData));

        // Show Content, Hide Placeholder
        document.getElementById('kycPreviewPlaceholder').classList.add('d-none');
        document.getElementById('kycPreviewContent').classList.remove('d-none');

        // Populate Header
        document.getElementById('previewOccName').innerText = occ['Name'];
        document.getElementById('previewOccStatus').className = occ['Status'] === 'Active' ? 'badge bg-success' : 'badge bg-secondary';
        document.getElementById('previewOccStatus').innerText = occ['Status'];
        document.getElementById('previewOccDates').innerText = `Mobile: ${occ['Mobile'] || 'N/A'}`;

        // Admin Action Bindings
        const btnInactive = document.getElementById('btnMarkInactive');
        if (occ['Status'] === 'Active') {
            btnInactive.classList.remove('d-none');
            btnInactive.onclick = () => adminMarkInactive(occ['Occupant UUID'], viewToken);
        } else {
            btnInactive.classList.add('d-none');
        }
        document.getElementById('btnDeleteOcc').onclick = () => adminDeleteOccupant(occ['Occupant UUID'], viewToken);

        // Populate Document Toggles
        const toggleBar = document.getElementById('documentToggles');
        toggleBar.innerHTML = '';

        let firstDocPath = null;
        let firstDocType = null;

        const addToggleButton = (label, filepath, type) => {
            if (!filepath) return;
            if (!firstDocPath) { firstDocPath = filepath; firstDocType = type; } // Keep track of first to auto-load

            const btn = document.createElement('button');
            btn.className = 'btn btn-sm btn-outline-primary rounded-pill fw-bold doc-toggle-btn';
            btn.innerHTML = label;
            btn.onclick = (e) => {
                document.querySelectorAll('.doc-toggle-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                renderDocument(filepath);
            };
            toggleBar.appendChild(btn);
        };

        if (occ['Aadhaar Combined']) {
            addToggleButton('<i class="bi bi-file-earmark-person me-1"></i>Aadhaar (Combined)', occ['Aadhaar Combined'], 'pdf');
        } else {
            addToggleButton('<i class="bi bi-person-bounding-box me-1"></i>Aadhaar Front', occ['Aadhaar Front'], 'img');
            addToggleButton('<i class="bi bi-upc-scan me-1"></i>Aadhaar Back', occ['Aadhaar Back'], 'img');
        }

        addToggleButton('<i class="bi bi-briefcase me-1"></i>Emp ID Front', occ['Emp Front'], 'img');
        addToggleButton('<i class="bi bi-briefcase-fill me-1"></i>Emp ID Back', occ['Emp Back'], 'img');

        if (firstDocPath) {
            toggleBar.firstChild.classList.add('active');
            renderDocument(firstDocPath);
        } else {
            document.getElementById('documentViewerContainer').innerHTML = `
                <div class="w-100 h-100 d-flex justify-content-center align-items-center bg-light text-muted">
                    <div class="text-center">
                        <i class="bi bi-file-earmark-x fs-1 mb-2"></i>
                        <h6>No Documents Uploaded</h6>
                    </div>
                </div>
            `;
        }
    }

    function renderDocument(filename) {
        const viewer = document.getElementById('documentViewerContainer');
        // Force the absolute URL using the window.APP_BASE
        const absoluteUrl = window.APP_BASE + `/api/kyc/${filename}`;
        const ext = filename.split('.').pop().toLowerCase();

        // Inject the absolute URL into the iframe or image
        if (ext === 'pdf') {
            viewer.innerHTML = `
                <object data="${absoluteUrl}" type="application/pdf" width="100%" height="100%" style="display: block;">
                    <iframe src="${absoluteUrl}" width="100%" height="100%" style="border: none;">
                        <div class="p-4 text-center bg-white h-100 d-flex flex-column justify-content-center align-items-center">
                            <i class="bi bi-file-earmark-pdf text-danger mb-3" style="font-size: 3rem;"></i>
                            <h5>PDF Ready</h5>
                            <a href="${absoluteUrl}" target="_blank" class="btn btn-primary mt-2">Open & View Document</a>
                        </div>
                    </iframe>
                </object>`;
        } else {
            // Wrap images in a scrollable container for zoom/pan ease
            viewer.innerHTML = `
                <div class="w-100 h-100 d-flex justify-content-center align-items-center" style="overflow: auto; background-color: #2b2b2b;">
                    <img src="${absoluteUrl}" style="max-width: 95%; max-height: 95%; object-fit: contain; box-shadow: 0 0 15px rgba(0,0,0,0.5);">
                </div>
            `;
        }
    }

    function resetPreviewPane() {
        document.getElementById('kycPreviewPlaceholder').classList.remove('d-none');
        document.getElementById('kycPreviewContent').classList.add('d-none');
        document.getElementById('documentViewerContainer').innerHTML = '';
    }

    function showQRCode(token) {
        if (!token) {
            alert("Token generating... Please refresh the page once.");
            return;
        }
        const qrContainer = document.getElementById('qrcode');
        const printQrContainer = document.getElementById('printQrcode');

        qrContainer.innerHTML = '';
        printQrContainer.innerHTML = '';

        // Use window.APP_BASE for proper reverse proxy handling
        const url = window.location.origin + window.APP_BASE + '/t/' + token;

        // Generate for Modal
        new QRCode(qrContainer, {
            text: url, width: 200, height: 200, colorDark: "#000000", colorLight: "#ffffff", correctLevel: QRCode.CorrectLevel.H
        });

        // Generate for Print Area (Slightly larger)
        new QRCode(printQrContainer, {
            text: url, width: 300, height: 300, colorDark: "#000000", colorLight: "#ffffff", correctLevel: QRCode.CorrectLevel.H
        });

        const modal = new bootstrap.Modal(document.getElementById('qrModal'));
        modal.show();
    }

    // --- Occupant KYC Admin Logic ---

    // Calculate Days Stayed Dynamically
    document.addEventListener("DOMContentLoaded", () => {
        const daysElements = document.querySelectorAll('.days-stayed');
        daysElements.forEach(el => {
            const joinStr = el.getAttribute('data-join');
            const leaveStr = el.getAttribute('data-leave');
            const status = el.getAttribute('data-status');

            if (joinStr) {
                const joinDate = new Date(joinStr);
                const endDate = (status === 'Inactive' && leaveStr) ? new Date(leaveStr) : new Date();

                const diffTime = Math.abs(endDate - joinDate);
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

                el.innerText = `${diffDays} Days Stayed`;
            }
        });
    });

    async function adminMarkInactive(uuid, token) {
        confirmAction(
            "Mark Occupant Inactive?",
            "This will lock their 'Days Stayed' to today.",
            "Yes, Mark Inactive",
            "#ffc107"
        ).then(async (result) => {
            if (result.isConfirmed) {
                try {
                    // We cleverly reuse the public API route by passing the tenant's token
                    const res = await fetch(window.APP.API + `/t/${token}/kyc/${uuid}/inactive`, { method: "PUT" });
                    if (res.ok) {
                        showToast("success", "Occupant marked inactive.");
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        showError("Failed", "Could not update status.");
                    }
                } catch (e) {
                    showError("Network Error", "An error occurred.");
                }
            }
        });
    }

    async function adminDeleteOccupant(uuid, token) {
        confirmAction(
            "Delete Occupant Record?",
            "This will permanently remove their details and delete their uploaded ID images from the server.",
            "Permanently Delete",
            "#dc3545"
        ).then(async (result) => {
            if (result.isConfirmed) {
                try {
                    const res = await fetch(window.APP.API + `/t/${token}/kyc/${uuid}`, { method: "DELETE" });
                    if (res.ok) {
                        showToast("success", "Occupant record deleted.");
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        showError("Failed", "Could not delete record.");
                    }
                } catch (e) {
                    showError("Network Error", "An error occurred.");
                }
            }
        });
    }
</script>
{% endblock %}
```

```html
// File: templates\tenant_public_profile.html
<!DOCTYPE html>
<html lang="en" data-bs-theme="{{ theme }}">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Rent Profile</title>
    <link rel="icon" type="image/svg+xml" href="{{ STATIC_URL(request, '/fevicon.svg') }}">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">

    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
    <style>
        body {
            background-color: var(--bs-tertiary-bg);
            padding-bottom: 40px;
        }

        .mobile-card {
            border-radius: 16px;
            border: none;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            margin-bottom: 15px;
        }

        .receipt-row {
            padding: 15px;
            border-bottom: 1px solid var(--bs-border-color-translucent);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .receipt-row:last-child {
            border-bottom: none;
        }

        .timeline-month {
            font-weight: bold;
            background: var(--bs-secondary-bg);
            cursor: pointer;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 10px;
        }

        .timeline-content {
            padding-left: 15px;
            border-left: 2px solid var(--bs-primary);
            margin-left: 10px;
            margin-bottom: 20px;
        }

        .occupant-card {
            border: 1px solid var(--bs-border-color);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            background: var(--bs-body-bg);
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .occupant-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }

        .occupant-card.active {
            border-color: var(--bs-primary);
            background-color: rgba(13, 110, 253, 0.05);
        }

        @media (min-width: 992px) {
            .kyc-layout {
                height: calc(100vh - 300px);
                min-height: 500px;
            }

            .kyc-sidebar {
                height: 100%;
                overflow-y: auto;
            }

            .kyc-viewer {
                height: 100%;
            }
        }
    </style>
</head>

<body>

    <div class="container-fluid mt-4" style="max-width: 1400px;">

        {% if not unlocked %}
        <div class="container mt-4" style="max-width: 600px;">
            <div class="card mobile-card text-center p-5 mt-5 shadow">
                <i class="bi bi-lock-fill text-primary mb-3" style="font-size: 3rem;"></i>
                <h4 class="fw-bold mb-3">Secure Access</h4>
                <p class="text-muted mb-4">Please enter your 4-digit PIN to view your rent profile and bills.</p>

                {% if error %}
                <div class="alert alert-danger py-2 fs-7">{{ error }}</div>
                {% endif %}

                <form method="POST" action="">
                    <div class="mb-3">
                        <input type="password" name="pin"
                            class="form-control form-control-lg text-center mx-auto shadow-sm" placeholder="••••"
                            maxlength="4" pattern="\d{4}" style="width: 150px; letter-spacing: 5px; font-size: 1.5rem;"
                            required autofocus>
                    </div>
                    <button type="submit"
                        class="btn btn-primary btn-lg rounded-pill px-5 shadow-sm mt-2">Unlock</button>
                </form>
            </div>
        </div>
        {% else %}

        <div class="d-flex justify-content-between align-items-center mb-4 px-2">
            <div>
                <h2 class="fw-bold mb-0"><i class="bi bi-folder2-open text-primary me-2"></i>Tenant Document Center</h2>
                <p class="text-muted mb-0">Secure portal for {{ tenant.name }}</p>
            </div>
            <button class="btn btn-primary rounded-pill fw-bold shadow-sm" data-bs-toggle="modal"
                data-bs-target="#uploadModal">
                <i class="bi bi-cloud-arrow-up-fill me-2"></i>Upload KYC
            </button>
        </div>

        <ul class="nav nav-pills mb-4 border-bottom pb-3 px-2" id="portalTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active rounded-pill fw-bold" id="kyc-tab" data-bs-toggle="tab"
                    data-bs-target="#kyc-pane" type="button" role="tab"><i class="bi bi-person-vcard me-2"></i>Occupant
                    KYC</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link rounded-pill fw-bold" id="receipts-tab" data-bs-toggle="tab"
                    data-bs-target="#receipts-pane" type="button" role="tab"><i class="bi bi-receipt me-2"></i>Receipts
                    ({{ receipts|length }})</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link rounded-pill fw-bold" id="profile-tab" data-bs-toggle="tab"
                    data-bs-target="#profile-pane" type="button" role="tab"><i
                        class="bi bi-person-circle me-2"></i>Profile</button>
            </li>
        </ul>

        <div class="tab-content px-2" id="portalTabsContent">

            <!-- ==================== TAB 1: OCCUPANT KYC ==================== -->
            <div class="tab-pane fade show active" id="kyc-pane" role="tabpanel" tabindex="0">

                <div class="row g-3 mb-4">
                    <div class="col-6 col-md-3">
                        <div class="card bg-primary text-white border-0 shadow-sm rounded-4 p-3">
                            <div class="fs-7 opacity-75 text-uppercase fw-bold mb-1">Occupants</div>
                            <div class="fs-3 fw-bold" id="statOccupants">0</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="card bg-info text-white border-0 shadow-sm rounded-4 p-3">
                            <div class="fs-7 opacity-75 text-uppercase fw-bold mb-1">Total Docs</div>
                            <div class="fs-3 fw-bold" id="statDocs">0</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="card bg-warning text-dark border-0 shadow-sm rounded-4 p-3">
                            <div class="fs-7 opacity-75 text-uppercase fw-bold mb-1">Upload Months</div>
                            <div class="fs-3 fw-bold" id="statMonths">0</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="card bg-success text-white border-0 shadow-sm rounded-4 p-3">
                            <div class="fs-7 opacity-75 text-uppercase fw-bold mb-1">Latest Upload</div>
                            <div class="fs-5 fw-bold mt-1" id="statLatest">-</div>
                        </div>
                    </div>
                </div>

                <div class="row g-4 kyc-layout">

                    <div class="col-lg-5 col-xl-4 kyc-sidebar">
                        <div class="position-sticky top-0 bg-body pt-1 pb-3" style="z-index: 10;">
                            <input type="text" id="searchInput"
                                class="form-control rounded-pill mb-3 shadow-sm border-0 bg-body-secondary"
                                placeholder="🔍 Search Occupant Name..." onkeyup="renderTimeline()">

                            <div class="d-flex gap-2 overflow-auto pb-1 hide-scrollbar">
                                <button class="btn btn-sm btn-dark rounded-pill px-3 filter-btn active"
                                    onclick="setFilter('All', this)">All</button>
                                <button class="btn btn-sm btn-outline-success rounded-pill px-3 filter-btn"
                                    onclick="setFilter('Active', this)">Active</button>
                                <button class="btn btn-sm btn-outline-secondary rounded-pill px-3 filter-btn"
                                    onclick="setFilter('Inactive', this)">Inactive</button>
                            </div>
                        </div>

                        <div id="timelineContainer" class="mt-2 pb-5">
                        </div>
                    </div>

                    <div class="col-lg-7 col-xl-8 kyc-viewer mb-5">
                        <div
                            class="card h-100 border-0 shadow-sm rounded-4 overflow-hidden position-relative bg-body-tertiary">

                            <div id="viewerPlaceholder"
                                class="position-absolute top-50 start-50 translate-middle text-center text-muted w-100">
                                <i class="bi bi-file-earmark-text mb-3" style="font-size: 4rem; opacity: 0.3;"></i>
                                <h5>Select an Occupant</h5>
                                <p class="fs-7">Click any occupant card on the left to view their uploaded KYC
                                    documents.</p>
                            </div>

                            <div id="viewerContent" class="d-none d-flex flex-column h-100 w-100 position-relative"
                                style="z-index: 2; background: var(--bs-body-bg);">

                                <div class="p-3 border-bottom bg-light">
                                    <div class="d-flex justify-content-between align-items-center mb-3">
                                        <div>
                                            <h4 class="fw-bold mb-1" id="previewName">Name</h4>
                                            <div class="d-flex align-items-center gap-2">
                                                <span class="badge" id="previewStatus">Status</span>
                                                <span class="text-muted fs-7"><i class="bi bi-telephone me-1"></i> <span
                                                        id="previewMobile"></span></span>
                                            </div>
                                        </div>
                                        <div>
                                            <button class="btn btn-sm btn-outline-danger rounded-pill fw-bold d-none"
                                                id="btnMarkInactive">Mark Inactive</button>
                                        </div>
                                    </div>
                                    <div class="d-flex gap-2 flex-wrap" id="documentToggles">
                                    </div>
                                </div>

                                <div class="flex-grow-1 bg-secondary position-relative p-0" id="documentIframeContainer"
                                    style="overflow: hidden; min-height: 400px;">
                                </div>

                            </div>

                        </div>
                    </div>

                </div>
            </div>

            <!-- ==================== TAB 2: RECEIPTS ==================== -->
            <div class="tab-pane fade" id="receipts-pane" role="tabpanel" tabindex="0">
                <div class="row">
                    <div class="col-lg-8 mx-auto">
                        <div class="card mobile-card rounded-4 border-0 shadow-sm">
                            {% for r in receipts %}
                            {% set curr_total = r.Total|default(0, true)|float %}
                            {% set prev_arr = r.Previous_Arrears|default(0, true)|float %}
                            {% set grand_total = curr_total + prev_arr %}
                            {% set amount_received = r.Amount_Received|default(0, true)|float %}
                            {% set net_balance = grand_total - amount_received %}
                            {% set advance_amount = 0 - net_balance if net_balance < 0 else 0 %}
                            <div class="receipt-row">
                                <div>
                                    <div class="fw-bold fs-5">{{ r.Month }}</div>
                                    <div class="text-muted fs-7">Bill #{{ r.Bill }} • Units: {{ r.Units }}</div>
                                    {% if r.Payment_Status == "PAID" %}
                                        <span class="badge bg-success rounded-pill px-2 mt-1">PAID</span>
                                    {% elif r.Payment_Status == "PARTIAL" %}
                                        <span class="badge bg-warning text-dark rounded-pill px-2 mt-1">PARTIAL</span>
                                    {% elif r.Payment_Status == "ADVANCE" %}
                                        <span class="badge bg-info text-dark rounded-pill px-2 mt-1">ADVANCE</span>
                                    {% else %}
                                        <span class="badge bg-danger rounded-pill px-2 mt-1">PENDING</span>
                                    {% endif %}
                                </div>
                                <div class="text-end">
                                    <div class="fs-7 text-muted fw-bold">Total Payable</div>
                                    <div class="fw-bold text-dark mb-1 fs-5">₹{{ "{:,.0f}".format(grand_total) }}</div>
                                    <div class="text-success fw-semibold fs-7">Paid: ₹{{ "{:,.0f}".format(amount_received) }}</div>
                                    {% if net_balance > 0 %}
                                        <div class="text-danger fw-semibold fs-7 mt-1">Due: ₹{{ "{:,.0f}".format(net_balance) }}</div>
                                    {% elif net_balance < 0 %}
                                        <div class="text-info fw-semibold fs-7 mt-1">Adv: ₹{{ "{:,.0f}".format(advance_amount) }}</div>
                                    {% endif %}
                                </div>
                                <a href="{{ request.url_for(Names.PDF_VIEW, bill_no=r.Bill) }}" target="_blank"
                                    class="btn btn-primary btn-sm rounded-circle ms-4 shadow-sm d-flex align-items-center justify-content-center"
                                    style="width: 45px; height: 45px;" title="View PDF">
                                    <i class="bi bi-file-earmark-pdf fs-4"></i>
                                </a>
                            </div>
                            {% endfor %}

                            {% if not receipts %}
                            <div class="text-center py-5 text-muted">
                                <i class="bi bi-inbox fs-1 mb-2 d-block opacity-50"></i>
                                <p>No bills generated yet.</p>
                            </div>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>

            <!-- ==================== TAB 3: PROFILE ==================== -->
            <div class="tab-pane fade" id="profile-pane" role="tabpanel" tabindex="0">
                <div class="row">
                    <div class="col-lg-6 mx-auto">
                        <div
                            class="card mobile-card text-center overflow-hidden position-relative pt-5 pb-4 px-4 shadow-sm rounded-4 border-0">
                            <div class="bg-primary bg-gradient position-absolute top-0 w-100"
                                style="height: 80px; left: 0;"></div>
                            <div class="bg-white text-primary rounded-circle shadow d-flex align-items-center justify-content-center mx-auto mb-3"
                                style="width: 90px; height: 90px; font-size: 2.5rem; font-weight: bold; border: 4px solid white; position: relative; z-index: 1; margin-top: -45px;">
                                {{ tenant.name[:1]|upper }}
                            </div>
                            <h3 class="fw-bold mb-1">{{ tenant.name }}</h3>
                            <div class="text-muted mb-4">
                                {% if tenant.room_number %}Room: {{ tenant.room_number }} • {% endif %}
                                Meter: {{ tenant.meter_id or "N/A" }}
                            </div>

                            <div class="d-flex justify-content-center gap-3 mb-4">
                                <div class="bg-body-secondary rounded-4 p-3 w-50">
                                    <div class="fs-7 text-muted text-uppercase mb-1">Monthly Rent</div>
                                    <div class="fs-4 fw-bold">₹{{ "{:,.0f}".format(tenant.rent) }}</div>
                                </div>
                                <div class="bg-body-secondary rounded-4 p-3 w-50">
                                    <div class="fs-7 text-muted text-uppercase mb-1">Electricity Rate</div>
                                    <div class="fs-4 fw-bold">₹{{ tenant.electricity_rate }}/u</div>
                                </div>
                            </div>

                            <div class="text-start bg-light rounded-4 p-4 border">
                                <h6 class="fw-bold mb-3 border-bottom pb-2">Contact Details</h6>
                                <div class="d-flex align-items-center mb-2">
                                    <i class="bi bi-telephone text-primary me-3"></i>
                                    <span>{{ tenant.phone or "Not Provided" }}</span>
                                </div>
                                <div class="d-flex align-items-center">
                                    <i class="bi bi-envelope text-primary me-3"></i>
                                    <span>{{ tenant.email or "Not Provided" }}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

        </div>

        <!-- Upload Modal -->
        <div class="modal fade" id="uploadModal" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow-lg rounded-4">
                    <div class="modal-header bg-light border-0 py-3 rounded-top-4">
                        <h5 class="modal-title fw-bold text-primary"><i class="bi bi-shield-check me-2"></i>New Occupant
                            KYC</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body p-4">
                        <form id="uploadForm">
                            <div class="form-floating mb-3">
                                <input type="text" class="form-control rounded-3" id="occName" placeholder="Full Name"
                                    required>
                                <label>Occupant Full Name</label>
                            </div>
                            <div class="form-floating mb-4">
                                <input type="tel" class="form-control rounded-3" id="mobile" placeholder="Mobile Number"
                                    pattern="[0-9]{10}" required>
                                <label>Mobile Number (10 digits)</label>
                            </div>

                            <h6
                                class="fw-bold mb-2 border-bottom pb-2 text-secondary d-flex justify-content-between align-items-center">
                                Aadhaar Card <span class="badge bg-danger rounded-pill">Required</span>
                            </h6>

                            <div class="mb-3 mt-3 bg-body-secondary p-2 rounded-3">
                                <div class="form-check form-check-inline">
                                    <input class="form-check-input" type="radio" name="aadhaarType" id="typeSeparate"
                                        value="separate" checked onchange="toggleAadhaarUpload()">
                                    <label class="form-check-label fw-bold fs-7" for="typeSeparate">Separate (Front &
                                        Back)</label>
                                </div>
                                <div class="form-check form-check-inline">
                                    <input class="form-check-input" type="radio" name="aadhaarType" id="typeCombined"
                                        value="combined" onchange="toggleAadhaarUpload()">
                                    <label class="form-check-label fw-bold fs-7" for="typeCombined">Single File
                                        (Combined)</label>
                                </div>
                            </div>

                            <div class="row g-2 mb-4" id="aadhaarSeparateContainer">
                                <div class="col-6">
                                    <label class="form-label fs-8 text-muted fw-bold mb-1">Front Side</label>
                                    <input type="file" class="form-control border-primary" id="aadhaarFront"
                                        accept="image/*,.pdf" required>
                                </div>
                                <div class="col-6">
                                    <label class="form-label fs-8 text-muted fw-bold mb-1">Back Side</label>
                                    <input type="file" class="form-control border-primary" id="aadhaarBack"
                                        accept="image/*,.pdf" required>
                                </div>
                            </div>

                            <div class="mb-4 d-none" id="aadhaarCombinedContainer">
                                <label class="form-label fs-8 text-muted fw-bold mb-1">Single PDF / Image (Front & Back
                                    included)</label>
                                <input type="file" class="form-control border-primary" id="aadhaarCombined"
                                    accept="image/*,.pdf">
                            </div>

                            <h6
                                class="fw-bold mb-3 border-bottom pb-2 mt-4 text-secondary d-flex justify-content-between align-items-center">
                                Employee ID <span class="badge bg-secondary rounded-pill">Optional</span>
                            </h6>
                            <div class="row g-2 mb-4">
                                <div class="col-6">
                                    <label class="form-label fs-8 text-muted fw-bold mb-1">Front Side</label>
                                    <input type="file" class="form-control" id="empFront" accept="image/*,.pdf">
                                </div>
                                <div class="col-6">
                                    <label class="form-label fs-8 text-muted fw-bold mb-1">Back Side</label>
                                    <input type="file" class="form-control" id="empBack" accept="image/*,.pdf">
                                </div>
                            </div>

                            <div class="alert alert-danger d-none fs-7 py-2" id="uploadError"></div>
                            <button type="submit" class="btn btn-primary w-100 rounded-pill fw-bold py-3 shadow-sm fs-5"
                                id="uploadBtn">Upload & Save KYC</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script id="occupants-data" type="application/json">
            {{ occupants|tojson|safe }}
        </script>
        <script>
            const rawOccupants = JSON.parse(document.getElementById('occupants-data').textContent);
            let currentFilter = 'All';

            document.addEventListener('DOMContentLoaded', () => {
                calculateStats();
                renderTimeline();
            });

            function parseDate(dateStr) {
                if (!dateStr || dateStr === "Legacy Uploads") return new Date(2000, 0, 1);
                return new Date(dateStr);
            }

            function calculateStats() {
                document.getElementById('statOccupants').innerText = rawOccupants.length;

                let totalDocs = 0;
                const monthsSet = new Set();
                let latestDate = null;

                rawOccupants.forEach(o => {
                    ['Aadhaar Front', 'Aadhaar Back', 'Aadhaar Combined', 'Emp Front', 'Emp Back'].forEach(k => {
                        if (o[k]) totalDocs++;
                    });

                    const m = o['Upload_Month'] || 'Legacy Uploads';
                    monthsSet.add(m);

                    const d = parseDate(o['Upload_Date']);
                    if (!latestDate || d > latestDate) {
                        if (d.getFullYear() > 2000) latestDate = d;
                    }
                });

                document.getElementById('statDocs').innerText = totalDocs;
                document.getElementById('statMonths').innerText = monthsSet.size;

                if (latestDate) {
                    const options = { day: '2-digit', month: 'short', year: 'numeric' };
                    document.getElementById('statLatest').innerText = latestDate.toLocaleDateString('en-GB', options);
                }
            }

            function setFilter(val, btnEl) {
                document.querySelectorAll('.filter-btn').forEach(b => {
                    b.classList.remove('btn-dark', 'active');
                    b.classList.add(b.innerText === 'Active' ? 'btn-outline-success' : (b.innerText === 'Inactive' ? 'btn-outline-secondary' : 'btn-outline-dark'));
                });

                btnEl.classList.remove('btn-outline-dark', 'btn-outline-success', 'btn-outline-secondary');
                btnEl.classList.add('btn-dark', 'active');

                currentFilter = val;
                renderTimeline();
            }

            function renderTimeline() {
                const search = document.getElementById('searchInput').value.toLowerCase();
                const container = document.getElementById('timelineContainer');
                container.innerHTML = '';

                const filtered = rawOccupants.filter(o => {
                    const matchName = o.Name.toLowerCase().includes(search);
                    const matchStatus = currentFilter === 'All' || o.Status === currentFilter;
                    return matchName && matchStatus;
                });

                filtered.sort((a, b) => parseDate(b.Upload_Date) - parseDate(a.Upload_Date));

                const groups = {};
                filtered.forEach(o => {
                    const month = o['Upload_Month'] || 'Legacy Uploads';
                    if (!groups[month]) groups[month] = [];
                    groups[month].push(o);
                });

                const sortedMonths = Object.keys(groups).sort((a, b) => {
                    if (a === 'Legacy Uploads') return 1;
                    if (b === 'Legacy Uploads') return -1;
                    return parseDate(groups[b][0].Upload_Date) - parseDate(groups[a][0].Upload_Date);
                });

                if (sortedMonths.length === 0) {
                    container.innerHTML = `<div class="text-center p-5 text-muted"><i class="bi bi-search fs-1 mb-2 d-block"></i>No occupants found</div>`;
                    return;
                }

                let html = '';
                sortedMonths.forEach(month => {
                    const occs = groups[month];
                    const safeId = month.replace(/[^a-zA-Z0-9]/g, '');

                    html += `
                    <div class="timeline-month d-flex justify-content-between align-items-center shadow-sm" data-bs-toggle="collapse" data-bs-target="#collapse-${safeId}">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-calendar3 me-2 text-primary"></i>${month}
                        </div>
                        <span class="badge bg-secondary rounded-pill">${occs.length} Occupant${occs.length > 1 ? 's' : ''}</span>
                    </div>
                `;

                    html += `<div class="collapse show timeline-content" id="collapse-${safeId}">`;

                    occs.forEach(o => {
                        const isActive = o.Status === 'Active';
                        const statusBadge = isActive
                            ? `<span class="badge bg-success bg-opacity-10 text-success border border-success"><i class="bi bi-check-circle-fill me-1"></i>Active</span>`
                            : `<span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary"><i class="bi bi-dash-circle-fill me-1"></i>Inactive</span>`;

                        let docsHtml = '';
                        if (o['Aadhaar Combined'] || o['Aadhaar Front']) docsHtml += `<span class="badge bg-primary bg-opacity-10 text-primary border border-primary me-1"><i class="bi bi-person-bounding-box me-1"></i>Aadhaar</span>`;
                        if (o['Emp Front']) docsHtml += `<span class="badge bg-info bg-opacity-10 text-info border border-info"><i class="bi bi-briefcase-fill me-1"></i>Emp ID</span>`;

                        let dateHtml = '';
                        if (o.Upload_Date && o.Upload_Date !== '') {
                            const d = parseDate(o.Upload_Date);
                            dateHtml = `<div class="text-muted fs-8 mt-2"><i class="bi bi-clock me-1"></i>Uploaded: ${d.toLocaleDateString()}</div>`;
                        }

                        const encodedData = encodeURIComponent(JSON.stringify(o));

                        html += `
                        <div class="occupant-card" onclick="viewOccupant(this, '${encodedData}')">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <h6 class="fw-bold mb-0">${o.Name}</h6>
                                ${statusBadge}
                            </div>
                            <div class="fs-7 text-muted mb-2"><i class="bi bi-telephone me-1"></i>${o.Mobile}</div>
                            <div>${docsHtml}</div>
                            ${dateHtml}
                        </div>
                    `;
                    });

                    html += `</div>`;
                });

                container.innerHTML = html;
            }

            function viewOccupant(cardEl, encodedData) {
                document.querySelectorAll('.occupant-card').forEach(c => c.classList.remove('active'));
                cardEl.classList.add('active');

                const occ = JSON.parse(decodeURIComponent(encodedData));

                document.getElementById('viewerPlaceholder').classList.add('d-none');
                document.getElementById('viewerContent').classList.remove('d-none');

                document.getElementById('previewName').innerText = occ.Name;
                document.getElementById('previewMobile').innerText = occ.Mobile;

                const badge = document.getElementById('previewStatus');
                if (occ.Status === 'Active') {
                    badge.className = 'badge bg-success';
                    badge.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i>Active';

                    const markBtn = document.getElementById('btnMarkInactive');
                    markBtn.classList.remove('d-none');
                    markBtn.onclick = () => markInactive(occ['Occupant UUID']);
                } else {
                    badge.className = 'badge bg-secondary';
                    badge.innerHTML = '<i class="bi bi-dash-circle-fill me-1"></i>Inactive';
                    document.getElementById('btnMarkInactive').classList.add('d-none');
                }

                const toggleBar = document.getElementById('documentToggles');
                toggleBar.innerHTML = '';

                let firstDocPath = null;
                let firstDocType = null;

                const addToggleButton = (label, filepath, type) => {
                    if (!filepath) return;
                    if (!firstDocPath) { firstDocPath = filepath; firstDocType = type; }

                    const btn = document.createElement('button');
                    btn.className = 'btn btn-sm btn-outline-primary rounded-pill fw-bold doc-toggle-btn';
                    btn.innerHTML = label;
                    btn.onclick = (e) => {
                        document.querySelectorAll('.doc-toggle-btn').forEach(b => b.classList.remove('active'));
                        e.target.classList.add('active');
                        renderDocument(filepath);
                    };
                    toggleBar.appendChild(btn);
                };

                if (occ['Aadhaar Combined']) {
                    addToggleButton('<i class="bi bi-file-earmark-person me-1"></i>Aadhaar (Combined)', occ['Aadhaar Combined'], 'pdf');
                } else {
                    addToggleButton('<i class="bi bi-person-bounding-box me-1"></i>Aadhaar Front', occ['Aadhaar Front'], 'img');
                    addToggleButton('<i class="bi bi-upc-scan me-1"></i>Aadhaar Back', occ['Aadhaar Back'], 'img');
                }
                addToggleButton('<i class="bi bi-briefcase me-1"></i>Emp ID Front', occ['Emp Front'], 'img');
                addToggleButton('<i class="bi bi-briefcase-fill me-1"></i>Emp ID Back', occ['Emp Back'], 'img');

                if (firstDocPath) {
                    toggleBar.firstChild.classList.add('active');
                    renderDocument(firstDocPath);
                } else {
                    document.getElementById('documentIframeContainer').innerHTML = '<div class="p-5 text-center text-muted">No documents available.</div>';
                }

                if (window.innerWidth < 992) {
                    document.getElementById('viewerContent').scrollIntoView({ behavior: 'smooth' });
                }
            }

            function renderDocument(filename) {
                const viewer = document.getElementById('documentIframeContainer');
                const relativeUrl = `../api/kyc/${filename}`;
                const ext = filename.split('.').pop().toLowerCase();

                if (ext === 'pdf') {
                    viewer.innerHTML = `
                    <object data="${relativeUrl}" type="application/pdf" width="100%" height="100%" style="display: block;">
                        <iframe src="${relativeUrl}" width="100%" height="100%" style="border: none;">
                            <div class="p-4 text-center bg-white h-100 d-flex flex-column justify-content-center align-items-center">
                                <i class="bi bi-file-earmark-pdf text-danger mb-3" style="font-size: 3rem;"></i>
                                <h5>PDF Ready</h5>
                                <a href="${relativeUrl}" target="_blank" class="btn btn-primary mt-2">Open & View Document</a>
                            </div>
                        </iframe>
                    </object>`;
                } else {
                    viewer.innerHTML = `
                    <div class="w-100 h-100 d-flex justify-content-center align-items-center p-3" style="overflow: auto; background-color: #2b2b2b;">
                        <img src="${relativeUrl}" style="max-width: 100%; max-height: 100%; object-fit: contain; box-shadow: 0 0 15px rgba(0,0,0,0.5);">
                    </div>
                `;
                }
            }

            function toggleAadhaarUpload() {
                const isSeparate = document.getElementById('typeSeparate').checked;
                const separateContainer = document.getElementById('aadhaarSeparateContainer');
                const combinedContainer = document.getElementById('aadhaarCombinedContainer');

                const aFront = document.getElementById('aadhaarFront');
                const aBack = document.getElementById('aadhaarBack');
                const aCombined = document.getElementById('aadhaarCombined');

                if (isSeparate) {
                    separateContainer.classList.remove('d-none');
                    combinedContainer.classList.add('d-none');
                    aFront.required = true;
                    aBack.required = true;
                    aCombined.required = false;
                    aCombined.value = '';
                } else {
                    separateContainer.classList.add('d-none');
                    combinedContainer.classList.remove('d-none');
                    aFront.required = false;
                    aBack.required = false;
                    aCombined.required = true;
                    aFront.value = '';
                    aBack.value = '';
                }
            }

            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const btn = document.getElementById('uploadBtn');
                const err = document.getElementById('uploadError');
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Uploading...';
                err.classList.add('d-none');

                const formData = new FormData();
                formData.append('name', document.getElementById('occName').value);
                formData.append('mobile', document.getElementById('mobile').value);

                const isSeparate = document.getElementById('typeSeparate').checked;
                if (isSeparate) {
                    formData.append('aadhaar_front', document.getElementById('aadhaarFront').files[0]);
                    formData.append('aadhaar_back', document.getElementById('aadhaarBack').files[0]);
                } else {
                    formData.append('aadhaar_combined', document.getElementById('aadhaarCombined').files[0]);
                }

                const empF = document.getElementById('empFront').files[0];
                const empB = document.getElementById('empBack').files[0];
                if (empF) formData.append('emp_front', empF);
                if (empB) formData.append('emp_back', empB);

                formData.append('pin', '{{ tenant.tenant_pin }}');

                try {
                    const res = await fetch("../api/t/{{ view_token }}/kyc", { method: "POST", body: formData });
                    if (res.ok) {
                        refreshUnlockedPage();
                    } else {
                        const result = await res.json();
                        err.innerText = result.detail || "Upload failed.";
                        err.classList.remove('d-none');
                        btn.disabled = false;
                        btn.innerText = "Upload & Save KYC";
                    }
                } catch (e) {
                    err.innerText = "Network Error.";
                    err.classList.remove('d-none');
                    btn.disabled = false;
                    btn.innerText = "Upload & Save KYC";
                }
            });

            async function markInactive(uuid) {
                Swal.fire({
                    title: 'Mark Inactive?',
                    text: "Are you sure you want to mark this occupant as moved out?",
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonColor: '#ffc107',
                    cancelButtonColor: '#6c757d',
                    confirmButtonText: 'Yes, Mark Inactive',
                    showClass: { popup: 'animate__animated animate__fadeIn animate__faster' }
                }).then(async (result) => {
                    if (result.isConfirmed) {
                        try {
                            const res = await fetch(`../api/t/{{ view_token }}/kyc/${uuid}/inactive`, { method: "PUT" });
                            if (res.ok) {
                                Swal.fire('Updated!', 'Occupant marked inactive.', 'success').then(() => refreshUnlockedPage());
                            } else {
                                Swal.fire('Failed', 'Failed to update status.', 'error');
                            }
                        } catch (e) {
                            Swal.fire('Error', 'Network Error.', 'error');
                        }
                    }
                });
            }

            function refreshUnlockedPage() {
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '';
                const pinInput = document.createElement('input');
                pinInput.type = 'hidden';
                pinInput.name = 'pin';
                pinInput.value = '{{ tenant.tenant_pin }}';
                form.appendChild(pinInput);
                document.body.appendChild(form);
                form.submit();
            }
        </script>
        {% endif %}

    </div>

</body>

</html>
```

```html
// File: templates\tenants.html
{% extends "base.html" %}

{% block title %}Tenants Directory | Rent Receipt System{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pb-3 mb-4 border-bottom">
    <h1 class="h2 mb-0 fw-bold">Tenants Directory</h1>

    <div class="d-flex align-items-center gap-3 ms-auto mt-3 mt-md-0">

        <button class="btn btn-primary rounded-pill shadow-sm px-4 fw-bold text-nowrap" onclick="openAddTenantModal()">
            <i class="bi bi-person-plus-fill me-2"></i>Add Tenant
        </button>

        <div class="input-group shadow-sm" style="max-width: 300px;">
            <span class="input-group-text bg-white border-end-0 rounded-start-pill">
                <i class="bi bi-search text-muted"></i>
            </span>
            <input type="text" class="form-control border-start-0 rounded-end-pill" id="tenantSearch"
                placeholder="Search tenants..." onkeyup="searchTenants()">
        </div>

    </div>
</div>

<div class="row g-4">
    <div class="col-12">
        <div class="card shadow-sm border-0">
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0" id="tenantsTable">
                        <thead class="table-light">
                            <tr>
                                <th class="ps-4">Tenant Info</th>
                                <th>Contact</th>
                                <th>Billing</th>
                                <th>Status</th>
                                <th class="text-end pe-4">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for t in tenants %}
                            <tr class="tenant-row">
                                <td class="ps-4 py-3">
                                    <div class="d-flex align-items-center">
                                        <div class="bg-primary-subtle text-primary rounded-circle d-flex align-items-center justify-content-center me-3"
                                            style="width: 40px; height: 40px; font-weight: bold;">
                                            T{{ t.id }}
                                        </div>
                                        <div>
                                            <a href="{{ APP_BASE(request) }}/tenant/{{ t.id }}"
                                                class="fw-bold tenant-name text-decoration-none text-primary">{{ t.name
                                                }}</a>
                                            <div class="mt-1">
                                                {% if t.room_number %}<small class="text-muted me-2">Room {{
                                                    t.room_number }}</small>{% endif %}
                                                {% if t.meter_id %}
                                                <span class="badge bg-light text-dark border"
                                                    style="font-size: 0.7rem;">
                                                    <i class="bi bi-speedometer2 text-warning me-1"></i>{{ t.meter_id }}
                                                </span>
                                                {% endif %}
                                            </div>
                                        </div>
                                    </div>
                                </td>
                                <td>
                                    <div class="fs-7 text-muted">
                                        {% if t.phone %}<div><i class="bi bi-telephone me-1"></i>{{ t.phone }}</div>{%
                                        endif %}
                                        {% if not t.phone %}-{% endif %}
                                    </div>
                                </td>
                                <td>
                                    <div class="fs-7">
                                        <div class="fw-bold text-success">₹{{ "{:,.0f}".format(t.rent) }} /mo</div>
                                        {% if t.arrears > 0 %}
                                        <div class="text-danger fw-bold mt-1 fs-8"><i
                                                class="bi bi-exclamation-circle me-1"></i>Due: ₹{{
                                            "%.2f"|format(t.arrears) }}</div>
                                        {% endif %}
                                        <div class="text-muted mt-1"><i class="bi bi-lightning-charge text-warning"></i>
                                            {{ t.previous_meter }}</div>
                                    </div>
                                </td>
                                <td>
                                    {% if t.status == 'Active' %}
                                    <span class="badge bg-success bg-gradient rounded-pill px-3 py-1 fw-normal"><i
                                            class="bi bi-check-circle me-1"></i>Active</span>
                                    {% else %}
                                    <span
                                        class="badge bg-danger bg-gradient rounded-pill px-3 py-1 fw-normal opacity-75">Inactive</span>
                                    {% endif %}
                                </td>
                                <td class="text-end pe-4">
                                    <div class="btn-group gap-1 shadow-sm rounded-pill">
                                        {% if t.status == 'Active' %}
                                        <button class="btn btn-sm btn-light border"
                                            onclick="toggleTenantStatus('{{ t.id }}', 'Inactive')"
                                            title="Mark as Inactive">
                                            <i class="bi bi-person-fill-slash text-warning"></i>
                                        </button>
                                        {% else %}
                                        <button class="btn btn-sm btn-light border"
                                            onclick="toggleTenantStatus('{{ t.id }}', 'Active')" title="Mark as Active">
                                            <i class="bi bi-person-fill-check text-success"></i>
                                        </button>
                                        {% endif %}

                                        <a href="{{ APP_BASE(request) }}/tenant/{{ t.id }}"
                                            class="btn btn-sm btn-light border" title="View Profile"><i
                                                class="bi bi-person-lines-fill text-info"></i></a>
                                        <button class="btn btn-sm btn-light border"
                                            onclick='editTenant("{{ t.dict() | tojson | safe }}")' title="Edit Tenant">
                                            <i class="bi bi-pencil text-primary"></i>
                                        </button>
                                        <button class="btn btn-sm btn-light border" onclick="deleteTenant('{{ t.id }}')"
                                            title="Deactivate / Delete Tenant">
                                            <i class="bi bi-trash text-danger"></i>
                                        </button>
                                    </div>
                                </td>
                            </tr>
                            {% endfor %}

                            <tr id="emptyState" class="{% if tenants %}d-none{% endif %}">
                                <td colspan="5" class="text-center py-5 text-muted">
                                    <i class="bi bi-people fs-1 d-block mb-3 opacity-50"></i>
                                    <h5>No Tenants Found</h5>
                                    <p class="fs-7">Register your first tenant by clicking the 'Add Tenant' button
                                        above.</p>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="modal fade" id="tenantModal" tabindex="-1" data-bs-backdrop="static">
    <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content border-0 shadow-lg rounded-4">
            <div class="modal-header bg-light border-bottom-0 py-3 rounded-top-4">
                <h5 class="modal-title fw-bold text-primary" id="formTitle">
                    <i class="bi bi-person-plus me-2" id="formIcon"></i>Add Tenant
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>

            <div class="modal-body p-4 bg-body-tertiary">
                <form id="tenantForm">
                    <input type="hidden" id="tenant_id">

                    <div class="card shadow-sm border-0 mb-3">
                        <div class="card-header bg-white border-bottom pt-3 pb-2 px-4">
                            <h6 class="fw-bold mb-0 text-secondary"><i class="bi bi-info-circle me-2"></i>General
                                Information</h6>
                        </div>
                        <div class="card-body p-4 pt-3">
                            <div class="form-floating mb-3">
                                <input type="text" class="form-control" id="name" placeholder="John Doe" required>
                                <label for="name">Tenant Name <span class="text-danger">*</span></label>
                            </div>
                            <div class="form-floating mb-3">
                                <input type="text" class="form-control" id="company" placeholder="Company">
                                <label for="company">Company Name</label>
                            </div>
                            <div class="row g-2 mb-3">
                                <div class="col-sm-6">
                                    <div class="form-floating">
                                        <input type="tel" class="form-control" id="phone" placeholder="Phone">
                                        <label for="phone">Phone</label>
                                    </div>
                                </div>
                                <div class="col-sm-6">
                                    <div class="form-floating">
                                        <input type="email" class="form-control" id="email" placeholder="Email"
                                            autocomplete="off">
                                        <label for="email">Email</label>
                                    </div>
                                </div>
                            </div>
                            <div class="form-floating mb-3">
                                <textarea class="form-control" id="address" placeholder="Address"
                                    style="height: 60px"></textarea>
                                <label for="address">Permanent Address</label>
                            </div>
                            <div class="row g-2 mb-3">
                                <div class="col-sm-6">
                                    <div class="form-floating">
                                        <input type="text" class="form-control border-primary" id="room_number"
                                            placeholder="Room">
                                        <label for="room_number" class="text-primary">Room/Unit No.</label>
                                    </div>
                                </div>
                                <div class="col-sm-6">
                                    <div class="form-floating">
                                        <input type="text" class="form-control border-warning" id="meter_id"
                                            placeholder="MTR - F - 01">
                                        <label for="meter_id" class="text-warning">Meter ID</label>
                                    </div>
                                </div>
                            </div>
                            <div class="row g-2">
                                <div class="col-sm-6">
                                    <div class="form-floating">
                                        <input type="text" class="form-control" id="occupation"
                                            placeholder="Occupation">
                                        <label for="occupation">Occupation</label>
                                    </div>
                                </div>
                                <div class="col-sm-6">
                                    <div class="form-floating">
                                        <select class="form-select" id="status">
                                            <option value="Active">Active</option>
                                            <option value="Inactive">Inactive</option>
                                        </select>
                                        <label for="status">Status</label>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="card shadow-sm border-0 mb-3">
                        <div class="card-header bg-white border-bottom pt-3 pb-2 px-4">
                            <h6 class="fw-bold mb-0 text-secondary"><i class="bi bi-receipt me-2"></i>Billing Profile
                            </h6>
                        </div>
                        <div class="card-body p-4 pt-3">
                            <div class="row g-2 mb-3">
                                <div class="col-sm-4">
                                    <div class="form-floating">
                                        <input type="number" class="form-control" id="rent" step="0.1" value="0"
                                            required>
                                        <label for="rent">Monthly Rent (₹)</label>
                                    </div>
                                </div>
                                <div class="col-sm-4">
                                    <div class="form-floating">
                                        <input type="number" class="form-control" id="water" step="0.1" value="0"
                                            required>
                                        <label for="water">Water Charge (₹)</label>
                                    </div>
                                </div>
                                <div class="col-sm-4">
                                    <div class="form-floating">
                                        <input type="number" class="form-control" id="default_tank_water_charge"
                                            step="0.1" value="0">
                                        <label for="default_tank_water_charge">Tank Water (₹)</label>
                                    </div>
                                </div>
                            </div>
                            <div class="row g-2 mb-3">
                                <div class="col-sm-6">
                                    <div class="form-floating">
                                        <input type="number" class="form-control" id="electricity_rate" step="0.1"
                                            value="0" required>
                                        <label for="electricity_rate">Elec. Rate (₹/unit)</label>
                                    </div>
                                </div>
                                <div class="col-sm-6">
                                    <div class="form-floating">
                                        <input type="number" class="form-control" id="additional_person_charge"
                                            step="0.1" value="0" required>
                                        <label for="additional_person_charge">Add. Person (₹)</label>
                                    </div>
                                </div>
                            </div>
                            <div class="form-floating">
                                <input type="number" class="form-control bg-warning-subtle" id="previous_meter"
                                    step="0.1" value="0" required>
                                <label for="previous_meter" class="text-warning-emphasis fw-bold">Previous Meter
                                    Reading</label>
                            </div>
                        </div>
                    </div>

                    <div class="card shadow-sm border-0 mb-4">
                        <div class="card-header bg-white border-bottom pt-3 pb-2 px-4">
                            <h6 class="fw-bold mb-0 text-secondary"><i class="bi bi-shield-lock me-2"></i>Security &
                                Notes</h6>
                        </div>
                        <div class="card-body p-4 pt-3">
                            <div class="row g-2 mb-3">
                                <div class="col-sm-6">
                                    <div class="form-floating">
                                        <input type="number" class="form-control" id="security_deposit" step="0.1"
                                            value="0">
                                        <label for="security_deposit">Security Deposit (₹)</label>
                                    </div>
                                </div>
                                <div class="col-sm-6">
                                    <div class="form-floating">
                                        <input type="text" class="form-control" id="tenant_pin" maxlength="4"
                                            pattern="\d{4}" value="1234">
                                        <label for="tenant_pin">Portal PIN (4 digits)</label>
                                    </div>
                                </div>
                            </div>
                            <div class="form-floating">
                                <textarea class="form-control" id="notes" placeholder="Notes"
                                    style="height: 60px"></textarea>
                                <label for="notes">Additional Notes</label>
                            </div>
                        </div>
                    </div>

                    <div class="card shadow-sm border-0 mb-3 d-none" id="historyCard">
                        <div class="card-header bg-success text-white border-bottom-0 pt-3 pb-2 px-4">
                            <h6 class="fw-bold mb-0"><i class="bi bi-clock-history me-2"></i>Billing History</h6>
                        </div>
                        <div class="card-body p-0 bg-white">
                            <div class="table-responsive" style="max-height: 250px;">
                                <table class="table table-hover table-sm align-middle mb-0 fs-7">
                                    <thead class="table-light sticky-top">
                                        <tr>
                                            <th class="ps-3">Date</th>
                                            <th>Units</th>
                                            <th>Total</th>
                                            <th class="text-end pe-3">Bill</th>
                                        </tr>
                                    </thead>
                                    <tbody id="historyTableBody">
                                    </tbody>
                                </table>
                            </div>
                            <div id="historyEmptyState" class="text-center p-4 d-none text-muted fs-7">
                                No billing history found.
                            </div>
                        </div>
                    </div>

                </form>
            </div>

            <div class="modal-footer border-top-0 pt-0 bg-body-tertiary">
                <button type="button" class="btn btn-light rounded-pill px-4 border shadow-sm"
                    data-bs-dismiss="modal">Cancel</button>
                <button type="submit" form="tenantForm" class="btn btn-primary rounded-pill px-5 fw-bold shadow-sm"
                    id="saveBtn">
                    <i class="bi bi-save me-2"></i>Save Tenant
                </button>
            </div>
        </div>
    </div>
</div>

{% endblock %}

{% block scripts %}
<script>
    let tenantModalInstance = null;

    document.addEventListener("DOMContentLoaded", () => {
        // Initialize the modal
        tenantModalInstance = new bootstrap.Modal(document.getElementById('tenantModal'));
    });

    function searchTenants() {
        const query = document.getElementById('tenantSearch').value.toLowerCase();
        const rows = document.querySelectorAll('.tenant-row');
        let visibleCount = 0;

        rows.forEach(row => {
            const name = row.querySelector('.tenant-name').innerText.toLowerCase();
            if (name.includes(query)) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });

        const emptyState = document.getElementById('emptyState');
        if (visibleCount === 0) {
            emptyState.classList.remove('d-none');
        } else {
            emptyState.classList.add('d-none');
        }
    }

    // Opens the modal for ADDING a new tenant
    function openAddTenantModal() {
        resetForm();
        document.getElementById("formTitle").innerHTML = `<i class="bi bi-person-plus me-2" id="formIcon"></i>Add Tenant`;
        document.getElementById("historyCard").classList.add("d-none");
        tenantModalInstance.show();
    }

    // Opens the modal for EDITING an existing tenant
    async function editTenant(tenant) {
        resetForm(); // clear first

        document.getElementById("tenant_id").value = tenant.id;

        // General
        document.getElementById("name").value = tenant.name || '';
        document.getElementById("company").value = tenant.company || '';
        document.getElementById("phone").value = tenant.phone || '';
        document.getElementById("email").value = tenant.email || '';
        document.getElementById("address").value = tenant.address || '';
        document.getElementById("room_number").value = tenant.room_number || '';
        document.getElementById("meter_id").value = tenant.meter_id || '';
        document.getElementById("occupation").value = tenant.occupation || '';
        document.getElementById("status").value = tenant.status || 'Active';

        // Billing
        document.getElementById("rent").value = tenant.rent || 0;
        document.getElementById("water").value = tenant.water || 0;
        document.getElementById("default_tank_water_charge").value = tenant.default_tank_water_charge || 0;
        document.getElementById("electricity_rate").value = tenant.electricity_rate || 0;
        document.getElementById("previous_meter").value = tenant.previous_meter || 0;
        document.getElementById("additional_person_charge").value = tenant.additional_person_charge || 0;

        // Security
        document.getElementById("security_deposit").value = tenant.security_deposit || 0;
        document.getElementById("tenant_pin").value = tenant.tenant_pin || '1234';
        document.getElementById("notes").value = tenant.notes || '';

        document.getElementById("formTitle").innerHTML = `<i class="bi bi-pencil-square me-2" id="formIcon"></i>Edit ${tenant.name}`;
        document.getElementById("historyCard").classList.remove("d-none");

        // Fetch Billing History for this specific tenant
        loadBillingHistory(tenant.name);

        tenantModalInstance.show();
    }

    document.getElementById("tenantForm").addEventListener("submit", async function (e) {
        e.preventDefault();

        const id = document.getElementById("tenant_id").value;
        const tenantData = {
            name: document.getElementById("name").value,
            company: document.getElementById("company").value,
            phone: document.getElementById("phone").value,
            email: document.getElementById("email").value,
            address: document.getElementById("address").value,
            room_number: document.getElementById("room_number").value,
            meter_id: document.getElementById("meter_id").value.trim(),
            occupation: document.getElementById("occupation").value,
            status: document.getElementById("status").value,
            notes: document.getElementById("notes").value,
            rent: parseFloat(document.getElementById("rent").value) || 0,
            water: parseFloat(document.getElementById("water").value) || 0,
            default_tank_water_charge: parseFloat(document.getElementById("default_tank_water_charge").value) || 0,
            electricity_rate: parseFloat(document.getElementById("electricity_rate").value) || 0,
            previous_meter: parseFloat(document.getElementById("previous_meter").value) || 0,
            additional_person_charge: parseFloat(document.getElementById("additional_person_charge").value) || 0,
            security_deposit: parseFloat(document.getElementById("security_deposit").value) || 0,
            tenant_pin: document.getElementById("tenant_pin").value || "1234"
        };

        const isEdit = !!id;
        const url = isEdit ? `api/tenants/${id}` : "api/tenants";
        const method = isEdit ? "PUT" : "POST";

        const saveBtn = document.getElementById("saveBtn");
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Saving...';

        try {
            const res = await fetch(url, {
                method: method,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(tenantData)
            });
            if (res.ok) {
                tenantModalInstance.hide();
                showToast("success", isEdit ? "Tenant Updated Successfully!" : "Tenant Added Successfully!");
                resetForm();
                await updateUI(); // Smooth refresh
            } else {
                showError("Save Failed", "Failed to save tenant information.");
                resetSaveBtn(saveBtn);
            }
        } catch (e) {
            showError("Network Error", "An error occurred while communicating with the server.");
            resetSaveBtn(saveBtn);
        }
    });

    function resetSaveBtn(btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-save me-2"></i>Save Tenant';
    }

    function resetForm() {
        document.getElementById("tenant_id").value = '';
        document.getElementById("tenantForm").reset();
        document.getElementById("meter_id").value = '';
        // Note: Title & History visibility are handled inside openAddTenantModal
    }

    async function loadBillingHistory(tenantName) {
        const tbody = document.getElementById('historyTableBody');
        const emptyState = document.getElementById('historyEmptyState');
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted"><div class="spinner-border spinner-border-sm mt-3 mb-3"></div></td></tr>';
        emptyState.classList.add('d-none');

        try {
            const res = await fetch(`api/tenant_receipts/${encodeURIComponent(tenantName)}`);
            if (res.ok) {
                const receipts = await res.json();
                tbody.innerHTML = '';

                if (receipts.length === 0) {
                    emptyState.classList.remove('d-none');
                } else {
                    receipts.forEach(r => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td class="ps-3"><div class="fw-bold">${r.Month}</div></td>
                            <td>${r.Units}</td>
                            <td class="text-success fw-bold">₹${parseFloat(r.Total).toLocaleString('en-IN')}</td>
                            <td class="text-end pe-3">
                                <button type="button" class="btn btn-sm btn-light border py-0 px-2" onclick="openGlobalPDFPreview('${r.Bill}')">
                                    <i class="bi bi-eye text-primary fs-7"></i>
                                </button>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
            }
        } catch (e) {
            tbody.innerHTML = '';
            emptyState.classList.remove('d-none');
            emptyState.innerText = "Error loading history.";
        }
    }

    function previewPDF(billNo) {
        openGlobalPDFPreview(billNo);
    }

    function deleteTenant(id) {
        Swal.fire({
            title: "Delete or Archive?",
            text: "Do you want to permanently delete this tenant AND all their receipts, or just archive them?",
            icon: "warning",
            showCancelButton: true,
            showDenyButton: true,
            confirmButtonColor: "#dc3545",
            denyButtonColor: "#ffc107",
            confirmButtonText: "Permanently Delete",
            denyButtonText: "Archive All Data",
            cancelButtonText: "Cancel"
        }).then(async (result) => {
            if (result.isConfirmed) {
                await processTenantDeletion(id, 'delete');
            } else if (result.isDenied) {
                await processTenantDeletion(id, 'archive');
            }
        });
    }

    async function processTenantDeletion(id, action) {
        try {
            const res = await fetch(`api/tenants/${id}?action=${action}`, { method: "DELETE" });
            if (res.ok) {
                showToast("success", `Tenant ${action === 'delete' ? 'Deleted' : 'Archived'} Successfully!`);
                await updateUI(); // Smooth refresh
            } else {
                showError("Failed", `Failed to ${action} tenant.`);
            }
        } catch (e) {
            showError("Network Error", "An error occurred.");
        }
    }

    async function toggleTenantStatus(id, newStatus) {
        confirmAction(
            `Mark ${newStatus}?`,
            `Are you sure you want to change this tenant's status to ${newStatus}?`,
            "Yes, Change Status",
            newStatus === 'Active' ? "#198754" : "#ffc107"
        ).then(async (result) => {
            if (result.isConfirmed) {
                try {
                    const getRes = await fetch(`api/tenants/${id}`);
                    if (!getRes.ok) throw new Error("Tenant not found");
                    const tenant = await getRes.json();

                    tenant.status = newStatus;

                    const updateRes = await fetch(`api/tenants/${id}`, {
                        method: "PUT",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(tenant)
                    });

                    if (updateRes.ok) {
                        showToast("success", `Tenant marked as ${newStatus}!`);
                        await updateUI(); // Smooth refresh
                    } else {
                        showError("Update Failed", "Failed to update tenant status.");
                    }
                } catch (e) {
                    showError("Error", "An error occurred while communicating with the server.");
                }
            }
        });
    }
</script>
{% endblock %}
```

```json
// File: domain.json
{
    "payment": {
        "allow_partial_payment": true,
        "allow_advance_payment": true,
        "carry_forward_arrears": true,
        "default_status": "PENDING",
        "statuses": [
            "PENDING",
            "PARTIAL",
            "PAID",
            "ADVANCE"
        ]
    },
    "tenant_profile": {
        "max_occupants": 20,
        "require_security_deposit": true,
        "enable_meter_reading": true,
        "history_months_visible": 12
    },
    "billing": {
        "enable_maintenance_charge": true,
        "enable_tank_water": true,
        "default_currency": "₹"
    }
}
```

```json
// File: receipt.json
{
    "layout": {
        "receipt_version": 9,
        "receipt_prefix": "T",
        "date_format": "%d %B %Y",
        "page_margin": 25,
        "line_spacing": 18
    },
    "typography": {
        "font_family_regular": "NotoSans",
        "font_family_bold": "NotoSans-Bold",
        "font_size_normal": 10,
        "font_size_header": 12,
        "font_size_title": 24
    },
    "toggles": {
        "show_bank_details": true,
        "show_signature": true,
        "show_payment_summary": true,
        "show_previous_balance": true,
        "show_qr": true
    }
}
```

```json
// File: system.json
{
    "features": {
        "tenant_portal": true,
        "public_portal": true,
        "payment_ledger": true,
        "whatsapp_sync": true,
        "kyc_upload": true,
        "archive_system": true,
        "backup_system": true
    },
    "security": {
        "tenant_pin_length": 4,
        "max_upload_size_mb": 10,
        "allowed_image_extensions": [
            ".png",
            ".jpg",
            ".jpeg",
            ".pdf"
        ]
    },
    "whatsapp": {
        "enable_bulk": true,
        "country_code": "91",
        "include_payment_summary": true,
        "include_public_link": true
    }
}
```

```json
// File: ui.json
{
  "dashboard": {
    "cards": {
      "active_tenants": true,
      "pending_amount": true,
      "arrears": true,
      "monthly_collection": true
    }
  },
  "labels": {
    "rent": "Monthly Rent",
    "water": "Water Charges",
    "electricity": "Electricity Charges",
    "arrears": "Previous Balance",
    "advance": "Advance Amount",
    "payment_received": "Payment Received"
  },
  "menu": [
    {"title": "Dashboard", "icon": "bi-house-door", "route": "home_page"},
    {"title": "New Receipt", "icon": "bi-file-earmark-plus", "route": "billing_page"},
    {"title": "Tenants", "icon": "bi-people", "route": "tenants_page"},
    {"title": "Receipt History", "icon": "bi-journal-text", "route": "history_page"},
    {"title": "Archived Receipts", "icon": "bi-archive", "route": "archive_page"},
    {"title": "Settings", "icon": "bi-gear", "route": "settings_page"}
  ]
}
```

```
// File: nginx.conf
events {
    worker_connections 1024;
}

http {
    # Add this line to allow uploads up to 20 Megabytes
    client_max_body_size 20M; 

    map $http_x_forwarded_proto $forwarded_proto {
        default $http_x_forwarded_proto;
        "" $scheme;
    }

    server {
        listen 80;
        server_name localhost;

        # Force trailing slash so the base href works perfectly
        location = /rent {
            return 301 /rent/;
        }

        # Route 1: The Rent App (Port 20081)
        location /rent/ {
            proxy_pass http://rent_app:20081/;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $forwarded_proto;
            
            # This ensures FastAPI gets the correct path headers
            proxy_set_header X-Forwarded-Prefix /rent;
        }
    }
}
```
