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
        fetch(Routes.ADMINAPIAUTHLOGIN)
        
        # Parameterized routes
        fetch(Routes.admin_api_billing_get(billNo="REC-001"))
        fetch(Routes.admin_api_tenants_get(tenantId=5))
    """
    
    # ── Base ──────────────────────────────────────────────────────
    BASE = property(lambda self: get_base_path())
    
    # ── Health ────────────────────────────────────────────────────
    HEALTHCHECK = property(lambda self: get_route("health", "check"))
    
    # ── Static ────────────────────────────────────────────────────
    STATICUPLOADS = property(lambda self: get_route("static", "uploads"))
    STATIC_ROOT = property(lambda self: get_route("static", "static"))
    STATICADMINASSETS = property(lambda self: get_route("static", "adminAssets"))
    STATICTENANTASSETS = property(lambda self: get_route("static", "tenantAssets"))
    STATICFAVICON = property(lambda self: get_route("static", "favicon"))
    
    # ── Admin Pages ───────────────────────────────────────────────
    ADMINPAGEROOT = property(lambda self: get_route("admin", "pages", "root"))
    ADMINPAGEHOME = property(lambda self: get_route("admin", "pages", "home"))
    ADMINPAGELOGIN = property(lambda self: get_route("admin", "pages", "login"))
    ADMINPAGELOGOUT = property(lambda self: get_route("admin", "pages", "logout"))
    ADMINPAGEDASHBOARD = property(lambda self: get_route("admin", "pages", "dashboard"))
    ADMINPAGEBILLING = property(lambda self: get_route("admin", "pages", "billing"))
    ADMINPAGEHISTORY = property(lambda self: get_route("admin", "pages", "history"))
    ADMINPAGETENANTS = property(lambda self: get_route("admin", "pages", "tenants"))
    ADMINPAGESETTINGS = property(lambda self: get_route("admin", "pages", "settings"))
    ADMINPAGEARCHIVE = property(lambda self: get_route("admin", "pages", "archive"))
    ADMINPAGEBACKUPS = property(lambda self: get_route("admin", "pages", "backups"))
    ADMIN_PAGE_CATCHALL = property(lambda self: get_route("admin", "pages", "catchAll"))
    
    @staticmethod
    def admin_page_tenant_profile(tenantId: int) -> str:
        return get_route("admin", "pages", "TENANTPROFILE", tenantId=tenantId)
    
    # ── Admin API: Setup ──────────────────────────────────────────
    ADMINAPISETUPREQUIRED = property(lambda self: get_route("admin", "api", "setup", "required"))
    ADMINAPISETUPCREATE = property(lambda self: get_route("admin", "api", "setup", "create"))
    
    # ── Admin API: Auth ───────────────────────────────────────────
    ADMINAPIAUTHPUBLICKEY = property(lambda self: get_route("admin", "api", "auth", "publicKey"))
    ADMINAPIAUTHLOGIN = property(lambda self: get_route("admin", "api", "auth", "login"))
    ADMINAPIAUTHLOGINTOTP = property(lambda self: get_route("admin", "api", "auth", "loginTotp"))
    ADMINAPIAUTHREFRESH = property(lambda self: get_route("admin", "api", "auth", "refresh"))
    ADMINAPIAUTHLOGOUT = property(lambda self: get_route("admin", "api", "auth", "logout"))
    ADMINAPIAUTHME = property(lambda self: get_route("admin", "api", "auth", "me"))
    
    # ── Admin API: TOTP ───────────────────────────────────────────
    ADMINAPITOTPQR = property(lambda self: get_route("admin", "api", "totp", "qr"))
    ADMINAPITOTPREGENERATE = property(lambda self: get_route("admin", "api", "totp", "regenerate"))
    
    # ── Admin API: Password ───────────────────────────────────────
    ADMINAPIPASSWORDFORGOTVERIFY = property(lambda self: get_route("admin", "api", "password", "forgotVerify"))
    ADMINAPIPASSWORDFORGOTRESET = property(lambda self: get_route("admin", "api", "password", "forgotReset"))
    
    # ── Admin API: Dashboard ──────────────────────────────────────
    ADMINAPIDASHBOARDSTATS = property(lambda self: get_route("admin", "api", "dashboard", "stats"))
    
    # ── Admin API: Config ─────────────────────────────────────────
    ADMINAPICONFIGGET = property(lambda self: get_route("admin", "api", "config", "get"))
    ADMINAPICONFIGUPDATE = property(lambda self: get_route("admin", "api", "config", "update"))
    ADMINAPICONFIGTHEME = property(lambda self: get_route("admin", "api", "config", "theme"))
    
    # ── Admin API: Billing ────────────────────────────────────────
    ADMINAPIBILLINGFILTER = property(lambda self: get_route("admin", "api", "billing", "filter"))
    ADMINAPIBILLINGMONTHS = property(lambda self: get_route("admin", "api", "billing", "months"))
    ADMINAPIBILLINGPREVIEW = property(lambda self: get_route("admin", "api", "billing", "preview"))
    ADMINAPIBILLINGCREATE = property(lambda self: get_route("admin", "api", "billing", "create"))
    
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
    ADMINAPITENANTSLIST = property(lambda self: get_route("admin", "api", "tenants", "list"))
    ADMINAPITENANTSCREATE = property(lambda self: get_route("admin", "api", "tenants", "create"))
    
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
    ADMINAPIOCCUPANTSLIST = property(lambda self: get_route("admin", "api", "occupants", "list"))
    ADMINAPIOCCUPANTSCREATE = property(lambda self: get_route("admin", "api", "occupants", "create"))
    
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
    ADMINAPISYNCEXPORTCSV = property(lambda self: get_route("admin", "api", "sync", "exportCsv"))
    ADMINAPISYNCEXPORTZIP = property(lambda self: get_route("admin", "api", "sync", "exportZip"))
    ADMINAPISYNCTEMPLATE = property(lambda self: get_route("admin", "api", "sync", "template"))
    
    @staticmethod
    def admin_api_sync_export_excel(format: str) -> str:
        return get_route("admin", "api", "sync", "exportExcel", format=format)
    
    ADMINAPISYNCIMPORTPREVIEW = property(lambda self: get_route("admin", "api", "sync", "importPreview"))
    ADMINAPISYNCIMPORTEXECUTE = property(lambda self: get_route("admin", "api", "sync", "importExecute"))
    
    # ── Admin API: Backups ────────────────────────────────────────
    ADMINAPIBACKUPSLIST = property(lambda self: get_route("admin", "api", "backups", "list"))
    ADMINAPIBACKUPSCREATEMANUAL = property(lambda self: get_route("admin", "api", "backups", "createManual"))
    
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
    ADMINAPISETTINGSUPLOADSIGNATURE = property(lambda self: get_route("admin", "api", "settings", "uploadSignature"))
    ADMINAPISETTINGSDELETESIGNATURE = property(lambda self: get_route("admin", "api", "settings", "deleteSignature"))
    
    # ── Tenant Pages ──────────────────────────────────────────────
    TENANTPAGEROOT = property(lambda self: get_route("tenant", "pages", "root"))
    TENANT_PAGE_CATCHALL = property(lambda self: get_route("tenant", "pages", "catchAll"))
    
    @staticmethod
    def tenant_page_profile(viewToken: str) -> str:
        return get_route("tenant", "pages", "profile", viewToken=viewToken)
    
    # ── Tenant API: Auth ──────────────────────────────────────────
    TENANTAPIAUTHPUBLICKEY = property(lambda self: get_route("tenant", "api", "auth", "publicKey"))
    
    @staticmethod
    def tenant_api_auth_login(viewToken: str) -> str:
        return get_route("tenant", "api", "auth", "login", viewToken=viewToken)
    
    TENANTAPIAUTHREFRESH = property(lambda self: get_route("tenant", "api", "auth", "refresh"))
    TENANTAPIAUTHLOGOUT = property(lambda self: get_route("tenant", "api", "auth", "logout"))
    TENANTAPIAUTHLOGOUTALL = property(lambda self: get_route("tenant", "api", "auth", "logoutAll"))
    
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
