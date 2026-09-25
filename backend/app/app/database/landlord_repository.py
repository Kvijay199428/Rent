"""
app/database/landlord_repository.py

Pure SQL helper functions for the landlord_accounts, landlord_sessions,
and landlord_audit_logs tables.  No business logic lives here — callers
are responsible for validation, hashing, and UUID generation.
"""
import base64
import hashlib
import io
import secrets
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


def update_landlord_profile(
    landlord_id: int,
    full_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    avatar_url: str | None = None,
) -> None:
    """Update editable profile fields on landlord_accounts.

    Only non-None fields are written; caller is responsible for validation
    (email uniqueness) and phone normalization.
    """
    now = datetime.utcnow().isoformat()
    assignments = ['"updatedAt" = %s']
    params = [now]
    if full_name is not None:
        assignments.append('"fullName" = %s')
        params.append(full_name)
    if email is not None:
        assignments.append("email = %s")
        params.append(email)
    if phone is not None:
        assignments.append("phone = %s")
        params.append(phone)
    if avatar_url is not None:
        assignments.append('"avatarUrl" = %s')
        params.append(avatar_url)
    params.append(landlord_id)
    with get_conn() as conn:
        conn.execute(
            f'UPDATE "landlordAccounts" SET {", ".join(assignments)} WHERE id = %s',
            tuple(params),
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
# Landlord recovery (backup) codes — SHA-256 hashed, single-use
# ──────────────────────────────────────────────────────────────────────────────

RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _normalize_recovery_code(code: str) -> str:
    """Strip everything outside the code alphabet and uppercase."""
    return "".join(ch for ch in code.upper() if ch in RECOVERY_CODE_ALPHABET)


def _hash_recovery_code(code: str) -> str:
    return hashlib.sha256(_normalize_recovery_code(code).encode("utf-8")).hexdigest()


def issue_landlord_recovery_codes(landlord_id: int, count: int = RECOVERY_CODE_COUNT) -> list:
    """Replace the landlord's unused recovery codes with a fresh batch.

    Returns the plaintext codes (shown exactly once to the caller); only the
    SHA-256 hashes are persisted.
    """
    now = datetime.utcnow().isoformat()
    codes = []
    for _ in range(count):
        raw = "".join(secrets.choice(RECOVERY_CODE_ALPHABET) for _ in range(8))
        codes.append(f"{raw[:4]}-{raw[4:]}")
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM \"landlordRecoveryCodes\" WHERE \"landlordId\" = %s",
            (landlord_id,),
        )
        for code in codes:
            conn.execute(
                "INSERT INTO \"landlordRecoveryCodes\" (\"landlordId\", \"codeHash\", \"createdAt\") VALUES (%s, %s, %s)",
                (landlord_id, _hash_recovery_code(code), now),
            )
        conn.commit()
    return codes


def consume_landlord_recovery_code(landlord_id: int, code: str) -> bool:
    """Consume a single unused recovery code for *landlord_id*.

    Returns True when the code matched and was marked used; False otherwise.
    """
    now = datetime.utcnow().isoformat()
    code_hash = _hash_recovery_code(code)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM \"landlordRecoveryCodes\" "
            "WHERE \"landlordId\" = %s AND \"codeHash\" = %s AND used = 0",
            (landlord_id, code_hash),
        ).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE \"landlordRecoveryCodes\" SET used = 1, \"usedAt\" = %s WHERE id = %s",
            (now, row["id"]),
        )
        conn.commit()
    return True


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
