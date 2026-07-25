from fastapi import FastAPI

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
from app.api.dashboard import router as dashboard_api_router
from app.routers.auth import router as auth_api_router
from app.routers.admin_auth import router as admin_auth_router
from app.api.tenant_pdf import router as tenant_pdf_api_router

from app.routers.landlord_routes import router as landlord_alias_router
from app.routers.platform_admin import router as platform_admin_router
from app.routers.landlordauth import router as landlordauth_router  # Landlord auth

# Page Routers
from app.pages.dashboard import router as dashboard_page_router
from app.pages.billing import router as billing_page_router
from app.pages.history import router as history_page_router
from app.pages.archive import router as archive_page_router
from app.pages.settings import router as settings_page_router
from app.pages.tenants import router as tenants_page_router
from app.pages.backups import router as backups_page_router
from app.pages.redirects import router as redirects_router
from app.pages.landing import router as landing_page_router  # Public landing page
from app.pages.spa import router as spa_router  # SPA catch-all (admin/landlord/tenant)
from app.pages.errors import register_exception_handlers

from fastapi import Depends
from app.authentication.landlord.middleware import get_current_landlord_page, get_current_landlord_api, get_current_landlord_api_strict

PROTECTED_PAGE_ROUTERS = [
    dashboard_page_router,
    billing_page_router,
    history_page_router,
    archive_page_router,
    settings_page_router,
    tenants_page_router,
    backups_page_router,
]

PROTECTED_API_ROUTERS = [
    billing_api_router,
    tenants_api_router,
    settings_api_router,
    backup_api_router,
    whatsapp_api_router,
    sync_api_router,
    pdf_api_router,
    dashboard_api_router,
]

PUBLIC_PAGE_ROUTERS = [
    redirects_router,
    landing_page_router,  # Serves GET / as public landing page
]

PUBLIC_API_ROUTERS = [
    public_api_router,
    health_api_router,
    auth_api_router,
    tenant_pdf_api_router
]

ADMIN_AUTH_ROUTERS = [
    admin_auth_router
]

# Landlord auth endpoints are public (no dependency) — they issue their own cookies
LANDLORD_AUTH_ROUTERS = [
    landlordauth_router,
]

def register_all_routers(app: FastAPI):
    page_landlord_deps = [Depends(get_current_landlord_page)]
    api_landlord_deps = [Depends(get_current_landlord_api_strict)]

    # NOTE: Landlord page routers (PROTECTED_PAGE_ROUTERS) are NOT registered.
    # The landlord React SPA handles all page routes via the SPA catch-all.
    # Only the SPA catch-all and API routers are active for landlord.

    # 1. Protected API routers (landlord API auth — these register at
    #    /landlord/{landlordUuid}/api/* paths, so they MUST come before
    #    the SPA catch-all which also matches /landlord/{path:path})
    for router in PROTECTED_API_ROUTERS:
        app.include_router(router, dependencies=api_landlord_deps)

    # 2. Admin auth routes
    for router in ADMIN_AUTH_ROUTERS:
        app.include_router(router, prefix="")

    # 3. Landlord auth — no dependency required; handles its own auth checks internally
    for router in LANDLORD_AUTH_ROUTERS:
        app.include_router(router, prefix="")

    # 4. Public routes
    for router in PUBLIC_PAGE_ROUTERS + PUBLIC_API_ROUTERS:
        app.include_router(router)

    # 5. Platform admin
    app.include_router(platform_admin_router)

    # 6. WebSocket sync (no auth dependency — channel-based access control)
    app.include_router(sync_ws_router)

    # 7. SPA catch-all routes: AFTER landlord API routes so they don't shadow
    #    /landlord/{landlordUuid}/api/* paths. The SPA handler returns 404
    #    for paths starting with "api/" so they fall through to landlords.
    app.include_router(spa_router)

    # 8. Landlord alias catch-all: /{landlordUuid}/... (registered last)
    app.include_router(landlord_alias_router)

    register_exception_handlers(app)
