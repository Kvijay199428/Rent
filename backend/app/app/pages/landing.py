"""
app/pages/landing.py

Public landing page at GET /.
Serves the landing app directly at the canonical root /. The legacy
base-path tree was migrated to the root and is no longer used.

The landing dist is shared with the dev frontend router
(app/pages/frontend.py) so the root HTML and its /assets/* chunks always
resolve to the same build (dist-dev in development).
"""
import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.core.routes_manifest import Names, Routes
from app.core.api_guard import check_api_host
from app.pages.frontend import LANDING_DIST

router = APIRouter(tags=["Public"])


@router.get(Routes.PUBLICLANDING, name=Names.PUBLICLANDING)
async def public_landing(request: Request):
    """Serve the landing app at the canonical root /."""
    check_api_host(request)
    return FileResponse(os.path.join(LANDING_DIST, "index.html"))


@router.get("/favicon.ico", include_in_schema=False)
async def landing_favicon(request: Request):
    check_api_host(request)
    return FileResponse(os.path.join(LANDING_DIST, "favicon.ico"))
