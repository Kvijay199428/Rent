from fastapi import Request, HTTPException
from app.authentication.tenant.jwt import decode_tenant_access_token
from app.authentication.tenant.sessions import get_tenant_session_db
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


def _tenant_redirect_url(request: Request) -> str:
    viewToken = request.path_params.get("viewToken")
    if viewToken:
        return str(request.url_for("public_tenant_profile_get", viewToken=viewToken))

    referer = request.headers.get("referer")
    if referer:
        return referer

    return "/"


def _raise_tenant_session_expired(request: Request, detail: str):
    redirect_url = _tenant_redirect_url(request)
    if _is_browser_navigation(request):
        raise HTTPException(status_code=303, headers={"Location": redirect_url})
    raise HTTPException(
        status_code=401,
        detail=detail,
        headers={
            "X-Session-Expired": "1",
            "X-Redirect-Url": redirect_url,
        },
    )


async def get_current_tenant(request: Request) -> AuthPrincipal:
    token = request.cookies.get("tenant_access_token")
    if not token:
        _raise_tenant_session_expired(request, "Access token missing. Requires refresh.")

    try:
        payload = decode_tenant_access_token(token)
        if payload.get("role") != "tenant":
            raise HTTPException(status_code=403, detail="Forbidden: Tenant access required")

        session_id = payload.get("sid")
        session = get_tenant_session_db(session_id)
        if not session:
            _raise_tenant_session_expired(request, "Session revoked")

        tenantId = int(payload.get("tenantId") or payload.get("sub"))
        return AuthPrincipal(
            authentication_type="tenant_api",
            role="tenant",
            id=tenantId,
            session_id=session_id,
            tenantId=tenantId
        )
    except HTTPException:
        raise
    except Exception:
        _raise_tenant_session_expired(request, "Access token expired. Requires refresh.")

