from fastapi import Request, HTTPException
from app.authentication.admin.jwt import decode_admin_access_token
from app.authentication.admin.sessions import get_admin_session_db
from app.authentication.common.principal import AuthPrincipal


def _is_browser_navigation(request: Request) -> bool:
    sec_fetch_mode = (request.headers.get("sec-fetch-mode") or "").lower()
    sec_fetch_dest = (request.headers.get("sec-fetch-dest") or "").lower()
    accept = (request.headers.get("accept") or "").lower()

    if sec_fetch_mode == "navigate":
        return True
    if sec_fetch_dest in {"document", "iframe"}:
        return True
    if "text/html" in accept or "application/pdf" in accept:
        return True
    return False


def _raise_admin_session_expired(request: Request, detail: str = "Unauthorized"):
    logout_url = str(request.url_for("ADMINLOGOUT"))
    if _is_browser_navigation(request):
        raise HTTPException(status_code=303, headers={"Location": logout_url})
    raise HTTPException(
        status_code=401,
        detail=detail,
        headers={
            "X-Session-Expired": "1",
            "X-Redirect-Url": logout_url,
            "X-Clear-Cookies": "admin",
        },
    )


async def get_current_admin_page(request: Request) -> AuthPrincipal:
    token = request.cookies.get("admin_access_token")
    if not token:
        logout_url = str(request.url_for("ADMINLOGOUT"))
        raise HTTPException(status_code=303, headers={"Location": logout_url})

    try:
        payload = decode_admin_access_token(token)
        if payload.get("role") != "admin":
            logout_url = str(request.url_for("ADMINLOGOUT"))
            raise HTTPException(status_code=303, headers={"Location": logout_url})

        session_id = payload.get("sid")
        session = get_admin_session_db(session_id)
        if not session:
            logout_url = str(request.url_for("ADMINLOGOUT"))
            raise HTTPException(status_code=303, headers={"Location": logout_url})

        admin_id = int(payload.get("admin_id") or payload.get("sub"))
        return AuthPrincipal(
            authentication_type="admin_page",
            role="admin",
            id=admin_id,
            session_id=session_id,
            admin_id=admin_id
        )
    except HTTPException:
        raise
    except Exception:
        logout_url = str(request.url_for("ADMINLOGOUT"))
        raise HTTPException(status_code=303, headers={"Location": logout_url})


async def get_current_admin_api(request: Request) -> AuthPrincipal:
    token = request.cookies.get("admin_access_token")
    if not token:
        _raise_admin_session_expired(request, "Unauthorized")

    try:
        payload = decode_admin_access_token(token)
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Forbidden: Admin access required")

        session_id = payload.get("sid")
        session = get_admin_session_db(session_id)
        if not session:
            _raise_admin_session_expired(request, "Session revoked")

        admin_id = int(payload.get("admin_id") or payload.get("sub"))
        return AuthPrincipal(
            authentication_type="admin_api",
            role="admin",
            id=admin_id,
            session_id=session_id,
            admin_id=admin_id
        )
    except HTTPException:
        raise
    except Exception:
        _raise_admin_session_expired(request, "Unauthorized: Token expired or invalid")

