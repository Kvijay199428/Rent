"""
app/routers/landlordauth.py

Public landlord authentication endpoints:
  GET  /landlord/api/auth/check-username   — username availability + suggestions
  POST /landlord/api/auth/signup           — create landlord account
  POST /landlord/api/auth/login            — authenticate + set cookies
  POST /landlord/api/login/totp            — complete login with TOTP verification
  POST /landlord/api/auth/logout           — clear cookies + revoke session
  GET  /landlord/api/auth/me               — return current landlord identity

Protected landlord TOTP management endpoints:
  GET  /landlord/{landlordUuid}/api/totp/qr         — get TOTP QR code
  POST /landlord/{landlordUuid}/api/totp/regenerate  — regenerate TOTP secret
"""
import json
import os
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.authentication.common.utils import hash_pin, verify_pin
from app.authentication.landlord.cookies import (
    clear_landlord_auth_cookies,
    set_landlord_auth_cookies,
)
from app.authentication.landlord.jwt import create_access_token
from app.authentication.landlord.middleware import get_current_landlord_api
from app.authentication.landlord.sessions import (
    create_landlord_session,
    get_landlord_session_db,
    revoke_landlord_session_db,
)
from app.services.phone_service import normalize_phone
from app.core.routes_manifest_landlord import LandlordRoutes as Routes, LandlordNames as Names
from app.database.landlord_repository import (
    create_landlord,
    create_landlord_audit_log,
    get_landlord_by_email,
    get_landlord_by_username,
    get_landlord_by_uuid,
    get_landlord_totp_secret,
    update_landlord_totp_secret,
    generate_totp_qr_base64,
    get_totp_uri,
    verify_totp,
    regenerate_landlord_totp_secret,
    username_exists,
    is_landlord_locked_out,
    record_landlord_failed_attempt,
    reset_landlord_failed_attempts,
    record_privacy_consent,
    record_terms_consent,
)
from app.models.landlord import (
    LandlordGoogleRequest,
    LandlordLoginRequest,
    LandlordLoginWithTotpRequest,
    LandlordPrivacyConsentRequest,
    LandlordSignupRequest,
    LandlordTermsConsentRequest,
)
from app.core.config_service import config
from app.core.db import get_conn
from app.core.paths import STATIC_DIR
from app.core.privacy import (
    PRIVACY_CONSENT_REQUIRED_HEADER,
    PRIVACY_POLICY_EFFECTIVE_DATE,
    PRIVACY_POLICY_VERSION,
    TERMS_CONDITIONS_EFFECTIVE_DATE,
    TERMS_CONDITIONS_VERSION,
)

router = APIRouter(tags=["Landlord Authentication"])

# ── Username rules ─────────────────────────────────────────────────────────────

RESERVED = {
    "admin", "root", "api", "login", "signup", "tenant",
    "landlord", "support", "system", "platform", "superuser",
}


def normalize_username(username: str) -> str:
    """Lowercase, strip whitespace, remove any char that is not [a-z0-9_]."""
    username = username.strip().lower()
    username = re.sub(r"[^a-z0-9_]", "", username)
    return username


def suggest_usernames(base: str) -> list[str]:
    """Generate 3–5 available username alternatives for *base*."""
    base = normalize_username(base) or "user"
    candidates = [
        f"{base}91",
        f"{base}123",
        f"{base}_01",
        f"{base}_91",
        f"{base}2026",
        f"{base}786",
    ]
    result = []
    for candidate in candidates:
        if candidate not in RESERVED and not username_exists(candidate):
            result.append(candidate)
        if len(result) >= 5:
            break
    return result


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get(Routes.LANDLORDAPIAUTHPUBLICKEY, name=Names.LANDLORDPUBLICKEY)
async def landlord_public_key():
    from app.encryption import get_public_key_pem
    return {"publicKey": get_public_key_pem()}


@router.post(Routes.LANDLORDAPIAUTHGOOGLE, name=Names.LANDLORDGOOGLE)
async def landlord_google(
    request: Request, response: Response, payload: LandlordGoogleRequest
):
    """
    Authenticate or sign up a landlord via Google Sign-In (ID token flow).
    Accepts a Google credential (ID token) and returns the same session
    format as password login.
    """
    from app.services.google_oauth_service import google_login
    try:
        result = google_login(payload.code, payload.rememberMe, request, response)
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google authentication failed: {str(e)}")


@router.get(Routes.LANDLORDAPIAUTHCHECKUSERNAME, name=Names.LANDLORDCHECKUSERNAME)
async def check_username(username: str):
    """
    Return whether *username* is available and, if not, suggest alternatives.
    Response: { username, available, suggestions[] }
    """
    normalized = normalize_username(username)
    if len(normalized) < 3:
        return {"username": normalized, "available": False, "suggestions": []}

    available = normalized not in RESERVED and not username_exists(normalized)
    return {
        "username": normalized,
        "available": available,
        "suggestions": [] if available else suggest_usernames(normalized),
    }


@router.get(Routes.LANDLORDAPIAUTHCHECKEMAIL, name=Names.LANDLORDCHECKEMAIL)
async def check_email(email: str):
    """Return whether *email* is available."""
    email_clean = email.strip().lower()
    if "@" not in email_clean or "." not in email_clean.split("@")[-1]:
        return {"email": email_clean, "available": False, "error": "Invalid email format"}
    available = get_landlord_by_email(email_clean) is None
    return {"email": email_clean, "available": available, "error": None}


@router.get(Routes.LANDLORDAPIPRIVACYPOLICY, name=Names.LANDLORDPRIVACYPOLICY)
async def landlord_privacy_policy():
    """Return the current Privacy Policy version, effective date and full text."""
    content = ""
    policy_path = os.path.join(STATIC_DIR, "privacy_policy_landlord.md")
    try:
        with open(policy_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        content = ""
    return {
        "version": PRIVACY_POLICY_VERSION,
        "effectiveDate": PRIVACY_POLICY_EFFECTIVE_DATE,
        "url": "/landlord/privacy-policy",
        "content": content,
    }


@router.get(Routes.LANDLORDAPITERMS, name=Names.LANDLORDTERMS)
async def landlord_terms():
    """Return the current Terms and Conditions version, effective date and full text."""
    content = ""
    terms_path = os.path.join(STATIC_DIR, "terms_conditions_landlord.md")
    try:
        with open(terms_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        content = ""
    return {
        "version": TERMS_CONDITIONS_VERSION,
        "effectiveDate": TERMS_CONDITIONS_EFFECTIVE_DATE,
        "url": "/landlord/terms",
        "content": content,
    }


@router.post(Routes.LANDLORDAPIAUTHSIGNUP, name=Names.LANDLORDSIGNUP)
async def landlord_signup(request: Request, payload: LandlordSignupRequest):
    """
    Create a new landlord account.
    Validates: username format, password match, uniqueness of username + email.
    Account creation is BLOCKED unless the landlord has accepted the current
    Privacy Policy (privacyAccepted + privacyVersion) AND the current Terms and
    Conditions (termsAccepted + termsVersion). Returns 400 otherwise.
    Returns: { status, landlord: { id, landlordUuid, username, fullName } }
    """
    username = normalize_username(payload.username)

    # ── Privacy Policy consent is mandatory before account creation ──
    if not payload.privacyAccepted:
        raise HTTPException(
            status_code=400,
            detail="You must accept the PROPAURA Privacy Policy to create an account.",
        )
    if payload.privacyVersion != PRIVACY_POLICY_VERSION:
        raise HTTPException(
            status_code=400,
            detail="The Privacy Policy version has changed. Please review and accept the current policy.",
        )

    # ── Terms and Conditions consent is mandatory before account creation ──
    if not payload.termsAccepted:
        raise HTTPException(
            status_code=400,
            detail="You must accept the PROPAURA Terms and Conditions to create an account.",
        )
    if payload.termsVersion != TERMS_CONDITIONS_VERSION:
        raise HTTPException(
            status_code=400,
            detail="The Terms and Conditions version has changed. Please review and accept the current terms.",
        )

    # ── Input validation ──
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if username in RESERVED:
        raise HTTPException(status_code=400, detail="Username is reserved.")
    if payload.password != payload.confirmPassword:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    # ── Unified uniqueness checks ──
    conflicts = []

    if username in RESERVED:
        conflicts.append({
            "field": "username",
            "code": "RESERVED",
            "message": "Username is reserved.",
            "suggestions": suggest_usernames(username),
        })
    elif username_exists(username):
        conflicts.append({
            "field": "username",
            "code": "USERNAME_TAKEN",
            "message": "Username is already registered.",
            "suggestions": suggest_usernames(username),
        })

    if payload.email and get_landlord_by_email(payload.email.strip().lower()):
        conflicts.append({
            "field": "email",
            "code": "EMAIL_TAKEN",
            "message": "Email is already registered.",
        })

    if conflicts:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICTS", "message": "Some fields need attention.", "conflicts": conflicts},
        )

    # ── Create account ──
    landlord_uuid = str(uuid.uuid4())
    password_hash = hash_pin(payload.password)
    consent_ip = request.client.host if request.client else None
    consent_ua = request.headers.get("User-Agent", "")

    landlord = create_landlord(
        full_name=payload.fullName.strip(),
        email=payload.email.strip().lower() if payload.email else None,
        phone=normalize_phone(payload.phone) if payload.phone else None,
        username=username,
        password_hash=password_hash,
        landlord_uuid=landlord_uuid,
        privacy_consented=1,
        privacy_version=payload.privacyVersion,
        privacy_accepted_at=datetime.utcnow().isoformat(),
        privacy_accepted_ip=consent_ip,
        privacy_accepted_user_agent=consent_ua,
        terms_consented=1,
        terms_version=payload.termsVersion,
        terms_accepted_at=datetime.utcnow().isoformat(),
        terms_accepted_ip=consent_ip,
        terms_accepted_user_agent=consent_ua,
    )

    # Record the consent events in the auditable consent trails
    record_privacy_consent(
        landlord["id"],
        privacy_version=payload.privacyVersion,
        ip_address=consent_ip,
        user_agent=consent_ua,
    )
    record_terms_consent(
        landlord["id"],
        terms_version=payload.termsVersion,
        ip_address=consent_ip,
        user_agent=consent_ua,
    )

    # Store encrypted password in admin vault (for platform admin reveal)
    from app.authentication.common.pin_vault import encrypt_admin_view_pin
    from app.core.db import get_conn as _get_conn
    encrypted_pw = encrypt_admin_view_pin(payload.password)
    now_iso = datetime.utcnow().isoformat()
    with _get_conn() as vault_conn:
        vault_conn.execute(
            """INSERT INTO "landlordPasswordAdminStore"
               ("landlordId", "encryptedPassword", "updatedAt") VALUES (%s, %s, %s)
               ON CONFLICT ("landlordId") DO UPDATE SET "encryptedPassword" = excluded."encryptedPassword", "updatedAt" = excluded."updatedAt""",
            (landlord["id"], encrypted_pw, now_iso),
        )
        vault_conn.commit()

    create_landlord_audit_log(
        landlord["id"],
        "signup_success",
        ip_address=consent_ip,
        meta_json=json.dumps({"username": username}),
    )
    create_landlord_audit_log(
        landlord["id"],
        "privacy_policy_accepted",
        ip_address=consent_ip,
        meta_json=json.dumps({"version": payload.privacyVersion, "user_agent": consent_ua}),
    )
    create_landlord_audit_log(
        landlord["id"],
        "terms_conditions_accepted",
        ip_address=consent_ip,
        meta_json=json.dumps({"version": payload.termsVersion, "user_agent": consent_ua}),
    )

    return {
        "status": "success",
        "landlord": {
            "id": landlord["id"],
            "landlordUuid": landlord["landlordUuid"],
            "username": landlord["username"],
            "fullName": landlord["fullName"],
        },
    }


@router.post(Routes.LANDLORDAPIAUTHPRIVACYCONSENT, name=Names.LANDLORDPRIVACYCONSENT)
async def landlord_privacy_consent(
    request: Request,
    payload: LandlordPrivacyConsentRequest,
    principal=Depends(get_current_landlord_api),
):
    """
    Record Privacy Policy acceptance for an authenticated landlord.

    Used for accounts created without an inline consent step (e.g. a brand-new
    Google-created account), which are unusable until this consent is recorded.
    """
    if not payload.accepted:
        raise HTTPException(status_code=400, detail="Privacy Policy acceptance is required.")
    if payload.privacyVersion != PRIVACY_POLICY_VERSION:
        raise HTTPException(
            status_code=400,
            detail="The Privacy Policy version has changed. Please review and accept the current policy.",
        )

    consent_ip = request.client.host if request.client else None
    consent_ua = request.headers.get("User-Agent", "")

    record_privacy_consent(
        principal.landlord_id,
        privacy_version=payload.privacyVersion,
        ip_address=consent_ip,
        user_agent=consent_ua,
    )
    create_landlord_audit_log(
        principal.landlord_id,
        "privacy_policy_accepted",
        ip_address=consent_ip,
        meta_json=json.dumps({"version": payload.privacyVersion, "user_agent": consent_ua}),
    )

    return {"status": "success", "message": "Privacy Policy accepted.", "version": PRIVACY_POLICY_VERSION}


@router.post(Routes.LANDLORDAPIAUTHTERMSCONSENT, name=Names.LANDLORDTERMSCONSENT)
async def landlord_terms_consent(
    request: Request,
    payload: LandlordTermsConsentRequest,
    principal=Depends(get_current_landlord_api),
):
    """
    Record Terms and Conditions acceptance for an authenticated landlord.

    Used for accounts created without an inline consent step (e.g. a brand-new
    Google-created account), which are unusable until this consent is recorded.
    """
    if not payload.accepted:
        raise HTTPException(status_code=400, detail="Terms and Conditions acceptance is required.")
    if payload.termsVersion != TERMS_CONDITIONS_VERSION:
        raise HTTPException(
            status_code=400,
            detail="The Terms and Conditions version has changed. Please review and accept the current terms.",
        )

    consent_ip = request.client.host if request.client else None
    consent_ua = request.headers.get("User-Agent", "")

    record_terms_consent(
        principal.landlord_id,
        terms_version=payload.termsVersion,
        ip_address=consent_ip,
        user_agent=consent_ua,
    )
    create_landlord_audit_log(
        principal.landlord_id,
        "terms_conditions_accepted",
        ip_address=consent_ip,
        meta_json=json.dumps({"version": payload.termsVersion, "user_agent": consent_ua}),
    )

    return {"status": "success", "message": "Terms and Conditions accepted.", "version": TERMS_CONDITIONS_VERSION}


@router.post(Routes.LANDLORDAPIAUTHLOGIN, name=Names.LANDLORDLOGIN)
async def landlord_login(
    request: Request, response: Response, payload: LandlordLoginRequest
):
    """
    Authenticate a landlord and issue access + refresh cookies.
    Returns: { status, landlord: { id, landlordUuid, username, fullName } }
    If TOTP is required and configured, returns { status: "totp_required" } instead.
    """
    username = normalize_username(payload.username)
    landlord = get_landlord_by_username(username)

    if not landlord:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    if is_landlord_locked_out(landlord):
        create_landlord_audit_log(
            landlord["id"],
            "login_locked_out",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"username": username}),
        )
        raise HTTPException(status_code=429, detail="Account locked. Try again later.")

    if not verify_pin(payload.password, landlord["passwordHash"]):
        record_landlord_failed_attempt(landlord["id"])
        create_landlord_audit_log(
            landlord["id"],
            "login_failed",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"username": username}),
        )
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # Check if TOTP is required for login
    if landlord["totpEnabled"] and landlord["totpSecret"]:
        return {
            "status": "totp_required",
            "message": "TOTP verification required.",
            "username": username,
        }

    # Check if password change is required (admin reset)
    if landlord["requiresPasswordChange"]:
        if dict(landlord).get("tempPasswordConsumed"):
            create_landlord_audit_log(
                landlord["id"],
                "temp_password_reuse_blocked",
                ip_address=request.client.host if request.client else None,
                meta_json=json.dumps({"username": username}),
            )
            raise HTTPException(
                status_code=403,
                detail="This temporary password has already been used. Contact your administrator to reset it again.",
            )

        # Mark temp password as consumed on first use
        now = datetime.utcnow().isoformat()
        with get_conn() as conn:
            conn.execute(
                "UPDATE \"landlordAccounts\" SET \"tempPasswordConsumed\" = 1 WHERE id = %s",
                (landlord["id"],),
            )
            conn.commit()

        reset_landlord_failed_attempts(landlord["id"])
        session_id, refresh_token = create_landlord_session(
            landlord["id"], request, payload.rememberMe
        )
        access_token = create_access_token(landlord["id"], session_id)
        cookie_value = f"{session_id}:{refresh_token}"
        set_landlord_auth_cookies(response, access_token, cookie_value, payload.rememberMe, request)

        create_landlord_audit_log(
            landlord["id"],
            "login_forced_password_change",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"username": username}),
        )

        return {
            "status": "password_change_required",
            "message": "You must change your password before continuing.",
            "username": username,
            "landlordUuid": landlord["landlordUuid"],
        }

    reset_landlord_failed_attempts(landlord["id"])
    session_id, refresh_token = create_landlord_session(
        landlord["id"], request, payload.rememberMe
    )
    access_token = create_access_token(landlord["id"], session_id)
    cookie_value = f"{session_id}:{refresh_token}"

    set_landlord_auth_cookies(response, access_token, cookie_value, payload.rememberMe, request)

    create_landlord_audit_log(
        landlord["id"],
        "login_success",
        ip_address=request.client.host if request.client else None,
        meta_json=json.dumps({"username": username}),
    )

    return {
        "status": "success",
        "landlord": {
            "id": landlord["id"],
            "landlordUuid": landlord["landlordUuid"],
            "username": landlord["username"],
            "fullName": landlord["fullName"],
        },
    }


@router.post(Routes.LANDLORDAPIAUTHREFRESH, name=Names.LANDLORDREFRESH)
async def landlord_refresh(request: Request, response: Response):
    """
    Silent token refresh for landlords.
    Rotates the refresh token on every use for security.
    """
    refresh_cookie = request.cookies.get("refresh_token")
    if not refresh_cookie or ":" not in refresh_cookie:
        clear_landlord_auth_cookies(response, request)
        raise HTTPException(status_code=401, detail="No refresh token")

    session_id, raw_token = refresh_cookie.split(":", 1)

    session = get_landlord_session_db(session_id)
    if not session or not verify_pin(raw_token, session["refreshTokenHash"]):
        if session:
            revoke_landlord_session_db(session_id)
        clear_landlord_auth_cookies(response, request)
        raise HTTPException(status_code=401, detail="Session expired or revoked")

    revoke_landlord_session_db(session_id)

    landlord_id = session["landlordId"]
    remember_me = bool(session["rememberMe"] or 0)

    new_session_id, new_refresh_token = create_landlord_session(
        landlord_id, request, remember_me=remember_me
    )
    new_access_token = create_access_token(landlord_id, new_session_id)
    new_cookie_val = f"{new_session_id}:{new_refresh_token}"

    set_landlord_auth_cookies(
        response, new_access_token, new_cookie_val, remember_me, request
    )
    return {"status": "success", "message": "Session refreshed"}


@router.post(Routes.LANDLORDAPIAUTHLOGOUT, name=Names.LANDLORDLOGOUT)
async def landlord_logout(request: Request, response: Response):
    """
    Clear landlord cookies and revoke the active session.
    """
    # Extract landlord_id from token before clearing cookies
    landlord_id = None
    token = request.cookies.get("access_token")
    if token:
        try:
            from app.authentication.landlord.jwt import decode_access_token
            payload = decode_access_token(token)
            landlord_id = int(payload.get("landlord_id") or payload.get("sub"))
        except Exception:
            pass

    clear_landlord_auth_cookies(response, request)
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token and ":" in refresh_token:
        session_id = refresh_token.split(":", 1)[0]
        revoke_landlord_session_db(session_id)

    if landlord_id:
        ip = request.client.host if request.client else None
        create_landlord_audit_log(
            landlord_id, "logout",
            ip_address=ip,
            meta_json=json.dumps({"user_agent": request.headers.get("User-Agent", "")}),
        )
    return {"status": "success"}


@router.get(Routes.LANDLORDAPIAUTHME, name=Names.LANDLORDME)
async def landlord_me(principal=Depends(get_current_landlord_api)):
    """
    Return the identity of the currently authenticated landlord.
    Requires a valid access_token cookie.
    Returns TOTP state and password change flag so frontend can sync state.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT \"totpSecret\", \"totpEnabled\", \"requiresPasswordChange\", "
            "\"privacyConsented\", \"privacyVersion\", "
            "\"termsConsented\", \"termsVersion\", "
            "\"setupCompleted\", \"setupSkipped\" "
            "FROM \"landlordAccounts\" WHERE id = %s",
            (principal.landlord_id,),
        ).fetchone()

    return {
        "status": "success",
        "landlord": {
            "id": principal.landlord_id,
            "landlordUuid": principal.landlord_uuid,
            "username": principal.username,
            "fullName": principal.fullname,
            "email": principal.email,
            "hasTotp": bool(row and row["totpSecret"]),
            "totpEnabled": bool(row and row["totpEnabled"]),
            "requiresPasswordChange": bool(row and row["requiresPasswordChange"]),
            "privacyConsented": bool(row and row["privacyConsented"]),
            "privacyVersion": row["privacyVersion"] if row else None,
            "termsConsented": bool(row and row["termsConsented"]),
            "termsVersion": row["termsVersion"] if row else None,
            "setupCompleted": bool(row and row["setupCompleted"]),
            "setupSkipped": bool(row and row["setupSkipped"]),
        },
    }


# ─── TOTP Login ────────────────────────────────────────────────────

@router.post(Routes.LANDLORDAPIAUTHLOGINTOTP, name=Names.LANDLORDLOGINTOTP)
async def landlord_login_with_totp(
    request: Request, response: Response, payload: LandlordLoginWithTotpRequest
):
    """
    Complete landlord login with TOTP verification.
    Re-verifies username + password, then validates the TOTP code.
    """
    username = normalize_username(payload.username)
    landlord = get_landlord_by_username(username)

    if not landlord:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    if is_landlord_locked_out(landlord):
        create_landlord_audit_log(
            landlord["id"],
            "login_locked_out",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"username": username}),
        )
        raise HTTPException(status_code=429, detail="Account locked. Try again later.")

    if not verify_pin(payload.password, landlord["passwordHash"]):
        record_landlord_failed_attempt(landlord["id"])
        create_landlord_audit_log(
            landlord["id"],
            "login_failed",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"username": username}),
        )
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    if not landlord["totpSecret"]:
        raise HTTPException(status_code=400, detail="TOTP not configured for this account.")

    if not verify_totp(landlord["totpSecret"], payload.totpToken):
        record_landlord_failed_attempt(landlord["id"])
        create_landlord_audit_log(
            landlord["id"],
            "totp_failed",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"username": username}),
        )
        raise HTTPException(status_code=401, detail="Invalid TOTP code. Please try again.")

    reset_landlord_failed_attempts(landlord["id"])

    # Check if password change is required (admin reset)
    if landlord["requiresPasswordChange"]:
        if dict(landlord).get("tempPasswordConsumed"):
            create_landlord_audit_log(
                landlord["id"],
                "temp_password_reuse_blocked",
                ip_address=request.client.host if request.client else None,
                meta_json=json.dumps({"username": username}),
            )
            raise HTTPException(
                status_code=403,
                detail="This temporary password has already been used. Contact your administrator to reset it again.",
            )

        now = datetime.utcnow().isoformat()
        with get_conn() as conn:
            conn.execute(
                "UPDATE \"landlordAccounts\" SET \"tempPasswordConsumed\" = 1 WHERE id = %s",
                (landlord["id"],),
            )
            conn.commit()

        session_id, refresh_token = create_landlord_session(
            landlord["id"], request, payload.rememberMe
        )
        access_token = create_access_token(landlord["id"], session_id)
        cookie_value = f"{session_id}:{refresh_token}"
        set_landlord_auth_cookies(response, access_token, cookie_value, payload.rememberMe, request)

        create_landlord_audit_log(
            landlord["id"],
            "login_forced_password_change",
            ip_address=request.client.host if request.client else None,
            meta_json=json.dumps({"username": username}),
        )

        return {
            "status": "password_change_required",
            "message": "You must change your password before continuing.",
            "username": username,
            "landlordUuid": landlord["landlordUuid"],
        }

    session_id, refresh_token = create_landlord_session(
        landlord["id"], request, payload.rememberMe
    )
    access_token = create_access_token(landlord["id"], session_id)
    cookie_value = f"{session_id}:{refresh_token}"

    set_landlord_auth_cookies(response, access_token, cookie_value, payload.rememberMe, request)

    create_landlord_audit_log(
        landlord["id"],
        "login_success",
        ip_address=request.client.host if request.client else None,
        meta_json=json.dumps({"username": username}),
    )

    return {
        "status": "success",
        "landlord": {
            "id": landlord["id"],
            "landlordUuid": landlord["landlordUuid"],
            "username": landlord["username"],
            "fullName": landlord["fullName"],
        },
    }


# ─── TOTP Management (protected) ───────────────────────────────────

@router.post(Routes.LANDLORDAPIAUTHCHANGEPASSWORD, name="landlordchangepassword")
async def landlord_change_password(
    request: Request,
    payload: dict,
):
    """
    Change landlord password. Used during forced password reset flow.
    Requires current password + new password + confirm password.
    Accepts encrypted (key/data/nonce) or plain JSON payload.
    """
    from app.authentication.common.pin_vault import encrypt_admin_view_pin
    from app.encryption import decrypt_payload

    # Handle encrypted payload from frontend apiPost
    if "key" in payload and "data" in payload and "nonce" in payload:
        try:
            decrypted = decrypt_payload(payload["key"], payload["data"], payload["nonce"])
            current_password = decrypted.get("currentPassword", "")
            new_password = decrypted.get("newPassword", "")
            confirm_password = decrypted.get("confirmPassword", "")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid encrypted payload")
    else:
        current_password = payload.get("currentPassword", "")
        new_password = payload.get("newPassword", "")
        confirm_password = payload.get("confirmPassword", "")

    if not new_password or not confirm_password:
        raise HTTPException(status_code=400, detail="All fields are required.")
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match.")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    # Extract landlord from token
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from app.authentication.landlord.jwt import decode_access_token
    payload_token = decode_access_token(token)
    landlord_id = int(payload_token.get("landlord_id") or payload_token.get("sub"))

    with get_conn() as conn:
        landlord = conn.execute(
            "SELECT id, \"landlordUuid\", username, \"passwordHash\", \"requiresPasswordChange\" FROM \"landlordAccounts\" WHERE id = %s",
            (landlord_id,),
        ).fetchone()
        if not landlord:
            raise HTTPException(status_code=404, detail="Landlord not found.")

    # When a password change is required (Google signup / admin reset), the user
    # does not know the current (placeholder/temporary) password, so skip it.
    if not landlord["requiresPasswordChange"]:
        if not current_password:
            raise HTTPException(status_code=400, detail="Current password is required.")
        if current_password == new_password:
            raise HTTPException(status_code=400, detail="New password must be different from current password.")
        if not verify_pin(current_password, landlord["passwordHash"]):
            raise HTTPException(status_code=401, detail="Current password is incorrect.")

    new_hash = hash_pin(new_password)
    encrypted_pw = encrypt_admin_view_pin(new_password)
    now = datetime.utcnow().isoformat()

    with get_conn() as conn:
        conn.execute(
            """UPDATE "landlordAccounts"
               SET "passwordHash" = %s,
                   "requiresPasswordChange" = 0,
                   "tempPasswordCreatedAt" = NULL,
                   "tempPasswordConsumed" = 0,
                   "updatedAt" = %s
               WHERE id = %s""",
            (new_hash, now, landlord_id),
        )
        conn.execute(
            """INSERT INTO "landlordPasswordAdminStore"
               ("landlordId", "encryptedPassword", "updatedAt") VALUES (%s, %s, %s)
               ON CONFLICT ("landlordId") DO UPDATE SET "encryptedPassword" = excluded."encryptedPassword", "updatedAt" = excluded."updatedAt""",
            (landlord_id, encrypted_pw, now),
        )
        # Check if landlord has TOTP configured
        row = conn.execute(
            "SELECT \"totpSecret\" FROM \"landlordAccounts\" WHERE id = %s",
            (landlord_id,),
        ).fetchone()
        conn.commit()

    create_landlord_audit_log(
        landlord_id,
        "password_changed",
        ip_address=request.client.host if request.client else None,
    )

    # Broadcast auth state change
    try:
        from app.core.websocket_manager import sync_manager
        ll_uuid = landlord["landlordUuid"]
        await sync_manager.broadcast(f"landlord:{ll_uuid}", {"type": "AUTH_STATE_CHANGED", "role": "landlord", "id": landlord_id})
        await sync_manager.broadcast("platform_admin", {"type": "AUTH_STATE_CHANGED", "role": "landlord", "id": landlord_id})
    except Exception:
        pass

    # Return TOTP data if configured, so frontend can show QR dialog
    if row and row["totpSecret"]:
        username = (landlord["username"] if landlord else "") or ""
        qr_base64 = generate_totp_qr_base64(username, row["totpSecret"])
        return {
            "status": "success",
            "message": "Password updated successfully.",
            "next_step": "totp_review",
            "totp": {
                "secret": row["totpSecret"],
                "qr_code_base64": qr_base64,
                "provisioning_uri": get_totp_uri(username, row["totpSecret"]),
            },
        }

    return {"status": "success", "message": "Password updated successfully."}


@router.get(Routes.LANDLORDAPITOTPQR, name=Names.LANDLORDTOTPQR)
async def landlord_totp_qr(
    landlordUuid: str,
    principal=Depends(get_current_landlord_api),
):
    """
    Get TOTP QR code and secret for the authenticated landlord.
    Auto-generates a secret on first access.
    """
    landlord = get_landlord_by_uuid(landlordUuid)
    if not landlord:
        raise HTTPException(status_code=404, detail="Landlord not found.")

    if not landlord["totpSecret"]:
        return {"status": "success", "totp": None, "message": "TOTP is not configured"}

    new_secret = landlord["totpSecret"]
    qr_base64 = generate_totp_qr_base64(landlord["username"], new_secret)

    return {
        "status": "success",
        "totp": {
            "secret": new_secret,
            "qr_code_base64": qr_base64,
            "provisioning_uri": get_totp_uri(landlord["username"], new_secret),
        },
    }


@router.post(Routes.LANDLORDAPITOTPREGENERATE, name=Names.LANDLORDTOTPREGENERATE)
async def landlord_totp_regenerate(
    landlordUuid: str,
    principal=Depends(get_current_landlord_api),
):
    """
    Regenerate TOTP secret for the authenticated landlord.
    Returns a new QR code and secret.
    """
    landlord = get_landlord_by_uuid(landlordUuid)
    if not landlord:
        raise HTTPException(status_code=404, detail="Landlord not found.")

    new_secret = regenerate_landlord_totp_secret(landlord["id"])
    qr_base64 = generate_totp_qr_base64(landlord["username"], new_secret)

    create_landlord_audit_log(
        landlord["id"],
        "totp_regenerated",
        ip_address=request.client.host if request.client else None,
    )

    return {
        "status": "success",
        "message": "TOTP secret regenerated successfully. Update your authenticator app!",
        "totp": {
            "secret": new_secret,
            "qr_code_base64": qr_base64,
            "provisioning_uri": get_totp_uri(landlord["username"], new_secret),
        },
    }


@router.post(Routes.LANDLORDAPITOTPENABLE, name=Names.LANDLORDTOTPENABLE)
async def landlord_totp_enable(
    landlordUuid: str,
    principal=Depends(get_current_landlord_api),
):
    """
    Enable TOTP for the authenticated landlord.
    Generates a TOTP secret if one doesn't exist.
    Returns QR code and secret for the landlord to scan.
    """
    landlord = get_landlord_by_uuid(landlordUuid)
    if not landlord:
        raise HTTPException(status_code=404, detail="Landlord not found.")

    now = datetime.utcnow().isoformat()

    if not landlord["totpSecret"]:
        new_secret = regenerate_landlord_totp_secret(landlord["id"])
    else:
        new_secret = landlord["totpSecret"]

    with get_conn() as conn:
        conn.execute(
            "UPDATE \"landlordAccounts\" SET \"totpEnabled\" = 1, \"updatedAt\" = %s WHERE id = %s",
            (now, landlord["id"]),
        )
        conn.commit()

    landlord = get_landlord_by_uuid(landlordUuid)
    qr_base64 = generate_totp_qr_base64(landlord["username"], new_secret)

    # Broadcast TOTP state change
    try:
        from app.core.websocket_manager import sync_manager
        await sync_manager.broadcast(f"landlord:{landlordUuid}", {"type": "TOTP_STATE_CHANGED", "enabled": True})
        await sync_manager.broadcast("platform_admin", {"type": "TOTP_STATE_CHANGED", "landlordId": landlord["id"], "enabled": True})
    except Exception:
        pass

    create_landlord_audit_log(
        landlord["id"],
        "totp_enabled",
        ip_address=None,
    )

    return {
        "status": "success",
        "message": "TOTP enabled successfully.",
        "totp": {
            "secret": new_secret,
            "qr_code_base64": qr_base64,
            "provisioning_uri": get_totp_uri(landlord["username"], new_secret),
        },
    }


@router.post(Routes.LANDLORDAPITOTPDISABLE, name=Names.LANDLORDTOTPDISABLE)
async def landlord_totp_disable(
    landlordUuid: str,
    principal=Depends(get_current_landlord_api),
):
    """
    Disable TOTP for the authenticated landlord.
    Keeps the totp_secret so it can be shown when re-enabled.
    Landlord can login with just username+password after disabling.
    """
    landlord = get_landlord_by_uuid(landlordUuid)
    if not landlord:
        raise HTTPException(status_code=404, detail="Landlord not found.")

    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE \"landlordAccounts\" SET \"totpEnabled\" = 0, \"updatedAt\" = %s WHERE id = %s",
            (now, landlord["id"]),
        )
        conn.commit()

    # Broadcast TOTP state change
    try:
        from app.core.websocket_manager import sync_manager
        await sync_manager.broadcast(f"landlord:{landlordUuid}", {"type": "TOTP_STATE_CHANGED", "enabled": False})
        await sync_manager.broadcast("platform_admin", {"type": "TOTP_STATE_CHANGED", "landlordId": landlord["id"], "enabled": False})
    except Exception:
        pass

    create_landlord_audit_log(
        landlord["id"],
        "totp_disabled",
        ip_address=None,
    )

    return {
        "status": "success",
        "message": "TOTP disabled. You can now login with just username and password.",
    }


# ─── Audit Logs ──────────────────────────────────────────────────────────────

@router.get(Routes.LANDLORDAPIAUDITLOGS, name=Names.LANDLORDAUDITLOGS)
async def landlord_audit_logs(
    landlordUuid: str,
    request: Request,
    principal=Depends(get_current_landlord_api),
    action_type: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """Return audit logs for this landlord (own actions + all their tenants' actions)."""
    landlord_id = principal.id

    query = '''
        SELECT * FROM (
            SELECT
                ll.id,
                'landlord' AS app_source,
                ll."landlordId" AS actor_id,
                la.username AS actor_name,
                ll.action,
                NULL AS target_type,
                NULL AS target_id,
                ll."ipAddress",
                ll."metaJson",
                ll."createdAt"
            FROM "landlordAuditLogs" ll
            LEFT JOIN "landlordAccounts" la ON ll."landlordId" = la.id
            WHERE ll."landlordId" = %s

            UNION ALL

            SELECT
                tl.id,
                'tenant' AS app_source,
                tl."tenantId" AS actor_id,
                t.name AS actor_name,
                tl.action,
                NULL AS target_type,
                NULL AS target_id,
                tl."ipAddress",
                tl."metaJson",
                tl."createdAt"
            FROM "tenantAuditLogs" tl
            LEFT JOIN tenants t ON tl."tenantId" = t.id
            WHERE tl."tenantId" IN (SELECT id FROM tenants WHERE "landlordId" = %s)
        ) unified
        WHERE 1=1
    '''
    params: list = [landlord_id, landlord_id]

    if action_type:
        query += " AND action LIKE %s"
        params.append(f"%{action_type}%")
    if search:
        query += " AND (action LIKE %s OR \"ipAddress\" LIKE %s OR actor_name LIKE %s)"
        params.extend([f"%{search}%"] * 3)
    if date_from:
        query += " AND \"createdAt\" >= %s"
        params.append(date_from)
    if date_to:
        query += " AND \"createdAt\" <= %s"
        params.append(date_to + "T23:59:59")

    count_query = "SELECT COUNT(*) FROM (" + query + ")"
    with get_conn() as conn:
        total = conn.execute(count_query, tuple(params)).fetchone()["count"]

    query += " ORDER BY \"createdAt\" DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    with get_conn() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()

    items = []
    for r in rows:
        meta = {}
        if r["metaJson"]:
            try:
                meta = json.loads(r["metaJson"])
            except Exception:
                pass
        items.append({
            "id": r["id"],
            "app_source": r["app_source"],
            "actor_id": r["actor_id"],
            "actor_name": r["actor_name"],
            "action": r["action"],
            "target_type": r["target_type"],
            "target_id": r["target_id"],
            "ip_address": r["ipAddress"],
            "meta": meta,
            "created_at": r["createdAt"],
        })

    return {"items": items, "total": total}


@router.get(Routes.LANDLORDAPIAUDITLOGSACTIONS, name=Names.LANDLORDAUDITLOGSACTIONS)
async def landlord_audit_action_types(
    landlordUuid: str,
    request: Request,
    principal=Depends(get_current_landlord_api),
):
    """Return distinct action types for this landlord's logs."""
    landlord_id = principal.id
    query = '''
        SELECT DISTINCT action FROM (
            SELECT action FROM "landlordAuditLogs" WHERE "landlordId" = %s
            UNION ALL
            SELECT action FROM "tenantAuditLogs"
            WHERE "tenantId" IN (SELECT id FROM tenants WHERE "landlordId" = %s)
        ) ORDER BY action
    '''
    with get_conn() as conn:
        rows = conn.execute(query, (landlord_id, landlord_id)).fetchall()
    return [r["action"] for r in rows]
