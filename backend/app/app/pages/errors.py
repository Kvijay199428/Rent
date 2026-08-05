from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.routes_manifest import Templates
from app.core.config_service import config


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # Pass through redirects properly
        if 300 <= exc.status_code < 400 and exc.headers and "Location" in exc.headers:
            return RedirectResponse(url=exc.headers["Location"], status_code=exc.status_code)

        accept = request.headers.get("accept", "")
        wants_html = "text/html" in accept

        if wants_html:
            from app.core.dependencies import templates
            response = templates.TemplateResponse(
                request=request,
                name=Templates.ERROR,
                context={
                    "request": request,
                    "status_code": exc.status_code,
                    "detail": exc.detail,
                    "sys": config.get("system", {}),
                },
                status_code=exc.status_code,
            )
        else:
            response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

        if exc.headers:
            for k, v in exc.headers.items():
                response.headers[k] = v

        clear_cookies_type = (exc.headers or {}).get("X-Clear-Cookies")
        if clear_cookies_type == "admin":
            from app.authentication.admin.cookies import clear_admin_auth_cookies
            clear_admin_auth_cookies(response, request)
        elif clear_cookies_type == "tenant":
            from app.authentication.tenant.cookies import clear_tenant_auth_cookies
            clear_tenant_auth_cookies(response, request)

        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

