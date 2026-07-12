from fastapi import Response, Request

def set_admin_auth_cookies(response: Response, access_token: str, refresh_token: str, remember_me: bool, request: Request = None):
    max_age_refresh = 180 * 24 * 60 * 60 if remember_me else 24 * 60 * 60
    
    root_path = request.scope.get("root_path", "") if request else ""
    cookie_path = f"{root_path}/admin"
    if not cookie_path.startswith("/"):
        cookie_path = "/" + cookie_path
    
    response.set_cookie(
        key="admin_access_token",
        value=access_token,
        httponly=True,
        secure=True, 
        samesite="Lax",
        path=cookie_path,
        max_age=15 * 60
    )
    
    response.set_cookie(
        key="admin_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="Strict",
        path=cookie_path,
        max_age=max_age_refresh
    )

def clear_admin_auth_cookies(response: Response, request: Request = None):
    root_path = request.scope.get("root_path", "") if request else ""
    cookie_path = f"{root_path}/admin"
    if not cookie_path.startswith("/"):
        cookie_path = "/" + cookie_path
        
    response.delete_cookie(key="admin_access_token", path=cookie_path, httponly=True, secure=True, samesite="Lax")
    response.delete_cookie(key="admin_refresh_token", path=cookie_path, httponly=True, secure=True, samesite="Strict")

