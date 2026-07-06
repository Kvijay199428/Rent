from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.dependencies import templates
from app.core.routes import Templates
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
            return templates.TemplateResponse(
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
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return templates.TemplateResponse(
                request=request,
                name=Templates.ERROR,
                context={
                    "request": request, 
                    "status_code": 500, 
                    "detail": "Internal Server Error",
                    "sys": config.get("system", {})  # Provide system config context
                },
                status_code=500
            )
        return JSONResponse({"detail": "Internal Server Error"}, status_code=500)