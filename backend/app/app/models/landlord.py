"""
app/models/landlord.py

Pydantic request / response models for the landlord authentication endpoints.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class LandlordSignupRequest(BaseModel):
    fullName: str = Field(min_length=2, max_length=120)
    email: Optional[str] = Field(default=None, max_length=254)
    phone: Optional[str] = Field(default=None, max_length=20)
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, max_length=128)
    confirmPassword: str = Field(min_length=8, max_length=128)
    privacyAccepted: bool = False
    privacyVersion: str = Field(default="", max_length=32)


class LandlordLoginRequest(BaseModel):
    username: str
    password: str
    rememberMe: bool = False


class LandlordLoginWithTotpRequest(BaseModel):
    username: str
    password: str
    totpToken: str
    rememberMe: bool = False


class LandlordGoogleRequest(BaseModel):
    credential: str
    rememberMe: bool = False


class LandlordPrivacyConsentRequest(BaseModel):
    accepted: bool = True
    privacyVersion: str = Field(default="", max_length=32)


class UsernameCheckResponse(BaseModel):
    username: str
    available: bool
    suggestions: List[str] = []

