from fastapi import FastAPI, Depends

from app.core.runtime import serve_frontend

# API Routers
from app.api.billing import router as billing_api_router
from app.api.tenants import router as tenants_api_router
from app.api.settings import router as settings_api_router
from app.api.backup import router as backup_api_router
from app.api.pdf import router as pdf_api_router
from app.api.whatsapp import router as whatsapp_api_router
from app.api.sync import router as sync_api_router
from app.api.sync_ws import router as sync_ws_router
from app.api.public import router as public_api_router
from app.api.health import router as health_api_router
from app.api.location import router as location_api_router
from app.api.dashboard import router as dashboard_api_router
from app.api.landlord_setup import router as landlord_setup_router
from app.routers.auth import router as auth_api_router
from app.routers.admin_auth import router as admin_auth_router
from app.api.tenant_pdf import router as tenant_pdf_api_router

from app.routers.platform_admin import router as platform_admin_router
from app.routers.landlordauth import router as landlordauth_router

from app.pages.errors import register_exception_handlers

# Public landing page at /
from app.pages.landing import router as landing_router

# Dev-only canonical /rent/ page structure (registered when serve_frontend())
from app.pages.frontend import router as frontend_pages_router

from app.authentication.landlord.middleware import get_current_landlord_api_strict

PROTECTED_API_ROUTERS = [
    billing_api_router,
    tenants_api_router,
    settings_api_router,
    whatsapp_api_router,
    sync_api_router,
    pdf_api_router,
    dashboard_api_router,
    landlord_setup_router,
]

# Backup router handles its own per-route auth: landlord auth for list/create/
# delete/verify/download/metadata, platform-admin auth for restore.
BACKUP_ROUTERS = [
    backup_api_router,
]

PUBLIC_API_ROUTERS = [
    public_api_router,
    health_api_router,
    auth_api_router,
    tenant_pdf_api_router,
    location_api_router,
]

ADMIN_AUTH_ROUTERS = [
    admin_auth_router,
]

LANDLORD_AUTH_ROUTERS = [
    landlordauth_router,
]


def register_all_routers(app: FastAPI):
    api_landlord_deps = [Depends(get_current_landlord_api_strict)]

    # 1. Protected API routers (landlord API auth — these register at
    #    /landlord/{landlordUuid}/api/* paths)
    for router in PROTECTED_API_ROUTERS:
        app.include_router(router, dependencies=api_landlord_deps)

    # 1b. Backup router — per-route auth (restore is platform-admin only)
    for router in BACKUP_ROUTERS:
        app.include_router(router)

    # 2. Admin auth routes
    for router in ADMIN_AUTH_ROUTERS:
        app.include_router(router, prefix="")

    # 3. Landlord auth — handles its own auth checks internally
    for router in LANDLORD_AUTH_ROUTERS:
        app.include_router(router, prefix="")

    # 4. Public API routes
    for router in PUBLIC_API_ROUTERS:
        app.include_router(router)

    # 5. Platform admin
    app.include_router(platform_admin_router)

    # 6. Public landing page at / (skipped on API-only release backend)
    if serve_frontend():
        app.include_router(landing_router)
        app.include_router(frontend_pages_router)

    # 7. WebSocket sync (no auth dependency — channel-based access control)
    app.include_router(sync_ws_router)

    register_exception_handlers(app)
