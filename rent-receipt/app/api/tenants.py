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


@router.get("/api/tenants", name=Names.API_GET_TENANTS)
async def api_get_tenants():
    return load_tenants()

@router.get("/api/tenants/{tenant_id}", name=Names.API_GET_TENANT)
async def api_get_tenant(tenant_id: int):
    tenants = load_tenants()
    tenant = next((t for t in tenants if t.id == tenant_id), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

@router.get("/api/tenant_receipts/{tenant_name}", name=Names.API_GET_TENANT_RECEIPTS)
async def api_get_tenant_receipts(tenant_name: str):
    receipts = get_all_receipts()
    tenant_receipts = [r for r in receipts if r["Tenant"] == tenant_name]
    tenant_receipts.reverse()
    return tenant_receipts

@router.post("/api/tenants", name=Names.API_ADD_TENANT)
async def api_add_tenant(t: Tenant, background_tasks: BackgroundTasks):
    background_tasks.add_task(create_full_backup, tag="add_tenant")
    return add_tenant(t)

@router.put("/api/tenants/{tenant_id}", name=Names.API_UPDATE_TENANT)
async def api_update_tenant(tenant_id: int, t: Tenant, background_tasks: BackgroundTasks):
    t.id = tenant_id
    background_tasks.add_task(create_full_backup, tag="update_tenant")
    return update_tenant(t)

@router.delete("/api/tenants/{tenant_id}", name=Names.API_DELETE_TENANT)
async def api_delete_tenant(tenant_id: int, action: str = "archive", background_tasks: BackgroundTasks = None):
    if background_tasks:
        background_tasks.add_task(create_full_backup, tag=f"{action}_tenant")
    delete_tenant(tenant_id, action)
    return {"status": "success"}

