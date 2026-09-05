"""app/pages/frontend.py

Dev-only frontend router that serves the canonical / page structure
(landing, admin, landlord, tenant apps + tenant deep links) straight from the
per-app dist builds. Mirrors the production routing in gateway/nginx/routes/
(frontend.conf + api.conf) so the dev stack behaves like prod when reached
through the ngrok tunnel.

Registered only when serve_frontend() is True (development). Release backends
are API-only (serve_frontend() is False) and never include this router — the
frontend container serves these pages instead.

Route order matters: specific asset/deep-link routes are registered before the
per-app SPA fallbacks and the final / catch-all.
"""
import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.core.api_guard import check_api_host

def _resolve_dist(app: str) -> str:
    """Prefer the dev dist build when present, else fall back to the prod dist.

    Dev deploys build each app into <app>/dist-dev pointed at the dev API
    (ngrok tunnel) so dev pages never collide with the prod API origin. This
    router is dev-only (serve_frontend()), so prod is never affected.
    """
    base = f"frontend/{app}-app"
    dev = f"{base}/dist-dev"
    if os.path.isdir(dev):
        return dev
    return f"{base}/dist"


LANDING_DIST = _resolve_dist("landing")
ADMIN_DIST = _resolve_dist("admin")
LANDLORD_DIST = _resolve_dist("landlord")
TENANT_DIST = _resolve_dist("tenant")

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
    """Register asset + SPA-fallback routes for one app at /{prefix}/..."""

    @router.get(f"/{prefix}/assets/{{asset_path:path}}", include_in_schema=False)
    async def app_assets(asset_path: str):
        return _serve_asset(os.path.join(dist, "assets"), asset_path)

    @router.get(f"/{prefix}", include_in_schema=False)
    async def app_root_redirect(request: Request):
        check_api_host(request)
        return RedirectResponse(url=f"/{prefix}/", status_code=301)

    @router.get(f"/{prefix}/", include_in_schema=False)
    @router.get(f"/{prefix}/{{path:path}}", include_in_schema=False)
    async def app_spa(request: Request, path: str = ""):
        return _spa_index(dist, request, path)


# ─── Landing app (root of the / tree) ───────────────────────────────────


@router.get("/", include_in_schema=False)
async def landing_app(request: Request):
    check_api_host(request)
    return FileResponse(os.path.join(LANDING_DIST, "index.html"))


@router.get("/favicon.ico", include_in_schema=False)
async def landing_favicon(request: Request):
    check_api_host(request)
    return FileResponse(os.path.join(LANDING_DIST, "favicon.ico"))


@router.get("/assets/{asset_path:path}", include_in_schema=False)
async def landing_assets(asset_path: str):
    return _serve_asset(os.path.join(LANDING_DIST, "assets"), asset_path)


# ─── Per-app routes (assets before SPA fallbacks) ────────────────────────────

_app_prefix("admin", ADMIN_DIST)
_app_prefix("landlord", LANDLORD_DIST)
_app_prefix("t", TENANT_DIST)
_app_prefix("tenant", TENANT_DIST)


# ─── Tenant portal deep links /{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken} ──

@router.get("/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}", include_in_schema=False)
@router.get("/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/{path:path}", include_in_schema=False)
async def tenant_deep_link(request: Request, landlordUuid: str, propertyId: str, tenantId: str, viewToken: str, path: str = ""):
    return _spa_index(TENANT_DIST, request, path)


# ─── Catch-all: anything else under / → landing app (prod try_files) ────

@router.get("/{path:path}", include_in_schema=False)
async def landing_app_fallback(request: Request, path: str = ""):
    return _spa_index(LANDING_DIST, request, path)
