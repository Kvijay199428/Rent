# app/app/core/routes_manifest_tenant.py

class TenantRoutes:
    # Canonical tenant portal URL: /{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}
    # The propertyId scopes the tenant link to a specific property (property-first billing).
    TENANTPAGEROOT = "/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}"

    # Tenant API: Auth — paths follow /{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/api/...
    TENANTAPIAUTHPUBLICKEY = "/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/api/auth/public-key"
    TENANTAPIAUTHLOGIN = "/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/api/auth/login"
    TENANTAPIAUTHREFRESH = "/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/api/auth/refresh"
    TENANTAPIAUTHLOGOUT = "/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/api/auth/logout"
    TENANTAPIAUTHLOGOUTALL = "/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/api/auth/logout-all"

    # Tenant API: Profile
    TENANTAPIPROFILEGET = "/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/api/profile"

    # Tenant API: KYC
    TENANTAPIKYCUPLOAD = "/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/api/kyc"
    TENANTAPIKYCMARKINACTIVE = "/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/api/kyc/{occupantUuid}/inactive"
    TENANTAPIKYCDELETE = "/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/api/kyc/{occupantUuid}"
    TENANTAPIKYCGETFILE = "/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/api/kyc/file/{filename}"

    # Tenant API: PDF
    TENANTAPIPDFVIEW = "/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/api/pdf/{billNo}/view"
    TENANTAPIPDFDOWNLOAD = "/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/api/pdf/{billNo}/download"

    # Tenant API: Audit Logs
    TENANTAPIAUDITLOGS = "/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/api/audit-logs"



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

    TENANTAUDITLOGS = "tenant_audit_logs"


class TenantTemplates:
    TENANTPUBLICPROFILE = "tenant_public_profile.html"
