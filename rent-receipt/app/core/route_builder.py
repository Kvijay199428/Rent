from app.core.routes import Names

class RouteBuilder:
    @staticmethod
    def build(request, name: str, **kwargs):
        return request.url_for(name, **kwargs)

    @staticmethod
    def static(request, path: str):
        return request.url_for("static", path=path)

    @staticmethod
    def pdf(request, bill_no: str):
        return request.url_for(Names.PDF_VIEW, bill_no=bill_no)

    @staticmethod
    def public_tenant(request, token: str):
        return request.url_for(Names.PUBLIC, view_token=token)
