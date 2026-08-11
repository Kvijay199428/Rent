"""
app/api/landlord_setup.py

Landlord initial-setup wizard + property management endpoints.

GET  /landlord/api/setup/required                → setup gate status
POST /landlord/api/setup/create                  → complete wizard (profile + properties)
POST /landlord/api/setup/skip                    → "Complete Later" (setup_skipped)
GET/POST  /landlord/{landlordUuid}/api/properties            → list / create
PUT/DELETE /landlord/{landlordUuid}/api/properties/{id}       → update / delete
GET  /landlord/{landlordUuid}/api/properties/{id}/tenants     → property's tenants
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Request

from app.authentication.landlord.middleware import get_current_landlord_api_strict
from app.core.routes_manifest_landlord import LandlordRoutes as Routes, LandlordNames as Names
from app.database.landlord_repository import create_landlord_audit_log
from app.database.property_repository import (
    count_properties,
    create_property,
    delete_property,
    get_property,
    get_setup_flags,
    list_properties,
    mark_setup_complete,
    mark_setup_skipped,
    tenants_for_property,
    update_property,
)
from app.models.property import (
    PropertyCreateRequest,
    PropertyUpdateRequest,
    LandlordSetupCompleteRequest,
)
from app.services.landlord_config_service import save_effective_landlord_config

router = APIRouter(tags=["Landlord Setup"])


@router.get(Routes.LANDLORDAPISETUPREQUIRED, name=Names.LANDLORDSETUPREQUIRED)
async def setup_required(principal=Depends(get_current_landlord_api_strict)):
    """Return whether the landlord still needs to complete initial setup."""
    flags = get_setup_flags(principal.landlord_id)
    return {
        "status": "success",
        "required": not flags["setupCompleted"],
        "setupCompleted": flags["setupCompleted"],
        "setupSkipped": flags["setupSkipped"],
        "propertyCount": count_properties(principal.landlord_id),
    }


@router.post(Routes.LANDLORDAPISETUPCREATE, name=Names.LANDLORDSETUPCREATE)
async def setup_create(
    request: Request,
    payload: LandlordSetupCompleteRequest,
    principal=Depends(get_current_landlord_api_strict),
):
    """Complete the initial-setup wizard: optional landlord profile, property list,
    or explicit skip ("Complete Later")."""
    if payload.skip:
        mark_setup_skipped(principal.landlord_id)
        create_landlord_audit_log(
            principal.landlord_id,
            "setup_skipped",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({}),
        )
        return {"status": "success", "skipped": True, "setupCompleted": False}

    if payload.properties:
        for prop in payload.properties:
            create_property(
                principal.landlord_id,
                prop.property_name.strip(),
                (prop.address or "").strip(),
            )

    if payload.landlord:
        save_effective_landlord_config(principal.landlord_id, dict(payload.landlord))

    mark_setup_complete(principal.landlord_id)
    create_landlord_audit_log(
        principal.landlord_id,
        "setup_completed",
        ip_address=request.client.host if request.client else None,
        meta_json=json.dumps({"properties_created": len(payload.properties)}),
    )
    return {
        "status": "success",
        "setupCompleted": True,
        "properties": list_properties(principal.landlord_id),
    }


@router.post(Routes.LANDLORDAPISETUPSKIP, name=Names.LANDLORDSETUPSKIP)
async def setup_skip(request: Request, principal=Depends(get_current_landlord_api_strict)):
    """Mark setup as skipped ("Complete Later")."""
    mark_setup_skipped(principal.landlord_id)
    create_landlord_audit_log(
        principal.landlord_id,
        "setup_skipped",
        ip_address=request.client.host if request.client else None,
        meta_json=json.dumps({"source": "setup_page"}),
    )
    return {"status": "success", "skipped": True, "setupCompleted": False}


# ─── Properties ──────────────────────────────────────────────────────────────

@router.get(Routes.LANDLORDAPIPROPERTIESLIST, name=Names.APIGETPROPERTIES)
async def api_list_properties(landlordUuid: str, principal=Depends(get_current_landlord_api_strict)):
    return {"status": "success", "properties": list_properties(principal.landlord_id)}


@router.post(Routes.LANDLORDAPIPROPERTIESCREATE, name=Names.APICREATEPROPERTY)
async def api_create_property(
    landlordUuid: str,
    request: Request,
    payload: PropertyCreateRequest,
    principal=Depends(get_current_landlord_api_strict),
):
    name = payload.property_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Property name is required.")
    prop = create_property(principal.landlord_id, name, (payload.address or "").strip())
    create_landlord_audit_log(
        principal.landlord_id,
        "property_created",
        ip_address=request.client.host if request.client else None,
        meta_json=json.dumps({"property_id": prop["id"], "property_name": prop["property_name"]}),
    )
    return {"status": "success", "property": prop}


@router.put(Routes.LANDLORDAPIPROPERTIESUPDATE, name=Names.APIUPDATEPROPERTY)
async def api_update_property(
    landlordUuid: str,
    propertyId: int,
    request: Request,
    payload: PropertyUpdateRequest,
    principal=Depends(get_current_landlord_api_strict),
):
    if payload.property_name is not None and not payload.property_name.strip():
        raise HTTPException(status_code=400, detail="Property name cannot be empty.")
    updated = update_property(
        principal.landlord_id,
        propertyId,
        property_name=payload.property_name.strip() if payload.property_name is not None else None,
        address=payload.address,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Property not found.")
    create_landlord_audit_log(
        principal.landlord_id,
        "property_updated",
        ip_address=request.client.host if request.client else None,
        meta_json=json.dumps({"property_id": propertyId}),
    )
    return {"status": "success", "property": updated}


@router.delete(Routes.LANDLORDAPIPROPERTIESDELETE, name=Names.APIDELETEPROPERTY)
async def api_delete_property(
    landlordUuid: str,
    propertyId: int,
    request: Request,
    principal=Depends(get_current_landlord_api_strict),
):
    if not delete_property(principal.landlord_id, propertyId):
        raise HTTPException(status_code=404, detail="Property not found.")
    create_landlord_audit_log(
        principal.landlord_id,
        "property_deleted",
        ip_address=request.client.host if request.client else None,
        meta_json=json.dumps({"property_id": propertyId}),
    )
    return {"status": "success"}


@router.get(Routes.LANDLORDAPIPROPERTIESTENANTS, name=Names.APIGETPROPERTYTENANTS)
async def api_property_tenants(
    landlordUuid: str,
    propertyId: int,
    principal=Depends(get_current_landlord_api_strict),
):
    if not get_property(principal.landlord_id, propertyId):
        raise HTTPException(status_code=404, detail="Property not found.")
    return {"status": "success", "tenants": tenants_for_property(principal.landlord_id, propertyId)}
