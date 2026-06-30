from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import os

from services.config_service import (
    get_billing_config, save_billing_config,
    get_landlord_config, save_landlord_config,
    get_ui_config, save_ui_config
)
from services.tenant_service import (
    load_tenants, add_tenant, update_tenant, delete_tenant
)
from services.billing_service import (
    get_all_receipts, get_receipt, get_billing_months,
    calculate_charges, create_bill, update_bill, delete_bill,
    get_dashboard_stats
)
from models.tenant import Tenant

app = FastAPI(title="Rent Receipt Web Application")

# Mount Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- UI Theme Context Injection ---
@app.middleware("http")
async def add_theme_to_templates(request: Request, call_next):
    # Store theme in request state so it is accessible in template responses
    ui_conf = get_ui_config()
    request.state.theme = ui_conf.get("theme", "system")
    response = await call_next(request)
    return response

# --- Page Routes ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = get_dashboard_stats()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name="dashboard.html", context={
            "stats": stats,
            "theme": theme
        }
    )

@app.get("/billing", response_class=HTMLResponse)
async def billing_page(request: Request):
    billing_conf = get_billing_config()
    tenants = [t for t in load_tenants() if t.status == "Active"]
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name="billing.html", context={
            "config": billing_conf,
            "tenants": tenants,
            "theme": theme
        }
    )

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    receipts = get_all_receipts()
    receipts.reverse()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name="history.html", context={
            "receipts": receipts,
            "theme": theme
        }
    )

@app.get("/tenants", response_class=HTMLResponse)
async def tenants_page(request: Request):
    tenants = load_tenants()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name="tenants.html", context={
            "tenants": tenants,
            "theme": theme
        }
    )

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    billing_conf = get_billing_config()
    landlord_conf = get_landlord_config()
    ui_conf = get_ui_config()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name="settings.html", context={
            "billing_config": billing_conf,
            "landlord_config": landlord_conf,
            "ui_config": ui_conf,
            "theme": theme
        }
    )

@app.get("/edit_bill/{bill_no}", response_class=HTMLResponse)
async def edit_bill_page(request: Request, bill_no: str):
    receipt = get_receipt(bill_no)
    if not receipt:
        raise HTTPException(status_code=404, detail="Bill not found")
        
    billing_conf = get_billing_config()
    tenants = load_tenants()
    theme = getattr(request.state, "theme", "system")
    return templates.TemplateResponse(
        request=request, name="edit_bill.html", context={
            "receipt": receipt,
            "config": billing_conf,
            "tenants": tenants,
            "theme": theme
        }
    )

# --- REST API ---

@app.get("/api/config")
async def get_config():
    return {
        "billing": get_billing_config(),
        "landlord": get_landlord_config(),
        "ui": get_ui_config()
    }

class ConfigUpdateModel(BaseModel):
    landlord: dict
    billing: dict

@app.post("/api/config")
async def update_config(data: ConfigUpdateModel):
    save_landlord_config(data.landlord)
    save_billing_config(data.billing)
    return {"status": "success"}

@app.post("/api/ui/theme")
async def update_theme(data: dict):
    theme = data.get("theme", "system")
    ui_conf = get_ui_config()
    ui_conf["theme"] = theme
    save_ui_config(ui_conf)
    return {"status": "success"}

@app.get("/api/billing/months")
async def api_billing_months():
    return get_billing_months()

@app.get("/api/billing/preview")
async def api_billing_preview(current_reading: float, additional_persons: int):
    return calculate_charges(current_reading, additional_persons)

class BillRequest(BaseModel):
    tenant: str
    month: str
    current_reading: float
    additional_persons: int

@app.post("/api/bill")
async def api_create_bill(request: BillRequest):
    billing_conf = get_billing_config()
    prev = float(billing_conf.get("previous_meter_reading", 0.0))
    if request.current_reading < prev:
        raise HTTPException(status_code=400, detail="Current meter reading cannot be less than previous reading.")
        
    try:
        data = create_bill(
            request.tenant,
            request.month,
            request.current_reading,
            request.additional_persons
        )
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/edit_bill/{bill_no}")
async def api_update_bill(bill_no: str, request: BillRequest):
    receipt = get_receipt(bill_no)
    if not receipt:
        raise HTTPException(status_code=404, detail="Bill not found")
        
    prev = float(receipt["Previous"])
    if request.current_reading < prev:
        raise HTTPException(status_code=400, detail="Current meter reading cannot be less than previous reading.")
        
    try:
        data = update_bill(
            bill_no,
            request.tenant,
            request.month,
            request.current_reading,
            request.additional_persons
        )
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/bill/{bill_no}")
async def api_delete_bill(bill_no: str):
    try:
        delete_bill(bill_no)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/pdf/{bill_no}")
async def download_pdf(bill_no: str):
    receipt = get_receipt(bill_no)
    if not receipt:
        raise HTTPException(status_code=404, detail="PDF not found")
        
    try:
        year_str = receipt["Month"].split()[-1]
    except Exception:
        year_str = datetime.now().strftime("%Y")
        
    pdf_path = os.path.join("receipts", year_str, receipt["PDF"])
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type='application/pdf', filename=f"Receipt_{bill_no}.pdf")
    else:
        # Fallback: Regenerate PDF if missing
        try:
            from services.pdf_service import generate_professional_pdf
            landlord_conf = get_landlord_config()
            generate_professional_pdf(receipt, landlord_conf, pdf_path)
            return FileResponse(pdf_path, media_type='application/pdf', filename=f"Receipt_{bill_no}.pdf")
        except Exception:
            raise HTTPException(status_code=404, detail="PDF file not found and could not be regenerated.")

@app.get("/api/tenants")
async def api_get_tenants():
    return load_tenants()

@app.post("/api/tenants")
async def api_add_tenant(t: Tenant):
    return add_tenant(t)

@app.put("/api/tenants/{tenant_id}")
async def api_update_tenant(tenant_id: int, t: Tenant):
    t.id = tenant_id
    return update_tenant(t)

@app.delete("/api/tenants/{tenant_id}")
async def api_delete_tenant(tenant_id: int):
    delete_tenant(tenant_id)
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=20081, reload=True)
