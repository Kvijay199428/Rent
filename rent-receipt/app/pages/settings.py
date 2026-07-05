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

