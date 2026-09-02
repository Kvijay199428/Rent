"""
app/authentication/landlord/sessions.py

Create, fetch, and revoke landlord sessions stored in landlord_sessions.
Mirrors the admin sessions pattern exactly.
"""
import uuid
import secrets
from datetime import datetime, timedelta

from app.core.db import get_conn
from app.authentication.common.utils import hash_pin


def create_landlord_session(landlord_id: int, request, remember_me: bool):
    """
    Persist a new landlord session and return (session_id, raw_refresh_token).
    The raw refresh token is returned once and never stored in plaintext.
    """
    refresh_token = secrets.token_urlsafe(64)
    refresh_hash = hash_pin(refresh_token)

    session_id = str(uuid.uuid4())
    days = 180 if remember_me else 30
    expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()

    user_agent = request.headers.get("User-Agent", "Unknown")
    ip = request.client.host if request.client else "Unknown"
    now = datetime.utcnow().isoformat()

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO landlord_sessions (
                session_id, landlord_id, refresh_token_hash,
                device_name, browser, os, ip_address,
                created_at, last_activity, expires_at, remember_me
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session_id, landlord_id, refresh_hash,
                "Unknown", user_agent, "Unknown", ip,
                now, now, expires_at, int(remember_me),
            ),
        )
        conn.commit()

    return session_id, refresh_token


def get_landlord_session_db(session_id: str):
    """Return the active landlord session row, or None if not found / revoked."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM landlord_sessions WHERE session_id = %s AND status = 'Active'",
            (session_id,),
        ).fetchone()


def revoke_landlord_session_db(session_id: str) -> None:
    """Mark a landlord session as Revoked."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE landlord_sessions SET status = 'Revoked', revoked_at = %s WHERE session_id = %s",
            (now, session_id),
        )
        conn.commit()


def revoke_all_landlord_sessions(landlord_id: int) -> None:
    """Revoke every active session for a landlord (e.g. on password change)."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE landlord_sessions
            SET status = 'Revoked', revoked_at = %s
            WHERE landlord_id = %s AND status = 'Active'
            """,
            (now, landlord_id),
        )
        conn.commit()
