# // File: app\app\api\whatsapp.py
from fastapi import APIRouter, Request, HTTPException, Depends
from urllib.parse import quote

from app.core.routes_manifest_landlord import LandlordRoutes as Routes, LandlordNames as Names

from app.core.dependencies import config
from app.core.runtime import public_app_url
from app.services.tenant_service import load_tenants, get_tenant
from app.services.billing_service import get_receipt
from app.authentication.landlord.middleware import get_current_landlord_api_strict
import re

router = APIRouter()

@router.get(Routes.LANDLORDAPIWHATSAPPSENDSINGLE, name=Names.SENDWHATSAPPSINGLE)
async def send_whatsapp_single(landlordUuid: str, request: Request, tenantId: int, billNo: str, principal=Depends(get_current_landlord_api_strict)):
    receipt = get_receipt(tenantId, billNo, landlord_id=principal.landlord_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Bill not found")

    tenant = get_tenant(tenantId, landlord_id=principal.landlord_id)
    if not tenant or not tenant.phone:
        raise HTTPException(status_code=400, detail="Tenant phone number not found")

    if not config.get("system.features.whatsapp_sync", False):
        raise HTTPException(status_code=403, detail="WhatsApp feature is disabled.")

    whatsapp_conf = config.get("whatsapp", {})
    template_conf = whatsapp_conf.get("single_template", {})
    template = template_conf.get("message") or template_conf.get("default_message", "")

    if not template.strip():
        raise HTTPException(status_code=400, detail="WhatsApp template is empty.")

    phone = re.sub(r"\D", "", str(tenant.phone))
    if len(phone) == 10:
        country_code = str(whatsapp_conf.get("country_code") or "91")
        phone = country_code + phone

    token = getattr(tenant, "viewToken", "")
    if not token:
        import uuid
        from app.services.tenant_service import update_tenant
        token = str(uuid.uuid4())
        tenant.viewToken = token
        update_tenant(tenant)

    header_uuid = request.headers.get("x-landlord-uuid")
    if header_uuid:
        landlordUuid = header_uuid
    if not landlordUuid:
        raise HTTPException(status_code=400, detail="Missing landlord context in request")
        
    link = f"{public_app_url()}/rent/{landlordUuid}/t/{getattr(tenant, 'propertyId', 0) or 0}/{tenant.id}/{token}"
    grandTotal = float(receipt.get("Total", 0)) + float(receipt.get("previousArrears", 0))

    tenant_portal_pin = "(Unavailable)"
    try:
        from app.authentication.common.pin_vault import decrypt_admin_view_pin
        from app.core.db import get_conn
        with get_conn() as conn:
            row = conn.execute(
                "SELECT encrypted_pin FROM tenantPin_admin_store WHERE tenantId = %s",
                (tenant.id,)
            ).fetchone()
        if row:
            tenant_portal_pin = decrypt_admin_view_pin(row["encrypted_pin"])
    except Exception as e:
        pass

    msg = template.format(
        tenantName=tenant.name,
        month=receipt.get("Month", ""),
        billNo=billNo,
        total="{:,.0f}".format(grandTotal),
        currency="Rs.",
        link=link,
        tenantPin=tenant_portal_pin
    )

    url = f"https://api.whatsapp.com/send?phone={phone}&text={quote(msg)}"
    return {"status": "success", "url": url}
