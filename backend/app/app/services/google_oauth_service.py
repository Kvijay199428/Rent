import json
import uuid
from datetime import datetime

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.authentication.common.utils import hash_pin
from app.authentication.landlord.cookies import set_landlord_auth_cookies
from app.authentication.landlord.jwt import create_access_token
from app.authentication.landlord.sessions import create_landlord_session
from app.database.landlord_repository import (
    create_landlord,
    create_landlord_audit_log,
    get_landlord_by_email,
)
from app.core.db import get_conn

GOOGLE_CLIENT_ID: str | None = None


def _get_client_id() -> str:
    global GOOGLE_CLIENT_ID
    if GOOGLE_CLIENT_ID is None:
        import os
        GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    return GOOGLE_CLIENT_ID


def verify_google_token(credential: str) -> dict | None:
    client_id = _get_client_id()
    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID is not configured")
    try:
        info = id_token.verify_oauth2_token(credential, google_requests.Request(), client_id)
        if info.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
            return None
        return info
    except ValueError:
        return None


def google_login(credential: str, remember_me: bool, request, response):
    info = verify_google_token(credential)
    if info is None:
        raise ValueError("Invalid Google credential")

    google_sub = info["sub"]
    email = info.get("email", "").strip().lower()
    name = info.get("name", "").strip()
    avatar_url = info.get("picture", "")

    with get_conn() as conn:
        landlord = conn.execute(
            "SELECT * FROM landlord_accounts WHERE google_sub = ?", (google_sub,)
        ).fetchone()

    created_new = False

    if not landlord and email:
        landlord = get_landlord_by_email(email)
        if landlord:
            with get_conn() as conn:
                conn.execute(
                    "UPDATE landlord_accounts SET google_sub = ?, avatar_url = ?, updated_at = ? WHERE id = ?",
                    (google_sub, avatar_url, datetime.utcnow().isoformat(), landlord["id"]),
                )
                conn.commit()

    if not landlord:
        created_new = True
        base_username = (email.split("@")[0] if email else "user").lower()
        username = _unique_username(base_username)
        landlord_uuid = str(uuid.uuid4())
        placeholder_hash = hash_pin(uuid.uuid4().hex)

        landlord = create_landlord(
            full_name=name or email or "Google User",
            email=email or None,
            phone=None,
            username=username,
            password_hash=placeholder_hash,
            landlord_uuid=landlord_uuid,
        )

        with get_conn() as conn:
            conn.execute(
                """UPDATE landlord_accounts
                   SET google_sub = ?, auth_provider = 'google', avatar_url = ?,
                       requires_password_change = 1, updated_at = ?
                   WHERE id = ?""",
                (google_sub, avatar_url, datetime.utcnow().isoformat(), landlord["id"]),
            )
            conn.commit()

        create_landlord_audit_log(
            landlord["id"],
            "signup_via_google",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"google_sub": google_sub, "email": email}),
        )

    session_id, refresh_token = create_landlord_session(
        landlord["id"], request, remember_me
    )
    access_token = create_access_token(landlord["id"], session_id)
    cookie_value = f"{session_id}:{refresh_token}"
    set_landlord_auth_cookies(response, access_token, cookie_value, remember_me, request)

    if created_new or landlord.get("requires_password_change"):
        return {
            "status": "password_change_required",
            "message": "You must set a password before continuing.",
            "landlordUuid": landlord["landlord_uuid"],
        }

    return {
        "status": "success",
        "landlord": {
            "id": landlord["id"],
            "landlordUuid": landlord["landlord_uuid"],
            "username": landlord["username"],
            "fullName": landlord["full_name"],
        },
    }


def _unique_username(base: str, max_length: int = 40) -> str:
    candidate = base[:max_length]
    from app.database.landlord_repository import username_exists
    if not username_exists(candidate):
        return candidate
    for suffix in range(1, 9999):
        shortened = base[: max_length - len(str(suffix)) - 1]
        candidate = f"{shortened}{suffix}"
        if not username_exists(candidate):
            return candidate
    return f"{base[:20]}{uuid.uuid4().hex[:8]}"
