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
