from fastapi import FastAPI

# API Routers
from app.api.billing import router as billing_api_router
from app.api.tenants import router as tenants_api_router
from app.api.settings import router as settings_api_router
from app.api.backup import router as backup_api_router
from app.api.pdf import router as pdf_api_router
from app.api.whatsapp import router as whatsapp_api_router
from app.api.sync import router as sync_api_router
from app.api.public import router as public_api_router
from app.api.health import router as health_api_router
from app.routers.auth import router as auth_api_router

# Page Routers
from app.pages.dashboard import router as dashboard_page_router
from app.pages.billing import router as billing_page_router
from app.pages.history import router as history_page_router
from app.pages.archive import router as archive_page_router
from app.pages.settings import router as settings_page_router
from app.pages.tenants import router as tenants_page_router
from app.pages.backups import router as backups_page_router
from app.pages.public import router as public_page_router
from app.pages.redirects import router as redirects_router
from app.pages.errors import register_exception_handlers

from app.routers.admin_auth import router as admin_auth_router
from fastapi import Depends
from app.authentication.admin.middleware import get_current_admin_page, get_current_admin_api

PROTECTED_PAGE_ROUTERS = [
    dashboard_page_router,
    billing_page_router,
    history_page_router,
    archive_page_router,
    settings_page_router,
    tenants_page_router,
    backups_page_router
]

PUBLIC_PAGE_ROUTERS = [
    public_page_router,
    redirects_router
]

PROTECTED_API_ROUTERS = [
    billing_api_router,
    tenants_api_router,
    settings_api_router,
    backup_api_router,
    whatsapp_api_router,
    sync_api_router,
    pdf_api_router
]

PUBLIC_API_ROUTERS = [
    public_api_router,
    health_api_router,
    auth_api_router
]

ADMIN_AUTH_ROUTERS = [
    admin_auth_router
]

def register_all_routers(app: FastAPI):
    page_admin_deps = [Depends(get_current_admin_page)]
    api_admin_deps = [Depends(get_current_admin_api)]
    
    for router in PROTECTED_PAGE_ROUTERS:
        app.include_router(router, prefix="/admin", dependencies=page_admin_deps)
        
    for router in PROTECTED_API_ROUTERS:
        app.include_router(router, prefix="/admin", dependencies=api_admin_deps)
        
    for router in ADMIN_AUTH_ROUTERS:
        app.include_router(router, prefix="/admin")
        
    for router in PUBLIC_PAGE_ROUTERS + PUBLIC_API_ROUTERS:
        app.include_router(router)
        
    register_exception_handlers(app)
