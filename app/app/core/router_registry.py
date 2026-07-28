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

from app.routers.platform_admin import router as platform_admin_router
from app.routers.landlordauth import router as landlordauth_router

# Tenant SPA routes (tenant stays in Docker, served through backend)
from app.pages.spa import router as spa_router
from app.pages.errors import register_exception_handlers

from fastapi import Depends
from app.authentication.landlord.middleware import get_current_landlord_api_strict

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

PUBLIC_API_ROUTERS = [
    public_api_router,
    health_api_router,
    auth_api_router,
    tenant_pdf_api_router,
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

    # 6. WebSocket sync (no auth dependency — channel-based access control)
    app.include_router(sync_ws_router)

    # 7. Tenant SPA routes (tenant stays in Docker — dynamic URL pattern
    #    /{landlordUuid}/t/{tenantId}/{viewToken} can't be served by Cloudflare Pages)
    app.include_router(spa_router)

    register_exception_handlers(app)
