import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.core.api_guard import check_api_host

TENANT_ASSETS_DIR = "frontend/tenant-app/dist/assets"

router = APIRouter()


@router.get("/landlord")
async def landlord_root_redirect(request: Request):
    check_api_host(request)
    url = request.url
    if not url.path.endswith("/"):
        return RedirectResponse(url=str(url.replace(path=url.path + "/")), status_code=307)
    return await serve_landlord_app(request, path="")


@router.get("/landlord/{path:path}")
async def serve_landlord_app(request: Request, path: str = ""):
    check_api_host(request)
    if path.startswith("api/") or path.startswith("assets/") or "." in path.split("/")[-1]:
        raise HTTPException(status_code=404, detail="Not found")

    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and len(parts[0]) >= 10 and parts[1] == "api":
        raise HTTPException(status_code=404, detail="API route not found")

    if not path:
        try:
            token = request.cookies.get("access_token")
            if token:
                from app.authentication.landlord.jwt import decode_access_token
                from app.authentication.landlord.sessions import get_landlord_session_db
                from app.database.landlord_repository import get_landlord_by_id

                payload = decode_access_token(token)
                if payload.get("role") == "landlord":
                    session_id = payload.get("sid")
                    session = get_landlord_session_db(session_id)
                    if session:
                        landlord_id = int(payload.get("landlord_id") or payload.get("sub"))
                        landlord = get_landlord_by_id(landlord_id)
                        if landlord:
                            uuid = landlord["landlord_uuid"]
                            root = (request.scope.get("root_path") or "").rstrip("/")
                            return RedirectResponse(
                                url=f"{root}/landlord/{uuid}/dashboard",
                                status_code=307,
                            )
        except Exception:
            pass

        root = (request.scope.get("root_path") or "").rstrip("/")
        return RedirectResponse(url=f"{root}/landlord/login", status_code=307)

    return FileResponse("frontend/landlord-app/dist/index.html")


@router.get("/tenant")
@router.get("/tenant/{path:path}", include_in_schema=False)
async def serve_tenant_app_login(request: Request, path: str = ""):
    check_api_host(request)
    if path.startswith("api/") or path.startswith("assets/") or "." in path.split("/")[-1]:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse("frontend/tenant-app/dist/index.html")


@router.get("/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/assets/{asset_path:path}", include_in_schema=False)
async def serve_tenant_assets(request: Request, landlordUuid: str, propertyId: int, tenantId: int, viewToken: str, asset_path: str):
    check_api_host(request)
    safe = os.path.normpath(asset_path).lstrip("/")
    if safe.startswith(".."):
        raise HTTPException(status_code=404, detail="Not found")
    fpath = os.path.join(TENANT_ASSETS_DIR, safe)
    if os.path.isfile(fpath):
        return FileResponse(fpath)
    raise HTTPException(status_code=404, detail="Asset not found")


@router.get("/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}", name="serve_tenant_app", include_in_schema=False)
@router.get("/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/{path:path}", name="serve_tenant_app_path", include_in_schema=False)
async def serve_tenant_app(request: Request, landlordUuid: str, propertyId: int, tenantId: int, viewToken: str, path: str = ""):
    check_api_host(request)
    if path.startswith("api/") or path.startswith("assets/") or "." in path.split("/")[-1]:
        raise HTTPException(status_code=404, detail="API route not found")
    return FileResponse("frontend/tenant-app/dist/index.html")
