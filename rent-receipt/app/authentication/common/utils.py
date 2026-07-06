import re
from fastapi import HTTPException
from passlib.context import CryptContext

# Phase 1: PIN Security using Argon2id
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_pin(pin: str) -> str:
    """Hashes a plaintext PIN or Token using Argon2id."""
    return pwd_context.hash(pin)

def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Verifies a plaintext PIN against the stored Argon2id hash."""
    try:
        return pwd_context.verify(plain_pin, hashed_pin)
    except Exception:
        return False

def validate_tenant_pin(pin: str) -> str:
    """Validates that a PIN is exactly 4 digits."""
    if not pin or not re.fullmatch(r"\d{4}", str(pin)):
        raise HTTPException(
            status_code=400,
            detail="Tenant PIN must contain exactly 4 digits."
        )
    return str(pin)