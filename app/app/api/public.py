# // File: app\app\api\public.py
from fastapi import APIRouter, Request, Response, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks

from app.core.routes_manifest import Names, Routes
from app.core.routes_manifest_tenant import TenantRoutes, TenantNames

from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder

from typing import Optional
from datetime import datetime
from app.core.paths import KYC_DIR
from app.models.tenant import Tenant
from app.models.receipt import BillRequest, PaymentStatusUpdate
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
    get_dashboard_stats, archive_bill, restore_bill, update_paymentStatus
)
from app.services.backup_service import create_full_backup

router = APIRouter()


from app.authentication.tenant.middleware import get_current_tenant

# @router.get("/t/api/{viewToken}/profile", name=TenantNames.TENANTPROFILEGET)
@router.get(TenantRoutes.TENANTAPIPROFILEGET, name=TenantNames.TENANTPROFILEGET)
async def public_tenant_profile_json(tenantId: int, viewToken: str, request: Request):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "viewToken", "") == viewToken), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")
        
    unlocked = False
    token = request.cookies.get("tenant_access_token")
    if token:
        from app.authentication.tenant.jwt import decode_tenant_access_token
        from app.authentication.tenant.sessions import get_tenant_session_db
        try:
            payload = decode_tenant_access_token(token)
            if payload.get("role") == "tenant" and int(payload.get("tenantId") or payload.get("sub")) == tenant.id:
                session_id = payload.get("sid")
                if get_tenant_session_db(session_id):
                    unlocked = True
        except Exception:
            pass
            
    base_info = {
        "id": tenant.id,
        "name": getattr(tenant, "name", ""),
        "viewToken": viewToken,
        "unlocked": unlocked
    }
    
    if unlocked:
        receipts = get_all_receipts()
        tenant_receipts = [
            r for r in receipts
            if int(r.get("TenantId", 0) or 0) == tenant.id
            and (r.get("Status") or "").upper() != "ARCHIVED"
        ]
        tenant_receipts.reverse()
        tenant_receipts = tenant_receipts[:config.get("system.limits.public_history_months", 12)]
        occupants = get_occupants(tenant.id)
        
        return {
            "tenant": base_info,
            "receipts": tenant_receipts,
            "occupants": occupants
        }
    else:
        return {
            "tenant": base_info
        }

@router.get(TenantRoutes.TENANTAPIAUTHPUBLICKEY, name=TenantNames.TENANTPUBLICKEY)
async def get_public_key():
    from app.encryption import get_public_key_pem
    return {"publicKey": get_public_key_pem()}


from pydantic import BaseModel

class EncryptedLoginRequest(BaseModel):
    encryptedKey: str      # Base64-encoded RSA-encrypted AES key
    encryptedData: str     # Base64-encoded AES-GCM encrypted payload
    nonce: str             # Base64-encoded nonce

@router.post(TenantRoutes.TENANTAPIAUTHLOGIN, name=TenantNames.TENANTLOGIN)
async def public_tenant_login(tenantId: int, viewToken: str, request: Request, response: Response, login_req: EncryptedLoginRequest):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "viewToken", "") == viewToken), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")

    from app.encryption import decrypt_payload
    try:
        decrypted = decrypt_payload(login_req.encryptedKey, login_req.encryptedData, login_req.nonce)
        pin = decrypted.get("pin", "")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid encrypted payload")

    if getattr(tenant, "tenantPin", None) != pin:
        from app.authentication.common.utils import verify_pin
        if not verify_pin(pin, getattr(tenant, "tenantPin", "")):
            raise HTTPException(status_code=401, detail="Invalid PIN")

    from app.authentication.tenant.sessions import create_tenant_session
    from app.authentication.tenant.jwt import create_tenant_access_token
    from app.authentication.tenant.cookies import set_tenant_auth_cookies

    session_id, refresh_token = create_tenant_session(tenant.id, request, remember_me=True)
    access_token = create_tenant_access_token(tenant.id, session_id)
    
    set_tenant_auth_cookies(response, access_token, refresh_token, True, request)
    
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return {
        "status": "success", 
        "message": "Unlocked successfully",
        "tenant": {
            "id": tenant.id,
            "name": getattr(tenant, "name", ""),
            "unlocked": True
        }
    }

@router.get(TenantRoutes.TENANTAPIPDFVIEW, name=TenantNames.TENANTPDFVIEW)
async def tenant_view_pdf(tenantId: int, viewToken: str, billNo: str, principal = Depends(get_current_tenant)):
    receipt = get_receipt(tenantId, billNo)
    if not receipt:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    # Verify tenant owns this receipt by ID (name-based check breaks after a rename)
    tenants = load_tenants()
    tenant = next((t for t in tenants if t.id == principal.id), None)
    if not tenant or int(receipt.get("TenantId", 0) or 0) != tenant.id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    from app.services.pdf_service import generate_professional_pdf
    landlord_conf = config.get("landlord", {})
    
    pdf_stream = generate_professional_pdf(receipt, landlord_conf)
    
    response = StreamingResponse(iter([pdf_stream.getvalue()]), media_type='application/pdf')
    response.headers["Content-Disposition"] = f"inline; filename=receipt_{billNo}.pdf"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@router.get(TenantRoutes.TENANTAPIPDFDOWNLOAD, name=TenantNames.TENANTPDFDOWNLOAD)
async def tenant_download_pdf(tenantId: int, viewToken: str, billNo: str, principal = Depends(get_current_tenant)):
    receipt = get_receipt(tenantId, billNo)
    if not receipt:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    # Verify tenant owns this receipt by ID (name-based check breaks after a rename)
    tenants = load_tenants()
    tenant = next((t for t in tenants if t.id == principal.id), None)
    if not tenant or int(receipt.get("TenantId", 0) or 0) != tenant.id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    tenantName = receipt.get("Tenant", "Unknown").replace(" ", "_")
    try:
        formatted_date = datetime.strptime(receipt.get("Date", ""), "%d %B %Y").strftime("%Y%m%d")
    except:
        formatted_date = receipt.get("Date", "").replace(" ", "")
    custom_filename = f"{tenantName}_{formatted_date}_{billNo}.pdf"
        
    from app.services.pdf_service import generate_professional_pdf
    landlord_conf = config.get("landlord", {})
    
    pdf_stream = generate_professional_pdf(receipt, landlord_conf)
    
    response = StreamingResponse(iter([pdf_stream.getvalue()]), media_type='application/pdf')
    response.headers["Content-Disposition"] = f'attachment; filename="{custom_filename}"'
    return response

@router.post(TenantRoutes.TENANTAPIKYCUPLOAD, name=TenantNames.TENANTKYCUPLOAD)
async def public_tenant_kyc_upload(
    tenantId: int,
    viewToken: str,
    name: str = Form(...),
    mobile: str = Form(""),
    address: str = Form(""),
    residentSince: str = Form(""),
    aadhaarfront: Optional[UploadFile] = File(None),
    aadhaarback: Optional[UploadFile] = File(None),
    aadhaarcombined: Optional[UploadFile] = File(None),
    empfront: Optional[UploadFile] = File(None),
    empback: Optional[UploadFile] = File(None),
    principal = Depends(get_current_tenant)
):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "viewToken", "") == viewToken), None)
    if not tenant or tenant.id != principal.id:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")

    # Validate residentSince date if provided
    if residentSince:
        try:
            from datetime import date
            parsed_date = date.fromisoformat(residentSince)
            if parsed_date > date.today():
                raise HTTPException(status_code=400, detail="Residing-since date cannot be in the future.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Residing-since date must use YYYY-MM-DD format.")

    # Need either combined OR both front+back (check filename to exclude empty browser inputs)
    has_combined = bool(aadhaarcombined and aadhaarcombined.filename)
    has_both = bool(
        (aadhaarfront and aadhaarfront.filename) and
        (aadhaarback and aadhaarback.filename)
    )
    if not has_combined and not has_both:
        raise HTTPException(
            status_code=400,
            detail="Please upload either a Combined Aadhaar file, or both Front and Back files."
        )

    occupantUuid = str(uuid.uuid4())

    async def save_kyc_img(file_obj: UploadFile, side: str):
        if not file_obj or not file_obj.filename:
            return ""
        ext = file_obj.filename.split('.')[-1] if '.' in file_obj.filename else 'jpg'
        filename = f"{tenant.id}_{occupantUuid}_{side}.{ext}"
        os.makedirs(KYC_DIR, exist_ok=True)
        file_path = os.path.join(KYC_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(await file_obj.read())
        return filename

    af_path = await save_kyc_img(aadhaarfront, "aadhaar_front") if has_both else ""
    ab_path = await save_kyc_img(aadhaarback, "aadhaar_back") if has_both else ""
    ac_path = await save_kyc_img(aadhaarcombined, "aadhaar_combined") if has_combined else ""
    ef_path = await save_kyc_img(empfront, "emp_front") if (empfront and empfront.filename) else ""
    eb_path = await save_kyc_img(empback, "emp_back") if (empback and empback.filename) else ""

    now = datetime.now()
    save_occupant(tenant.id, {
        "uuid": occupantUuid,
        "name": name.strip(),
        "mobile": mobile.strip(),
        "address": address.strip(),
        "residentSince": residentSince,
        "status": "Active",
        "aadhaar_front": af_path,
        "aadhaar_back": ab_path,
        "aadhaar_combined": ac_path,
        "emp_front": ef_path,
        "emp_back": eb_path,
        "uploaddate": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "uploadmonth": now.strftime("%B %Y"),
    })

    return {"status": "success", "message": "KYC uploaded successfully"}

@router.put(TenantRoutes.TENANTAPIKYCMARKINACTIVE, name=TenantNames.TENANTKYCMARKINACTIVE)
async def public_tenant_kyc_mark_inactive(tenantId: int, viewToken: str, occupantUuid: str, principal = Depends(get_current_tenant)):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "viewToken", "") == viewToken), None)
    if not tenant or tenant.id != principal.id:
        raise HTTPException(status_code=404, detail="Invalid link.")
        
    from app.services.tenant_service import update_occupant_status
    update_occupant_status(occupantUuid, "Inactive")
    return {"status": "success"}

@router.delete(TenantRoutes.TENANTAPIKYCDELETE, name=TenantNames.TENANTKYCDELETE)
async def public_tenant_kyc_delete(tenantId: int, viewToken: str, occupantUuid: str, principal = Depends(get_current_tenant)):
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "viewToken", "") == viewToken), None)
    if not tenant or tenant.id != principal.id:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")

    occupants = get_occupants(tenant.id)
    target = next((o for o in occupants if o.get("occupantUuid") == occupantUuid or o.get("Occupant UUID") == occupantUuid), None)

    if target:
        doc_keys = ["aadhaarfront", "aadhaarback", "aadhaarcombined", "empfront", "empback"]
        for key in doc_keys:
            filename = target.get(key)
            if filename:
                file_path = os.path.join(KYC_DIR, filename)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
            
    delete_occupant(occupantUuid)
    return {"status": "success"}

@router.get(TenantRoutes.TENANTAPIKYCGETFILE, name=TenantNames.TENANTKYCGETFILE)
async def tenant_public_get_kyc_file(tenantId: int, viewToken: str, filename: str, principal = Depends(get_current_tenant)):
    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = os.path.join(KYC_DIR, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    if not safe_filename.startswith(f"{principal.id}_"):
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access this file")
    
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "application/octet-stream"
        
    headers = {
        "Content-Disposition": f'inline; filename="{safe_filename}"'
    }
    return FileResponse(file_path, media_type=mime_type, headers=headers)