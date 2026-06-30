from pydantic import BaseModel, Field
from typing import Optional

class Tenant(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., alias="Tenant Name")
    company: Optional[str] = Field("", alias="Company")
    phone: Optional[str] = Field("", alias="Phone")
    email: Optional[str] = Field("", alias="Email")
    address: Optional[str] = Field("", alias="Permanent Address")
    room_number: Optional[str] = Field("", alias="Room Number")
    occupation: Optional[str] = Field("", alias="Occupation")
    notes: Optional[str] = Field("", alias="Notes")
    status: str = Field("Active", alias="Status") # Active or Inactive

    class Config:
        populate_by_name = True
