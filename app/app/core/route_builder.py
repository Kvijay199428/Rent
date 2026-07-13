# from app.core.routes import Names
# AFTER:
from app.core.routes_manifest import Names

class RouteBuilder:
    @staticmethod
    def build(request, name: str, **kwargs):
        return request.url_for(name, **kwargs)

    @staticmethod
    def pdf(request, billNo: str):
        return request.url_for(Names.PDFVIEW, billNo=billNo)

    @staticmethod
    def public_tenant(request, token: str):
        return request.url_for(Names.PUBLICTENANTPROFILEGET, viewToken=token)

    @staticmethod
    def static(request, path: str):
        return request.url_for("static", path=path)
