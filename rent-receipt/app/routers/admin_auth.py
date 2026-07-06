from fastapi import APIRouter, Depends, Request, Response, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from app.core.dependencies import templates
from app.core.db import get_conn
from app.authentication.common.utils import verify_pin
from app.authentication.admin.jwt import create_admin_access_token
from app.authentication.admin.sessions import create_admin_session, get_admin_session_db, revoke_admin_session_db
from app.authentication.admin.cookies import set_admin_auth_cookies, clear_admin_auth_cookies

router = APIRouter(tags=["Admin Authentication"])

@router.get("/login", name="adminloginpage", response_class=HTMLResponse)
async def adminloginpage(request: Request, error: str = None):
    """Serves the Admin Login HTML UI"""
    return templates.TemplateResponse(
        request=request, 
        name="admin_login.html", 
        context={"request": request, "error": error}
    )

@router.post("/api/login", name="adminloginpost")
async def adminloginpost(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False),
):
    """Processes the login form submission"""
    with get_conn() as conn:
        admin = conn.execute("SELECT id, password_hash FROM admins WHERE username = ?", (username,)).fetchone()
        
    # Verify Admin Username & Password Hash
    if not admin or not verify_pin(password, admin["password_hash"]):
        # Redirect back to login with an error message
        login_url = f"{request.url_for('adminloginpage')}?error=Invalid+username+or+password"
        return RedirectResponse(url=login_url, status_code=303)
        
    # Generate Session & Tokens
    session_id, refresh_token = create_admin_session(admin['id'], request, remember_me)
    access_token = create_admin_access_token(admin['id'], session_id)
    
    # Format cookie value correctly for rotation
    cookie_val = f"{session_id}:{refresh_token}"
    
    # Redirect to the main dashboard upon success
    from app.core.routes import Names
    dashboard_url = str(request.url_for(Names.HOME))
    response = RedirectResponse(url=dashboard_url, status_code=303)
    set_admin_auth_cookies(response, access_token, cookie_val, remember_me, request)
    
    return response

@router.post("/api/refresh")
async def admin_refresh(request: Request, response: Response):
    """Admin Refresh Token Rotation Flow"""
    refresh_token = request.cookies.get("admin_refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
        
    parts = refresh_token.split(":")
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="Malformed refresh token")
    
    session_id, token_secret = parts[0], parts[1]
    
    session = get_admin_session_db(session_id)
    if not session or not verify_pin(token_secret, session["refresh_token_hash"]):
        revoke_admin_session_db(session_id)
        clear_admin_auth_cookies(response, request)
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    revoke_admin_session_db(session_id) 
    
    new_session_id, new_refresh_token = create_admin_session(session["admin_id"], request, remember_me=True)
    new_access_token = create_admin_access_token(session["admin_id"], new_session_id)
    
    new_cookie_val = f"{new_session_id}:{new_refresh_token}"
    set_admin_auth_cookies(response, new_access_token, new_cookie_val, remember_me=True, request=request)
    
    return {"status": "success", "message": "Admin tokens refreshed silently"}


@router.get("/logout", name="adminlogout")
async def adminlogout(request: Request):
    """Logs the admin out and clears cookies"""
    token = request.cookies.get("admin_access_token")
    if token:
        try:
            from app.authentication.admin.jwt import decode_admin_access_token
            payload = decode_admin_access_token(token)
            revoke_admin_session_db(payload.get("sid"))
        except Exception:
            pass
            
    login_url = str(request.url_for("adminloginpage"))
    response = RedirectResponse(url=login_url, status_code=303)
    clear_admin_auth_cookies(response, request)
    return response