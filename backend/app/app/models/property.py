"""
app/models/property.py

Pydantic request / response models for the landlord property entity
(initial setup wizard + property-first billing).
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class Property(BaseModel):
    id: Optional[int] = None
    landlord_id: Optional[int] = None
    property_name: str = Field(min_length=1, max_length=120)
    address: Optional[str] = ""
    sort_order: Optional[int] = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PropertyCreateRequest(BaseModel):
    property_name: str = Field(min_length=1, max_length=120)
    address: Optional[str] = ""


class PropertyUpdateRequest(BaseModel):
    property_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    address: Optional[str] = None


class PropertyResponse(BaseModel):
    properties: List[Property]
    total: int


class LandlordSetupStatus(BaseModel):
    required: bool
    setupCompleted: bool = False
    setupSkipped: bool = False
    propertyCount: int = 0
    landlord: Optional[dict] = None


class LandlordSetupCompleteRequest(BaseModel):
    skip: bool = False
    propertyName: Optional[str] = None
    address: Optional[str] = ""
    properties: List[PropertyCreateRequest] = []
    landlord: Optional[dict] = None
