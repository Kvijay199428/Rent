# File: app/app/api/tenant_pdf.py
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.core.routes_manifest_tenant import TenantRoutes, TenantNames
from app.services.billing_service import get_receipt
from app.core.config_service import config
from app.authentication.tenant.middleware import get_current_tenant
from datetime import datetime

router = APIRouter()


@router.get("/t/{propertyId}/{tenantId}/{viewToken}/api/pdf/{billNo}/view", include_in_schema=False)
@router.get(TenantRoutes.TENANTAPIPDFVIEW, name=TenantNames.TENANTPDFVIEW)
async def tenant_view_pdf(
    propertyId: int,
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
    if int(getattr(tenant, "propertyId", 0) or 0) != int(propertyId or 0):
        raise HTTPException(status_code=403, detail="Property mismatch")

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

    from app.services.cacheservice import cache_get, cache_set
    pdf_cache_key = f"pdf:{tenantId}:{billNo}"
    cached_pdf = cache_get(pdf_cache_key)
    if cached_pdf is not None:
        response = StreamingResponse(
            iter([cached_pdf]),
            media_type='application/pdf'
        )
        response.headers["Content-Disposition"] = f"inline; filename={custom_filename}"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    from app.services.pdf_service import generate_professional_pdf
    from app.services.landlord_config_service import get_effective_landlord_config
    landlord_conf = get_effective_landlord_config(getattr(tenant, "landlord_id", None))

    pdf_stream = generate_professional_pdf(receipt, landlord_conf)
    pdf_bytes = pdf_stream.getvalue()
    cache_set(pdf_cache_key, pdf_bytes, ttl=300)

    response = StreamingResponse(
        iter([pdf_bytes]),
        media_type='application/pdf'
    )
    response.headers["Content-Disposition"] = f"inline; filename={custom_filename}"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@router.get("/t/{propertyId}/{tenantId}/{viewToken}/api/pdf/{billNo}/download", include_in_schema=False)
@router.get(TenantRoutes.TENANTAPIPDFDOWNLOAD, name=TenantNames.TENANTPDFDOWNLOAD)
async def tenant_download_pdf(
    propertyId: int,
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
    if int(getattr(tenant, "propertyId", 0) or 0) != int(propertyId or 0):
        raise HTTPException(status_code=403, detail="Property mismatch")

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

    from app.services.cacheservice import cache_get, cache_set
    pdf_cache_key = f"pdf:{tenantId}:{billNo}"
    cached_pdf = cache_get(pdf_cache_key)
    if cached_pdf is not None:
        response = StreamingResponse(
            iter([cached_pdf]),
            media_type='application/pdf'
        )
        response.headers["Content-Disposition"] = f'attachment; filename="{custom_filename}"'
        return response

    from app.services.pdf_service import generate_professional_pdf
    from app.services.landlord_config_service import get_effective_landlord_config
    landlord_conf = get_effective_landlord_config(getattr(tenant, "landlord_id", None))

    pdf_stream = generate_professional_pdf(receipt, landlord_conf)
    pdf_bytes = pdf_stream.getvalue()
    cache_set(pdf_cache_key, pdf_bytes, ttl=300)

    response = StreamingResponse(
        iter([pdf_bytes]),
        media_type='application/pdf'
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{custom_filename}"'
    return response
