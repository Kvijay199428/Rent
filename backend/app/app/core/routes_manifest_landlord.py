# app/core/routes_manifest_landlord.py

class LandlordRoutes:
    # Landlord Pages
    LANDLORDPAGEROOT = "/landlord"
    LANDLORDPAGEHOME = "/landlord/home"
    LANDLORDPAGELOGIN = "/landlord/login"
    LANDLORDPAGESIGNUP = "/landlord/signup"
    LANDLORDPAGELOGOUT = "/landlord/logout"
    LANDLORDPAGEDASHBOARD = "/landlord/dashboard"
    LANDLORDPAGEBILLING = "/landlord/billing"
    LANDLORDPAGEHISTORY = "/landlord/history"
    LANDLORDPAGETENANTS = "/landlord/tenants"
    LANDLORDPAGESETTINGS = "/landlord/settings"
    LANDLORDPAGEARCHIVE = "/landlord/archive"
    LANDLORDPAGEBACKUPS = "/landlord/backups"
    LANDLORDPAGECATCHALL = "/landlord/*"
    LANDLORDPAGETENANTPROFILE = "/landlord/tenant/{tenantId}"

    # Landlord Auth API (from existing Landlord Auth routes)
    LANDLORDAPIAUTHGOOGLE = "/landlord/api/auth/google"
    LANDLORDAPIAUTHCHECKUSERNAME = "/landlord/api/auth/check-username"
    LANDLORDAPIAUTHCHECKEMAIL = "/landlord/api/auth/check-email"
    LANDLORDAPIAUTHSIGNUP = "/landlord/api/auth/signup"
    LANDLORDAPIAUTHLOGIN = "/landlord/api/auth/login"
    LANDLORDAPIAUTHREFRESH = "/landlord/api/auth/refresh"
    LANDLORDAPIAUTHLOGOUT = "/landlord/api/auth/logout"
    LANDLORDAPIAUTHME = "/landlord/api/auth/me"
    LANDLORDAPIAUTHCHANGEPASSWORD = "/landlord/api/auth/change-password"

    # Landlord API: Setup wizard (post-signup initial configuration)
    LANDLORDAPISETUPREQUIRED = "/landlord/api/setup/required"
    LANDLORDAPISETUPCREATE = "/landlord/api/setup/create"
    LANDLORDAPISETUPSKIP = "/landlord/api/setup/skip"

    # Landlord API: Properties (property-first billing)
    LANDLORDAPIPROPERTIESLIST = "/landlord/{landlordUuid}/api/properties"
    LANDLORDAPIPROPERTIESCREATE = "/landlord/{landlordUuid}/api/properties"
    LANDLORDAPIPROPERTIESGET = "/landlord/{landlordUuid}/api/properties/{propertyId}"
    LANDLORDAPIPROPERTIESUPDATE = "/landlord/{landlordUuid}/api/properties/{propertyId}"
    LANDLORDAPIPROPERTIESDELETE = "/landlord/{landlordUuid}/api/properties/{propertyId}"
    LANDLORDAPIPROPERTIESTENANTS = "/landlord/{landlordUuid}/api/properties/{propertyId}/tenants"

    # Landlord API: Auth (legacy equivalents, mostly obsolete but kept if referenced)
    LANDLORDAPIAUTHPUBLICKEY = "/landlord/api/auth/public-key"
    LANDLORDAPIAUTHLOGINTOTP = "/landlord/api/login/totp"
    LANDLORDAPIAUTHLOGOUTJSON = "/landlord/api/logout/json"

    # Landlord API: Totp
    LANDLORDAPITOTPQR = "/landlord/{landlordUuid}/api/totp/qr"
    LANDLORDAPITOTPREGENERATE = "/landlord/{landlordUuid}/api/totp/regenerate"
    LANDLORDAPITOTPENABLE = "/landlord/{landlordUuid}/api/totp/enable"
    LANDLORDAPITOTPDISABLE = "/landlord/{landlordUuid}/api/totp/disable"

    # Landlord API: Audit Logs
    LANDLORDAPIAUDITLOGS = "/landlord/{landlordUuid}/api/audit-logs"
    LANDLORDAPIAUDITLOGSACTIONS = "/landlord/{landlordUuid}/api/audit-logs/actions"

    # Landlord API: Password
    LANDLORDAPIPASSWORDFORGOTVERIFY = "/landlord/api/forgot-password/verify"
    LANDLORDAPIPASSWORDFORGOTRESET = "/landlord/api/forgot-password/reset"

    # Landlord API: Privacy policy (public consent metadata + consent recording)
    LANDLORDAPIPRIVACYPOLICY = "/landlord/api/privacy-policy"
    LANDLORDAPIAUTHPRIVACYCONSENT = "/landlord/api/auth/privacy-consent"

    # Landlord API: Terms and Conditions (public document + consent recording)
    LANDLORDAPITERMS = "/landlord/api/terms"
    LANDLORDAPIAUTHTERMSCONSENT = "/landlord/api/auth/terms-consent"

    # Landlord API: Dashboard
    LANDLORDAPIDASHBOARDSTATS = "/landlord/{landlordUuid}/api/dashboard"

    # Landlord API: Config
    LANDLORDAPICONFIGGET = "/landlord/{landlordUuid}/api/config"
    LANDLORDAPICONFIGUPDATE = "/landlord/{landlordUuid}/api/config/update"
    LANDLORDAPICONFIGTHEMEGET = "/landlord/{landlordUuid}/api/ui/theme"
    LANDLORDAPICONFIGTHEME = "/landlord/{landlordUuid}/api/ui/theme"

    # Landlord API: Billing
    LANDLORDAPIBILLINGFILTER = "/landlord/{landlordUuid}/api/receipts/filter"
    LANDLORDAPIBILLINGMONTHS = "/landlord/{landlordUuid}/api/receipts/months"
    LANDLORDAPIBILLINGPREVIEW = "/landlord/{landlordUuid}/api/receipts/preview"
    LANDLORDAPIBILLINGCREATE = "/landlord/{landlordUuid}/api/tenants/{tenantId}/receipts"
    LANDLORDAPIBILLINGGET = "/landlord/{landlordUuid}/api/tenants/{tenantId}/receipts/{billNo}"
    LANDLORDAPIBILLINGUPDATE = "/landlord/{landlordUuid}/api/tenants/{tenantId}/receipts/{billNo}"
    LANDLORDAPIBILLINGUPDATEPAYMENT = "/landlord/{landlordUuid}/api/tenants/{tenantId}/receipts/{billNo}/payment-status"
    LANDLORDAPIBILLINGARCHIVE = "/landlord/{landlordUuid}/api/tenants/{tenantId}/receipts/{billNo}/archive"
    LANDLORDAPIBILLINGRESTORE = "/landlord/{landlordUuid}/api/tenants/{tenantId}/receipts/{billNo}/restore"
    LANDLORDAPIBILLINGDELETE = "/landlord/{landlordUuid}/api/tenants/{tenantId}/receipts/{billNo}"
    LANDLORDAPIBILLINGARCHIVEDATA = "/landlord/{landlordUuid}/api/archive-data"

    # Landlord API: Tenants
    LANDLORDAPITENANTSLIST = "/landlord/{landlordUuid}/api/tenants"
    LANDLORDAPITENANTSCREATE = "/landlord/{landlordUuid}/api/tenants"
    LANDLORDAPITENANTSGET = "/landlord/{landlordUuid}/api/tenants/{tenantId}"
    LANDLORDAPITENANTSUPDATE = "/landlord/{landlordUuid}/api/tenants/{tenantId}"
    LANDLORDAPITENANTSDELETE = "/landlord/{landlordUuid}/api/tenants/{tenantId}"
    LANDLORDAPITENANTSRESTORE = "/landlord/{landlordUuid}/api/tenants/{tenantId}/restore"
    LANDLORDAPITENANTSCHANGEPIN = "/landlord/{landlordUuid}/api/tenants/{tenantId}/change-pin"
    LANDLORDAPITENANTSREVEALPIN = "/landlord/{landlordUuid}/api/tenants/{tenantId}/reveal-pin"
    LANDLORDAPITENANTSRECEIPTS = "/landlord/{landlordUuid}/api/tenants/{tenantId}/receipts"
    LANDLORDAPITENANTSPORTALAUTH = "/landlord/{landlordUuid}/api/tenants/{tenantId}/portal-auth"
    LANDLORDAPITENANTSQRKEY = "/landlord/{landlordUuid}/api/tenants/{tenantId}/qr-key"

    # Landlord API: Tenant Recovery Snapshots
    LANDLORDAPITENANTSNAPSHOTS = "/landlord/{landlordUuid}/api/tenant-recovery-snapshots"
    LANDLORDAPITENANTSNAPSHOT_PREVIEW = "/landlord/{landlordUuid}/api/tenant-recovery-snapshots/{snapshotId}/preview"
    LANDLORDAPITENANTSNAPSHOT_RESTORE = "/landlord/{landlordUuid}/api/tenant-recovery-snapshots/{snapshotId}/restore"

    # Landlord API: Occupants
    LANDLORDAPIOCCUPANTSLIST = "/landlord/{landlordUuid}/api/occupants/{tenantId}"
    LANDLORDAPIOCCUPANTSCREATE = "/landlord/{landlordUuid}/api/occupants/{tenantId}"
    LANDLORDAPIOCCUPANTSMARKINACTIVE = "/landlord/{landlordUuid}/api/occupants/{tenantId}/{occupantUuid}/inactive"
    LANDLORDAPIOCCUPANTSDELETE = "/landlord/{landlordUuid}/api/occupants/{tenantId}/{occupantUuid}"
    LANDLORDAPIOCCUPANTSGETFILE = "/landlord/{landlordUuid}/api/occupants/{tenantId}/file/{filename}"

    # Landlord API: Pdf
    LANDLORDAPIPDFDOWNLOAD = "/landlord/{landlordUuid}/api/tenants/{tenantId}/receipts/{billNo}/pdf/download"
    LANDLORDAPIPDFVIEW = "/landlord/{landlordUuid}/api/tenants/{tenantId}/receipts/{billNo}/pdf/view"

    # Landlord API: Whatsapp
    LANDLORDAPIWHATSAPPSENDSINGLE = "/landlord/{landlordUuid}/api/tenants/{tenantId}/receipts/{billNo}/whatsapp"

    # Landlord API: Sync
    LANDLORDAPISYNCEXPORTCSV = "/landlord/{landlordUuid}/api/export-csv"
    LANDLORDAPISYNCEXPORTZIP = "/landlord/{landlordUuid}/api/export-zip"
    LANDLORDAPISYNCEXPORTEXCEL = "/landlord/{landlordUuid}/api/export-excel"
    LANDLORDAPISYNCTEMPLATE = "/landlord/{landlordUuid}/api/import-template"
    LANDLORDAPISYNCIMPORTPREVIEW = "/landlord/{landlordUuid}/api/import-preview"
    LANDLORDAPISYNCIMPORTEXECUTE = "/landlord/{landlordUuid}/api/import-execute"

    # Landlord API: Backups
    LANDLORDAPIBACKUPSLIST = "/landlord/{landlordUuid}/api/backups"
    LANDLORDAPIBACKUPSCREATEMANUAL = "/landlord/{landlordUuid}/api/backups/manual"
    LANDLORDAPIBACKUPSDELETE = "/landlord/{landlordUuid}/api/backups/{backupId}"
    LANDLORDAPIBACKUPSVERIFY = "/landlord/{landlordUuid}/api/backups/{backupId}/verify"
    LANDLORDAPIBACKUPSRESTORE = "/landlord/{landlordUuid}/api/backups/{backupId}/restore"
    LANDLORDAPIBACKUPSDOWNLOAD = "/landlord/{landlordUuid}/api/backups/{backupId}/download"
    LANDLORDAPIBACKUPSMETADATA = "/landlord/{landlordUuid}/api/backups/{backupId}/metadata"

    # Landlord API: Settings
    LANDLORDAPISETTINGSUPLOADSIGNATURE = "/landlord/{landlordUuid}/api/settings/upload-signature"
    LANDLORDAPISETTINGSDELETESIGNATURE = "/landlord/{landlordUuid}/api/settings/delete-signature"


class LandlordNames:
    """Route names for use with request.url_for() and FastAPI name= parameter."""

    # Landlord Pages
    LANDLORDLOGINPAGE = "landlordloginpage"
    LANDLORDSIGNUPPAGE = "landlordsignuppage"
    LANDLORDDASHBOARDPAGE = "landlorddashboardpage"
    LANDLORDLOGOUTPAGE = "landlordlogoutpage"

    # Landlord Auth API
    LANDLORDGOOGLE = "landlordgoogle"
    LANDLORDCHECKUSERNAME = "landlordcheckusername"
    LANDLORDCHECKEMAIL = "landlordcheckemail"
    LANDLORDSIGNUP = "landlordsignup"
    LANDLORDLOGIN = "landlordlogin"
    LANDLORDREFRESH = "landlordrefresh"
    LANDLORDLOGOUT = "landlordlogout"
    LANDLORDME = "landlordme"
    LANDLORDCHANGEPASSWORD = "landlordchangepassword"
    LANDLORDPRIVACYPOLICY = "landlordprivacypolicy"
    LANDLORDPRIVACYCONSENT = "landlordprivacyconsent"
    LANDLORDTERMS = "landlordterms"
    LANDLORDTERMSCONSENT = "landlordtermsconsent"

    # Pages
    HOME = "home_page"
    BILLINGPAGE = "billing_page"
    HISTORYPAGE = "history_page"
    TENANTSPAGE = "tenants_page"
    SETTINGSPAGE = "settings_page"
    ARCHIVEPAGE = "archive_page"
    BACKUPSPAGE = "backups_page"

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

    # API - Setup wizard
    LANDLORDSETUPREQUIRED = "landlord_setup_required"
    LANDLORDSETUPCREATE = "landlord_setup_create"
    LANDLORDSETUPSKIP = "landlord_setup_skip"

    # API - Properties
    APIGETPROPERTIES = "api_get_properties"
    APICREATEPROPERTY = "api_create_property"
    APIGETPROPERTY = "api_get_property"
    APIUPDATEPROPERTY = "api_update_property"
    APIDELETEPROPERTY = "api_delete_property"
    APIGETPROPERTYTENANTS = "api_get_property_tenants"

    # Auth Names (from old ADMIN prefixed)
    LANDLORDLOGINPOST = "landlordloginpost"
    LANDLORDLOGINTOTP = "landlord_login_totp"
    LANDLORDLOGOUTJSON = "LANDLORDLOGOUTJSON"
    LANDLORDSETUPREQUIRED = "landlord_setup_required"
    LANDLORDSETUPCREATE = "landlord_setup_create"
    LANDLORDTOTPQR = "landlord_totp_qr"
    LANDLORDTOTPREGENERATE = "landlord_totp_regenerate"
    LANDLORDTOTPENABLE = "landlord_totp_enable"
    LANDLORDTOTPDISABLE = "landlord_totp_disable"
    LANDLORDAUDITLOGS = "landlord_audit_logs"
    LANDLORDAUDITLOGSACTIONS = "landlord_audit_logs_actions"
    LANDLORDFORGOTVERIFY = "landlord_forgot_password_verify"
    LANDLORDFORGOTRESET = "landlord_forgot_password_reset"
    LANDLORDPUBLICKEY = "landlord_public_key"

    CHANGETENANTPIN = "change_tenantPin"
    LANDLORDREVEALPIN = "landlord_reveal_tenantPin"
    LANDLORDTENANTPORTALAUTH = "landlord_tenant_portal_auth"
    LANDLORDTENANTQRKEY = "landlord_tenant_qr_key"


class LandlordTemplates:
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
