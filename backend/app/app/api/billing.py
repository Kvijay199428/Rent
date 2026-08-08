# // File: app\app\api\billing.py
from app.core.routes_manifest_landlord import LandlordRoutes as Routes, LandlordNames as Names
from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder

from typing import Optional
from app.models.tenant import Tenant
from app.models.receipt import BillRequest, PaymentStatusUpdate
import os, io, re, json, datetime
import shutil, logging


async def _broadcast(channel: str, event: dict):
    try:
        from app.core.websocket_manager import sync_manager
        await sync_manager.broadcast(channel, event)
    except Exception:
        pass

from app.services.tenant_service import (
    load_tenants, add_tenant, update_tenant, delete_tenant,
    get_occupants, save_occupant, delete_occupant,
    get_tenant, tenant_belongs_to_landlord
)
from app.services.billing_service import (
    get_all_receipts, get_receipt, get_billing_months,
    calculate_charges, create_bill, update_bill, delete_bill,
    get_dashboard_stats, archive_bill, restore_bill, update_paymentStatus
)
from app.services.backup_service import create_full_backup
from app.authentication.landlord.middleware import get_current_landlord_api_strict

router = APIRouter()


def _require_active_tenant(tenantId: int, landlord_id=None):
    """Block bill operations for tenants that are not Active or not owned by the landlord."""
    tenant = get_tenant(tenantId, landlord_id=landlord_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")
    if (tenant.status or "").strip().lower() != "active":
        raise HTTPException(
            status_code=403,
            detail=f"Cannot generate or edit bills for a tenant with status '{tenant.status}'.",
        )


@router.get(Routes.LANDLORDAPIBILLINGFILTER, name=Names.APIFILTERBILLS)
async def api_filter_bills(landlordUuid: str, status: str = "active", principal=Depends(get_current_landlord_api_strict)):
    receipts = get_all_receipts(include_archived_tenants=False, landlord_id=principal.landlord_id)
    if status == "pending":
        filtered = [
            r for r in receipts
            if r.get("paymentStatus", "PENDING") in ["PENDING", "PARTIAL"]
            and r.get("Status") != "ARCHIVED"
        ]
    elif status == "paid":
        filtered = [
            r for r in receipts
            if r.get("paymentStatus", "PENDING") in ["PAID", "ADVANCE"]
            and r.get("Status") != "ARCHIVED"
        ]
    elif status == "active":
        filtered = [r for r in receipts if r.get("Status") != "ARCHIVED"]
    else:
        filtered = receipts

    filtered.reverse()
    return filtered

@router.get(Routes.LANDLORDAPIBILLINGMONTHS, name=Names.APIBILLINGMONTHS)
async def api_billing_months(landlordUuid: str):
    return get_billing_months()

@router.get(Routes.LANDLORDAPIBILLINGPREVIEW, name=Names.APIBILLINGPREVIEW)
async def api_billing_preview(
    landlordUuid: str,
    currentreading: float,
    additionalpersons: int,
    prevreading: float = 0.0,
    rent: float | None = None,
    water: float | None = None,
    tankWater: float = 0.0,
    maintenancecharge: float = 0.0,
    rate: float | None = None,
    addpersoncharge: float | None = None,
):
    billing_conf = config.get("billing", {})
    rent = float(rent if rent is not None else billing_conf.get("rent", 0.0))
    water = float(water if water is not None else billing_conf.get("water", 0.0))
    rate = float(rate if rate is not None else billing_conf.get("electricityRate", 0.0))
    addpersoncharge = float(
        addpersoncharge if addpersoncharge is not None
        else billing_conf.get("additionalPersonCharge", 0.0)
    )

    return calculate_charges(
        currentreading,
        additionalpersons,
        prevreading,
        rent,
        water,
        tankWater,
        maintenancecharge,
        rate,
        addpersoncharge,
    )

@router.get(Routes.LANDLORDAPIBILLINGGET, name=Names.APIGETSINGLEBILL)
async def api_get_single_bill(landlordUuid: str, tenantId: int, billNo: str, principal=Depends(get_current_landlord_api_strict)):
    receipt = get_receipt(tenantId, billNo, landlord_id=principal.landlord_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Bill not found")
    return receipt

@router.post(Routes.LANDLORDAPIBILLINGCREATE, name=Names.APICREATEBILL)
async def api_create_bill(landlordUuid: str, tenantId: int, bill_req: BillRequest, http_request: Request, background_tasks: BackgroundTasks, principal=Depends(get_current_landlord_api_strict)):
    from app.database.landlord_repository import create_landlord_audit_log

    _require_active_tenant(tenantId, landlord_id=principal.landlord_id)
    try:
        data = create_bill(
            tenantId,
            bill_req.month,
            bill_req.currentreading,
            bill_req.additionalpersons,
            bill_req.tankWater,
            bill_req.maintenancecharge,
            bill_req.maintenancedesc,
            bill_req.previousarrears,
            bill_req.amountreceived,
            bill_req.paymentstatus,
            landlord_id=principal.landlord_id
        )
        background_tasks.add_task(create_full_backup, tag="create_bill")

        landlord_id = principal.landlord_id
        if landlord_id:
            create_landlord_audit_log(
                landlord_id, "bill_created",
                ip_address=http_request.client.host if http_request.client else None,
                meta_json=json.dumps({"tenant_id": tenantId, "bill_no": data.get("billNo", "")}),
            )

        await _broadcast(f"landlord:{landlordUuid}", {"type": "RECEIPT_CREATED", "billNo": data.get("billNo", ""), "tenantId": tenantId})
        return {"status": "success", "data": data}
    except ValueError as e:
        msg = str(e)
        if "already exists" in msg.lower():
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put(Routes.LANDLORDAPIBILLINGUPDATE, name=Names.APIUPDATEBILL)
async def api_update_bill(landlordUuid: str, tenantId: int, billNo: str, bill_req: BillRequest, http_request: Request, background_tasks: BackgroundTasks, principal=Depends(get_current_landlord_api_strict)):
    from app.database.landlord_repository import create_landlord_audit_log

    _require_active_tenant(tenantId, landlord_id=principal.landlord_id)
    try:
        data = update_bill(
            tenantId,
            billNo,
            bill_req.month,
            bill_req.currentreading,
            bill_req.additionalpersons or 0,
            bill_req.tankWater or 0.0,
            bill_req.maintenancecharge or 0.0,
            bill_req.maintenancedesc or "",
            bill_req.previousarrears or 0.0,
            bill_req.amountreceived,
            (bill_req.paymentstatus or "PENDING").upper(),
            landlord_id=principal.landlord_id
        )
        background_tasks.add_task(create_full_backup, tag="edit_bill")

        landlord_id = principal.landlord_id
        if landlord_id:
            create_landlord_audit_log(
                landlord_id, "bill_updated",
                ip_address=http_request.client.host if http_request.client else None,
                meta_json=json.dumps({"tenant_id": tenantId, "bill_no": billNo}),
            )

        await _broadcast(f"landlord:{landlordUuid}", {"type": "RECEIPT_UPDATED", "billNo": billNo, "tenantId": tenantId})
        return {"status": "success", "data": data}
    except ValueError as e:
        msg = str(e)
        if "already exists" in msg.lower():
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post(Routes.LANDLORDAPIBILLINGUPDATEPAYMENT, name=Names.APIUPDATEPAYMENT)
async def api_update_payment(landlordUuid: str, tenantId: int, billNo: str, data: PaymentStatusUpdate, background_tasks: BackgroundTasks, principal=Depends(get_current_landlord_api_strict)):
    try:
        status = (data.paymentstatus or "").strip().upper()
        if status not in {"PAID", "PENDING", "PARTIAL", "ADVANCE"}:
            raise HTTPException(status_code=400, detail="Invalid payment status.")

        amount = data.amountreceived
        if amount is not None and amount < 0:
            raise HTTPException(status_code=400, detail="Amount received cannot be negative.")

        update_paymentStatus(tenantId, billNo, status, amount, landlord_id=principal.landlord_id)
        background_tasks.add_task(create_full_backup, tag="paymentStatus")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post(Routes.LANDLORDAPIBILLINGARCHIVE, name=Names.APIARCHIVEBILL)
async def api_archive_bill(landlordUuid: str, tenantId: int, billNo: str, background_tasks: BackgroundTasks, principal=Depends(get_current_landlord_api_strict)):
    try:
        archive_bill(tenantId, billNo, landlord_id=principal.landlord_id)
        background_tasks.add_task(create_full_backup, tag="archive_bill")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post(Routes.LANDLORDAPIBILLINGRESTORE, name=Names.APIRESTOREBILL)
async def api_restore_bill(landlordUuid: str, tenantId: int, billNo: str, background_tasks: BackgroundTasks, principal=Depends(get_current_landlord_api_strict)):
    try:
        restore_bill(tenantId, billNo, landlord_id=principal.landlord_id)
        background_tasks.add_task(create_full_backup, tag="restore_bill")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete(Routes.LANDLORDAPIBILLINGDELETE, name=Names.APIDELETEBILL)
async def api_delete_bill(landlordUuid: str, tenantId: int, billNo: str, request: Request, background_tasks: BackgroundTasks, principal=Depends(get_current_landlord_api_strict)):
    from app.database.landlord_repository import create_landlord_audit_log

    try:
        delete_bill(tenantId, billNo, landlord_id=principal.landlord_id)
        background_tasks.add_task(create_full_backup, tag="delete_bill")

        landlord_id = principal.landlord_id
        if landlord_id:
            create_landlord_audit_log(
                landlord_id, "bill_deleted",
                ip_address=request.client.host if request.client else None,
                meta_json=json.dumps({"tenant_id": tenantId, "bill_no": billNo}),
            )

        await _broadcast(f"landlord:{landlordUuid}", {"type": "RECEIPT_DELETED", "billNo": billNo, "tenantId": tenantId})
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
