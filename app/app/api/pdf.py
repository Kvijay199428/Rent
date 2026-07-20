# File: app\app\api\pdf.py
from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder

from app.core.routes_manifest import Routes, Names

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
from app.services.backup_service import create_full_backup

router = APIRouter()


from app.authentication.admin.middleware import get_current_admin_api
from datetime import datetime

@router.get(Routes.ADMINAPIPDFDOWNLOAD, name=Names.PDFDOWNLOAD)
async def download_pdf(tenantId: int, billNo: str, admin = Depends(get_current_admin_api)):
    billNo = billNo
    receipt = get_receipt(tenantId, billNo)
    if not receipt:
        raise HTTPException(status_code=404, detail="PDF not found")
        
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

@router.get(Routes.ADMINAPIPDFVIEW, name=Names.PDFVIEW)
async def view_pdf(tenantId: int, billNo: str, admin = Depends(get_current_admin_api)):
    billNo = billNo
    receipt = get_receipt(tenantId, billNo)
    if not receipt:
        raise HTTPException(status_code=404, detail="PDF not found")
        
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
    response.headers["Content-Disposition"] = f"inline; filename={custom_filename}"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response