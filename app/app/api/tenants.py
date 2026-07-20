# app\app\api\tenants.py

from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder

from app.core.routes_manifest import Routes, Names

from typing import Optional, List
from app.models.tenant import Tenant
from app.models.receipt import BillRequest, PaymentStatusUpdate
import os, io, re, json, datetime
import shutil, logging
from pydantic import BaseModel


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


@router.get(Routes.ADMINAPITENANTSLIST, name=Names.APIGETTENANTS)
async def api_get_tenants():
    return load_tenants(include_archived=False)

@router.get(Routes.ADMINAPITENANTSUPDATE, name=Names.APIGETTENANT)
async def api_get_tenant(tenantId: int):
    tenants = load_tenants()
    tenant = next((t for t in tenants if t.id == tenantId), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

@router.get(Routes.ADMINAPITENANTSRECEIPTS, name=Names.APIGETTENANTRECEIPTS)
async def api_get_tenant_receipts(tenantId: int):
    # Use include_archived=True so admin can view receipts of archived tenants
    tenants = load_tenants(include_archived=True)
    tenant = next((t for t in tenants if t.id == tenantId), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # ID-based lookup only — name is display-only and must never be used for ownership
    receipts = get_all_receipts(include_archived_tenants=True)
    tenant_receipts = [r for r in receipts if int(r.get("TenantId", 0) or 0) == tenantId]
    tenant_receipts.reverse()
    return tenant_receipts

@router.post(Routes.ADMINAPITENANTSLIST, name=Names.APIADDTENANT)
async def api_add_tenant(t: Tenant, request: Request, background_tasks: BackgroundTasks):
    from app.authentication.common.utils import hash_pin, validate_tenantPin
    from app.authentication.common.pin_vault import encrypt_admin_view_pin
    from app.core.db import get_conn
    from datetime import datetime
    
    background_tasks.add_task(create_full_backup, tag="add_tenant")
    
    # Strictly validate 4-digit PIN on creation
    validate_tenantPin(t.tenantPin)
    
    plain_pin = str(t.tenantPin)
    hashed_pin = hash_pin(plain_pin)
    encrypted_pin = encrypt_admin_view_pin(plain_pin)
    
    t.tenantPin = hashed_pin
        
    tenantId = add_tenant(t)
    t.id = tenantId
    
    # Add to PIN history
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("INSERT INTO tenantPin_history (tenantId, pin_hash, changed_at) VALUES (?, ?, ?)", (tenantId, hashed_pin, now))
        conn.execute("INSERT OR REPLACE INTO tenantPin_admin_store (tenantId, encrypted_pin, updated_at) VALUES (?, ?, ?)", (tenantId, encrypted_pin, now))
        conn.commit()
    
    response_tenant = t.dict()
    response_tenant.pop("tenantPin", None)
    
    return {"status": "success", "tenant": response_tenant}

@router.put(Routes.ADMINAPITENANTSUPDATE, name=Names.APIUPDATETENANT)
async def api_update_tenant(tenantId: int, t: Tenant, background_tasks: BackgroundTasks):
    t.id = tenantId
    background_tasks.add_task(create_full_backup, tag="update_tenant")
    
    existing = load_tenants()
    existing_t = next((x for x in existing if x.id == tenantId), None)
    if not existing_t:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    # The general update endpoint does NOT change the PIN.
    # We forcefully retain the existing PIN hash.
    t.tenantPin = existing_t.tenantPin
            
    update_tenant(t)
    
    response_tenant = t.dict()
    response_tenant.pop("tenantPin", None)
    
    return {"status": "success", "tenant": response_tenant}

from pydantic import BaseModel

class ChangePinRequest(BaseModel):
    pin: str
    logout_all: bool = True

@router.post(Routes.ADMINAPITENANTSCHANGEPIN, name=Names.CHANGETENANTPIN)
async def api_change_tenantPin(tenantId: int, payload: ChangePinRequest, request: Request, background_tasks: BackgroundTasks):
    from app.authentication.common.utils import hash_pin, validate_tenantPin, verify_pin
    from app.authentication.common.pin_vault import encrypt_admin_view_pin
    from app.authentication.tenant.sessions import revoke_all_tenant_sessions
    from app.database.auth_repository import log_audit
    from app.core.db import get_conn
    from datetime import datetime
    
    validate_tenantPin(payload.pin)
    
    # Prevent immediate reuse (last 5 PINs)
    with get_conn() as conn:
        history = conn.execute("SELECT pin_hash FROM tenantPin_history WHERE tenantId = ? ORDER BY id DESC LIMIT 5", (tenantId,)).fetchall()
        for row in history:
            if verify_pin(payload.pin, row["pin_hash"]):
                raise HTTPException(status_code=400, detail="Cannot reuse a recently used PIN.")
                
    new_hash = hash_pin(payload.pin)
    encrypted_pin = encrypt_admin_view_pin(payload.pin)
    
    existing = load_tenants()
    existing_t = next((x for x in existing if x.id == tenantId), None)
    if not existing_t:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    existing_t.tenantPin = new_hash
    update_tenant(existing_t)
    
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("INSERT INTO tenantPin_history (tenantId, pin_hash, changed_at) VALUES (?, ?, ?)", (tenantId, new_hash, now))
        conn.execute("INSERT OR REPLACE INTO tenantPin_admin_store (tenantId, encrypted_pin, updated_at) VALUES (?, ?, ?)", (tenantId, encrypted_pin, now))
        conn.commit()
    
    if payload.logout_all:
        revoke_all_tenant_sessions(tenantId)
        
    ip = request.client.host if request.client else "Unknown IP"
    log_audit(tenantId, "Tenant PIN Changed", ip)
    
    background_tasks.add_task(create_full_backup, tag="change_pin")
    
    return {"status": "success", "message": "PIN changed successfully."}

@router.get(Routes.ADMINAPITENANTSREVEALPIN, name=Names.ADMINREVEALPIN)
async def admin_reveal_tenantPin(
    tenantId: int,  # CHANGED: tenantId → tenantId
):
    from app.authentication.common.pin_vault import decrypt_admin_view_pin
    from app.core.db import get_conn
    
    with get_conn() as conn:
        row = conn.execute(
            "SELECT encrypted_pin, updated_at FROM tenantPin_admin_store WHERE tenantId = ?",
            (tenantId,)  # CHANGED: tenantId → tenantId
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

@router.delete(Routes.ADMINAPITENANTSUPDATE, name=Names.APIDELETETENANT)
async def api_delete_tenant(
    tenantId: int,
    background_tasks: BackgroundTasks,
    action: str = "archive",
):
    action = (action or "archive").strip().lower()

    # ── New: permanent-with-recovery action ──────────────────────────────────
    if action == "permanent-with-recovery":
        from app.services.tenant_recovery_service import (
            create_tenant_recovery_snapshot,
            permanently_delete_tenant_data,
        )

        tenants = load_tenants(include_archived=True)
        tenant = next((t for t in tenants if t.id == tenantId), None)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found.")

        if (tenant.status or "").strip().lower() != "archived":
            raise HTTPException(
                status_code=409,
                detail="Only archived tenants can be permanently deleted. Archive the tenant first.",
            )

        try:
            # Step 1: Create recovery snapshot SYNCHRONOUSLY (must complete before deletion)
            snapshot = create_tenant_recovery_snapshot(
                tenant_id=tenantId,
                admin_id=None,  # admin principal not injected here; safe to omit
            )
            # Step 2: Permanently delete all live data
            permanently_delete_tenant_data(tenantId)

            return {
                "status": "success",
                "action": "permanent-with-recovery",
                "snapshotId": snapshot["id"],
                "expiresAt": snapshot["expires_at"],
                "tenantId": tenantId,
                "tenantName": snapshot["tenant_name"],
            }
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Permanent deletion failed; no live data was deleted: {exc}",
            )

    # ── Existing actions ─────────────────────────────────────────────────────
    if action not in {"archive", "delete", "hard", "inactive"}:
        raise HTTPException(status_code=400, detail="Invalid tenant action.")

    # Must include archived tenants so an already-archived tenant is not missed
    tenants = load_tenants(include_archived=True)
    tenant = next((t for t in tenants if t.id == tenantId), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    try:
        background_tasks.add_task(create_full_backup, tag=f"{action}_tenant")
        result = delete_tenant(tenantId, action)
        return {"status": "success", "action": action, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tenant {action} failed: {str(e)}")


# ── Tenant Recovery Snapshot Endpoints ───────────────────────────────────────

@router.get(Routes.ADMINAPITENANTSNAPSHOTS, name=Names.APILISTRECOVERYSNAPSHOTS)
async def api_list_recovery_snapshots():
    """List all tenant recovery snapshots (runs expiry purge first)."""
    from app.services.tenant_recovery_service import get_tenant_recovery_snapshots
    snapshots = get_tenant_recovery_snapshots()
    return {"status": "success", "snapshots": snapshots}


@router.get(Routes.ADMINAPITENANTSNAPSHOT_PREVIEW, name=Names.APIRECOVERYSNAPSHOT_PREVIEW)
async def api_recovery_snapshot_preview(snapshotId: str):
    """Return a conflict preview for restoring a tenant recovery snapshot."""
    from app.services.tenant_recovery_service import get_snapshot_restore_preview
    try:
        preview = get_snapshot_restore_preview(snapshotId)
        return {"status": "success", **preview}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {e}")


class RestoreSnapshotRequest(BaseModel):
    force_new_id: bool = False


@router.post(Routes.ADMINAPITENANTSNAPSHOT_RESTORE, name=Names.APIRECOVERYSNAPSHOT_RESTORE)
async def api_restore_recovery_snapshot(snapshotId: str, payload: RestoreSnapshotRequest = RestoreSnapshotRequest()):
    """Restore a tenant from a recovery snapshot."""
    from app.services.tenant_recovery_service import restore_tenant_from_snapshot
    try:
        result = restore_tenant_from_snapshot(snapshotId, force_new_id=payload.force_new_id)
        return {"status": "success", **result}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {e}")


@router.post(Routes.ADMINAPITENANTSRESTORE, name=Names.APIRESTORETENANT)
async def api_restore_tenant(
    tenantId: int,
    background_tasks: BackgroundTasks,
):
    # Archived tenants must be visible for the existence check — this is why restore
    # cannot share the normal pre-check that excludes archived tenants.
    tenants = load_tenants(include_archived=True)
    tenant = next((t for t in tenants if t.id == tenantId), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    try:
        background_tasks.add_task(create_full_backup, tag="restore_tenant")
        result = delete_tenant(tenantId, "restore")
        return {"status": "success", "action": "restore", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tenant restore failed: {str(e)}")

from app.core.paths import KYC_DIR
import mimetypes

@router.get(Routes.ADMINAPIOCCUPANTSLIST, name=Names.APIGETOCCUPANTS)
async def admin_get_occupants(tenantId: int):
    occupants = get_occupants(tenantId)
    return {"occupants": occupants}

@router.post(Routes.ADMINAPIOCCUPANTSCREATE, name=Names.APICREATEOCCUPANT)
async def admin_post_occupants(
    tenantId: int,
    name: str = Form(...),
    mobile: str = Form(""),
    address: str = Form(""),
    residentSince: str = Form(""),
    aadhaarfront: Optional[UploadFile] = File(None),
    aadhaarback: Optional[UploadFile] = File(None),
    aadhaarcombined: Optional[UploadFile] = File(None),
    empfront: Optional[UploadFile] = File(None),
    empback: Optional[UploadFile] = File(None),
):
    import uuid
    from app.core.paths import KYC_DIR
    import os
    import shutil

    # Validate Aadhaar: need combined OR both front+back
    has_combined = aadhaarcombined and aadhaarcombined.filename
    has_both = (aadhaarfront and aadhaarfront.filename) and (aadhaarback and aadhaarback.filename)
    if not has_combined and not has_both:
        raise HTTPException(
            status_code=400,
            detail="Upload one combined Aadhaar document, or both front and back.",
        )

    # Validate residentSince date if provided
    if residentSince:
        try:
            from datetime import date
            parsed = date.fromisoformat(residentSince)
            if parsed > date.today():
                raise HTTPException(status_code=400, detail="Residing since date cannot be in the future.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid residentSince date format. Use YYYY-MM-DD.")

    occ_uuid = str(uuid.uuid4())
    prefix = f"{tenantId}_{occ_uuid}"
    doc_urls: dict = {}

    async def _save(upload: UploadFile, field: str):
        if not upload or not upload.filename:
            return
        ext = os.path.splitext(upload.filename)[-1].lower()
        safe_name = f"{prefix}_{field}{ext}"
        file_path = os.path.join(KYC_DIR, safe_name)
        with open(file_path, "wb") as buf:
            shutil.copyfileobj(upload.file, buf)
        doc_urls[field] = safe_name

    await _save(aadhaarcombined, "aadhaar_combined")
    await _save(aadhaarfront,    "aadhaar_front")
    await _save(aadhaarback,     "aadhaar_back")
    await _save(empfront,        "emp_front")
    await _save(empback,         "emp_back")

    from datetime import datetime
    now = datetime.utcnow()
    occ_data = {
        "occupantUuid":    occ_uuid,
        "name":            name,
        "mobile":          mobile,
        "address":         address,
        "residentSince":   residentSince,
        "status":          "Active",
        "aadhaar_combined": doc_urls.get("aadhaar_combined", ""),
        "aadhaar_front":   doc_urls.get("aadhaar_front", ""),
        "aadhaar_back":    doc_urls.get("aadhaar_back", ""),
        "emp_front":       doc_urls.get("emp_front", ""),
        "emp_back":        doc_urls.get("emp_back", ""),
        "uploaddate":      now.strftime("%d %b %Y"),
        "uploadmonth":     now.strftime("%B %Y"),
    }
    save_occupant(tenantId, occ_data)
    return {"status": "success", "occupantUuid": occ_uuid}

@router.put(Routes.ADMINAPIOCCUPANTSMARKINACTIVE, name=Names.APIMARKOCCUPANTINACTIVE)
async def admin_tenant_kyc_mark_inactive(tenantId: int, occupantUuid: str):
    from app.services.tenant_service import update_occupant_status
    update_occupant_status(occupantUuid, "Inactive")
    return {"status": "success"}

@router.delete(Routes.ADMINAPIOCCUPANTSDELETE, name=Names.APIDELETEOCCUPANT)
async def admin_tenant_kyc_delete(tenantId: int, occupantUuid: str):
    tenantId = tenantId
    occupantUuid = occupantUuid
    occupants = get_occupants(tenantId)
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

@router.get(Routes.ADMINAPIOCCUPANTSGETFILE, name=Names.APIGETOCCUPANTFILE)
async def admin_get_kyc_file(tenantId: int, filename: str):
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

