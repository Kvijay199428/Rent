"""
app/database/landlord_repository.py

Pure SQL helper functions for the landlord_accounts, landlord_sessions,
and landlord_audit_logs tables.  No business logic lives here — callers
are responsible for validation, hashing, and UUID generation.
"""
import base64
import io
from datetime import datetime

import pyotp
import qrcode

from app.core.db import get_conn


# ──────────────────────────────────────────────────────────────────────────────
# Landlord account helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_landlord_by_username(username: str):
    """Return a single row from landlord_accounts matching *username*, or None."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM landlord_accounts WHERE username = ?",
            (username,),
        ).fetchone()


def get_landlord_by_email(email: str):
    """Return a single row from landlord_accounts matching *email*, or None."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM landlord_accounts WHERE email = ?",
            (email,),
        ).fetchone()


def get_landlord_by_id(landlord_id: int):
    """Return a single row from landlord_accounts matching *landlord_id*, or None."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM landlord_accounts WHERE id = ?",
            (landlord_id,),
        ).fetchone()


def username_exists(username: str) -> bool:
    """Return True if *username* is already taken in landlord_accounts."""
    return get_landlord_by_username(username) is not None


def create_landlord(
    full_name: str,
    email: str | None,
    phone: str | None,
    username: str,
    password_hash: str,
    landlord_uuid: str,
):
    """
    Insert a new landlord account and return the created row.

    Raises sqlite3.IntegrityError on unique-constraint violations (username / email).
    """
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO landlord_accounts (
                landlord_uuid, full_name, email, phone, username,
                password_hash, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'Active', ?, ?)
            """,
            (landlord_uuid, full_name, email, phone, username, password_hash, now, now),
        )
        conn.commit()
        return conn.execute(
            "SELECT * FROM landlord_accounts WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()


# ──────────────────────────────────────────────────────────────────────────────
# Audit log helpers
# ──────────────────────────────────────────────────────────────────────────────

def create_landlord_audit_log(
    landlord_id: int | None,
    action: str,
    ip_address: str | None = None,
    meta_json: str | None = None,
):
    """Append a row to landlord_audit_logs."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO landlord_audit_logs (landlord_id, action, ip_address, created_at, meta_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (landlord_id, action, ip_address, now, meta_json),
        )
        conn.commit()


# ──────────────────────────────────────────────────────────────────────────────
# TOTP helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_landlord_by_uuid(landlord_uuid: str):
    """Return a single row from landlord_accounts matching *landlord_uuid*, or None."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM landlord_accounts WHERE landlord_uuid = ?",
            (landlord_uuid,),
        ).fetchone()


def get_landlord_totp_secret(landlord_id: int):
    """Return the totp_secret for the given landlord, or None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT totp_secret FROM landlord_accounts WHERE id = ?",
            (landlord_id,),
        ).fetchone()
        return row["totp_secret"] if row else None


def update_landlord_totp_secret(landlord_id: int, secret: str):
    """Set the totp_secret for the given landlord."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE landlord_accounts SET totp_secret = ?, updated_at = ? WHERE id = ?",
            (secret, now, landlord_id),
        )
        conn.commit()


def get_totp_uri(username: str, totp_secret: str, issuer: str = "PROPAURA") -> str:
    """Generate TOTP provisioning URI for QR code."""
    return pyotp.totp.TOTP(totp_secret).provisioning_uri(
        name=username,
        issuer_name=issuer,
    )


def generate_totp_qr_base64(username: str, totp_secret: str, issuer: str = "PROPAURA") -> str:
    """Generate base64-encoded QR code for TOTP setup."""
    uri = get_totp_uri(username, totp_secret, issuer)
    qr = qrcode.make(uri)
    buffer = io.BytesIO()
    qr.save(buffer)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode()


def verify_totp(totp_secret: str, token: str) -> bool:
    """Verify a TOTP token against the secret."""
    if not totp_secret or not token:
        return False
    totp = pyotp.TOTP(totp_secret)
    return totp.verify(token, valid_window=1)


def regenerate_landlord_totp_secret(landlord_id: int) -> str:
    """Generate a new TOTP secret, update the DB, and return it."""
    new_secret = pyotp.random_base32()
    update_landlord_totp_secret(landlord_id, new_secret)
    return new_secret


# ──────────────────────────────────────────────────────────────────────────────
# Rate limiting helpers
# ──────────────────────────────────────────────────────────────────────────────

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def is_landlord_locked_out(landlord) -> bool:
    """Check if the landlord account is currently locked out."""
    if not landlord["locked_until"]:
        return False
    try:
        locked_until = datetime.fromisoformat(landlord["locked_until"])
        return datetime.utcnow() < locked_until
    except (ValueError, TypeError):
        return False


def record_landlord_failed_attempt(landlord_id: int):
    """Increment failed_attempts and lock if threshold reached."""
    now = datetime.utcnow()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT failed_attempts FROM landlord_accounts WHERE id = ?",
            (landlord_id,),
        ).fetchone()
        attempts = (row["failed_attempts"] or 0) + 1

        if attempts >= MAX_FAILED_ATTEMPTS:
            locked_until = now.replace(
                minute=now.minute + LOCKOUT_MINUTES
            )
            conn.execute(
                "UPDATE landlord_accounts SET failed_attempts = ?, locked_until = ?, updated_at = ? WHERE id = ?",
                (attempts, locked_until.isoformat(), now.isoformat(), landlord_id),
            )
        else:
            conn.execute(
                "UPDATE landlord_accounts SET failed_attempts = ?, updated_at = ? WHERE id = ?",
                (attempts, now.isoformat(), landlord_id),
            )
        conn.commit()


def reset_landlord_failed_attempts(landlord_id: int):
    """Reset failed attempts and lock on successful login."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE landlord_accounts SET failed_attempts = 0, locked_until = NULL, updated_at = ? WHERE id = ?",
            (now, landlord_id),
        )
        conn.commit()
