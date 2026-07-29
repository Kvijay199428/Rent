# File: app\app\api\dashboard.py
from fastapi import APIRouter
from app.services.billing_service import get_dashboard_stats

from app.core.routes_manifest_landlord import LandlordRoutes as Routes, LandlordNames as Names

router = APIRouter(tags=["Dashboard API"])

@router.get(Routes.LANDLORDAPIDASHBOARDSTATS, name="api_dashboard_stats")
async def dashboard_api(landlordUuid: str):
    """Returns dashboard statistics as JSON."""
    stats = get_dashboard_stats()
    return {"stats": stats}
