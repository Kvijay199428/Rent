# from app.core.routes import Names
# AFTER:
from app.core.routes_manifest import Names
from app.core.routes_manifest_tenant import TenantNames

class RouteBuilder:
    @staticmethod
    def build(request, name: str, **kwargs):
        return request.url_for(name, **kwargs)

    @staticmethod
    def public_tenant_profile(request, tenantId: int, viewToken: str):
        return request.url_for(
            TenantNames.TENANTPROFILEGET,
            tenantId=str(tenantId),
            viewToken=viewToken,
        )

    @staticmethod
    def tenant_pdf_view(request, tenantId: int, viewToken: str, billNo: str):
        return request.url_for(
            TenantNames.TENANTPDFVIEW,
            tenantId=str(tenantId),
            viewToken=viewToken,
            billNo=billNo,
        )

    @staticmethod
    def static(request, path: str):
        return request.url_for("static", path=path)
