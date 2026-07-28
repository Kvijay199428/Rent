"""
app/authentication/platform/cookies.py
Cookie helpers scoped to /platform-admin for the platform super-admin role.
"""
from fastapi import Response, Request, HTTPException

def get_platform_cookie_path(request: Request | None = None) -> str:
    if request is None:
        return "/platform-admin"
    root = (request.scope.get("root_path") or "").rstrip("/")
    return f"{root}/platform-admin" if root else "/platform-admin"

def set_platform_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    remember_me: bool,
    request: Request | None = None,
) -> None:
    cookie_path = get_platform_cookie_path(request)
    max_age_refresh = 180 * 24 * 60 * 60 if remember_me else 24 * 60 * 60

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
        path=cookie_path,
        max_age=30 * 60,
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


def clear_platform_auth_cookies(
    response: Response,
    request: Request | None = None,
) -> None:
    cookie_path = get_platform_cookie_path(request)
    
    response.delete_cookie(
        key="access_token",
        path=cookie_path,
        httponly=True,
        secure=True,
        samesite="none",
    )
    response.delete_cookie(
        key="refresh_token",
        path=cookie_path,
        httponly=True,
        secure=True,
        samesite="strict",
    )


def get_platform_token(request: Request) -> str:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token
