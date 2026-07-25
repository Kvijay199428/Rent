"""
app/authentication/platform/jwt.py
Separate JWT layer for the platform admin (super-admin) role.
Uses a distinct secret and role='platform_admin' so it cannot
be confused with landlord-admin or tenant tokens.
"""
import os
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import HTTPException

PLATFORM_JWT_SECRET = os.environ.get(
    "PLATFORM_JWT_SECRET", "REPLACE_WITH_PLATFORM_SECURE_RANDOM_KEY"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_platform_access_token(admin_id: int, session_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(admin_id),
        "admin_id": admin_id,
        "sid": session_id,
        "role": "platform_admin",
        "type": "access",
        "ver": 1,
        "iat": datetime.utcnow(),
        "exp": expire,
    }
    return jwt.encode(payload, PLATFORM_JWT_SECRET, algorithm=ALGORITHM)


def decode_platform_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, PLATFORM_JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get("role") != "platform_admin":
            raise JWTError("wrong role")
        return payload
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid platform token") from exc
