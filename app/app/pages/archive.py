from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.dependencies import templates, config

from app.core.routes_manifest import Routes, Names, Templates

from app.services.tenant_service import load_tenants
from app.services.billing_service import get_all_receipts

router = APIRouter()

@router.get(Routes.ADMINPAGEARCHIVE, name=Names.ARCHIVEPAGE, response_class=HTMLResponse)
async def archive_page(request: Request):
    # Get archived tenants
    all_tenants = load_tenants(include_archived=True)
    archived_tenants = [
        t for t in all_tenants
        if (t.status or "").strip().lower() == "archived"
    ]
    # ID-based set — never use tenant names for ownership/grouping
    archived_tenant_ids = {int(t.id) for t in archived_tenants}

    # Get receipts that are either ARCHIVED status OR belong to archived tenants (by ID)
    all_receipts = get_all_receipts(include_archived_tenants=True)
    archived_receipts = [
        r for r in all_receipts
        if str(r.get("Status", "") or "").strip().upper() == "ARCHIVED"
        or int(r.get("TenantId", 0) or 0) in archived_tenant_ids
    ]
    archived_receipts.reverse()
    
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name=Templates.ARCHIVE, context={
            "receipts": archived_receipts,
            "archived_tenants": archived_tenants,  # Pass archived tenants too
            "theme": theme,
            "sys": getattr(request.state, "sys", config.get("system", {}))
        }
    )

