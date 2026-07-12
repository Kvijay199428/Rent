"""
app/core/routes_manifest.py
Shared routes manifest loader — single source of truth for ALL routes.
Both backend and frontend consume routes.json.
"""

import json
import os
import re
from typing import Dict, Any, Optional
from functools import lru_cache

# ── Load manifest ──────────────────────────────────────────────────

_MANIFEST: Dict[str, Any] = {}
_MANIFEST_LOADED = False

def _get_manifest_path() -> str:
    """Find routes.json relative to project root."""
    # Try multiple locations for flexibility
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "shared", "routes.json"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "routes.json"),
        os.path.join(os.path.dirname(__file__), "routes.json"),
        "/code/shared/routes.json",
        "./shared/routes.json",
    ]
    for path in candidates:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return abs_path
    raise FileNotFoundError("routes.json not found. Searched: " + str(candidates))

def load_manifest(force: bool = False) -> Dict[str, Any]:
    """Load the shared routes manifest. Call once at startup."""
    global _MANIFEST, _MANIFEST_LOADED
    if _MANIFEST_LOADED and not force:
        return _MANIFEST
    
    path = _get_manifest_path()
    with open(path, "r", encoding="utf-8") as f:
        _MANIFEST = json.load(f)
    _MANIFEST_LOADED = True
    return _MANIFEST

def get_manifest() -> Dict[str, Any]:
    """Get the loaded manifest. Auto-loads if not already loaded."""
    if not _MANIFEST_LOADED:
        load_manifest()
    return _MANIFEST

# ── Route resolution helpers ───────────────────────────────────────

def _resolve_path(path_template: str, **kwargs) -> str:
    """Replace {param} placeholders with actual values."""
    result = path_template
    for key, value in kwargs.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result

def get_base_path() -> str:
    """Get the application base path (e.g., '/rent')."""
    return get_manifest().get("basePath", "")

def get_full_path(path_template: str, **kwargs) -> str:
    """Get a full URL path with basePath prepended."""
    base = get_base_path()
    path = _resolve_path(path_template, **kwargs)
    return f"{base}{path}" if base else path

def get_route(*path_parts: str, **kwargs) -> str:
    """
    Navigate the manifest tree by dot-notation keys.
    
    Examples:
        get_route("admin", "api", "auth", "login")  -> "/rent/admin/api/login"
        get_route("admin", "api", "billing", "get", billNo="REC-001")  -> "/rent/admin/api/bill/REC-001"
    """
    node = get_manifest()
    for part in path_parts:
        if not isinstance(node, dict):
            raise KeyError(f"Cannot navigate past '{part}' — not a dict")
        if part not in node:
            available = list(node.keys())
            raise KeyError(f"Route key '{part}' not found. Available: {available}")
        node = node[part]
    
    if not isinstance(node, str):
        raise ValueError(f"Route path at {path_parts} is not a string: {type(node)}")
    
    return get_full_path(node, **kwargs)

# ── Convenience class with ALL routes ─────────────────────────────

class Routes:
    """
    Static access to every route in the application.
    All paths include the basePath (e.g., '/rent').
    
    Usage:
        from app.core.routes_manifest import Routes
        
        # Static routes
        fetch(Routes.ADMIN_API_AUTH_LOGIN)
        
        # Parameterized routes
        fetch(Routes.admin_api_billing_get(billNo="REC-001"))
        fetch(Routes.admin_api_tenants_get(tenantId=5))
    """
    
    # ── Base ──────────────────────────────────────────────────────
    BASE = property(lambda self: get_base_path())
    
    # ── Health ────────────────────────────────────────────────────
    HEALTH_CHECK = property(lambda self: get_route("health", "check"))
    
    # ── Static ────────────────────────────────────────────────────
    STATIC_UPLOADS = property(lambda self: get_route("static", "uploads"))
    STATIC_ROOT = property(lambda self: get_route("static", "static"))
    STATIC_ADMIN_ASSETS = property(lambda self: get_route("static", "adminAssets"))
    STATIC_TENANT_ASSETS = property(lambda self: get_route("static", "tenantAssets"))
    STATIC_FAVICON = property(lambda self: get_route("static", "favicon"))
    
    # ── Admin Pages ───────────────────────────────────────────────
    ADMIN_PAGE_ROOT = property(lambda self: get_route("admin", "pages", "root"))
    ADMIN_PAGE_HOME = property(lambda self: get_route("admin", "pages", "home"))
    ADMIN_PAGE_LOGIN = property(lambda self: get_route("admin", "pages", "login"))
    ADMIN_PAGE_LOGOUT = property(lambda self: get_route("admin", "pages", "logout"))
    ADMIN_PAGE_DASHBOARD = property(lambda self: get_route("admin", "pages", "dashboard"))
    ADMIN_PAGE_BILLING = property(lambda self: get_route("admin", "pages", "billing"))
    ADMIN_PAGE_HISTORY = property(lambda self: get_route("admin", "pages", "history"))
    ADMIN_PAGE_TENANTS = property(lambda self: get_route("admin", "pages", "tenants"))
    ADMIN_PAGE_SETTINGS = property(lambda self: get_route("admin", "pages", "settings"))
    ADMIN_PAGE_ARCHIVE = property(lambda self: get_route("admin", "pages", "archive"))
    ADMIN_PAGE_BACKUPS = property(lambda self: get_route("admin", "pages", "backups"))
    ADMIN_PAGE_CATCHALL = property(lambda self: get_route("admin", "pages", "catchAll"))
    
    @staticmethod
    def admin_page_tenant_profile(tenantId: int) -> str:
        return get_route("admin", "pages", "tenantProfile", tenantId=tenantId)
    
    # ── Admin API: Setup ──────────────────────────────────────────
    ADMIN_API_SETUP_REQUIRED = property(lambda self: get_route("admin", "api", "setup", "required"))
    ADMIN_API_SETUP_CREATE = property(lambda self: get_route("admin", "api", "setup", "create"))
    
    # ── Admin API: Auth ───────────────────────────────────────────
    ADMIN_API_AUTH_PUBLIC_KEY = property(lambda self: get_route("admin", "api", "auth", "publicKey"))
    ADMIN_API_AUTH_LOGIN = property(lambda self: get_route("admin", "api", "auth", "login"))
    ADMIN_API_AUTH_LOGIN_TOTP = property(lambda self: get_route("admin", "api", "auth", "loginTotp"))
    ADMIN_API_AUTH_REFRESH = property(lambda self: get_route("admin", "api", "auth", "refresh"))
    ADMIN_API_AUTH_LOGOUT = property(lambda self: get_route("admin", "api", "auth", "logout"))
    ADMIN_API_AUTH_ME = property(lambda self: get_route("admin", "api", "auth", "me"))
    
    # ── Admin API: TOTP ───────────────────────────────────────────
    ADMIN_API_TOTP_QR = property(lambda self: get_route("admin", "api", "totp", "qr"))
    ADMIN_API_TOTP_REGENERATE = property(lambda self: get_route("admin", "api", "totp", "regenerate"))
    
    # ── Admin API: Password ───────────────────────────────────────
    ADMIN_API_PASSWORD_FORGOT_VERIFY = property(lambda self: get_route("admin", "api", "password", "forgotVerify"))
    ADMIN_API_PASSWORD_FORGOT_RESET = property(lambda self: get_route("admin", "api", "password", "forgotReset"))
    
    # ── Admin API: Dashboard ──────────────────────────────────────
    ADMIN_API_DASHBOARD_STATS = property(lambda self: get_route("admin", "api", "dashboard", "stats"))
    
    # ── Admin API: Config ─────────────────────────────────────────
    ADMIN_API_CONFIG_GET = property(lambda self: get_route("admin", "api", "config", "get"))
    ADMIN_API_CONFIG_UPDATE = property(lambda self: get_route("admin", "api", "config", "update"))
    ADMIN_API_CONFIG_THEME = property(lambda self: get_route("admin", "api", "config", "theme"))
    
    # ── Admin API: Billing ────────────────────────────────────────
    ADMIN_API_BILLING_FILTER = property(lambda self: get_route("admin", "api", "billing", "filter"))
    ADMIN_API_BILLING_MONTHS = property(lambda self: get_route("admin", "api", "billing", "months"))
    ADMIN_API_BILLING_PREVIEW = property(lambda self: get_route("admin", "api", "billing", "preview"))
    ADMIN_API_BILLING_CREATE = property(lambda self: get_route("admin", "api", "billing", "create"))
    
    @staticmethod
    def admin_api_billing_get(billNo: str) -> str:
        return get_route("admin", "api", "billing", "get", billNo=billNo)
    
    @staticmethod
    def admin_api_billing_update(billNo: str) -> str:
        return get_route("admin", "api", "billing", "update", billNo=billNo)
    
    @staticmethod
    def admin_api_billing_update_payment(billNo: str) -> str:
        return get_route("admin", "api", "billing", "updatePayment", billNo=billNo)
    
    @staticmethod
    def admin_api_billing_archive(billNo: str) -> str:
        return get_route("admin", "api", "billing", "archive", billNo=billNo)
    
    @staticmethod
    def admin_api_billing_restore(billNo: str) -> str:
        return get_route("admin", "api", "billing", "restore", billNo=billNo)
    
    @staticmethod
    def admin_api_billing_delete(billNo: str) -> str:
        return get_route("admin", "api", "billing", "delete", billNo=billNo)
    
    # ── Admin API: Tenants ────────────────────────────────────────
    ADMIN_API_TENANTS_LIST = property(lambda self: get_route("admin", "api", "tenants", "list"))
    ADMIN_API_TENANTS_CREATE = property(lambda self: get_route("admin", "api", "tenants", "create"))
    
    @staticmethod
    def admin_api_tenants_get(tenantId: int) -> str:
        return get_route("admin", "api", "tenants", "get", tenantId=tenantId)
    
    @staticmethod
    def admin_api_tenants_update(tenantId: int) -> str:
        return get_route("admin", "api", "tenants", "update", tenantId=tenantId)
    
    @staticmethod
    def admin_api_tenants_delete(tenantId: int) -> str:
        return get_route("admin", "api", "tenants", "delete", tenantId=tenantId)
    
    @staticmethod
    def admin_api_tenants_change_pin(tenantId: int) -> str:
        return get_route("admin", "api", "tenants", "changePin", tenantId=tenantId)
    
    @staticmethod
    def admin_api_tenants_reveal_pin(tenantId: int) -> str:
        return get_route("admin", "api", "tenants", "revealPin", tenantId=tenantId)
    
    @staticmethod
    def admin_api_tenants_receipts(tenantName: str) -> str:
        return get_route("admin", "api", "tenants", "receipts", tenantName=tenantName)
    
    # ── Admin API: Occupants ──────────────────────────────────────
    ADMIN_API_OCCUPANTS_LIST = property(lambda self: get_route("admin", "api", "occupants", "list"))
    ADMIN_API_OCCUPANTS_CREATE = property(lambda self: get_route("admin", "api", "occupants", "create"))
    
    @staticmethod
    def admin_api_occupants_mark_inactive(tenantId: int, occupantUuid: str) -> str:
        return get_route("admin", "api", "occupants", "markInactive", tenantId=tenantId, occupantUuid=occupantUuid)
    
    @staticmethod
    def admin_api_occupants_delete(tenantId: int, occupantUuid: str) -> str:
        return get_route("admin", "api", "occupants", "delete", tenantId=tenantId, occupantUuid=occupantUuid)
    
    @staticmethod
    def admin_api_occupants_get_file(filename: str) -> str:
        return get_route("admin", "api", "occupants", "getFile", filename=filename)
    
    # ── Admin API: PDF ────────────────────────────────────────────
    @staticmethod
    def admin_api_pdf_download(billNo: str) -> str:
        return get_route("admin", "api", "pdf", "download", billNo=billNo)
    
    @staticmethod
    def admin_api_pdf_view(billNo: str) -> str:
        return get_route("admin", "api", "pdf", "view", billNo=billNo)
    
    # ── Admin API: WhatsApp ───────────────────────────────────────
    @staticmethod
    def admin_api_whatsapp_send_single(billNo: str) -> str:
        return get_route("admin", "api", "whatsapp", "sendSingle", billNo=billNo)
    
    # ── Admin API: Sync ─────────────────────────────────────────────
    ADMIN_API_SYNC_EXPORT_CSV = property(lambda self: get_route("admin", "api", "sync", "exportCsv"))
    ADMIN_API_SYNC_EXPORT_ZIP = property(lambda self: get_route("admin", "api", "sync", "exportZip"))
    ADMIN_API_SYNC_TEMPLATE = property(lambda self: get_route("admin", "api", "sync", "template"))
    
    @staticmethod
    def admin_api_sync_export_excel(format: str) -> str:
        return get_route("admin", "api", "sync", "exportExcel", format=format)
    
    ADMIN_API_SYNC_IMPORT_PREVIEW = property(lambda self: get_route("admin", "api", "sync", "importPreview"))
    ADMIN_API_SYNC_IMPORT_EXECUTE = property(lambda self: get_route("admin", "api", "sync", "importExecute"))
    
    # ── Admin API: Backups ────────────────────────────────────────
    ADMIN_API_BACKUPS_LIST = property(lambda self: get_route("admin", "api", "backups", "list"))
    ADMIN_API_BACKUPS_CREATE_MANUAL = property(lambda self: get_route("admin", "api", "backups", "createManual"))
    
    @staticmethod
    def admin_api_backups_delete(backupId: str) -> str:
        return get_route("admin", "api", "backups", "delete", backupId=backupId)
    
    @staticmethod
    def admin_api_backups_verify(backupId: str) -> str:
        return get_route("admin", "api", "backups", "verify", backupId=backupId)
    
    @staticmethod
    def admin_api_backups_restore(backupId: str) -> str:
        return get_route("admin", "api", "backups", "restore", backupId=backupId)
    
    @staticmethod
    def admin_api_backups_download(backupId: str) -> str:
        return get_route("admin", "api", "backups", "download", backupId=backupId)
    
    @staticmethod
    def admin_api_backups_metadata(backupId: str) -> str:
        return get_route("admin", "api", "backups", "metadata", backupId=backupId)
    
    # ── Admin API: Settings ───────────────────────────────────────
    ADMIN_API_SETTINGS_UPLOAD_SIGNATURE = property(lambda self: get_route("admin", "api", "settings", "uploadSignature"))
    ADMIN_API_SETTINGS_DELETE_SIGNATURE = property(lambda self: get_route("admin", "api", "settings", "deleteSignature"))
    
    # ── Tenant Pages ──────────────────────────────────────────────
    TENANT_PAGE_ROOT = property(lambda self: get_route("tenant", "pages", "root"))
    TENANT_PAGE_CATCHALL = property(lambda self: get_route("tenant", "pages", "catchAll"))
    
    @staticmethod
    def tenant_page_profile(viewToken: str) -> str:
        return get_route("tenant", "pages", "profile", viewToken=viewToken)
    
    # ── Tenant API: Auth ──────────────────────────────────────────
    TENANT_API_AUTH_PUBLIC_KEY = property(lambda self: get_route("tenant", "api", "auth", "publicKey"))
    
    @staticmethod
    def tenant_api_auth_login(viewToken: str) -> str:
        return get_route("tenant", "api", "auth", "login", viewToken=viewToken)
    
    TENANT_API_AUTH_REFRESH = property(lambda self: get_route("tenant", "api", "auth", "refresh"))
    TENANT_API_AUTH_LOGOUT = property(lambda self: get_route("tenant", "api", "auth", "logout"))
    TENANT_API_AUTH_LOGOUT_ALL = property(lambda self: get_route("tenant", "api", "auth", "logoutAll"))
    
    # ── Tenant API: Profile ─────────────────────────────────────
    @staticmethod
    def tenant_api_profile_get(viewToken: str) -> str:
        return get_route("tenant", "api", "profile", "get", viewToken=viewToken)
    
    # ── Tenant API: KYC ───────────────────────────────────────────
    @staticmethod
    def tenant_api_kyc_upload(viewToken: str) -> str:
        return get_route("tenant", "api", "kyc", "upload", viewToken=viewToken)
    
    @staticmethod
    def tenant_api_kyc_mark_inactive(viewToken: str, occupantUuid: str) -> str:
        return get_route("tenant", "api", "kyc", "markInactive", viewToken=viewToken, occupantUuid=occupantUuid)
    
    @staticmethod
    def tenant_api_kyc_delete(viewToken: str, occupantUuid: str) -> str:
        return get_route("tenant", "api", "kyc", "delete", viewToken=viewToken, occupantUuid=occupantUuid)
    
    @staticmethod
    def tenant_api_kyc_get_file(filename: str) -> str:
        return get_route("tenant", "api", "kyc", "getFile", filename=filename)


# ── Legacy redirect paths (for reference) ─────────────────────────

LEGACY_REDIRECTS = [
    "/dashboard", "/billing", "/history", "/tenants",
    "/settings", "/archive", "/backups", "/login"
]

# ── Initialize on import (for eager loading) ─────────────────────
# Call load_manifest() explicitly in startup.py instead
