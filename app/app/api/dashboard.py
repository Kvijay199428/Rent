# File: app\app\api\dashboard.py
from fastapi import APIRouter
from app.services.billing_service import get_dashboard_stats

from app.core.routes_manifest import Routes, Names

router = APIRouter(tags=["Dashboard API"])

@router.get(Routes.ADMINAPIDASHBOARDSTATS, name=Names.HEALTHCHECK)
async def dashboard_api():
    """Returns dashboard statistics as JSON."""
    stats = get_dashboard_stats()
    return {"stats": stats}