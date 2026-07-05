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
        filtered = [r for r in receipts if r.get("Payment_Status", "PENDING") == "PENDING" and r.get("Status") != "ARCHIVED"]
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
        if data.payment_status not in ["PAID", "PENDING"]:
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

