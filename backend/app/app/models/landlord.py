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
    termsAccepted: bool = False
    termsVersion: str = Field(default="", max_length=32)


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
    code: str
    rememberMe: bool = False


class LandlordGoogleConnectRequest(BaseModel):
    """OAuth authorization code for linking Google to an authenticated account."""

    code: str = Field(min_length=1, max_length=8192)


class LandlordPrivacyConsentRequest(BaseModel):
    accepted: bool = True
    privacyVersion: str = Field(default="", max_length=32)


class LandlordTermsConsentRequest(BaseModel):
    accepted: bool = True
    termsVersion: str = Field(default="", max_length=32)


class UsernameCheckResponse(BaseModel):
    username: str
    available: bool
    suggestions: List[str] = []


class LandlordProfileUpdateRequest(BaseModel):
    """Editable account profile fields (Settings -> Profile). All optional;
    only provided fields are updated."""

    fullName: Optional[str] = Field(default=None, min_length=2, max_length=120)
    email: Optional[str] = Field(default=None, max_length=254)
    phone: Optional[str] = Field(default=None, max_length=20)
    avatarUrl: Optional[str] = Field(default=None, max_length=2048)


class LandlordForgotPasswordVerifyRequest(BaseModel):
    """Verify username + TOTP code before a landlord reset their password."""

    username: str = Field(min_length=1, max_length=40)
    totpToken: str = Field(min_length=1, max_length=16)


class LandlordForgotPasswordResetRequest(BaseModel):
    """Reset a landlord password after TOTP verification."""

    username: str = Field(min_length=1, max_length=40)
    totpToken: str = Field(min_length=1, max_length=16)
    newPassword: str = Field(min_length=8, max_length=128)
    confirmPassword: str = Field(min_length=8, max_length=128)

