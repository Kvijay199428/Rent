# from app.core.routes import Names
# AFTER:
from app.core.routes_manifest import Names

class RouteBuilder:
    @staticmethod
    def build(request, name: str, **kwargs):
        return request.url_for(name, **kwargs)

    @staticmethod
    def pdf(request, billno: str):
        return request.url_for(Names.PDF_VIEW, billno=billno)

    @staticmethod
    def public_tenant(request, token: str):
        return request.url_for(Names.PUBLIC_TENANT_PROFILE_GET, view_token=token)

    @staticmethod
    def static(request, path: str):
        return request.url_for("static", path=path)
