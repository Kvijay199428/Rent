import os
from jose import jwt
from datetime import datetime, timedelta

TENANT_JWT_SECRET = os.environ.get("TENANT_JWT_SECRET", "REPLACE_WITH_TENANT_SECURE_RANDOM_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15

def create_tenant_access_token(tenant_id: int, session_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(tenant_id),
        "tenant_id": tenant_id,
        "sid": session_id,
        "role": "tenant",
        "type": "access",
        "ver": 1,
        "iat": datetime.utcnow(),
        "exp": expire
    }
    return jwt.encode(to_encode, TENANT_JWT_SECRET, algorithm=ALGORITHM)

def decode_tenant_access_token(token: str):
    return jwt.decode(token, TENANT_JWT_SECRET, algorithms=[ALGORITHM])

