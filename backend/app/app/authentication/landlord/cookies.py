"""
app/authentication/landlord/cookies.py

Set and clear landlord-specific auth cookies.
Cookie names and path are deliberately separate from admin and tenant cookies
to prevent any cross-role contamination.

Cookie names : access_token / refresh_token
Cookie path  : {root_path}/landlord   (e.g. /rent/landlord)
"""
from fastapi import Request, Response


def _get_landlord_cookie_path(request: Request | None = None) -> str:
    """Resolve the cookie path as root_path + /landlord."""
    if request is None:
        return "/landlord"
    root = (
        request.scope.get("root_path")
        or request.scope.get("rootpath")
        or ""
    ).rstrip("/")
    return f"{root}/landlord" if root else "/landlord"


def set_landlord_auth_cookies(
    response: Response,
    access_token: str,
    refresh_cookie: str,
    remember_me: bool,
    request: Request | None = None,
) -> None:
    """Attach landlord access + refresh cookies to *response*."""
    cookie_path = _get_landlord_cookie_path(request)
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
        value=refresh_cookie,
        httponly=True,
        secure=True,
        samesite="none",
        path=cookie_path,
        max_age=max_age_refresh,
    )


def clear_landlord_auth_cookies(
    response: Response,
    request: Request | None = None,
) -> None:
    """Remove landlord auth cookies from the browser."""
    cookie_path = _get_landlord_cookie_path(request)
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
        samesite="none",
    )
