# app\app\core\routes_manifest.py

"""
Auto-generated route manifest from shared/routes.json.
Do not edit manually if possible. If you change routes.json, update this file.
"""
from app.core.routes_manifest_tenant import TenantRoutes, TenantNames

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
    BASEPATH = "/rent"

    HEALTHCHECK = "/health"

    # Admin Pages
    ADMINPAGEROOT = "/admin/"
    ADMINPAGEHOME = "/admin/home"
    ADMINPAGELOGIN = "/admin/login"
    ADMINPAGELOGOUT = "/admin/logout"
    ADMINPAGEDASHBOARD = "/admin/dashboard"
    ADMINPAGEBILLING = "/admin/billing"
    ADMINPAGEHISTORY = "/admin/history"
    ADMINPAGETENANTS = "/admin/tenants"
    ADMINPAGESETTINGS = "/admin/settings"
    ADMINPAGEARCHIVE = "/admin/archive"
    ADMINPAGEBACKUPS = "/admin/backups"
    ADMINPAGECATCHALL = "/admin/*"
    ADMINPAGETENANTPROFILE = "/admin/tenant/{tenantId}"

    # Admin API: Setup
    ADMINAPISETUPREQUIRED = "/admin/api/setup/required"
    ADMINAPISETUPCREATE = "/admin/api/setup/create"

    # Admin API: Auth
    ADMINAPIAUTHPUBLICKEY = "/admin/api/auth/public-key"
    ADMINAPIAUTHLOGIN = "/admin/api/login"
    ADMINAPIAUTHLOGINTOTP = "/admin/api/login/totp"
    ADMINAPIAUTHREFRESH = "/admin/api/refresh"
    ADMINAPIAUTHLOGOUT = "/admin/api/logout/json"
    ADMINAPIAUTHME = "/admin/api/me"

    # Admin API: Totp
    ADMINAPITOTPQR = "/admin/api/totp/qr"
    ADMINAPITOTPREGENERATE = "/admin/api/totp/regenerate"

    # Admin API: Password
    ADMINAPIPASSWORDFORGOTVERIFY = "/admin/api/forgot-password/verify"
    ADMINAPIPASSWORDFORGOTRESET = "/admin/api/forgot-password/reset"

    # Admin API: Dashboard
    ADMINAPIDASHBOARDSTATS = "/admin/api/dashboard"

    # Admin API: Config
    ADMINAPICONFIGGET = "/admin/api/config"
    ADMINAPICONFIGUPDATE = "/admin/api/config/update"
    ADMINAPICONFIGTHEME = "/admin/api/ui/theme"

    # Admin API: Billing
    ADMINAPIBILLINGFILTER = "/admin/api/receipts/filter"
    ADMINAPIBILLINGMONTHS = "/admin/api/receipts/months"
    ADMINAPIBILLINGPREVIEW = "/admin/api/receipts/preview"
    ADMINAPIBILLINGCREATE = "/admin/api/tenants/{tenantId}/receipts"
    ADMINAPIBILLINGGET = "/admin/api/tenants/{tenantId}/receipts/{billNo}"
    ADMINAPIBILLINGUPDATE = "/admin/api/tenants/{tenantId}/receipts/{billNo}"
    ADMINAPIBILLINGUPDATEPAYMENT = "/admin/api/tenants/{tenantId}/receipts/{billNo}/payment-status"
    ADMINAPIBILLINGARCHIVE = "/admin/api/tenants/{tenantId}/receipts/{billNo}/archive"
    ADMINAPIBILLINGRESTORE = "/admin/api/tenants/{tenantId}/receipts/{billNo}/restore"
    ADMINAPIBILLINGDELETE = "/admin/api/tenants/{tenantId}/receipts/{billNo}"
    ADMINAPIBILLINGARCHIVEDATA = "/admin/api/archive-data"

    # Admin API: Tenants
    ADMINAPITENANTSLIST = "/admin/api/tenants"
    ADMINAPITENANTSCREATE = "/admin/api/tenants"
    ADMINAPITENANTSGET = "/admin/api/tenants/{tenantId}"
    ADMINAPITENANTSUPDATE = "/admin/api/tenants/{tenantId}"
    ADMINAPITENANTSDELETE = "/admin/api/tenants/{tenantId}"
    ADMINAPITENANTSRESTORE = "/admin/api/tenants/{tenantId}/restore"
    ADMINAPITENANTSCHANGEPIN = "/admin/api/tenants/{tenantId}/change-pin"
    ADMINAPITENANTSREVEALPIN = "/admin/api/tenants/{tenantId}/reveal-pin"
    ADMINAPITENANTSRECEIPTS = "/admin/api/tenants/{tenantId}/receipts"

    # Admin API: Tenant Recovery Snapshots
    ADMINAPITENANTSNAPSHOTS = "/admin/api/tenant-recovery-snapshots"
    ADMINAPITENANTSNAPSHOT_PREVIEW = "/admin/api/tenant-recovery-snapshots/{snapshotId}/preview"
    ADMINAPITENANTSNAPSHOT_RESTORE = "/admin/api/tenant-recovery-snapshots/{snapshotId}/restore"

    # Admin API: Occupants
    ADMINAPIOCCUPANTSLIST = "/admin/api/occupants/{tenantId}"
    ADMINAPIOCCUPANTSCREATE = "/admin/api/occupants/{tenantId}"
    ADMINAPIOCCUPANTSMARKINACTIVE = "/admin/api/occupants/{tenantId}/{occupantUuid}/inactive"
    ADMINAPIOCCUPANTSDELETE = "/admin/api/occupants/{tenantId}/{occupantUuid}"
    ADMINAPIOCCUPANTSGETFILE = "/admin/api/occupants/{tenantId}/file/{filename}"

    # Admin API: Pdf
    ADMINAPIPDFDOWNLOAD = "/admin/api/tenants/{tenantId}/receipts/{billNo}/pdf/download"
    ADMINAPIPDFVIEW = "/admin/api/tenants/{tenantId}/receipts/{billNo}/pdf/view"

    # Admin API: Whatsapp
    ADMINAPIWHATSAPPSENDSINGLE = "/admin/api/tenants/{tenantId}/receipts/{billNo}/whatsapp"

    # Admin API: Sync
    ADMINAPISYNCEXPORTCSV = "/admin/api/export-csv"
    ADMINAPISYNCEXPORTZIP = "/admin/api/export-zip"
    ADMINAPISYNCEXPORTEXCEL = "/admin/api/export-excel"
    ADMINAPISYNCTEMPLATE = "/admin/api/import-template"
    ADMINAPISYNCIMPORTPREVIEW = "/admin/api/import-preview"
    ADMINAPISYNCIMPORTEXECUTE = "/admin/api/import-execute"

    # Admin API: Backups
    ADMINAPIBACKUPSLIST = "/admin/api/backups"
    ADMINAPIBACKUPSCREATEMANUAL = "/admin/api/backups/manual"
    ADMINAPIBACKUPSDELETE = "/admin/api/backups/{backupId}"
    ADMINAPIBACKUPSVERIFY = "/admin/api/backups/{backupId}/verify"
    ADMINAPIBACKUPSRESTORE = "/admin/api/backups/{backupId}/restore"
    ADMINAPIBACKUPSDOWNLOAD = "/admin/api/backups/{backupId}/download"
    ADMINAPIBACKUPSMETADATA = "/admin/api/backups/{backupId}/metadata"

    # Admin API: Settings
    ADMINAPISETTINGSUPLOADSIGNATURE = "/admin/api/settings/upload-signature"
    ADMINAPISETTINGSDELETESIGNATURE = "/admin/api/settings/delete-signature"



    # Static & Health
    STATICUPLOADS = "/static/uploads"
    STATICSTATIC = "/static"
    STATICADMINASSETS = "/admin/assets"
    STATICTENANTASSETS = "/tenant/assets"
    STATICFAVICON = "/admin/favicon.svg"


class Names:
    """Route names for use with request.url_for() and FastAPI name= parameter."""

    # Pages
    HOME = "home_page"
    BILLINGPAGE = "billing_page"
    HISTORYPAGE = "history_page"
    TENANTSPAGE = "tenants_page"
    SETTINGSPAGE = "settings_page"
    ARCHIVEPAGE = "archive_page"
    BACKUPSPAGE = "backups_page"
    FAVICON = "favicon"

    # API - Backups
    APIGETBACKUPS = "api_get_backups"
    APICREATEMANUALBACKUP = "api_create_manual_backup"
    APIDELETEBACKUP = "api_delete_backup"
    APIVERIFYBACKUP = "api_verify_backup"
    APIRESTOREBACKUP = "api_restore_backup"
    APIDOWNLOADBACKUP = "api_download_backup"
    APIDOWNLOADMETADATA = "api_download_metadata"

    # API - Billing
    APIFILTERBILLS = "api_filter_bills"
    APIBILLINGMONTHS = "api_billing_months"
    APIBILLINGPREVIEW = "api_billing_preview"
    APIGETSINGLEBILL = "api_get_single_bill"
    APICREATEBILL = "api_create_bill"
    APIUPDATEBILL = "api_update_bill"
    APIUPDATEPAYMENT = "api_update_payment"
    APIARCHIVEBILL = "api_archive_bill"
    APIRESTOREBILL = "api_restore_bill"
    APIDELETEBILL = "api_delete_bill"

    # API - PDF
    PDFDOWNLOAD = "download_pdf"
    PDFVIEW = "view_pdf"



    # API - Settings
    APIGETCONFIG = "api_get_config"
    APIUPLOADSIGNATURE = "api_upload_signature"
    APIDELETESIGNATURE = "api_delete_signature"
    UPDATECONFIG = "update_config"
    UPDATETHEME = "update_theme"

    # API - Sync
    EXPORTRECEIPTSCSV = "export_receipts_csv"
    EXPORTFULLZIP = "export_full_zip"
    DOWNLOADEXCELTEMPLATE = "download_excel_template"
    EXPORTEXCELDATA = "export_excel_data"
    IMPORTPREVIEWDATA = "import_preview_data"
    IMPORTEXECUTEDATA = "import_execute_data"

    # API - Tenants
    APIGETTENANTS = "api_get_tenants"
    APIGETTENANT = "api_get_tenant"
    APIGETTENANTRECEIPTS = "api_get_tenant_receipts"
    APIADDTENANT = "api_add_tenant"
    APIUPDATETENANT = "api_update_tenant"
    APIDELETETENANT = "api_delete_tenant"
    APIRESTORETENANT = "api_restore_tenant"

    # API - Whatsapp
    SENDWHATSAPPSINGLE = "send_whatsapp_single"
    SENDWHATSAPPBULK = "send_whatsapp_bulk"

    # API - Health
    HEALTHCHECK = "health_check"

    # Auth
    ADMINLOGIN = "adminloginpost"
    ADMINLOGINTOTP = "admin_login_totp"
    ADMINLOGOUT = "ADMINLOGOUT"
    ADMINLOGOUTJSON = "ADMINLOGOUTJSON"
    ADMINREFRESH = "admin_refresh"
    ADMINME = "ADMINME"
    ADMINSETUPREQUIRED = "admin_setup_required"
    ADMINSETUPCREATE = "admin_setup_create"
    ADMINTOTPQR = "admin_totp_qr"
    ADMINTOTPREGENERATE = "admin_totp_regenerate"
    ADMINFORGOTVERIFY = "admin_forgot_password_verify"
    ADMINFORGOTRESET = "admin_forgot_password_reset"
    ADMINPUBLICKEY = "admin_public_key"

    CHANGETENANTPIN = "change_tenantPin"
    ADMINREVEALPIN = "admin_reveal_tenantPin"

    # API - Tenant Recovery Snapshots
    APILISTRECOVERYSNAPSHOTS = "api_list_recovery_snapshots"
    APIRECOVERYSNAPSHOT_PREVIEW = "api_recovery_snapshot_preview"
    APIRECOVERYSNAPSHOT_RESTORE = "api_recovery_snapshot_restore"


    # API - Occupants
    APIGETOCCUPANTS = "api_get_occupants"
    APICREATEOCCUPANT = "api_create_occupant"
    APIMARKOCCUPANTINACTIVE = "api_mark_occupant_inactive"
    APIDELETEOCCUPANT = "api_delete_occupant"
    APIGETOCCUPANTFILE = "api_get_occupant_file"


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
    TENANTPROFILE = "tenant_profile.html"


class Prefixes:
    """URL path prefixes."""
    API = "/api"
    STATIC = "/static"
    UPLOADS = "/static/uploads"