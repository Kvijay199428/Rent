"""
app/authentication/landlord/sessions.py

Create, fetch, and revoke landlord sessions stored in landlord_sessions.
Mirrors the admin sessions pattern exactly.
"""
import re
import uuid
import secrets
from datetime import datetime, timedelta

from app.core.db import get_conn
from app.authentication.common.utils import hash_pin


def parse_user_agent(user_agent: str):
    """
    Lightweight, dependency-free parse of a User-Agent string into
    (device_name, browser, os). Falls back to "Unknown" / "Desktop".
    """
    ua = user_agent or "Unknown"

    if "Edg/" in ua:
        browser = "Edge"
    elif "OPR/" in ua or "Opera" in ua:
        browser = "Opera"
    elif "SamsungBrowser" in ua:
        browser = "Samsung Internet"
    elif "Chrome/" in ua:
        browser = "Chrome"
    elif "Firefox/" in ua:
        browser = "Firefox"
    elif "Safari/" in ua:
        browser = "Safari"
    else:
        browser = "Unknown"

    if "Windows" in ua:
        os_name = "Windows"
    elif "iPhone" in ua or "iPad" in ua:
        os_name = "iOS"
    elif "Android" in ua:
        os_name = "Android"
    elif "CrOS" in ua:
        os_name = "Chrome OS"
    elif "Mac OS X" in ua:
        os_name = "macOS"
    elif "Linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Unknown"

    if "iPhone" in ua:
        device_name = "iPhone"
    elif "iPad" in ua:
        device_name = "iPad"
    elif "Android" in ua:
        device_name = "Android Phone" if "Mobile" in ua else "Android Tablet"
    elif "Macintosh" in ua:
        device_name = "Mac"
    elif "Windows" in ua:
        device_name = "Windows Phone" if "Mobile" in ua else "Windows PC"
    else:
        device_name = "Desktop" if os_name in ("Windows", "macOS", "Linux") else "Unknown"

    return device_name, browser, os_name


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
    device_name, browser, os_name = parse_user_agent(user_agent)
    ip = request.client.host if request.client else "Unknown"
    now = datetime.utcnow().isoformat()

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO "landlordSessions" (
                "sessionId", "landlordId", "refreshTokenHash",
                "deviceName", browser, os, "ipAddress",
                "createdAt", "lastActivity", "expiresAt", "rememberMe"
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session_id, landlord_id, refresh_hash,
                device_name, browser, os_name, ip,
                now, now, expires_at, int(remember_me),
            ),
        )
        conn.commit()

    return session_id, refresh_token


def get_landlord_session_db(session_id: str):
    """Return the active landlord session row, or None if not found / revoked / expired."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM \"landlordSessions\" WHERE \"sessionId\" = %s AND status = 'Active' AND \"expiresAt\" > %s",
            (session_id, now),
        ).fetchone()


def revoke_landlord_session_db(session_id: str) -> None:
    """Mark a landlord session as Revoked."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE \"landlordSessions\" SET status = 'Revoked', \"revokedAt\" = %s WHERE \"sessionId\" = %s",
            (now, session_id),
        )
        conn.commit()


def revoke_landlord_session_by_id(landlord_id: int, session_id: str) -> bool:
    """Revoke one active session, but only if it belongs to the landlord.

    Returns True when a session was actually revoked.
    """
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """
            UPDATE "landlordSessions"
            SET status = 'Revoked', "revokedAt" = %s
            WHERE "sessionId" = %s AND "landlordId" = %s AND status = 'Active'
            """,
            (now, session_id, landlord_id),
        )
        conn.commit()
        return cur.rowcount > 0


def list_landlord_sessions(landlord_id: int):
    """Return every session for a landlord, newest activity first."""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT "sessionId", "deviceName", browser, os, "ipAddress",
                   "createdAt", "lastActivity", "expiresAt", "rememberMe", status
            FROM "landlordSessions"
            WHERE "landlordId" = %s
            ORDER BY "lastActivity" DESC
            """,
            (landlord_id,),
        ).fetchall()


def revoke_all_landlord_sessions(landlord_id: int) -> None:
    """Revoke every active session for a landlord (e.g. on password change)."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE "landlordSessions"
            SET status = 'Revoked', "revokedAt" = %s
            WHERE "landlordId" = %s AND status = 'Active'
            """,
            (now, landlord_id),
        )
        conn.commit()
