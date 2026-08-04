from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    viewToken: str
    pin: str
    remember_me: bool = False

class UsernameLoginRequest(BaseModel):
    username: str
    pin: str
    remember_me: bool = False

class ForgotPasswordRequest(BaseModel):
    username: str

class ResetPasswordRequest(BaseModel):
    username: str
    token: str
    new_password: str

class ChangePinRequest(BaseModel):
    current_pin: str
    new_pin: str

class DeviceSession(BaseModel):
    session_id: str
    device_name: str
    ip_address: str
    last_activity: str
    status: str

