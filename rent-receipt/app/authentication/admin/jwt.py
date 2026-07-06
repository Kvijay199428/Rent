import os
from jose import jwt
from datetime import datetime, timedelta

ADMIN_JWT_SECRET = os.environ.get("ADMIN_JWT_SECRET", "REPLACE_WITH_ADMIN_SECURE_RANDOM_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15

def create_admin_access_token(admin_id: int, session_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(admin_id),
        "admin_id": admin_id,
        "sid": session_id,
        "role": "admin",
        "type": "access",
        "ver": 1,
        "iat": datetime.utcnow(),
        "exp": expire
    }
    return jwt.encode(to_encode, ADMIN_JWT_SECRET, algorithm=ALGORITHM)

def decode_admin_access_token(token: str):
    return jwt.decode(token, ADMIN_JWT_SECRET, algorithms=[ALGORITHM])
