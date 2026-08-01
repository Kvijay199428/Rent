"""
app/pages/landing.py

Public landing page at GET /.
Renders landing.html with role-selection buttons:
  - Landlord Login / Signup
  - Platform Admin Login

This router replaces the old root 301 redirect in redirects.py.
"""
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from app.core.routes_manifest import Names, Routes

router = APIRouter(tags=["Public"])


@router.get(Routes.PUBLICLANDING, name=Names.PUBLICLANDING)
async def public_landing(request: Request):
    """Serve the public landing page for the Rent app."""
    return FileResponse("frontend/landing-app/dist/index.html")


@router.get("/favicon.svg", include_in_schema=False)
async def landing_favicon():
    return FileResponse("frontend/landing-app/dist/favicon.svg")
