from fastapi import Response, Request

def _tenant_cookie_paths(request: Request | None):
    if request is None:
        access_path = "/"
        refresh_path = "/api/auth"
        return access_path, refresh_path

    rootpath = (request.scope.get("root_path") or "").rstrip("/")

    params = request.path_params or {}
    landlordUuid = params.get("landlordUuid")
    tenant_id = params.get("tenantId")
    view_token = params.get("viewToken")

    # Canonical: /{landlordUuid}/t/{tenantId}/{viewToken}
    if landlordUuid and tenant_id and view_token:
        base = f"{rootpath}/{landlordUuid}/t/{tenant_id}/{view_token}".rstrip("/")
        return base, f"{base}/api/auth"
    access_path = rootpath if rootpath else "/"
    refresh_path = f"{rootpath}/api/auth" if rootpath else "/api/auth"
    return access_path, refresh_path

def set_tenant_auth_cookies(response: Response, access_token: str, refresh_token: str, remember_me: bool, request: Request = None):
    max_age_refresh = 180 * 24 * 60 * 60 if remember_me else 24 * 60 * 60
    access_path, refresh_path = _tenant_cookie_paths(request)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path=access_path,
        max_age=15 * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path=refresh_path,
        max_age=max_age_refresh,
    )

def clear_tenant_auth_cookies(response: Response, request: Request = None):
    access_path, refresh_path = _tenant_cookie_paths(request)

    response.delete_cookie(
        key="access_token",
        path=access_path,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    response.delete_cookie(
        key="refresh_token",
        path=refresh_path,
        httponly=True,
        secure=True,
        samesite="strict",
    )
