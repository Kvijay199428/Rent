"""
app/services/telegram_otp_service.py
Telegram OTP delivery + verification for platform admin login.

Flow:
  1. Admin submits username+password at login.
  2. Frontend offers "Telegram OTP" as a second factor.
  3. login-otp-send -> generate 6-digit code, store hashed (single-use, TTL,
     max attempts, resend cooldown), deliver via the Telegram bot.
  4. login-otp-verify -> constant-time compare, invalidate on success/failure,
     then the caller issues the session.

The bot token is read from the TELEGRAM_BOT_TOKEN env var only. The recipient
chat id is stored per-admin in admins.telegram_chat_id (captured through the
Settings UI "Link Telegram" flow).
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta

import requests

from app.core.db import get_conn
from app.authentication.common.utils import hash_pin, verify_pin, constant_time_eq

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# OTP policy
OTP_DIGITS = 6
OTP_TTL_SECONDS = 300          # 5 minutes
OTP_MAX_ATTEMPTS = 5           # attempts before the code is invalidated
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_PENDING_PER_ADMIN = 3  # cap on unconsumed codes per admin


def get_bot_token() -> str | None:
    """Return the Telegram bot token from env, or None if not configured."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    return token or None


def bot_configured() -> bool:
    return get_bot_token() is not None


def get_admin_chat_id(admin_id: int) -> str | None:
    """Return the linked Telegram chat_id for an admin, or None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT telegram_chat_id FROM admins WHERE id = %s", (admin_id,)
        ).fetchone()
    if not row:
        return None
    return (row["telegram_chat_id"] or "").strip() or None


def set_admin_chat_id(admin_id: int, chat_id: str | None) -> None:
    """Persist the linked Telegram chat_id for an admin (None clears it)."""
    if chat_id is None:
        value = None
    else:
        value = str(chat_id).strip() or None
    with get_conn() as conn:
        conn.execute(
            "UPDATE admins SET telegram_chat_id = %s, updated_at = %s WHERE id = %s",
            (value, datetime.utcnow().isoformat(), admin_id),
        )
        conn.commit()


def _telegram_request(method: str, **params) -> dict | None:
    """Low-level Telegram Bot API call. Returns JSON payload or None on failure."""
    token = get_bot_token()
    if not token:
        return None
    try:
        resp = requests.post(
            TELEGRAM_API.format(token=token, method=method),
            json=params,
            timeout=10,
        )
        data = resp.json()
        if not data.get("ok"):
            return None
        return data
    except Exception:
        return None


def send_telegram_message(chat_id: str, text: str) -> bool:
    """Send a message to a chat via the bot. Never raises."""
    if not bot_configured() or not chat_id:
        return False
    data = _telegram_request(
        "sendMessage", chat_id=chat_id, text=text, parse_mode="HTML"
    )
    return data is not None


def fetch_latest_chat_id() -> dict | None:
    """
    Poll getUpdates and return the newest private-chat chat that messaged the
    bot. Consumes updates (offsets) so each message is only captured once.
    Returns {chat_id, first_name, username} or None if nothing to link.
    """
    if not bot_configured():
        return None
    try:
        resp = requests.get(
            TELEGRAM_API.format(token=get_bot_token(), method="getUpdates"),
            params={"timeout": 0},
            timeout=10,
        )
        data = resp.json()
        if not data.get("ok"):
            return None
        result = data.get("result", [])
    except Exception:
        return None

    candidate = None
    last_update_id = 0
    for update in result:
        update_id = update.get("update_id", 0)
        last_update_id = max(last_update_id, update_id)
        message = update.get("message") or update.get("edited_message") or {}
        chat = message.get("chat") or {}
        if not chat.get("id"):
            continue
        # Only link private chats; ignore groups/channels.
        if chat.get("type") in (None, "private"):
            candidate = {
                "chat_id": str(chat.get("id")),
                "first_name": message.get("from", {}).get("first_name", ""),
                "username": message.get("from", {}).get("username", ""),
            }
            # Keep scanning; candidate ends as the newest update.
    if candidate is None:
        return None

    # Consume all processed updates so they are not re-linked next time.
    if last_update_id:
        _telegram_request("getUpdates", offset=last_update_id + 1)
    return candidate


# ─── OTP generation / storage ─────────────────────────────────────────────────

def generate_otp() -> str:
    """Generate a cryptographically random 6-digit code."""
    return f"{secrets.randbelow(10 ** OTP_DIGITS):0{OTP_DIGITS}d}"


def store_otp(admin_id: int, otp: str) -> None:
    """Store a hashed, expiring OTP for an admin. Prunes stale/used codes first."""
    now = datetime.utcnow()
    with get_conn() as conn:
        # Prune consumed, expired, or over-attempted codes for this admin.
        conn.execute(
            """
            DELETE FROM admin_login_otps
            WHERE admin_id = %s
              AND (used = 1 OR attempts >= %s OR expires_at < %s)
            """,
            (admin_id, OTP_MAX_ATTEMPTS, now.isoformat()),
        )
        # Keep the pending cap by dropping the oldest unconsumed codes.
        pending = conn.execute(
            """
            SELECT id FROM admin_login_otps
            WHERE admin_id = %s AND used = 0 AND expires_at >= %s
            ORDER BY created_at DESC
            """,
            (admin_id, now.isoformat()),
        ).fetchall()
        overflow = len(pending) - (OTP_MAX_PENDING_PER_ADMIN - 1)
        if overflow > 0:
            drop_ids = [row["id"] for row in pending[overflow:]]
            placeholders = ",".join("%s" * len(drop_ids))
            conn.execute(
                f"DELETE FROM admin_login_otps WHERE id IN ({placeholders})",
                drop_ids,
            )

        conn.execute(
            """
            INSERT INTO admin_login_otps
                (admin_id, otp_hash, expires_at, attempts, used, created_at)
            VALUES (%s, %s, %s, 0, 0, %s)
            """,
            (
                admin_id,
                hash_pin(otp),
                (now + timedelta(seconds=OTP_TTL_SECONDS)).isoformat(),
                now.isoformat(),
            ),
        )
        conn.commit()


def delete_pending_otp(admin_id: int) -> None:
    """Remove the newest unconsumed OTP for an admin (e.g. when delivery fails)."""
    now = datetime.utcnow()
    with get_conn() as conn:
        conn.execute(
            """
            DELETE FROM admin_login_otps
            WHERE id IN (
                SELECT id FROM admin_login_otps
                WHERE admin_id = %s AND used = 0 AND expires_at >= %s
                ORDER BY created_at DESC LIMIT 1
            )
            """,
            (admin_id, now.isoformat()),
        )
        conn.commit()


def cooldown_remaining(admin_id: int) -> int:
    """Seconds until the admin may request a new code, or 0 if allowed."""
    now = datetime.utcnow()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT created_at FROM admin_login_otps
            WHERE admin_id = %s AND used = 0 AND expires_at >= %s
            ORDER BY created_at DESC LIMIT 1
            """,
            (admin_id, now.isoformat()),
        ).fetchone()
    if not row:
        return 0
    created = datetime.fromisoformat(row["created_at"])
    remaining = OTP_RESEND_COOLDOWN_SECONDS - int((now - created).total_seconds())
    return max(remaining, 0)


def verify_otp(admin_id: int, otp: str) -> bool:
    """
    Verify an OTP. Single-use and attempt-limited: on success the code is
    invalidated; on failure attempts are incremented and the code is
    invalidated once the attempt cap is reached.
    """
    if not otp:
        return False
    now = datetime.utcnow()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, otp_hash, attempts, expires_at FROM admin_login_otps
            WHERE admin_id = %s AND used = 0
            ORDER BY created_at DESC LIMIT 1
            """,
            (admin_id,),
        ).fetchone()
        if not row:
            return False

        # Expired or exhausted codes are treated as invalid.
        if row["expires_at"] < now.isoformat() or row["attempts"] >= OTP_MAX_ATTEMPTS:
            conn.execute(
                "DELETE FROM admin_login_otps WHERE id = %s", (row["id"],)
            )
            conn.commit()
            return False

        if constant_time_eq(str(otp), "") or not verify_pin(str(otp), row["otp_hash"]):
            new_attempts = row["attempts"] + 1
            conn.execute(
                "UPDATE admin_login_otps SET attempts = %s WHERE id = %s",
                (new_attempts, row["id"]),
            )
            if new_attempts >= OTP_MAX_ATTEMPTS:
                conn.execute("DELETE FROM admin_login_otps WHERE id = %s", (row["id"],))
            conn.commit()
            return False

        # Success: single-use invalidation.
        conn.execute(
            "UPDATE admin_login_otps SET used = 1 WHERE id = %s", (row["id"],)
        )
        conn.commit()
        return True
