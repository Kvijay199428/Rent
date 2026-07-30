from fastapi import Response, Request

def get_admin_cookie_path(request: Request | None = None) -> str:
    if request is None:
        return "/admin"

    rootpath = (request.scope.get("root_path") or request.scope.get("rootpath") or "").rstrip("/")
    path = request.url.path.rstrip("/")

    if rootpath and rootpath != "/":
        return rootpath

    parts = [p for p in path.split("/") if p]
    if parts and parts[0] not in {"admin", "api", "static"}:
        return f"/{parts[0]}"

    return "/admin"

def set_admin_auth_cookies(response: Response, access_token: str, refresh_token: str, remember_me: bool, request: Request = None):
    cookie_path = get_admin_cookie_path(request)
    max_age_refresh = 180 * 24 * 60 * 60 if remember_me else 24 * 60 * 60

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
        path=cookie_path,
        max_age=15 * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path=cookie_path,
        max_age=max_age_refresh,
    )

def clear_admin_auth_cookies(response: Response, request: Request = None):
    cookie_path = get_admin_cookie_path(request)
    response.delete_cookie(key="access_token", path=cookie_path, httponly=True, secure=True, samesite="none")
    response.delete_cookie(key="refresh_token", path=cookie_path, httponly=True, secure=True, samesite="strict")
