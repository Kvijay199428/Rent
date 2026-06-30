from pydantic import BaseModel, Field
from typing import Optional

class Tenant(BaseModel):
    id: Optional[int] = None
    name: str
    company: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    room_number: Optional[str] = ""
    occupation: Optional[str] = ""
    notes: Optional[str] = ""
    status: str = "Active" # Active or Inactive
