# File: app/app/api/tenant_pdf.py
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.core.routes_manifest import Routes, Names
from app.services.billing_service import get_receipt
from app.core.config_service import config
from app.authentication.tenant.middleware import get_current_tenant
from datetime import datetime

router = APIRouter()


@router.get(Routes.TENANTAPIPDFVIEW, name=Names.TENANTPDFVIEW)
async def tenant_view_pdf(
    viewToken: str,
    billNo: str,
    request: Request,
    principal=Depends(get_current_tenant)
):
    """Tenant-facing PDF view endpoint — requires tenant authentication."""
    receipt = get_receipt(billNo)
    if not receipt:
        raise HTTPException(status_code=404, detail="PDF not found")

    # Security: ensure tenant can only view their own receipts
    from app.services.tenant_service import load_tenants
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "viewToken", "") == viewToken), None)
    if not tenant or tenant.id != principal.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Verify receipt belongs to this tenant
    if receipt.get("Tenant") != tenant.name:
        raise HTTPException(status_code=403, detail="Receipt does not belong to this tenant")

    tenantName = receipt.get("Tenant", "Unknown").replace(" ", "_")
    try:
        formatted_date = datetime.strptime(receipt.get("Date", ""), "%d %B %Y").strftime("%Y%m%d")
    except:
        formatted_date = receipt.get("Date", "").replace(" ", "")
    custom_filename = f"{tenantName}_{formatted_date}_{billNo}.pdf"

    from app.services.pdf_service import generate_professional_pdf
    landlord_conf = config.get("landlord", {})

    pdf_stream = generate_professional_pdf(receipt, landlord_conf)

    response = StreamingResponse(
        iter([pdf_stream.getvalue()]),
        media_type='application/pdf'
    )
    response.headers["Content-Disposition"] = f"inline; filename={custom_filename}"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@router.get(Routes.TENANTAPIPDFDOWNLOAD, name=Names.TENANTPDFDOWNLOAD)
async def tenant_download_pdf(
    viewToken: str,
    billNo: str,
    request: Request,
    principal=Depends(get_current_tenant)
):
    """Tenant-facing PDF download endpoint — requires tenant authentication."""
    receipt = get_receipt(billNo)
    if not receipt:
        raise HTTPException(status_code=404, detail="PDF not found")

    # Security: ensure tenant can only download their own receipts
    from app.services.tenant_service import load_tenants
    tenants = load_tenants()
    tenant = next((t for t in tenants if getattr(t, "viewToken", "") == viewToken), None)
    if not tenant or tenant.id != principal.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Verify receipt belongs to this tenant
    if receipt.get("Tenant") != tenant.name:
        raise HTTPException(status_code=403, detail="Receipt does not belong to this tenant")

    tenantName = receipt.get("Tenant", "Unknown").replace(" ", "_")
    try:
        formatted_date = datetime.strptime(receipt.get("Date", ""), "%d %B %Y").strftime("%Y%m%d")
    except:
        formatted_date = receipt.get("Date", "").replace(" ", "")
    custom_filename = f"{tenantName}_{formatted_date}_{billNo}.pdf"

    from app.services.pdf_service import generate_professional_pdf
    landlord_conf = config.get("landlord", {})

    pdf_stream = generate_professional_pdf(receipt, landlord_conf)

    response = StreamingResponse(
        iter([pdf_stream.getvalue()]),
        media_type='application/pdf'
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{custom_filename}"'
    return response