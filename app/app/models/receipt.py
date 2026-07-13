from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional

class Receipt(BaseModel):
    billNo: str
    date: str
    month: str
    tenantName: str
    tenantId: int
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
    model_config = ConfigDict(populate_by_name=True)

    tenant: str
    month: str
    currentreading: float = Field(..., alias="current_reading")
    additionalpersons: int = Field(0, alias="additional_persons")
    tankWater: float = Field(0.0, alias="tankWater")
    maintenancecharge: float = Field(0.0, alias="MaintenanceCharge")
    maintenancedesc: str = Field("", alias="MaintenanceDesc")
    previousarrears: float = Field(0.0, alias="previousArrears")
    amountreceived: Optional[float] = Field(None, alias="amountReceived")
    paymentstatus: str = Field("PENDING", alias="paymentStatus")

    @field_validator("tenant", "month", "maintenancedesc", mode="before")
    @classmethod
    def normalize_strs(cls, v):
        return "" if v is None else str(v).strip()

    @field_validator("additionalpersons", mode="before")
    @classmethod
    def normalize_int(cls, v):
        if v in ("", None):
            return 0
        return int(v)

    @field_validator("currentreading", "tankWater", "maintenancecharge", "previousarrears", mode="before")
    @classmethod
    def normalize_required_floats(cls, v):
        if v in ("", None):
            return 0.0
        return float(v)

    @field_validator("amountreceived", mode="before")
    @classmethod
    def normalize_optional_amount(cls, v):
        if v in ("", None):
            return None
        return float(v)

    @field_validator("paymentstatus", mode="before")
    @classmethod
    def normalize_status(cls, v):
        return str(v or "PENDING").strip().upper()

class PaymentStatusUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    paymentstatus: str = Field(..., alias="paymentStatus")
    amountreceived: Optional[float] = Field(None, alias="amountReceived")

    @field_validator("paymentstatus", mode="before")
    @classmethod
    def normalize_status(cls, v):
        return str(v or "").strip().upper()

    @field_validator("amountreceived", mode="before")
    @classmethod
    def normalize_amount(cls, v):
        if v in ("", None):
            return None
        return float(v)

