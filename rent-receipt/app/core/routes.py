class Paths:
    HOME = "/"
    BILLING = "/billing"
    HISTORY = "/history"
    TENANTS = "/tenants"
    SETTINGS = "/settings"
    ARCHIVE = "/archive"
    BACKUPS = "/backups"
    TENANT = "/tenant"
    PUBLIC = "/t"

class Names:
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

class Prefixes:
    API = "/api"
    STATIC = "/static"
    UPLOADS = "/static/uploads"

class Templates:
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
