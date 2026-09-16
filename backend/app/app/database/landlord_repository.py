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
            "SELECT * FROM \"landlordAccounts\" WHERE username = %s",
            (username,),
        ).fetchone()


def get_landlord_by_email(email: str):
    """Return a single row from landlord_accounts matching *email*, or None."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM \"landlordAccounts\" WHERE email = %s",
            (email,),
        ).fetchone()


def get_landlord_by_id(landlord_id: int):
    """Return a single row from landlord_accounts matching *landlord_id*, or None."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM \"landlordAccounts\" WHERE id = %s",
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
    privacy_consented: int = 1,
    privacy_version: str | None = None,
    privacy_accepted_at: str | None = None,
    privacy_accepted_ip: str | None = None,
    privacy_accepted_user_agent: str | None = None,
    terms_consented: int = 1,
    terms_version: str | None = None,
    terms_accepted_at: str | None = None,
    terms_accepted_ip: str | None = None,
    terms_accepted_user_agent: str | None = None,
):
    """
    Insert a new landlord account and return the created row.

    Raises sqlite3.IntegrityError on unique-constraint violations (username / email).
    """
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO "landlordAccounts" (
                "landlordUuid", "fullName", email, phone, username,
                "passwordHash", status, "createdAt", "updatedAt",
                "privacyConsented", "privacyVersion", "privacyAcceptedAt",
                "privacyAcceptedIp", "privacyAcceptedUserAgent",
                "termsConsented", "termsVersion", "termsAcceptedAt",
                "termsAcceptedIp", "termsAcceptedUserAgent"
            ) VALUES (%s, %s, %s, %s, %s, %s, 'Active', %s, %s,
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                landlord_uuid, full_name, email, phone, username, password_hash,
                now, now,
                privacy_consented, privacy_version, privacy_accepted_at,
                privacy_accepted_ip, privacy_accepted_user_agent,
                terms_consented, terms_version, terms_accepted_at,
                terms_accepted_ip, terms_accepted_user_agent,
            ),
        ).fetchone()
        conn.commit()
        return row


def record_privacy_consent(
    landlord_id: int,
    privacy_version: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    """
    Mark a landlord as having accepted the current Privacy Policy.

    Updates landlord_accounts consent fields and appends a row to
    landlord_privacy_consents so acceptance is auditable.
    """
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """UPDATE "landlordAccounts"
               SET "privacyConsented" = 1,
                   "privacyVersion" = %s,
                   "privacyAcceptedAt" = %s,
                   "privacyAcceptedIp" = %s,
                   "privacyAcceptedUserAgent" = %s,
                   "updatedAt" = %s
               WHERE id = %s""",
            (privacy_version, now, ip_address, user_agent, now, landlord_id),
        )
        conn.execute(
            """INSERT INTO "landlordPrivacyConsents"
               ("landlordId", "privacyVersion", accepted, "acceptedAt", "acceptedIp", "acceptedUserAgent")
               VALUES (%s, %s, 1, %s, %s, %s)""",
            (landlord_id, privacy_version, now, ip_address, user_agent),
        )
        conn.commit()


def record_terms_consent(
    landlord_id: int,
    terms_version: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    """
    Mark a landlord as having accepted the current Terms and Conditions.

    Updates landlord_accounts terms fields and appends a row to
    landlord_terms_consents so acceptance is auditable.
    """
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """UPDATE "landlordAccounts"
               SET "termsConsented" = 1,
                   "termsVersion" = %s,
                   "termsAcceptedAt" = %s,
                   "termsAcceptedIp" = %s,
                   "termsAcceptedUserAgent" = %s,
                   "updatedAt" = %s
               WHERE id = %s""",
            (terms_version, now, ip_address, user_agent, now, landlord_id),
        )
        conn.execute(
            """INSERT INTO "landlordTermsConsents"
               ("landlordId", "termsVersion", accepted, "acceptedAt", "acceptedIp", "acceptedUserAgent")
               VALUES (%s, %s, 1, %s, %s, %s)""",
            (landlord_id, terms_version, now, ip_address, user_agent),
        )
        conn.commit()


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
            INSERT INTO "landlordAuditLogs" ("landlordId", action, "ipAddress", "createdAt", "metaJson")
            VALUES (%s, %s, %s, %s, %s)
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
            "SELECT * FROM \"landlordAccounts\" WHERE \"landlordUuid\" = %s",
            (landlord_uuid,),
        ).fetchone()


def get_landlord_totp_secret(landlord_id: int):
    """Return the totp_secret for the given landlord, or None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT \"totpSecret\" FROM \"landlordAccounts\" WHERE id = %s",
            (landlord_id,),
        ).fetchone()
        return row["totpSecret"] if row else None


def update_landlord_totp_secret(landlord_id: int, secret: str):
    """Set the totp_secret for the given landlord."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE \"landlordAccounts\" SET \"totpSecret\" = %s, \"updatedAt\" = %s WHERE id = %s",
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
    if not landlord["lockedUntil"]:
        return False
    try:
        locked_until = datetime.fromisoformat(landlord["lockedUntil"])
        return datetime.utcnow() < locked_until
    except (ValueError, TypeError):
        return False


def record_landlord_failed_attempt(landlord_id: int):
    """Increment failed_attempts and lock if threshold reached."""
    now = datetime.utcnow()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT \"failedAttempts\" FROM \"landlordAccounts\" WHERE id = %s",
            (landlord_id,),
        ).fetchone()
        attempts = (row["failedAttempts"] or 0) + 1

        if attempts >= MAX_FAILED_ATTEMPTS:
            locked_until = now.replace(
                minute=now.minute + LOCKOUT_MINUTES
            )
            conn.execute(
                "UPDATE \"landlordAccounts\" SET \"failedAttempts\" = %s, \"lockedUntil\" = %s, \"updatedAt\" = %s WHERE id = %s",
                (attempts, locked_until.isoformat(), now.isoformat(), landlord_id),
            )
        else:
            conn.execute(
                "UPDATE \"landlordAccounts\" SET \"failedAttempts\" = %s, \"updatedAt\" = %s WHERE id = %s",
                (attempts, now.isoformat(), landlord_id),
            )
        conn.commit()


def reset_landlord_failed_attempts(landlord_id: int):
    """Reset failed attempts and lock on successful login."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE \"landlordAccounts\" SET \"failedAttempts\" = 0, \"lockedUntil\" = NULL, \"updatedAt\" = %s WHERE id = %s",
            (now, landlord_id),
        )
        conn.commit()
