from dataclasses import dataclass
from typing import Optional

@dataclass
class AuthPrincipal:
    authentication_type: str
    role: str
    id: int
    session_id: str

    tenantId: Optional[int] = None
    admin_id: Optional[int] = None
    landlord_id: Optional[int] = None

    # Landlord-specific profile fields (populated by landlord middleware)
    landlord_uuid: Optional[str] = None
    username: Optional[str] = None
    fullname: Optional[str] = None
    email: Optional[str] = None

