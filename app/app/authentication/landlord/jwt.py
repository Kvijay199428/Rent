"""
app/authentication/landlord/jwt.py

Create and decode landlord access tokens.
JWT payload carries role='landlord' so it can never be confused with
admin or tenant tokens.
"""
import os
from datetime import datetime, timedelta

from jose import jwt

LANDLORD_JWT_SECRET = os.environ.get(
    "LANDLORD_JWT_SECRET", "REPLACE_WITH_LANDLORD_SECURE_RANDOM_KEY"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15


def create_landlord_access_token(landlord_id: int, session_id: str) -> str:
    """Return a signed JWT for the given landlord + session."""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(landlord_id),
        "landlord_id": landlord_id,
        "sid": session_id,
        "role": "landlord",
        "type": "access",
        "ver": 1,
        "iat": datetime.utcnow(),
        "exp": expire,
    }
    return jwt.encode(payload, LANDLORD_JWT_SECRET, algorithm=ALGORITHM)


def decode_landlord_access_token(token: str) -> dict:
    """Decode and verify a landlord JWT, raising jose.JWTError on failure."""
    return jwt.decode(token, LANDLORD_JWT_SECRET, algorithms=[ALGORITHM])
