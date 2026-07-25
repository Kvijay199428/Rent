# app/app/core/routes_manifest_tenant.py

class TenantRoutes:
    TENANTPAGEROOT = "/{landlordUuid}/t/{tenantId}/{viewToken}"

    # Tenant API: Auth — paths follow /{landlordUuid}/t/{tenantId}/{viewToken}/api/...
    TENANTAPIAUTHPUBLICKEY = "/{landlordUuid}/t/{tenantId}/{viewToken}/api/auth/public-key"
    TENANTAPIAUTHLOGIN = "/{landlordUuid}/t/{tenantId}/{viewToken}/api/auth/login"
    TENANTAPIAUTHREFRESH = "/{landlordUuid}/t/{tenantId}/{viewToken}/api/auth/refresh"
    TENANTAPIAUTHLOGOUT = "/{landlordUuid}/t/{tenantId}/{viewToken}/api/auth/logout"
    TENANTAPIAUTHLOGOUTALL = "/{landlordUuid}/t/{tenantId}/{viewToken}/api/auth/logout-all"

    # Tenant API: Profile
    TENANTAPIPROFILEGET = "/{landlordUuid}/t/{tenantId}/{viewToken}/api/profile"

    # Tenant API: KYC
    TENANTAPIKYCUPLOAD = "/{landlordUuid}/t/{tenantId}/{viewToken}/api/kyc"
    TENANTAPIKYCMARKINACTIVE = "/{landlordUuid}/t/{tenantId}/{viewToken}/api/kyc/{occupantUuid}/inactive"
    TENANTAPIKYCDELETE = "/{landlordUuid}/t/{tenantId}/{viewToken}/api/kyc/{occupantUuid}"
    TENANTAPIKYCGETFILE = "/{landlordUuid}/t/{tenantId}/{viewToken}/api/kyc/file/{filename}"

    # Tenant API: PDF
    TENANTAPIPDFVIEW = "/{landlordUuid}/t/{tenantId}/{viewToken}/api/pdf/{billNo}/view"
    TENANTAPIPDFDOWNLOAD = "/{landlordUuid}/t/{tenantId}/{viewToken}/api/pdf/{billNo}/download"



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
