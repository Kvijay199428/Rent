# // File: app\app\api\billing.py
from app.core.routes_manifest import Routes, Names
from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder

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


@router.get(Routes.ADMIN_API_BILLING_FILTER, name=Names.API_FILTER_BILLS)
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
            if r.get("Payment_Status", "PENDING") in ["PAID", "ADVANCE"]
            and r.get("Status") != "ARCHIVED"
        ]
    elif status == "active":
        filtered = [r for r in receipts if r.get("Status") != "ARCHIVED"]
    else:
        filtered = receipts

    filtered.reverse()
    return filtered

@router.get(Routes.ADMIN_API_BILLING_MONTHS, name=Names.API_BILLING_MONTHS)
async def api_billing_months():
    return get_billing_months()

@router.get(Routes.ADMIN_API_BILLING_PREVIEW, name=Names.API_BILLING_PREVIEW)
async def api_billing_preview(
    currentreading: float,
    additionalpersons: int,
    prevreading: float = 0.0,
    rent: float | None = None,
    water: float | None = None,
    tankwater: float = 0.0,
    maintenancecharge: float = 0.0,
    rate: float | None = None,
    addpersoncharge: float | None = None,
):
    billing_conf = config.get("billing", {})
    rent = float(rent if rent is not None else billing_conf.get("rent", 0.0))
    water = float(water if water is not None else billing_conf.get("water", 0.0))
    rate = float(rate if rate is not None else billing_conf.get("electricity_rate", 0.0))
    addpersoncharge = float(
        addpersoncharge if addpersoncharge is not None
        else billing_conf.get("additional_person_charge", 0.0)
    )

    return calculate_charges(
        currentreading,
        additionalpersons,
        prevreading,
        rent,
        water,
        tankwater,
        maintenancecharge,
        rate,
        addpersoncharge,
    )

@router.get(Routes.ADMIN_API_BILLING_GET, name=Names.API_GET_SINGLE_BILL)
async def api_get_single_bill(billno: str):
    receipt = get_receipt(billno)
    if not receipt:
        raise HTTPException(status_code=404, detail="Bill not found")
    return receipt

@router.post(Routes.ADMIN_API_BILLING_CREATE, name=Names.API_CREATE_BILL)
async def api_create_bill(request: BillRequest, background_tasks: BackgroundTasks):
    try:
        data = create_bill(
            request.tenant,
            request.month,
            request.currentreading,
            request.additionalpersons,
            request.tankwater,
            request.maintenancecharge,
            request.maintenancedesc,
            request.previousarrears,
            request.amountreceived,
            request.paymentstatus
        )
        background_tasks.add_task(create_full_backup, tag="create_bill")
        return {"status": "success", "data": data}
    except ValueError as e:
        msg = str(e)
        if "already exists" in msg.lower():
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# @router.post(Routes.ADMIN_API_BILLING_UPDATE, name=Names.API_UPDATE_BILL)
# async def api_update_bill(billno: str, request: BillRequest, background_tasks: BackgroundTasks):
#     try:
#         data = update_bill(
#             billno,
#             request.tenant,
#             request.month,
#             request.currentreading,
#             request.additionalpersons or 0,
#             request.tankwater or 0.0,
#             request.maintenancecharge or 0.0,
#             request.maintenancedesc or "",
#             request.previousarrears or 0.0,
#             request.amountreceived,
#             (request.paymentstatus or "PENDING").upper()
#         )
#         background_tasks.add_task(create_full_backup, tag="edit_bill")
#         return {"status": "success", "data": data}
#     except ValueError as e:
#         msg = str(e)
#         if "already exists" in msg.lower():
#             raise HTTPException(status_code=409, detail=msg)
#         raise HTTPException(status_code=400, detail=msg)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

@router.post(Routes.ADMIN_API_BILLING_UPDATE_PAYMENT, name=Names.API_UPDATE_PAYMENT)
async def api_update_payment(billno: str, data: PaymentStatusUpdate, background_tasks: BackgroundTasks):
    try:
        status = (data.paymentstatus or "").strip().upper()
        if status not in {"PAID", "PENDING", "PARTIAL", "ADVANCE"}:
            raise HTTPException(status_code=400, detail="Invalid payment status.")

        amount = data.amountreceived
        if amount is not None and amount < 0:
            raise HTTPException(status_code=400, detail="Amount received cannot be negative.")

        update_payment_status(billno, status, amount)
        background_tasks.add_task(create_full_backup, tag="payment_status")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post(Routes.ADMIN_API_BILLING_ARCHIVE, name=Names.API_ARCHIVE_BILL)
async def api_archive_bill(billno: str, background_tasks: BackgroundTasks):
    try:
        archive_bill(billno)
        background_tasks.add_task(create_full_backup, tag="archive_bill")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post(Routes.ADMIN_API_BILLING_RESTORE, name=Names.API_RESTORE_BILL)
async def api_restore_bill(billno: str, background_tasks: BackgroundTasks):
    try:
        restore_bill(billno)
        background_tasks.add_task(create_full_backup, tag="restore_bill")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete(Routes.ADMIN_API_BILLING_DELETE, name=Names.API_DELETE_BILL)
async def api_delete_bill(billno: str, background_tasks: BackgroundTasks):
    try:
        delete_bill(billno)
        background_tasks.add_task(create_full_backup, tag="delete_bill")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))