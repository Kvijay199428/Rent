import os
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send
from app.core.startup import StartupManager
from app.core.router_registry import register_all_routers
from app.core.app_info import APP_INFO


def normalize_base_path(path: str | None) -> str:
    if not path or path == "/":
        return ""
    normalized = path.strip()
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized.rstrip("/")


class ProxyContextMiddleware:
    """
    Pure ASGI middleware that correctly handles proxy prefixes for Starlette.
    Starlette's routing ALWAYS assumes that scope["path"] starts with scope["root_path"].
    If Nginx strips the prefix (e.g. proxy_pass http://upstream/), scope["path"] will not
    contain the prefix. We must prepend root_path to scope["path"] if it's missing,
    otherwise nested mounts (like StaticFiles) will fail to strip root_path correctly
    and return 404.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            headers = dict(scope.get("headers", []))

            forwarded_proto = headers.get(b"x-forwarded-proto", b"").decode("latin1")
            forwarded_prefix = headers.get(b"x-forwarded-prefix", b"").decode("latin1")

            if forwarded_proto:
                scope["scheme"] = forwarded_proto.split(",")[0].strip()

            root_path = normalize_base_path(forwarded_prefix or os.getenv("APP_BASE_PATH"))

            if root_path:
                scope["root_path"] = root_path
                # PREPEND root_path to path if it was stripped by Nginx.
                # Starlette explicitly requires path to contain root_path.
                current_path = scope.get("path", "")
                if not current_path.startswith(root_path):
                    scope["path"] = root_path + current_path

                # Keep raw_path in sync
                raw_prefix = root_path.encode("ascii")
                raw_path = scope.get("raw_path", b"")
                if not raw_path.startswith(raw_prefix):
                    scope["raw_path"] = raw_prefix + raw_path

        await self.app(scope, receive, send)


# ── Build the application ────────────────────────────────────────────────────

app = FastAPI(title=APP_INFO["name"], version=APP_INFO["version"])

# Initialize Storage, Config, DB, Migrations, Static mounts, Middlewares, and Events
StartupManager.initialize(app)

# Register all modular routers
register_all_routers(app)

# Serve Admin React App
admin_assets_path = "frontend/admin-app/dist/assets"
if os.path.isdir(admin_assets_path):
    app.mount("/admin/assets", StaticFiles(directory=admin_assets_path), name="admin_assets")

# Serve Tenant React App
tenant_assets_path = "frontend/tenant-app/dist/assets"
if os.path.isdir(tenant_assets_path):
    app.mount("/t/assets", StaticFiles(directory=tenant_assets_path), name="tenant_assets")

# Register SPA catch-all routes LAST so they don't shadow API routes
from app.pages.spa import router as spa_router
app.include_router(spa_router)

# Add proxy middleware — must be added AFTER routes so it sits outermost in the stack
app.add_middleware(ProxyContextMiddleware)  # type: ignore[arg-type]


# Request timing / logging middleware
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
    # Local dev mode
    uvicorn.run("app.main:app", host="127.0.0.1", port=20081, reload=True)

