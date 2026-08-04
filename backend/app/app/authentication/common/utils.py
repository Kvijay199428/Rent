import re
from fastapi import HTTPException
from passlib.context import CryptContext
from hmac import compare_digest

# Phase 1: PIN Security using Argon2id
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def constant_time_eq(a: str, b: str) -> bool:
    """Constant-time string comparison."""
    try:
        return compare_digest(str(a or ""), str(b or ""))
    except Exception:
        return False

def hash_pin(pin: str) -> str:
    """Hashes a plaintext PIN or Token using Argon2id."""
    return pwd_context.hash(pin)

def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Verifies a plaintext PIN against the stored Argon2id hash."""
    try:
        return pwd_context.verify(plain_pin, hashed_pin)
    except Exception:
        return False

def validate_tenantPin(pin: str) -> str:
    """Validates that a PIN is exactly 4 digits."""
    if not pin or not re.fullmatch(r"\d{4}", str(pin)):
        raise HTTPException(
            status_code=400,
            detail="Tenant PIN must contain exactly 4 digits."
        )
    return str(pin)

_USERNAME_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-_.!@#$%^&*+]{2,}$')

def validate_username(username: str):
    """Username must not contain spaces, be 3-50 chars, and use only letters, digits, and special characters."""
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    if re.search(r'\s', username):
        raise HTTPException(status_code=400, detail="Username must not contain spaces")
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(username) > 50:
        raise HTTPException(status_code=400, detail="Username must not exceed 50 characters")
    if not _USERNAME_RE.match(username):
        raise HTTPException(
            status_code=400,
            detail="Username must start with a letter or digit and contain only letters, digits, and !@#$%^&*_-."
        )

def validate_password(password: str):
    """Password must not contain spaces and be at least 8 characters."""
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")
    if re.search(r'\s', password):
        raise HTTPException(status_code=400, detail="Password must not contain spaces")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

