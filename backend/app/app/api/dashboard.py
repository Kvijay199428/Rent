# File: app\app\api\dashboard.py
from fastapi import APIRouter, Depends
from app.services.billing_service import get_dashboard_stats

from app.core.routes_manifest_landlord import LandlordRoutes as Routes, LandlordNames as Names
from app.authentication.landlord.middleware import get_current_landlord_api_strict

router = APIRouter(tags=["Dashboard API"])

@router.get(Routes.LANDLORDAPIDASHBOARDSTATS, name="api_dashboard_stats")
async def dashboard_api(landlordUuid: str, principal=Depends(get_current_landlord_api_strict)):
    """Returns dashboard statistics as JSON."""
    stats = get_dashboard_stats(landlord_id=principal.landlord_id)
    return {"stats": stats}
