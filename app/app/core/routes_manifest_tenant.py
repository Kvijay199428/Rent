# app/app/core/routes_manifest_tenant.py

class TenantRoutes:
    TENANTPAGEROOT = "/t/{tenantId}/{viewToken}"

    # Tenant API: Auth
    TENANTAPIAUTHPUBLICKEY = "/t/api/auth/public-key"
    TENANTAPIAUTHLOGIN = "/t/api/{tenantId}/{viewToken}/auth/login"
    TENANTAPIAUTHREFRESH = "/t/api/{tenantId}/{viewToken}/auth/refresh"
    TENANTAPIAUTHLOGOUT = "/t/api/{tenantId}/{viewToken}/auth/logout"
    TENANTAPIAUTHLOGOUTALL = "/t/api/{tenantId}/{viewToken}/auth/logout-all"

    # Tenant API: Profile
    TENANTAPIPROFILEGET = "/t/api/{tenantId}/{viewToken}/profile"

    # Tenant API: KYC
    TENANTAPIKYCUPLOAD = "/t/api/{tenantId}/{viewToken}/kyc"
    TENANTAPIKYCMARKINACTIVE = "/t/api/{tenantId}/{viewToken}/kyc/{occupantUuid}/inactive"
    TENANTAPIKYCDELETE = "/t/api/{tenantId}/{viewToken}/kyc/{occupantUuid}"
    TENANTAPIKYCGETFILE = "/t/api/{tenantId}/{viewToken}/kyc/file/{filename}"

    # Tenant API: PDF
    TENANTAPIPDFVIEW = "/t/api/{tenantId}/{viewToken}/pdf/{billNo}/view"
    TENANTAPIPDFDOWNLOAD = "/t/api/{tenantId}/{viewToken}/pdf/{billNo}/download"


class TenantNames:
    TENANTPROFILEPAGE = "tenant_profile_page"
    TENANTPUBLICKEY = "tenant_public_key"
    TENANTLOGIN = "tenant_login"
    TENANTREFRESH = "tenant_refresh"
    TENANTLOGOUT = "tenant_logout"
    TENANTLOGOUTALL = "tenant_logout_all"

    TENANTPROFILEGET = "tenant_profile_get"

    TENANTKYCUPLOAD = "tenant_kyc_upload"
    TENANTKYCMARKINACTIVE = "tenant_kyc_mark_inactive"
    TENANTKYCDELETE = "tenant_kyc_delete"
    TENANTKYCGETFILE = "tenant_kyc_get_file"

    TENANTPDFVIEW = "tenant_pdf_view"
    TENANTPDFDOWNLOAD = "tenant_pdf_download"


class TenantTemplates:
    TENANTPUBLICPROFILE = "tenant_public_profile.html"
