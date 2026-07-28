import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

TENANT_ASSETS_DIR = "frontend/tenant-app/dist/assets"

router = APIRouter()


@router.get("/{landlordUuid}/t/{tenantId}/{viewToken}/assets/{asset_path:path}", include_in_schema=False)
async def serve_tenant_assets(landlordUuid: str, tenantId: int, viewToken: str, asset_path: str):
    safe = os.path.normpath(asset_path).lstrip("/")
    if safe.startswith(".."):
        raise HTTPException(status_code=404, detail="Not found")
    fpath = os.path.join(TENANT_ASSETS_DIR, safe)
    if os.path.isfile(fpath):
        return FileResponse(fpath)
    raise HTTPException(status_code=404, detail="Asset not found")


@router.get("/{landlordUuid}/t/{tenantId}/{viewToken}", name="serve_tenant_app", include_in_schema=False)
@router.get("/{landlordUuid}/t/{tenantId}/{viewToken}/{path:path}", name="serve_tenant_app_path", include_in_schema=False)
async def serve_tenant_app(landlordUuid: str, tenantId: int, viewToken: str, path: str = ""):
    if path.startswith("api/") or path.startswith("assets/") or "." in path.split("/")[-1]:
        raise HTTPException(status_code=404, detail="API route not found")
    return FileResponse("frontend/tenant-app/dist/index.html")
