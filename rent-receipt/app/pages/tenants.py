from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from app.core.routes import Names
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from app.core.dependencies import templates, config
from app.core.route_builder import RouteBuilder
from app.core.routes import Paths, Names, Prefixes, Templates
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

