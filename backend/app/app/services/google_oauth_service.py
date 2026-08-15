import json
import uuid
from datetime import datetime

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.authentication.common.utils import hash_pin
from app.authentication.landlord.cookies import set_landlord_auth_cookies
from app.authentication.landlord.jwt import create_access_token
from app.authentication.landlord.sessions import create_landlord_session
from app.core.db import get_conn
from app.core.privacy import PRIVACY_POLICY_VERSION, TERMS_CONDITIONS_VERSION
from app.database.landlord_repository import (
    create_landlord,
    create_landlord_audit_log,
    get_landlord_by_email,
    record_privacy_consent,
    record_terms_consent,
)

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
            privacy_consented=1,
            terms_consented=1,
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

    # ── Privacy Policy + Terms and Conditions acceptance ──
    # Accepting via the Google button is an explicit affirmative action in the
    # signup/sign-in flow. Record consent for brand-new accounts and heal any
    # existing account that is still in a consent-pending state.
    consent_ip = request.client.host if request.client else None
    consent_ua = request.headers.get("User-Agent", "")
    if created_new or not landlord["privacy_consented"]:
        record_privacy_consent(
            landlord["id"],
            privacy_version=PRIVACY_POLICY_VERSION,
            ip_address=consent_ip,
            user_agent=consent_ua,
        )
        create_landlord_audit_log(
            landlord["id"],
            "privacy_policy_accepted",
            ip_address=consent_ip,
            meta_json=json.dumps({
                "version": PRIVACY_POLICY_VERSION,
                "user_agent": consent_ua,
                "source": "google_signup" if created_new else "google_signin",
            }),
        )
    if created_new or not landlord["terms_consented"]:
        record_terms_consent(
            landlord["id"],
            terms_version=TERMS_CONDITIONS_VERSION,
            ip_address=consent_ip,
            user_agent=consent_ua,
        )
        create_landlord_audit_log(
            landlord["id"],
            "terms_conditions_accepted",
            ip_address=consent_ip,
            meta_json=json.dumps({
                "version": TERMS_CONDITIONS_VERSION,
                "user_agent": consent_ua,
                "source": "google_signup" if created_new else "google_signin",
            }),
        )

    session_id, refresh_token = create_landlord_session(
        landlord["id"], request, remember_me
    )
    access_token = create_access_token(landlord["id"], session_id)
    cookie_value = f"{session_id}:{refresh_token}"
    set_landlord_auth_cookies(response, access_token, cookie_value, remember_me, request)

    if created_new or bool(landlord["requires_password_change"]):
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
