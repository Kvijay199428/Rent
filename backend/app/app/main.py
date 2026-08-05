import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.startup import StartupManager
from app.core.router_registry import register_all_routers
from app.core.app_info import APP_INFO
from app.core.runtime import cors_origins, enable_swagger


app = FastAPI(
    title=APP_INFO["name"],
    version=APP_INFO["version"],
    docs_url="/docs" if enable_swagger() else None,
    redoc_url="/redoc" if enable_swagger() else None,
    openapi_url="/openapi.json" if enable_swagger() else None,
)

StartupManager.initialize(app)
register_all_routers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Session-Expired",
        "X-Redirect-Url",
        "X-Clear-Cookies",
        "X-Password-Change-Required",
    ],
)


@app.middleware("http")
async def forwarded_prefix_middleware(request: Request, call_next):
    prefix = request.headers.get("X-Forwarded-Prefix", "")
    if prefix:
        request.scope["root_path"] = prefix.rstrip("/")
    return await call_next(request)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    path = request.scope.get("path", "?")
    print(f"[{response.status_code}] {request.method} {path} - {duration:.4f}s")
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=20081, reload=True)

