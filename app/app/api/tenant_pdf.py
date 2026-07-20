# File: app/app/api/tenant_pdf.py
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.core.routes_manifest_tenant import TenantRoutes, TenantNames
from app.services.billing_service import get_receipt
from app.core.config_service import config
from app.authentication.tenant.middleware import get_current_tenant
from datetime import datetime

router = APIRouter()


@router.get(TenantRoutes.TENANTAPIPDFVIEW, name=TenantNames.TENANTPDFVIEW)
async def tenant_view_pdf(
    tenantId: int,
    viewToken: str,
    billNo: str,
    request: Request,
    principal=Depends(get_current_tenant)
):
    """Tenant-facing PDF view endpoint — requires tenant authentication."""
    if principal.id != tenantId:
        raise HTTPException(status_code=403, detail="Forbidden")

    from app.services.tenant_service import load_tenants
    tenant = next((t for t in load_tenants(include_archived=True) if t.id == tenantId and getattr(t, "viewToken", None) == viewToken), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid tenant link")

    receipt = get_receipt(tenantId, billNo)
    if not receipt:
        raise HTTPException(status_code=404, detail="PDF not found")

    if int(receipt.get("TenantId", 0) or 0) != tenantId:
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


@router.get(TenantRoutes.TENANTAPIPDFDOWNLOAD, name=TenantNames.TENANTPDFDOWNLOAD)
async def tenant_download_pdf(
    tenantId: int,
    viewToken: str,
    billNo: str,
    request: Request,
    principal=Depends(get_current_tenant)
):
    """Tenant-facing PDF download endpoint — requires tenant authentication."""
    if principal.id != tenantId:
        raise HTTPException(status_code=403, detail="Forbidden")

    from app.services.tenant_service import load_tenants
    tenant = next((t for t in load_tenants(include_archived=True) if t.id == tenantId and getattr(t, "viewToken", None) == viewToken), None)
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid tenant link")

    receipt = get_receipt(tenantId, billNo)
    if not receipt:
        raise HTTPException(status_code=404, detail="PDF not found")

    if int(receipt.get("TenantId", 0) or 0) != tenantId:
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