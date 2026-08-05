"""Host-based guard for blocking frontend page serving on the API domain."""
from fastapi import Request, HTTPException
from starlette.staticfiles import StaticFiles
from starlette.responses import JSONResponse

API_DOMAIN = "api.vijaykrsha.online"


def is_api_host(host: str) -> bool:
    """Return True if the request host resolves to the API-only domain."""
    return API_DOMAIN in (host or "")


def check_api_host(request: Request):
    """Raise 404 if the request arrives via the API domain.

    This keeps the backend monolith serving both API + frontend,
    but blocks frontend pages when accessed through the API hostname.
    """
    if is_api_host(request.headers.get("host", "")):
        raise HTTPException(status_code=404, detail="Not found")


class APIGuardedStaticFiles(StaticFiles):
    """StaticFiles mount that refuses to serve anything on the API domain."""

    async def __call__(self, scope, receive, send):
        host = ""
        for name, value in scope.get("headers", []):
            if name == b"host":
                host = value.decode(errors="replace")
                break
        if is_api_host(host):
            response = JSONResponse({"detail": "Not found"}, status_code=404)
            await response(scope, receive, send)
            return
        await super().__call__(scope, receive, send)
