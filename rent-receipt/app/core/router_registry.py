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

# Page Routers
from app.pages.dashboard import router as dashboard_page_router
from app.pages.billing import router as billing_page_router
from app.pages.history import router as history_page_router
from app.pages.archive import router as archive_page_router
from app.pages.settings import router as settings_page_router
from app.pages.tenants import router as tenants_page_router
from app.pages.backups import router as backups_page_router
from app.pages.public import router as public_page_router
from app.pages.errors import register_exception_handlers

PAGE_ROUTERS = [
    dashboard_page_router,
    billing_page_router,
    history_page_router,
    archive_page_router,
    settings_page_router,
    tenants_page_router,
    backups_page_router,
    public_page_router
]

API_ROUTERS = [
    billing_api_router,
    tenants_api_router,
    settings_api_router,
    backup_api_router,
    pdf_api_router,
    whatsapp_api_router,
    sync_api_router,
    public_api_router,
    health_api_router
]

def register_all_routers(app: FastAPI):
    for router in PAGE_ROUTERS:
        app.include_router(router)
    for router in API_ROUTERS:
        app.include_router(router)
    register_exception_handlers(app)
