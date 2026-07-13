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
    roomNumber: Optional[str] = ""
    occupation: Optional[str] = ""
    notes: Optional[str] = ""
    status: str = "Active" # Active or Inactive

    # Billing Profile
    rent: float = 0.0
    water: float = 0.0
    defaulttankWaterCharge: float = 0.0
    electricityRate: float = 0.0
    previousMeter: float = 0.0
    additionalPersonCharge: float = 0.0
    
    # Security Profile
    securityDeposit: float = 0.0
    
    # Utilities
    meterId: Optional[str] = ""
    
    # NEW: Secure access token for public QR profiles
    viewToken: Optional[str] = ""
    
    # NEW: Security PIN for Tenant Portal
    tenantPin: Optional[str] = None
    
    # NEW: Current arrears (balance due)
    arrears: float = 0.0

