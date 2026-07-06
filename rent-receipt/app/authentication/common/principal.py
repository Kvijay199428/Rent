from dataclasses import dataclass
from typing import Optional

@dataclass
class AuthPrincipal:
    authentication_type: str
    role: str
    id: int
    session_id: str
    tenant_id: Optional[int] = None
    admin_id: Optional[int] = None
