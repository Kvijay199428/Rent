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

