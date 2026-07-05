from pydantic import BaseModel
from typing import Optional

class Receipt(BaseModel):
    bill_no: str
    date: str
    month: str
    tenant_name: str
    previous_reading: float
    current_reading: float
    units_consumed: float
    rent: float
    additional_charge: float
    water_charge: float
    electricity_charge: float
    total: float
    pdf_filename: str

class BillRequest(BaseModel):
    tenant: str
    month: str
    current_reading: float
    additional_persons: int
    tank_water: float = 0.0
    maintenance_charge: float = 0.0
    maintenance_desc: str = ""
    previous_arrears: float = 0.0
    amount_received: Optional[float] = None
    payment_status: str = "PENDING"

class PaymentStatusUpdate(BaseModel):
    payment_status: str
    amount_received: Optional[float] = None

class BulkWhatsappRequest(BaseModel):
    bill_nos: list[str]
