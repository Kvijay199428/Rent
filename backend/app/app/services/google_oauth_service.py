import json
import os
import uuid
from datetime import datetime

import requests
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
GOOGLE_CLIENT_SECRET: str | None = None
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


def _get_client_id() -> str:
    global GOOGLE_CLIENT_ID
    if GOOGLE_CLIENT_ID is None:
        GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    return GOOGLE_CLIENT_ID


def _get_client_secret() -> str:
    global GOOGLE_CLIENT_SECRET
    if GOOGLE_CLIENT_SECRET is None:
        GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    return GOOGLE_CLIENT_SECRET


def _exchange_code_for_id_token(code: str) -> str:
    client_id = _get_client_id()
    client_secret = _get_client_secret()
    if not client_secret:
        raise ValueError("GOOGLE_CLIENT_SECRET is not configured")
    resp = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": "postmessage",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        raise ValueError("Google authorization code exchange failed")
    id_token = resp.json().get("id_token")
    if not id_token:
        raise ValueError("Google token response did not include an id_token")
    return id_token


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


def google_login(code: str, remember_me: bool, request, response):
    credential = _exchange_code_for_id_token(code)
    info = verify_google_token(credential)
    if info is None:
        raise ValueError("Invalid Google credential")

    google_sub = info["sub"]
    email = info.get("email", "").strip().lower()
    name = info.get("name", "").strip()
    avatar_url = info.get("picture", "")

    with get_conn() as conn:
        landlord = conn.execute(
            "SELECT * FROM \"landlordAccounts\" WHERE \"googleSub\" = %s", (google_sub,)
        ).fetchone()

    created_new = False

    if not landlord and email:
        landlord = get_landlord_by_email(email)
        if landlord:
            with get_conn() as conn:
                conn.execute(
                    "UPDATE \"landlordAccounts\" SET \"googleSub\" = %s, \"avatarUrl\" = %s, \"updatedAt\" = %s WHERE id = %s",
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
                """UPDATE "landlordAccounts"
                   SET "googleSub" = %s, "authProvider" = 'google', "avatarUrl" = %s,
                       "requiresPasswordChange" = 1, "updatedAt" = %s
                   WHERE id = %s""",
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
    if created_new or not landlord["privacyConsented"]:
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
    if created_new or not landlord["termsConsented"]:
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

    if created_new or bool(landlord["requiresPasswordChange"]):
        return {
            "status": "password_change_required",
            "message": "You must set a password before continuing.",
            "landlordUuid": landlord["landlordUuid"],
        }

    return {
        "status": "success",
        "landlord": {
            "id": landlord["id"],
            "landlordUuid": landlord["landlordUuid"],
            "username": landlord["username"],
            "fullName": landlord["fullName"],
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


def google_connect(landlord_id: int, code: str, request):
    """Link an authenticated landlord account to a Google account (Settings -> Security)."""
    credential = _exchange_code_for_id_token(code)
    info = verify_google_token(credential)
    if info is None:
        raise ValueError("Invalid Google credential")

    google_sub = info["sub"]
    email = info.get("email", "").strip().lower()
    avatar_url = info.get("picture", "")

    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM \"landlordAccounts\" WHERE id = %s", (landlord_id,)
        ).fetchone()
        if not row:
            raise ValueError("Landlord account not found")
        conflict = conn.execute(
            "SELECT id FROM \"landlordAccounts\" WHERE \"googleSub\" = %s AND id <> %s",
            (google_sub, landlord_id),
        ).fetchone()
        if conflict:
            raise ValueError("This Google account is already linked to another account.")

        now = datetime.utcnow().isoformat()
        if row["avatarUrl"] or not avatar_url:
            conn.execute(
                "UPDATE \"landlordAccounts\" SET \"googleSub\" = %s, \"authProvider\" = %s, \"updatedAt\" = %s WHERE id = %s",
                (google_sub, "google", now, landlord_id),
            )
        else:
            conn.execute(
                "UPDATE \"landlordAccounts\" SET \"googleSub\" = %s, \"authProvider\" = %s, \"avatarUrl\" = %s, \"updatedAt\" = %s WHERE id = %s",
                (google_sub, "google", avatar_url, now, landlord_id),
            )
        conn.commit()

    create_landlord_audit_log(
        landlord_id,
        "google_connected",
        ip_address=request.client.host if request.client else None,
        meta_json=json.dumps({"google_sub": google_sub, "email": email}),
    )
    return {"status": "success", "authProvider": "google"}


def google_disconnect(landlord_id: int, request):
    """Unlink Google from a landlord account (Settings -> Security)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT \"googleSub\", \"authProvider\", \"requiresPasswordChange\" FROM \"landlordAccounts\" WHERE id = %s",
            (landlord_id,),
        ).fetchone()
        if not row:
            raise ValueError("Landlord account not found")
        if not row["googleSub"]:
            raise ValueError("No Google account is linked.")
        if bool(row["requiresPasswordChange"]):
            raise ValueError("Set a password before disconnecting Google.")

        conn.execute(
            "UPDATE \"landlordAccounts\" SET \"googleSub\" = NULL, \"authProvider\" = %s, \"updatedAt\" = %s WHERE id = %s",
            ("email", datetime.utcnow().isoformat(), landlord_id),
        )
        conn.commit()

    create_landlord_audit_log(
        landlord_id,
        "google_disconnected",
        ip_address=request.client.host if request.client else None,
        meta_json=json.dumps({}),
    )
    return {"status": "success", "authProvider": "email"}
