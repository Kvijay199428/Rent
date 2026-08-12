"""app/pages/frontend.py

Dev-only frontend router that serves the canonical /rent/ page structure
(landing, admin, landlord, tenant apps + tenant deep links) straight from the
per-app dist builds. Mirrors the production routing in gateway/nginx/routes/
(frontend.conf + api.conf) so the dev stack behaves like prod when reached
through the ngrok tunnel.

Registered only when serve_frontend() is True (development). Release backends
are API-only (serve_frontend() is False) and never include this router — the
frontend container serves these pages instead.

Route order matters: specific asset/deep-link routes are registered before the
per-app SPA fallbacks and the final /rent/ catch-all.
"""
import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.core.api_guard import check_api_host

LANDING_DIST = "frontend/landing-app/dist"
ADMIN_DIST = "frontend/admin-app/dist"
LANDLORD_DIST = "frontend/landlord-app/dist"
TENANT_DIST = "frontend/tenant-app/dist"

router = APIRouter(tags=["Frontend"])


def _serve_asset(root: str, path: str) -> FileResponse:
    """Serve a static file from an app dist, refusing path traversal."""
    safe = os.path.normpath(path).lstrip("/")
    if safe.startswith(".."):
        raise HTTPException(status_code=404, detail="Not found")
    fpath = os.path.join(root, safe)
    if os.path.isfile(fpath):
        return FileResponse(fpath)
    raise HTTPException(status_code=404, detail="Asset not found")


def _spa_index(root: str, request: Request, path: str) -> FileResponse:
    """Serve an SPA entry point, rejecting API/asset traffic and file paths."""
    check_api_host(request)
    if path.startswith("api/") or path.startswith("assets/"):
        raise HTTPException(status_code=404, detail="Not found")
    last = path.split("/")[-1]
    if "." in last:
        return _serve_asset(root, path)
    return FileResponse(os.path.join(root, "index.html"))


def _app_prefix(prefix: str, dist: str) -> None:
    """Register asset + SPA-fallback routes for one app at /rent/{prefix}/..."""

    @router.get(f"/rent/{prefix}/assets/{{asset_path:path}}", include_in_schema=False)
    async def app_assets(asset_path: str):
        return _serve_asset(os.path.join(dist, "assets"), asset_path)

    @router.get(f"/rent/{prefix}", include_in_schema=False)
    async def app_root_redirect(request: Request):
        check_api_host(request)
        return RedirectResponse(url=f"/rent/{prefix}/", status_code=301)

    @router.get(f"/rent/{prefix}/", include_in_schema=False)
    @router.get(f"/rent/{prefix}/{{path:path}}", include_in_schema=False)
    async def app_spa(request: Request, path: str = ""):
        return _spa_index(dist, request, path)


# ─── Landing app (root of the /rent/ tree) ───────────────────────────────────

@router.get("/rent", include_in_schema=False)
async def rent_root_redirect(request: Request):
    check_api_host(request)
    return RedirectResponse(url="/rent/", status_code=301)


@router.get("/rent/", include_in_schema=False)
async def landing_app(request: Request):
    check_api_host(request)
    return FileResponse(os.path.join(LANDING_DIST, "index.html"))


@router.get("/rent/favicon.svg", include_in_schema=False)
async def landing_favicon(request: Request):
    check_api_host(request)
    return FileResponse(os.path.join(LANDING_DIST, "favicon.svg"))


@router.get("/rent/assets/{asset_path:path}", include_in_schema=False)
async def landing_assets(asset_path: str):
    return _serve_asset(os.path.join(LANDING_DIST, "assets"), asset_path)


# ─── Per-app routes (assets before SPA fallbacks) ────────────────────────────

_app_prefix("admin", ADMIN_DIST)
_app_prefix("landlord", LANDLORD_DIST)
_app_prefix("t", TENANT_DIST)
_app_prefix("tenant", TENANT_DIST)


# ─── Tenant portal deep links /rent/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken} ──

@router.get("/rent/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}", include_in_schema=False)
@router.get("/rent/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/{path:path}", include_in_schema=False)
async def tenant_deep_link(request: Request, landlordUuid: str, propertyId: str, tenantId: str, viewToken: str, path: str = ""):
    return _spa_index(TENANT_DIST, request, path)


# ─── Catch-all: anything else under /rent/ → landing app (prod try_files) ────

@router.get("/rent/{path:path}", include_in_schema=False)
async def landing_app_fallback(request: Request, path: str = ""):
    return _spa_index(LANDING_DIST, request, path)
