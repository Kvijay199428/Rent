from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from app.core.routes import Names
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder
from app.core.routes import Paths, Names, Prefixes
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
from app.services.backup_service import create_full_backup

router = APIRouter()


@router.get("/api/tenants", name=Names.API_GET_TENANTS)
async def api_get_tenants():
    return load_tenants()

@router.get("/api/tenants/{tenantid}", name=Names.API_GET_TENANT)
async def api_get_tenant(tenantid: int):
    tenants = load_tenants()
    tenant = next((t for t in tenants if t.id == tenantid), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

@router.get("/api/tenantreceipts/{tenantname}", name=Names.API_GET_TENANT_RECEIPTS + "_legacy")
@router.get("/api/tenant_receipts/{tenantname}", name=Names.API_GET_TENANT_RECEIPTS)
async def api_get_tenant_receipts(tenantname: str):
    receipts = get_all_receipts()
    target = tenantname.strip().casefold()
    tenant_receipts = [r for r in receipts if r.get("Tenant", "").strip().casefold() == target]
    tenant_receipts.reverse()
    return tenant_receipts

@router.post("/api/tenants", name=Names.API_ADD_TENANT)
async def api_add_tenant(t: Tenant, request: Request, background_tasks: BackgroundTasks):
    from app.authentication.common.utils import hash_pin, validate_tenant_pin
    from app.authentication.common.pin_vault import encrypt_admin_view_pin
    from app.core.db import get_conn
    from datetime import datetime
    
    background_tasks.add_task(create_full_backup, tag="add_tenant")
    
    # Strictly validate 4-digit PIN on creation
    validate_tenant_pin(t.tenant_pin)
    
    plain_pin = str(t.tenant_pin)
    hashed_pin = hash_pin(plain_pin)
    encrypted_pin = encrypt_admin_view_pin(plain_pin)
    
    t.tenant_pin = hashed_pin
        
    tenant_id = add_tenant(t)
    t.id = tenant_id
    
    # Add to PIN history
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("INSERT INTO tenant_pin_history (tenant_id, pin_hash, changed_at) VALUES (?, ?, ?)", (tenant_id, hashed_pin, now))
        conn.execute("INSERT OR REPLACE INTO tenant_pin_admin_store (tenant_id, encrypted_pin, updated_at) VALUES (?, ?, ?)", (tenant_id, encrypted_pin, now))
        conn.commit()
    
    response_tenant = t.dict()
    response_tenant.pop("tenant_pin", None)
    
    return {"status": "success", "tenant": response_tenant}

@router.put("/api/tenants/{tenantid}", name=Names.API_UPDATE_TENANT)
async def api_update_tenant(tenantid: int, t: Tenant, background_tasks: BackgroundTasks):
    t.id = tenantid
    background_tasks.add_task(create_full_backup, tag="update_tenant")
    
    existing = load_tenants()
    existing_t = next((x for x in existing if x.id == tenantid), None)
    if not existing_t:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    # The general update endpoint does NOT change the PIN.
    # We forcefully retain the existing PIN hash.
    t.tenant_pin = existing_t.tenant_pin
            
    update_tenant(t)
    
    response_tenant = t.dict()
    response_tenant.pop("tenant_pin", None)
    
    return {"status": "success", "tenant": response_tenant}

from pydantic import BaseModel

class ChangePinRequest(BaseModel):
    pin: str
    logout_all: bool = True

@router.post("/api/tenants/{tenantid}/change-pin", name="change_tenant_pin")
async def api_change_tenant_pin(tenantid: int, payload: ChangePinRequest, request: Request, background_tasks: BackgroundTasks):
    from app.authentication.common.utils import hash_pin, validate_tenant_pin, verify_pin
    from app.authentication.common.pin_vault import encrypt_admin_view_pin
    from app.authentication.tenant.sessions import revoke_all_tenant_sessions
    from app.database.auth_repository import log_audit
    from app.core.db import get_conn
    from datetime import datetime
    
    validate_tenant_pin(payload.pin)
    
    # Prevent immediate reuse (last 5 PINs)
    with get_conn() as conn:
        history = conn.execute("SELECT pin_hash FROM tenant_pin_history WHERE tenant_id = ? ORDER BY id DESC LIMIT 5", (tenantid,)).fetchall()
        for row in history:
            if verify_pin(payload.pin, row["pin_hash"]):
                raise HTTPException(status_code=400, detail="Cannot reuse a recently used PIN.")
                
    new_hash = hash_pin(payload.pin)
    encrypted_pin = encrypt_admin_view_pin(payload.pin)
    
    existing = load_tenants()
    existing_t = next((x for x in existing if x.id == tenantid), None)
    if not existing_t:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    existing_t.tenant_pin = new_hash
    update_tenant(existing_t)
    
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("INSERT INTO tenant_pin_history (tenant_id, pin_hash, changed_at) VALUES (?, ?, ?)", (tenantid, new_hash, now))
        conn.execute("INSERT OR REPLACE INTO tenant_pin_admin_store (tenant_id, encrypted_pin, updated_at) VALUES (?, ?, ?)", (tenantid, encrypted_pin, now))
        conn.commit()
    
    if payload.logout_all:
        revoke_all_tenant_sessions(tenantid)
        
    ip = request.client.host if request.client else "Unknown IP"
    log_audit(tenantid, "Tenant PIN Changed", ip)
    
    background_tasks.add_task(create_full_backup, tag="change_pin")
    
    return {"status": "success", "message": "PIN changed successfully."}

@router.get("/api/tenants/{tenantid}/reveal-pin", name="admin_reveal_tenant_pin")
async def admin_reveal_tenant_pin(
    tenantid: int,
):
    from app.authentication.common.pin_vault import decrypt_admin_view_pin
    from app.core.db import get_conn
    
    with get_conn() as conn:
        row = conn.execute(
            "SELECT encrypted_pin, updated_at FROM tenant_pin_admin_store WHERE tenant_id = ?",
            (tenantid,)
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="PIN not available for this tenant yet. Reset the PIN once to enable admin reveal."
        )

    return {
        "status": "success",
        "pin": decrypt_admin_view_pin(row["encrypted_pin"]),
        "updated_at": row["updated_at"]
    }

@router.delete("/api/tenants/{tenantid}", name=Names.API_DELETE_TENANT)
async def api_delete_tenant(
    tenantid: int,
    background_tasks: BackgroundTasks,
    action: str = "archive",
):
    action = (action or "archive").strip().lower()

    if action not in {"archive", "delete", "hard", "inactive"}:
        raise HTTPException(status_code=400, detail="Invalid tenant action.")

    tenants = load_tenants()
    tenant = next((t for t in tenants if t.id == tenantid), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    try:
        background_tasks.add_task(create_full_backup, tag=f"{action}_tenant")
        result = delete_tenant(tenantid, action)
        return {"status": "success", "action": action, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tenant {action} failed: {str(e)}")

from app.core.paths import KYC_DIR
import mimetypes

@router.put("/api/kyc/{tenantid}/{occupant_uuid}/inactive", name="admin_tenant_kyc_mark_inactive")
async def admin_tenant_kyc_mark_inactive(tenantid: int, occupant_uuid: str):
    from app.services.tenant_service import update_occupant_status
    update_occupant_status(occupant_uuid, "Inactive")
    return {"status": "success"}

@router.delete("/api/kyc/{tenantid}/{occupant_uuid}", name="admin_tenant_kyc_delete")
async def admin_tenant_kyc_delete(tenantid: int, occupant_uuid: str):
    occupants = get_occupants(tenantid)
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
async def admin_get_kyc_file(filename: str):
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

