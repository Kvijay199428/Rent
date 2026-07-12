from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    view_token: str
    pin: str
    remember_me: bool = False

class ChangePinRequest(BaseModel):
    current_pin: str
    new_pin: str

class DeviceSession(BaseModel):
    session_id: str
    device_name: str
    ip_address: str
    last_activity: str
    status: str

