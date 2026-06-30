from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
import os

from utils.config_manager import load_config, save_config
from utils.csv_manager import get_all_receipts, get_receipt
from utils.billing import process_bill, edit_bill_process, BillRequest
from utils.tenant_manager import get_tenants, add_tenant, delete_tenant

app = FastAPI(title="Rent Receipt Generator")

# Create required directories if not exist
os.makedirs("receipts", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Page Routes ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    config = load_config()
    receipts = get_all_receipts()
    tenants = get_tenants()
    last_tenant = "-"
    if receipts:
        last_tenant = receipts[-1].get("Tenant", "-")
    return templates.TemplateResponse(
        request=request, name="index.html", context={
        "next_bill_number": str(config.get("next_bill_number", 1)).zfill(3),
        "last_meter_reading": config.get("previous_meter_reading", 0),
        "last_tenant": last_tenant,
        "total_tenants": len(tenants)
    })

@app.get("/billing", response_class=HTMLResponse)
async def billing_page(request: Request):
    config = load_config()
    tenants = get_tenants()
    return templates.TemplateResponse(
        request=request, name="billing.html", context={
        "config": config,
        "tenants": tenants
    })

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    receipts = get_all_receipts()
    receipts.reverse()
    return templates.TemplateResponse(
        request=request, name="history.html", context={
        "receipts": receipts
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    config = load_config()
    return templates.TemplateResponse(
        request=request, name="settings.html", context={
        "config": config
    })

@app.get("/tenants", response_class=HTMLResponse)
async def tenants_page(request: Request):
    tenants = get_tenants()
    return templates.TemplateResponse(
        request=request, name="tenants.html", context={
        "tenants": tenants
    })

@app.get("/edit_bill/{bill_no}", response_class=HTMLResponse)
async def edit_bill_page(request: Request, bill_no: str):
    config = load_config()
    tenants = get_tenants()
    receipt = get_receipt(bill_no)
    if not receipt:
        raise HTTPException(status_code=404, detail="Bill not found")
        
    return templates.TemplateResponse(
        request=request, name="edit_bill.html", context={
        "config": config,
        "tenants": tenants,
        "receipt": receipt
    })

# --- REST API ---

@app.get("/api/config")
async def get_config():
    return load_config()

class ConfigUpdate(BaseModel):
    landlord_name: str
    landlord_phone: str
    landlord_email: str
    property_address: str
    default_rent: float
    additional_person_charge: float
    water_charge: float
    electricity_rate: float
    previous_meter_reading: float
    next_bill_number: int

@app.post("/api/config")
async def update_config(data: ConfigUpdate):
    config = load_config()
    config.update(data.dict())
    save_config(config)
    return {"status": "success", "config": config}

@app.get("/api/history")
async def get_history():
    receipts = get_all_receipts()
    receipts.reverse()
    return {"receipts": receipts}

@app.post("/api/bill")
async def create_bill(request: BillRequest):
    config = load_config()
    prev = float(config.get("previous_meter_reading", 0))
    if request.current_reading < prev:
        raise HTTPException(status_code=400, detail="Current reading cannot be less than previous reading.")
    
    data_dict = process_bill(request)
    return {"status": "success", "data": data_dict}

@app.post("/api/edit_bill/{bill_no}")
async def edit_bill(bill_no: str, request: BillRequest):
    try:
        data_dict = edit_bill_process(bill_no, request)
        return {"status": "success", "data": data_dict}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class TenantCreate(BaseModel):
    name: str
    phone: str
    email: str

@app.post("/api/tenants")
async def api_add_tenant(data: TenantCreate):
    return add_tenant(data.name, data.phone, data.email)

@app.delete("/api/tenants/{tenant_id}")
async def api_delete_tenant(tenant_id: int):
    return delete_tenant(tenant_id)


@app.get("/api/pdf/{bill_no}")
async def download_pdf(bill_no: str):
    pdf_path = os.path.join("receipts", f"{bill_no}.pdf")
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type='application/pdf', filename=f"Receipt_{bill_no}.pdf")
    else:
        raise HTTPException(status_code=404, detail="PDF not found")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=20081, reload=True)
