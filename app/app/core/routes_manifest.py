# app\app\core\routes_manifest.py

"""
Auto-generated route manifest from shared/routes.json.
Do not edit manually if possible. If you change routes.json, update this file.
"""
# Add this class to app/core/routes_manifest.py, before the Routes class

class Paths:
    """Legacy path constants. Use Routes class for new code."""
    HOME = "/"
    BILLING = "/billing"
    HISTORY = "/history"
    TENANTS = "/tenants"
    SETTINGS = "/settings"
    ARCHIVE = "/archive"
    BACKUPS = "/backups"
    TENANT = "/tenant"
    PUBLIC = "/t"

class Routes:
    BASE_PATH = "/rent"

    HEALTH_CHECK = "/health"

    # Admin Pages
    ADMIN_PAGE_ROOT = "/admin/"
    ADMIN_PAGE_HOME = "/admin/home"
    ADMIN_PAGE_LOGIN = "/admin/login"
    ADMIN_PAGE_LOGOUT = "/admin/logout"
    ADMIN_PAGE_DASHBOARD = "/admin/dashboard"
    ADMIN_PAGE_BILLING = "/admin/billing"
    ADMIN_PAGE_HISTORY = "/admin/history"
    ADMIN_PAGE_TENANTS = "/admin/tenants"
    ADMIN_PAGE_SETTINGS = "/admin/settings"
    ADMIN_PAGE_ARCHIVE = "/admin/archive"
    ADMIN_PAGE_BACKUPS = "/admin/backups"
    ADMIN_PAGE_CATCH_ALL = "/admin/*"
    ADMIN_PAGE_TENANT_PROFILE = "/admin/tenant/{tenant_id}"

    # Admin API: Setup
    ADMIN_API_SETUP_REQUIRED = "/admin/api/setup/required"
    ADMIN_API_SETUP_CREATE = "/admin/api/setup/create"

    # Admin API: Auth
    ADMIN_API_AUTH_PUBLIC_KEY = "/admin/api/auth/public-key"
    ADMIN_API_AUTH_LOGIN = "/admin/api/login"
    ADMIN_API_AUTH_LOGIN_TOTP = "/admin/api/login/totp"
    ADMIN_API_AUTH_REFRESH = "/admin/api/refresh"
    ADMIN_API_AUTH_LOGOUT = "/admin/api/logout/json"
    ADMIN_API_AUTH_ME = "/admin/api/me"

    # Admin API: Totp
    ADMIN_API_TOTP_QR = "/admin/api/totp/qr"
    ADMIN_API_TOTP_REGENERATE = "/admin/api/totp/regenerate"

    # Admin API: Password
    ADMIN_API_PASSWORD_FORGOT_VERIFY = "/admin/api/forgot-password/verify"
    ADMIN_API_PASSWORD_FORGOT_RESET = "/admin/api/forgot-password/reset"

    # Admin API: Dashboard
    ADMIN_API_DASHBOARD_STATS = "/admin/api/dashboard"

    # Admin API: Config
    ADMIN_API_CONFIG_GET = "/admin/api/config"
    ADMIN_API_CONFIG_UPDATE = "/admin/api/config/update"
    ADMIN_API_CONFIG_THEME = "/admin/api/ui/theme"

    # Admin API: Billing
    ADMIN_API_BILLING_FILTER = "/admin/api/receipts/filter"
    ADMIN_API_BILLING_MONTHS = "/admin/api/receipts/months"
    ADMIN_API_BILLING_PREVIEW = "/admin/api/receipts/preview"
    ADMIN_API_BILLING_CREATE = "/admin/api/receipts/create"
    ADMIN_API_BILLING_GET = "/admin/api/receipts/{billno}"
    ADMIN_API_BILLING_UPDATE = "/admin/api/receipts/{billno}"
    ADMIN_API_BILLING_UPDATE_PAYMENT = "/admin/api/receipts/{billno}/payment-status"
    ADMIN_API_BILLING_ARCHIVE = "/admin/api/receipts/{billno}/archive"
    ADMIN_API_BILLING_RESTORE = "/admin/api/receipts/{billno}/restore"
    ADMIN_API_BILLING_DELETE = "/admin/api/receipts/{billno}"

    # Admin API: Tenants
    ADMIN_API_TENANTS_LIST = "/admin/api/tenants"
    ADMIN_API_TENANTS_CREATE = "/admin/api/tenants"
    ADMIN_API_TENANTS_GET = "/admin/api/tenants/{tenant_id}"
    ADMIN_API_TENANTS_UPDATE = "/admin/api/tenants/{tenant_id}"
    ADMIN_API_TENANTS_DELETE = "/admin/api/tenants/{tenant_id}"
    ADMIN_API_TENANTS_CHANGE_PIN = "/admin/api/tenants/{tenant_id}/change-pin"
    ADMIN_API_TENANTS_REVEAL_PIN = "/admin/api/tenants/{tenant_id}/reveal-pin"
    ADMIN_API_TENANTS_RECEIPTS = "/admin/api/tenants/{tenant_name}/receipts"

    # Admin API: Occupants
    ADMIN_API_OCCUPANTS_LIST = "/admin/api/occupants"
    ADMIN_API_OCCUPANTS_CREATE = "/admin/api/occupants"
    ADMIN_API_OCCUPANTS_MARK_INACTIVE = "/admin/api/occupants/{tenant_id}/{occupant_uuid}/inactive"
    ADMIN_API_OCCUPANTS_DELETE = "/admin/api/occupants/{tenant_id}/{occupant_uuid}"
    ADMIN_API_OCCUPANTS_GET_FILE = "/admin/api/occupants/file/{filename}"

    # Admin API: Pdf
    ADMIN_API_PDF_DOWNLOAD = "/admin/api/pdf/receipt/{billno}"
    ADMIN_API_PDF_VIEW = "/admin/api/pdf/receipt/{billno}/view"

    # Admin API: Whatsapp
    ADMIN_API_WHATSAPP_SEND_SINGLE = "/admin/api/whatsapp/send-single/{billno}"

    # Admin API: Sync
    ADMIN_API_SYNC_EXPORT_CSV = "/admin/api/export-csv"
    ADMIN_API_SYNC_EXPORT_ZIP = "/admin/api/export-zip"
    ADMIN_API_SYNC_TEMPLATE = "/admin/api/import-template"
    # ADMIN_API_SYNC_EXPORT_EXCEL = "/admin/api/export-excel?format={format}"
    ADMIN_API_SYNC_EXPORT_EXCEL = "/admin/api/export-excel"
    ADMIN_API_SYNC_IMPORT_PREVIEW = "/admin/api/import-preview"
    ADMIN_API_SYNC_IMPORT_EXECUTE = "/admin/api/import-execute"

    # Admin API: Backups
    ADMIN_API_BACKUPS_LIST = "/admin/api/backups"
    ADMIN_API_BACKUPS_CREATE_MANUAL = "/admin/api/backups/manual"
    ADMIN_API_BACKUPS_DELETE = "/admin/api/backups/{backup_id}"
    ADMIN_API_BACKUPS_VERIFY = "/admin/api/backups/{backup_id}/verify"
    ADMIN_API_BACKUPS_RESTORE = "/admin/api/backups/{backup_id}/restore"
    ADMIN_API_BACKUPS_DOWNLOAD = "/admin/api/backups/{backup_id}/download"
    ADMIN_API_BACKUPS_METADATA = "/admin/api/backups/{backup_id}/metadata"

    # Admin API: Settings
    ADMIN_API_SETTINGS_UPLOAD_SIGNATURE = "/admin/api/settings/upload-signature"
    ADMIN_API_SETTINGS_DELETE_SIGNATURE = "/admin/api/settings/delete-signature"

    # Tenant Pages
    TENANT_PAGE_ROOT = '/t/{view_token}'

    # Tenant API: Auth
    TENANT_API_AUTH_PUBLIC_KEY = "/api/auth/public-key"
    TENANT_API_AUTH_LOGIN = "/api/auth/login/{view_token}"
    TENANT_API_AUTH_REFRESH = "/api/auth/refresh/{view_token}"
    TENANT_API_AUTH_LOGOUT = "/api/auth/logout/{view_token}"
    TENANT_API_AUTH_LOGOUT_ALL = "/api/auth/logout-all/{view_token}"

    # Tenant API: Profile
    TENANT_API_PROFILE_GET = "/api/{view_token}"

    # Tenant API: Kyc
    TENANT_API_KYC_UPLOAD = "/api/{view_token}/kyc"
    TENANT_API_KYC_MARK_INACTIVE = "/api/{view_token}/kyc/{occupant_uuid}/inactive"
    TENANT_API_KYC_DELETE = "/api/{view_token}/kyc/{occupant_uuid}"
    TENANT_API_KYC_GET_FILE = "/api/{view_token}/kyc/file/{filename}"

    TENANT_API_PDF_VIEW = "/t/api/{view_token}/pdf/{billno}/view"
    TENANT_API_PDF_DOWNLOAD = "/t/api/{view_token}/pdf/{billno}/download"

    # Static & Health
    STATIC_UPLOADS = "/static/uploads"
    STATIC_STATIC = "/static"
    STATIC_ADMIN_ASSETS = "/admin/assets"
    STATIC_TENANT_ASSETS = "/tenant/assets"
    STATIC_FAVICON = "/admin/favicon.svg"


class Names:
    """Route names for use with request.url_for() and FastAPI name= parameter."""

    # Pages
    HOME = "home_page"
    BILLING_PAGE = "billing_page"
    HISTORY_PAGE = "history_page"
    TENANTS_PAGE = "tenants_page"
    SETTINGS_PAGE = "settings_page"
    ARCHIVE_PAGE = "archive_page"
    BACKUPS_PAGE = "backups_page"
    TENANT_PROFILE_PAGE = "tenant_profile_page"
    PUBLIC_TENANT_PROFILE_GET = "public_tenant_profile_get"
    PUBLIC_TENANT_PROFILE_POST = "public_tenant_profile_post"
    FAVICON = "favicon"

    # API - Backups
    API_GET_BACKUPS = "api_get_backups"
    API_CREATE_MANUAL_BACKUP = "api_create_manual_backup"
    API_DELETE_BACKUP = "api_delete_backup"
    API_VERIFY_BACKUP = "api_verify_backup"
    API_RESTORE_BACKUP = "api_restore_backup"
    API_DOWNLOAD_BACKUP = "api_download_backup"
    API_DOWNLOAD_METADATA = "api_download_metadata"

    # API - Billing
    API_FILTER_BILLS = "api_filter_bills"
    API_BILLING_MONTHS = "api_billing_months"
    API_BILLING_PREVIEW = "api_billing_preview"
    API_GET_SINGLE_BILL = "api_get_single_bill"
    API_CREATE_BILL = "api_create_bill"
    API_UPDATE_BILL = "api_update_bill"
    API_UPDATE_PAYMENT = "api_update_payment"
    API_ARCHIVE_BILL = "api_archive_bill"
    API_RESTORE_BILL = "api_restore_bill"
    API_DELETE_BILL = "api_delete_bill"

    # API - PDF
    PDF_DOWNLOAD = "download_pdf"
    PDF_VIEW = "view_pdf"

    # API - Public / KYC
    PUBLIC_TENANT_KYC_UPLOAD = "public_tenant_kyc_upload"
    PUBLIC_TENANT_KYC_MARK_INACTIVE = "public_tenant_kyc_mark_inactive"
    PUBLIC_TENANT_KYC_DELETE = "public_tenant_kyc_delete"
    GET_KYC_FILE = "get_kyc_file"

    # API - Settings
    API_GET_CONFIG = "api_get_config"
    API_UPLOAD_SIGNATURE = "api_upload_signature"
    API_DELETE_SIGNATURE = "api_delete_signature"
    UPDATE_CONFIG = "update_config"
    UPDATE_THEME = "update_theme"

    # API - Sync
    EXPORT_RECEIPTS_CSV = "export_receipts_csv"
    EXPORT_FULL_ZIP = "export_full_zip"
    DOWNLOAD_EXCEL_TEMPLATE = "download_excel_template"
    EXPORT_EXCEL_DATA = "export_excel_data"
    IMPORT_PREVIEW_DATA = "import_preview_data"
    IMPORT_EXECUTE_DATA = "import_execute_data"

    # API - Tenants
    API_GET_TENANTS = "api_get_tenants"
    API_GET_TENANT = "api_get_tenant"
    API_GET_TENANT_RECEIPTS = "api_get_tenant_receipts"
    API_ADD_TENANT = "api_add_tenant"
    API_UPDATE_TENANT = "api_update_tenant"
    API_DELETE_TENANT = "api_delete_tenant"

    # API - Whatsapp
    SEND_WHATSAPP_SINGLE = "send_whatsapp_single"
    SEND_WHATSAPP_BULK = "send_whatsapp_bulk"

    # API - Health
    HEALTH_CHECK = "health_check"

    # Auth
    ADMIN_LOGIN = "adminloginpost"
    ADMIN_LOGIN_TOTP = "admin_login_totp"
    ADMIN_LOGOUT = "adminlogout"
    ADMIN_LOGOUT_JSON = "adminlogoutjson"
    ADMIN_REFRESH = "admin_refresh"
    ADMIN_ME = "adminme"
    ADMIN_SETUP_REQUIRED = "admin_setup_required"
    ADMIN_SETUP_CREATE = "admin_setup_create"
    ADMIN_TOTP_QR = "admin_totp_qr"
    ADMIN_TOTP_REGENERATE = "admin_totp_regenerate"
    ADMIN_FORGOT_VERIFY = "admin_forgot_password_verify"
    ADMIN_FORGOT_RESET = "admin_forgot_password_reset"
    ADMIN_PUBLIC_KEY = "admin_public_key"

    CHANGE_TENANT_PIN = "change_tenant_pin"
    ADMIN_REVEAL_PIN = "admin_reveal_tenant_pin"

    # Tenant Auth
    TENANT_PUBLIC_KEY = "public_key"
    TENANT_LOGIN = "public_tenant_login"
    TENANT_LOGOUT = "auth_logout"
    TENANT_LOGOUT_ALL = "auth_logout_all"
    TENANT_REFRESH = "auth_refresh"
    TENANT_PDF_VIEW = "tenant_pdf_view"
    TENANT_PDF_DOWNLOAD = "tenant_pdf_download"

    # API - Occupants
    API_GET_OCCUPANTS = "api_get_occupants"
    API_CREATE_OCCUPANT = "api_create_occupant"
    API_MARK_OCCUPANT_INACTIVE = "api_mark_occupant_inactive"
    API_DELETE_OCCUPANT = "api_delete_occupant"


class Templates:
    """Jinja2 template filenames."""
    DASHBOARD = "dashboard.html"
    BILLING = "billing.html"
    HISTORY = "history.html"
    SETTINGS = "settings.html"
    TENANTS = "tenants.html"
    ARCHIVE = "archive.html"
    BACKUPS = "backups.html"
    ERROR = "error.html"
    TENANT_PROFILE = "tenant_profile.html"
    TENANT_PUBLIC_PROFILE = "tenant_public_profile.html"


class Prefixes:
    """URL path prefixes."""
    API = "/api"
    STATIC = "/static"
    UPLOADS = "/static/uploads"