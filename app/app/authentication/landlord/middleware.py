"""
app/authentication/landlord/middleware.py

FastAPI dependency functions for landlord-protected routes.

get_current_landlord_page  — for HTML page routes; redirects to landlord login on failure.
get_current_landlord_api   — for API routes; returns HTTP 401 on failure.
                             Also enforces UUID path matching for /landlord/{landlordUuid}/api/* routes.
get_current_landlord_api_strict — like get_current_landlord_api but also blocks
                             access when the landlord has requires_password_change set.
"""
from fastapi import HTTPException, Request

from app.authentication.common.principal import AuthPrincipal
from app.authentication.landlord.jwt import decode_landlord_access_token
from app.authentication.landlord.sessions import get_landlord_session_db
from app.database.landlord_repository import get_landlord_by_id


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


def _landlord_login_url(request: Request) -> str:
    try:
        return str(request.url_for("landlordloginpage"))
    except Exception:
        root = (request.scope.get("root_path") or "").rstrip("/")
        return f"{root}/landlord/login"


def _build_principal(payload: dict, session_id: str, auth_type: str) -> AuthPrincipal:
    """Build an AuthPrincipal, eagerly loading landlord profile fields from the DB."""
    landlord_id = int(payload.get("landlord_id") or payload.get("sub"))
    landlord = get_landlord_by_id(landlord_id)

    landlord_uuid = landlord["landlord_uuid"] if landlord else None
    username = landlord["username"] if landlord else None
    fullname = landlord["full_name"] if landlord else None
    email = landlord["email"] if landlord else None

    return AuthPrincipal(
        authentication_type=auth_type,
        role="landlord",
        id=landlord_id,
        session_id=session_id,
        landlord_id=landlord_id,
        landlord_uuid=landlord_uuid,
        username=username,
        fullname=fullname,
        email=email,
    )


async def get_current_landlord_page(request: Request) -> AuthPrincipal:
    """
    Dependency for landlord-protected *page* routes.
    Redirects to landlord login page on any auth failure.
    """
    token = request.cookies.get("landlord_access_token")
    if not token:
        raise HTTPException(
            status_code=303,
            headers={"Location": _landlord_login_url(request)},
        )

    try:
        payload = decode_landlord_access_token(token)
        if payload.get("role") != "landlord":
            raise HTTPException(
                status_code=303,
                headers={"Location": _landlord_login_url(request)},
            )

        session_id = payload.get("sid")
        session = get_landlord_session_db(session_id)
        if not session:
            raise HTTPException(
                status_code=303,
                headers={"Location": _landlord_login_url(request)},
            )

        return _build_principal(payload, session_id, "landlord_page")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=303,
            headers={"Location": _landlord_login_url(request)},
        )


async def get_current_landlord_api(request: Request) -> AuthPrincipal:
    """
    Dependency for landlord-protected *API* routes.
    Returns HTTP 401 on any auth failure.
    Enforces UUID path matching: if the route contains {landlordUuid},
    the authenticated landlord's UUID must match the path UUID.
    """
    token = request.cookies.get("landlord_access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        payload = decode_landlord_access_token(token)
        if payload.get("role") != "landlord":
            raise HTTPException(status_code=403, detail="Forbidden: Landlord access required")

        session_id = payload.get("sid")
        session = get_landlord_session_db(session_id)
        if not session:
            raise HTTPException(
                status_code=401,
                detail="Session expired or revoked",
                headers={"X-Session-Expired": "1"},
            )

        principal = _build_principal(payload, session_id, "landlord_api")

        # Enforce UUID path matching for /landlord/{landlordUuid}/api/* routes
        path_uuid = request.path_params.get("landlordUuid")
        if path_uuid and principal.landlord_uuid != path_uuid:
            raise HTTPException(status_code=403, detail="Forbidden: UUID mismatch")

        return principal
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized: Token expired or invalid")


async def get_current_landlord_api_strict(request: Request) -> AuthPrincipal:
    """
    Stricter variant of get_current_landlord_api.
    In addition to normal auth checks, it blocks access when the landlord
    has requires_password_change = 1, returning HTTP 403 with a special header.
    Only the change-password endpoint itself is exempted (checked via path).
    """
    principal = await get_current_landlord_api(request)

    # Exempt the change-password endpoint itself
    path = request.url.path
    if path.endswith("/api/auth/change-password"):
        return principal

    from app.core.db import get_conn as _get_conn
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT requires_password_change FROM landlord_accounts WHERE id = ?",
            (principal.landlord_id,),
        ).fetchone()

    if row and row["requires_password_change"]:
        raise HTTPException(
            status_code=403,
            detail="Password change required. Please update your password to continue.",
            headers={"X-Password-Change-Required": "1"},
        )

    return principal
