# // File: app\app\api\whatsapp.py
from fastapi import APIRouter, Request, HTTPException
from urllib.parse import quote

from app.core.routes_manifest import Names, Routes

from app.core.dependencies import config
from app.services.tenant_service import load_tenants
from app.services.billing_service import get_receipt
import re

router = APIRouter()

@router.get(Routes.ADMIN_API_WHATSAPP_SEND_SINGLE, name=Names.SEND_WHATSAPP_SINGLE)
async def send_whatsapp_single(request: Request, billno: str):
    billno = billno
    receipt = get_receipt(billno)
    if not receipt:
        raise HTTPException(status_code=404, detail="Bill not found")

    tenants = load_tenants()
    tenant = next((t for t in tenants if t.name == receipt.get("Tenant")), None)
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

    token = getattr(tenant, "view_token", "")
    if not token:
        import uuid
        from app.services.tenant_service import update_tenant
        token = str(uuid.uuid4())
        tenant.view_token = token
        update_tenant(tenant)

    base_url = str(request.base_url).rstrip("/")
    link = f"{base_url}/t/{token}"
    grand_total = float(receipt.get("Total", 0)) + float(receipt.get("Previous_Arrears", 0))

    tenant_portal_pin = "(Unavailable)"
    try:
        from app.authentication.common.pin_vault import decrypt_admin_view_pin
        from app.core.db import get_conn
        with get_conn() as conn:
            row = conn.execute(
                "SELECT encrypted_pin FROM tenant_pin_admin_store WHERE tenant_id = ?",
                (tenant.id,)
            ).fetchone()
        if row:
            tenant_portal_pin = decrypt_admin_view_pin(row["encrypted_pin"])
    except Exception as e:
        pass

    msg = template.format(
        tenant_name=tenant.name,
        month=receipt.get("Month", ""),
        billno=billno,
        total="{:,.0f}".format(grand_total),
        currency="Rs.",
        link=link,
        tenant_pin=tenant_portal_pin
    )

    url = f"https://api.whatsapp.com/send?phone={phone}&text={quote(msg)}"
    return {"status": "success", "url": url}