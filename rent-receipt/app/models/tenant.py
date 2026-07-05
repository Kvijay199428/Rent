from pydantic import BaseModel
from typing import Optional

class Tenant(BaseModel):
    id: Optional[int] = None
    
    # General Info
    name: str
    company: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    room_number: Optional[str] = ""
    occupation: Optional[str] = ""
    notes: Optional[str] = ""
    status: str = "Active" # Active or Inactive

    # Billing Profile
    rent: float = 0.0
    water: float = 0.0
    default_tank_water_charge: float = 0.0
    electricity_rate: float = 0.0
    previous_meter: float = 0.0
    additional_person_charge: float = 0.0
    
    # Security Profile
    security_deposit: float = 0.0
    
    # Utilities
    meter_id: Optional[str] = ""
    
    # NEW: Secure access token for public QR profiles
    view_token: Optional[str] = ""
    
    # NEW: Security PIN for Tenant Portal (Default to 1234)
    tenant_pin: str = "1234"
    
    # NEW: Current arrears (balance due)
    arrears: float = 0.0
