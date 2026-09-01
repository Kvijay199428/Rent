"""
app/pages/landing.py

Public landing page at GET /.
Redirects to the canonical landing app at /rent/ (mirrors the prod
_redirects rule "/ /rent/ 301"). The /rent/ tree is served by
app/pages/frontend.py in dev and by the frontend container in prod.
"""
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.core.routes_manifest import Names, Routes
from app.core.api_guard import check_api_host

router = APIRouter(tags=["Public"])


@router.get(Routes.PUBLICLANDING, name=Names.PUBLICLANDING)
async def public_landing(request: Request):
    """Redirect the bare domain to the canonical landing app at /rent/."""
    check_api_host(request)
    return RedirectResponse(url="/rent/", status_code=301)


@router.get("/favicon.ico", include_in_schema=False)
async def landing_favicon(request: Request):
    check_api_host(request)
    return FileResponse("frontend/landing-app/dist/favicon.ico")
