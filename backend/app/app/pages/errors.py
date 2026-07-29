from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.dependencies import templates

from app.core.routes_manifest import Routes, Templates

from app.core.config_service import config  # Import the configuration service

def register_exception_handlers(app: FastAPI):
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # Pass through redirects properly
        if 300 <= exc.status_code < 400 and exc.headers and "Location" in exc.headers:
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=exc.headers["Location"], status_code=exc.status_code)
            
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            response = templates.TemplateResponse(
                request=request,
                name=Templates.ERROR,
                context={
                    "request": request, 
                    "status_code": exc.status_code, 
                    "detail": exc.detail,
                    "sys": config.get("system", {})  # Provide system config context
                },
                status_code=exc.status_code
            )
        else:
            response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
            
        if exc.headers:
            for k, v in exc.headers.items():
                response.headers[k] = v
                
        # If the backend signaled to clear cookies, clear them on the response
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
        from fastapi.responses import JSONResponse, PlainTextResponse
        if request.url.path.startswith("/rent/admin/api/") or request.url.path.startswith("/api/"):
            return JSONResponse(status_code=500, content={"detail": str(exc)})
        
        return PlainTextResponse("Internal Server Error", status_code=500)

