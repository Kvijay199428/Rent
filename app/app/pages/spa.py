import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

TENANT_ASSETS_DIR = "frontend/tenant-app/dist/assets"

router = APIRouter()

@router.get("/admin")
async def admin_root_redirect(request: Request):
    url = request.url
    if not url.path.endswith("/"):
        return RedirectResponse(url=str(url.replace(path=url.path + "/")), status_code=307)
    return FileResponse("frontend/admin-app/dist/index.html")


@router.get("/admin/{path:path}")
async def serve_admin_app(path: str = ""):
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    return FileResponse("frontend/admin-app/dist/index.html")


@router.get("/landlord")
async def landlord_root_redirect(request: Request):
    url = request.url
    if not url.path.endswith("/"):
        return RedirectResponse(url=str(url.replace(path=url.path + "/")), status_code=307)
    return await serve_landlord_app(request, path="")


@router.get("/landlord/{path:path}")
async def serve_landlord_app(request: Request, path: str = ""):
    if path.startswith("api/") or path.startswith("assets/") or "." in path.split("/")[-1]:
        raise HTTPException(status_code=404, detail="Not found")

    # Reject UUID-prefixed API paths — these should be handled by API routers,
    # not served as the SPA index.html fallback.
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and len(parts[0]) >= 10 and parts[1] == "api":
        raise HTTPException(status_code=404, detail="API route not found")

    # Resolver: when hitting /landlord with no path, check session and redirect
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

        # Not authenticated -- redirect to login
        root = (request.scope.get("root_path") or "").rstrip("/")
        return RedirectResponse(url=f"{root}/landlord/login", status_code=307)

    return FileResponse("frontend/landlord-app/dist/index.html")

@router.get("/{landlordUuid}/t/{tenantId}/{viewToken}/assets/{asset_path:path}", include_in_schema=False)
async def serve_tenant_assets(landlordUuid: str, tenantId: int, viewToken: str, asset_path: str):
    safe = os.path.normpath(asset_path).lstrip("/")
    if safe.startswith(".."):
        raise HTTPException(status_code=404, detail="Not found")
    fpath = os.path.join(TENANT_ASSETS_DIR, safe)
    if os.path.isfile(fpath):
        return FileResponse(fpath)
    raise HTTPException(status_code=404, detail="Asset not found")

@router.get("/tenant")
@router.get("/tenant/{path:path}", include_in_schema=False)
async def serve_tenant_app_login(path: str = ""):
    if path.startswith("api/") or path.startswith("assets/") or "." in path.split("/")[-1]:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse("frontend/tenant-app/dist/index.html")


@router.get("/{landlordUuid}/t/{tenantId}/{viewToken}", name="serve_tenant_app", include_in_schema=False)
@router.get("/{landlordUuid}/t/{tenantId}/{viewToken}/{path:path}", name="serve_tenant_app_path", include_in_schema=False)
async def serve_tenant_app(landlordUuid: str, tenantId: int, viewToken: str, path: str = ""):
    if path.startswith("api/") or path.startswith("assets/") or "." in path.split("/")[-1]:
        raise HTTPException(status_code=404, detail="API route not found")
    return FileResponse("frontend/tenant-app/dist/index.html")
