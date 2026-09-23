# app/api/notifications.py
"""Reusable, landlord-auth-scoped notification surface.

A single source-driven rule set. Each rule inspects the landlord's data and may
emit one generic notice: {slug, title, message, action?}. The landlord SPA polls
GET /landlord/{landlordUuid}/api/notifications once after auth (and can re-poll
on demand), so future notices ("maintenance window", "data export ready", ...)
are added here without touching UI code.
"""

from fastapi import APIRouter, Depends

from app.core.routes_manifest_landlord import LandlordRoutes as Routes, LandlordNames as Names
from app.authentication.landlord.middleware import get_current_landlord_api_strict
from app.core.db import get_conn
from app.services.qr_service import QR_URI_SCHEME_VERSION

router = APIRouter()


@router.get(Routes.LANDLORDAPINOTIFICATIONS, name=Names.LANDLORDNOTIFICATIONS)
async def api_landlord_notifications(
    landlordUuid: str,
    principal=Depends(get_current_landlord_api_strict),
):
    """Return active notifications for the authenticated landlord.

    Generic payload: {"notifications":[{slug,title,message,action}]}.
    Empty list means nothing to show.
    """
    period = []
    with get_conn() as conn:
        stale = conn.execute(
            'SELECT COUNT(*) AS n FROM tenants '
            'WHERE "landlordId" = %s AND "qrUriVersion" < %s',
            (principal.landlord_id, QR_URI_SCHEME_VERSION),
        ).fetchone()["n"]

    if stale:
        period = [
            {
                "slug": "tenant_qr_uri_version",
                "title": "Regenerate tenant QRs",
                "message": (
                    f"{stale} tenant QR(s) still use the previous portal-link scheme and "
                    "no longer reach the tenant app. Regenerate them in Tenants to keep "
                    "printed material and stored QR codes working."
                ),
                "action": {"label": "Go to Tenants", "href": "/landlord/tenants"},
            }
        ]

    return {"notifications": period}