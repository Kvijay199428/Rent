# // File: app\app\api\whatsapp.py
from fastapi import APIRouter, Request, HTTPException
from urllib.parse import quote

from app.core.routes_manifest import Names, Routes

from app.core.dependencies import config
from app.services.tenant_service import load_tenants
from app.services.billing_service import get_receipt
import re

router = APIRouter()

@router.get(Routes.ADMINAPIWHATSAPPSENDSINGLE, name=Names.SENDWHATSAPPSINGLE)
async def send_whatsapp_single(request: Request, tenantId: int, billNo: str):
    billNo = billNo
    receipt = get_receipt(tenantId, billNo)
    if not receipt:
        raise HTTPException(status_code=404, detail="Bill not found")

    from app.services.tenant_service import get_tenant
    tenant = get_tenant(tenantId)
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

    base_url = str(request.base_url).rstrip("/")
    link = f"{base_url}/t/{token}"
    grandTotal = float(receipt.get("Total", 0)) + float(receipt.get("previousArrears", 0))

    tenant_portal_pin = "(Unavailable)"
    try:
        from app.authentication.common.pin_vault import decrypt_admin_view_pin
        from app.core.db import get_conn
        with get_conn() as conn:
            row = conn.execute(
                "SELECT encrypted_pin FROM tenantPin_admin_store WHERE tenantId = ?",
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