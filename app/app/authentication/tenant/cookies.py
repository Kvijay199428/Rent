from fastapi import Response, Request

def set_tenant_auth_cookies(response: Response, access_token: str, refresh_token: str, remember_me: bool, request: Request = None):
    max_age_refresh = 180 * 24 * 60 * 60 if remember_me else 24 * 60 * 60
    
    root_path = request.scope.get("root_path", "") if request else ""
    access_path = root_path if root_path else "/"
    if not access_path.endswith("/"):
        access_path = access_path + "/"
    
    refresh_path = f"{root_path}/api/auth"
    if not refresh_path.startswith("/"): refresh_path = "/" + refresh_path
    
    response.set_cookie(
        key="tenant_access_token",
        value=access_token,
        httponly=True,
        secure=True, 
        samesite="Lax",
        path=access_path,
        max_age=15 * 60
    )
    
    response.set_cookie(
        key="tenant_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="Strict",
        path=refresh_path,
        max_age=max_age_refresh
    )

def clear_tenant_auth_cookies(response: Response, request: Request = None):
    root_path = request.scope.get("root_path", "") if request else ""
    access_path = root_path if root_path else "/"
    if not access_path.endswith("/"):
        access_path = access_path + "/"
    
    refresh_path = f"{root_path}/api/auth"
    if not refresh_path.startswith("/"): refresh_path = "/" + refresh_path
    
    response.delete_cookie(key="tenant_access_token", path=access_path, httponly=True, secure=True, samesite="Lax")
    response.delete_cookie(key="tenant_refresh_token", path=refresh_path, httponly=True, secure=True, samesite="Strict")

