"""
app/routers/platform_admin.py
Platform super-admin router — serves the SPA and exposes:
  POST   /platform-admin/api/auth/login
  POST   /platform-admin/api/auth/refresh
  POST   /platform-admin/api/auth/logout
  GET    /platform-admin/api/landlords
  POST   /platform-admin/api/landlords
  PATCH  /platform-admin/api/landlords/{landlord_id}
  GET    /platform-admin/api/stats
"""
from __future__ import annotations

import json
import os
import secrets
import string
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from app.core.db import get_conn
from app.core.config_service import ConfigService
from app.authentication.platform.jwt import (
    create_platform_access_token,
    decode_platform_access_token,
)
from app.authentication.platform.cookies import (
    set_platform_auth_cookies,
    clear_platform_auth_cookies,
    get_platform_token,
)
from app.authentication.common.utils import verify_pin, hash_pin
from app.database.auth_repository import (
    get_admin_by_username,
    get_admin_by_id,
    verify_totp,
    generate_totp_qr_base64,
    get_totp_uri,
    regenerate_totp_secret,
)
from app.routers.landlord_routes import (
    generate_landlordUuid,
    is_valid_landlordUuid,
)
from app.core.audit import (
    create_platform_admin_audit_log,
    cleanup_old_audit_logs,
    get_audit_log_path,
)

router = APIRouter(prefix="/admin", tags=["Platform Admin"])

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _dist_index() -> str:
    return os.path.join("frontend", "admin-app", "dist", "index.html")


async def _serve_platform_admin_spa():
    index_file = _dist_index()
    if not os.path.exists(index_file):
        raise HTTPException(
            status_code=503,
            detail="Platform admin frontend build not found. Run: npm run build inside frontend/admin-app",
        )
    return FileResponse(index_file)


def _get_platform_admin(request: Request) -> dict:
    """Decode the platform access cookie and return the admin row."""
    token = get_platform_token(request)
    payload = decode_platform_access_token(token)
    admin_id = int(payload["admin_id"])
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, username, email, is_platform_admin, totp_secret FROM admins WHERE id = ?", (admin_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Platform admin not found")
    if not row["is_platform_admin"]:
        raise HTTPException(status_code=403, detail="Platform admin access required")
    return dict(row)


def _create_session_token(admin_id: int) -> tuple[str, str]:
    """Return (session_id, access_token)."""
    session_id = secrets.token_hex(16)
    access_token = create_platform_access_token(admin_id, session_id)
    return session_id, access_token


def _make_refresh_token() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(64))


# ─── Request / Response models ────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class CreateLandlordRequest(BaseModel):
    admin_id: int
    landlordUuid: str | None = None   # auto-generated when omitted


class PatchLandlordRequest(BaseModel):
    active: bool


# ─── Auth endpoints ───────────────────────────────────────────────────────────

@router.post("/api/auth/login")
async def platform_login(body: LoginRequest, request: Request, response: Response):
    ip = request.client.host if request.client else "Unknown"
    ua = request.headers.get("User-Agent", "Unknown")

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, totp_secret, is_platform_admin, failed_attempts, locked_until FROM admins WHERE username = ?",
            (body.username,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Brute-force check
    if row["locked_until"]:
        try:
            locked_dt = datetime.fromisoformat(row["locked_until"])
            if datetime.utcnow() < locked_dt:
                remaining = int((locked_dt - datetime.utcnow()).total_seconds() / 60) + 1
                create_platform_admin_audit_log(
                    row["id"], "login_locked_out",
                    admin_username=row["username"], ip_address=ip, user_agent=ua,
                )
                raise HTTPException(status_code=429, detail=f"Account locked. Try again in {remaining} minute(s).")
            else:
                with get_conn() as conn:
                    conn.execute("UPDATE admins SET failed_attempts = 0, locked_until = NULL WHERE id = ?", (row["id"],))
                    conn.commit()
        except HTTPException:
            raise
        except Exception:
            pass

    if not verify_pin(body.password, row["password_hash"]):
        # Record failed attempt
        new_attempts = (row["failed_attempts"] or 0) + 1
        locked_until_str = None
        if new_attempts >= 5:
            locked_until_str = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
        with get_conn() as conn:
            conn.execute(
                "UPDATE admins SET failed_attempts = ?, locked_until = ? WHERE id = ?",
                (new_attempts, locked_until_str, row["id"]),
            )
            conn.commit()
        create_platform_admin_audit_log(
            row["id"], "login_failed",
            admin_username=row["username"], ip_address=ip, user_agent=ua,
            meta={"attempts": new_attempts, "locked": bool(locked_until_str)},
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not row["is_platform_admin"]:
        raise HTTPException(status_code=403, detail="Platform admin access required")

    # Reset failed attempts on success
    with get_conn() as conn:
        conn.execute("UPDATE admins SET failed_attempts = 0, locked_until = NULL WHERE id = ?", (row["id"],))
        conn.commit()

    # TOTP gate: if TOTP is configured, require it before issuing tokens
    if row["totp_secret"]:
        create_platform_admin_audit_log(
            row["id"], "login_password_ok",
            admin_username=row["username"], ip_address=ip, user_agent=ua,
        )
        return {
            "status": "totp_required",
            "message": "TOTP verification required.",
            "username": body.username,
        }

    session_id, access_token = _create_session_token(row["id"])
    refresh_token = _make_refresh_token()
    refresh_hash = hash_pin(refresh_token)

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO admin_sessions
            (session_id, admin_id, refresh_token_hash, device_name, browser, os, ip_address, created_at, last_activity, expires_at, remember_me, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now', ?), ?, 'Active')
            """,
            (
                session_id,
                row["id"],
                refresh_hash,
                "Platform Admin",
                ua,
                "Unknown",
                ip,
                "+180 days" if body.remember_me else "+30 days",
                1 if body.remember_me else 0,
            ),
        )
        conn.commit()

    set_platform_auth_cookies(response, access_token, f"{session_id}.{refresh_token}", body.remember_me, request)

    create_platform_admin_audit_log(
        row["id"], "login_success",
        admin_username=row["username"], ip_address=ip, user_agent=ua,
    )
    return {"status": "ok", "username": row["username"]}


class TotpVerifyRequest(BaseModel):
    username: str
    password: str
    totpToken: str
    remember_me: bool = False


@router.post("/api/auth/login-totp")
async def platform_login_totp(body: TotpVerifyRequest, request: Request, response: Response):
    ip = request.client.host if request.client else "Unknown"
    ua = request.headers.get("User-Agent", "Unknown")

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, totp_secret, is_platform_admin, failed_attempts, locked_until FROM admins WHERE username = ?",
            (body.username,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Brute-force check
    if row["locked_until"]:
        try:
            locked_dt = datetime.fromisoformat(row["locked_until"])
            if datetime.utcnow() < locked_dt:
                remaining = int((locked_dt - datetime.utcnow()).total_seconds() / 60) + 1
                create_platform_admin_audit_log(
                    row["id"], "login_locked_out",
                    admin_username=row["username"], ip_address=ip, user_agent=ua,
                )
                raise HTTPException(status_code=429, detail=f"Account locked. Try again in {remaining} minute(s).")
            else:
                with get_conn() as conn:
                    conn.execute("UPDATE admins SET failed_attempts = 0, locked_until = NULL WHERE id = ?", (row["id"],))
                    conn.commit()
        except HTTPException:
            raise
        except Exception:
            pass

    if not verify_pin(body.password, row["password_hash"]):
        new_attempts = (row["failed_attempts"] or 0) + 1
        locked_until_str = None
        if new_attempts >= 5:
            locked_until_str = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
        with get_conn() as conn:
            conn.execute(
                "UPDATE admins SET failed_attempts = ?, locked_until = ? WHERE id = ?",
                (new_attempts, locked_until_str, row["id"]),
            )
            conn.commit()
        create_platform_admin_audit_log(
            row["id"], "login_failed",
            admin_username=row["username"], ip_address=ip, user_agent=ua,
            meta={"attempts": new_attempts, "locked": bool(locked_until_str)},
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not row["is_platform_admin"]:
        raise HTTPException(status_code=403, detail="Platform admin access required")
    if not row["totp_secret"]:
        raise HTTPException(status_code=400, detail="TOTP not configured for this account")
    if not verify_totp(row["totp_secret"], body.totpToken):
        new_attempts = (row["failed_attempts"] or 0) + 1
        locked_until_str = None
        if new_attempts >= 5:
            locked_until_str = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
        with get_conn() as conn:
            conn.execute(
                "UPDATE admins SET failed_attempts = ?, locked_until = ? WHERE id = ?",
                (new_attempts, locked_until_str, row["id"]),
            )
            conn.commit()
        create_platform_admin_audit_log(
            row["id"], "login_totp_failed",
            admin_username=row["username"], ip_address=ip, user_agent=ua,
            meta={"attempts": new_attempts, "locked": bool(locked_until_str)},
        )
        raise HTTPException(status_code=401, detail="Invalid TOTP code. Please try again.")

    # Reset failed attempts on success
    with get_conn() as conn:
        conn.execute("UPDATE admins SET failed_attempts = 0, locked_until = NULL WHERE id = ?", (row["id"],))
        conn.commit()

    session_id, access_token = _create_session_token(row["id"])
    refresh_token = _make_refresh_token()
    refresh_hash = hash_pin(refresh_token)

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO admin_sessions
            (session_id, admin_id, refresh_token_hash, device_name, browser, os, ip_address, created_at, last_activity, expires_at, remember_me, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now', ?), ?, 'Active')
            """,
            (
                session_id,
                row["id"],
                refresh_hash,
                "Platform Admin",
                ua,
                "Unknown",
                ip,
                "+180 days" if body.remember_me else "+30 days",
                1 if body.remember_me else 0,
            ),
        )
        conn.commit()

    set_platform_auth_cookies(response, access_token, f"{session_id}.{refresh_token}", body.remember_me, request)

    create_platform_admin_audit_log(
        row["id"], "login_success",
        admin_username=row["username"], ip_address=ip, user_agent=ua,
        meta={"totp": True},
    )
    return {"status": "ok", "username": row["username"]}


@router.post("/api/auth/refresh")
async def platform_refresh(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    parts = refresh_token.split(".", 1)
    if len(parts) != 2:
        clear_platform_auth_cookies(response, request)
        raise HTTPException(status_code=401, detail="Malformed refresh token")

    session_id, raw_token = parts

    with get_conn() as conn:
        session = conn.execute(
            "SELECT * FROM admin_sessions WHERE session_id = ? AND status = 'Active'",
            (session_id,),
        ).fetchone()

        if not session or not verify_pin(raw_token, session["refresh_token_hash"]):
            if session:
                conn.execute(
                    "UPDATE admin_sessions SET status = 'Revoked', revoked_at = datetime('now') WHERE session_id = ?",
                    (session_id,),
                )
                conn.commit()
            clear_platform_auth_cookies(response, request)
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        conn.execute(
            "UPDATE admin_sessions SET status = 'Revoked', revoked_at = datetime('now') WHERE session_id = ?",
            (session_id,),
        )

        new_session_id, new_access_token = _create_session_token(session["admin_id"])
        new_refresh_token = _make_refresh_token()
        new_refresh_hash = hash_pin(new_refresh_token)
        remember_me = bool(session.get("remember_me", 0))
        expiry = "+180 days" if remember_me else "+30 days"

        conn.execute(
            """
            INSERT INTO admin_sessions
            (session_id, admin_id, refresh_token_hash, device_name, browser, os, ip_address, created_at, last_activity, expires_at, remember_me, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now', ?), ?, 'Active')
            """,
            (
                new_session_id,
                session["admin_id"],
                new_refresh_hash,
                session["device_name"],
                session["browser"],
                session["os"],
                session["ip_address"],
                expiry,
                remember_me,
            ),
        )
        conn.commit()

    set_platform_auth_cookies(response, new_access_token, f"{new_session_id}.{new_refresh_token}", remember_me, request)
    return {"status": "ok"}


@router.post("/api/auth/logout")
async def platform_logout(request: Request, response: Response):
    token = get_platform_token(request)
    payload = decode_platform_access_token(token)
    session_id = payload.get("sid")
    admin_id = int(payload.get("admin_id", 0))

    with get_conn() as conn:
        conn.execute(
            "UPDATE admin_sessions SET status = 'Revoked', revoked_at = datetime('now') WHERE session_id = ?",
            (session_id,),
        )
        conn.commit()

    ip = request.client.host if request.client else "Unknown"
    create_platform_admin_audit_log(
        admin_id, "logout",
        ip_address=ip, user_agent=request.headers.get("User-Agent"),
    )
    clear_platform_auth_cookies(response, request)
    return {"status": "ok"}


@router.get("/api/auth/me")
async def platform_me(request: Request):
    admin = _get_platform_admin(request)
    return {"id": admin["id"], "username": admin["username"], "email": admin["email"], "has_totp": bool(admin.get("totp_secret"))}


@router.get("/api/auth/totp-qr")
async def platform_totp_qr(request: Request):
    admin = _get_platform_admin(request)
    admin_data = get_admin_by_id(admin["id"])
    if not admin_data:
        raise HTTPException(status_code=404, detail="Admin not found")
    if not admin_data["totp_secret"]:
        new_secret = regenerate_totp_secret(admin["id"])
        admin_data = get_admin_by_id(admin["id"])
    qr_base64 = generate_totp_qr_base64(admin_data["username"], admin_data["totp_secret"])
    return {
        "qr_code_base64": qr_base64,
        "secret": admin_data["totp_secret"],
        "provisioning_uri": get_totp_uri(admin_data["username"], admin_data["totp_secret"]),
    }


class TotpRegenerateRequest(BaseModel):
    current_password: str


@router.post("/api/auth/totp-regenerate")
async def platform_totp_regenerate(body: TotpRegenerateRequest, request: Request):
    admin = _get_platform_admin(request)
    admin_data = get_admin_by_id(admin["id"])
    if not admin_data:
        raise HTTPException(status_code=404, detail="Admin not found")
    if not verify_pin(body.current_password, admin_data["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid password")
    new_secret = regenerate_totp_secret(admin["id"])
    qr_base64 = generate_totp_qr_base64(admin_data["username"], new_secret)
    ip = request.client.host if request.client else "Unknown"
    create_platform_admin_audit_log(
        admin["id"], "totp_regenerated",
        admin_username=admin["username"], ip_address=ip,
        user_agent=request.headers.get("User-Agent"),
    )
    return {
        "status": "success",
        "message": "TOTP secret regenerated. Update your authenticator app!",
        "qr_code_base64": qr_base64,
        "secret": new_secret,
        "provisioning_uri": get_totp_uri(admin_data["username"], new_secret),
    }


# ─── Settings & Profile ─────────────────────────────────────────────────────

@router.get("/api/settings/profile")
async def get_profile(request: Request):
    admin = _get_platform_admin(request)
    return {
        "id": admin["id"],
        "username": admin["username"],
        "email": admin["email"],
        "is_platform_admin": bool(admin["is_platform_admin"]),
        "has_totp": bool(admin.get("totp_secret")),
        "created_at": admin.get("created_at"),
        "updated_at": admin.get("updated_at"),
    }


class UpdateProfileRequest(BaseModel):
    username: str | None = None
    email: str | None = None


@router.put("/api/settings/profile")
async def update_profile(request: Request, body: UpdateProfileRequest):
    admin = _get_platform_admin(request)
    updates = []
    params = []
    if body.username:
        existing = get_admin_by_username(body.username)
        if existing and existing["id"] != admin["id"]:
            raise HTTPException(status_code=409, detail="Username already taken")
        updates.append("username = ?")
        params.append(body.username)
    if body.email is not None:
        updates.append("email = ?")
        params.append(body.email)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    params.append(datetime.utcnow().isoformat())
    params.append(admin["id"])
    with get_conn() as conn:
        conn.execute(
            f"UPDATE admins SET {', '.join(updates)}, updated_at = ? WHERE id = ?",
            tuple(params),
        )
        conn.commit()
    ip = request.client.host if request.client else "Unknown"
    create_platform_admin_audit_log(
        admin["id"], "profile_updated",
        admin_username=admin["username"], ip_address=ip,
        user_agent=request.headers.get("User-Agent"),
        meta={"fields_updated": [u.split(" =")[0] for u in updates]},
    )
    return {"status": "success"}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


@router.post("/api/settings/change-password")
async def change_password(request: Request, body: ChangePasswordRequest):
    admin = _get_platform_admin(request)
    admin_data = get_admin_by_id(admin["id"])
    if not verify_pin(body.current_password, admin_data["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if body.new_password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    new_hash = hash_pin(body.new_password)
    from app.database.auth_repository import update_admin_password
    update_admin_password(admin["id"], new_hash)
    ip = request.client.host if request.client else "Unknown"
    create_platform_admin_audit_log(
        admin["id"], "password_changed",
        admin_username=admin["username"], ip_address=ip,
        user_agent=request.headers.get("User-Agent"),
    )
    return {"status": "success", "message": "Password updated successfully"}


# ─── Stats ────────────────────────────────────────────────────────────────────

@router.get("/api/stats")
async def platform_stats(request: Request):
    _get_platform_admin(request)
    with get_conn() as conn:
        total_landlords = conn.execute("SELECT COUNT(*) FROM landlord_accounts").fetchone()[0]
        active_landlords = conn.execute(
            "SELECT COUNT(*) FROM landlord_accounts WHERE status = 'Active'"
        ).fetchone()[0]
        total_admins = conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
        total_tenants = conn.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]
    return {
        "total_landlords": total_landlords,
        "active_landlords": active_landlords,
        "total_admins": total_admins,
        "total_tenants": total_tenants,
    }


# ─── Landlord Discovery (auto-detect from landlord_accounts) ───────────────

@router.get("/api/landlords")
async def list_landlords(
    request: Request,
    search: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    _get_platform_admin(request)
    query = """
        SELECT
            la.id, la.landlord_uuid, la.full_name, la.email, la.phone,
            la.username, la.status, la.created_at, la.updated_at,
            (la.totp_enabled = 1 AND la.totp_secret IS NOT NULL) as has_totp,
            la.failed_attempts, la.locked_until,
            la.requires_password_change,
            (SELECT COUNT(*) FROM tenants WHERE landlord_id = la.id) as tenant_count,
            (SELECT COUNT(*) FROM receipts WHERE landlord_id = la.id) as receipt_count,
            (SELECT COUNT(*) FROM occupants WHERE landlord_id = la.id) as kyc_count
        FROM landlord_accounts la
        WHERE 1=1
    """
    params: list = []
    if search:
        query += " AND (la.username LIKE ? OR la.full_name LIKE ? OR la.email LIKE ?)"
        params.extend([f"%{search}%"] * 3)
    if status:
        query += " AND la.status = ?"
        params.append(status)
    query += " ORDER BY la.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_conn() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(r) for r in rows]


@router.get("/api/landlords/{landlord_id}/details")
async def get_landlord_details(landlord_id: int, request: Request):
    _get_platform_admin(request)
    with get_conn() as conn:
        landlord = conn.execute(
            "SELECT * FROM landlord_accounts WHERE id = ?", (landlord_id,)
        ).fetchone()
        if not landlord:
            raise HTTPException(status_code=404, detail="Landlord not found")
        stats = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM tenants WHERE landlord_id = ?) as tenants,
                (SELECT COUNT(*) FROM receipts WHERE landlord_id = ?) as receipts,
                (SELECT COUNT(*) FROM occupants WHERE landlord_id = ?) as kyc,
                (SELECT COALESCE(SUM(total), 0) FROM receipts WHERE landlord_id = ? AND paymentstatus = 'PENDING') as pending_revenue
            """,
            (landlord_id, landlord_id, landlord_id, landlord_id),
        ).fetchone()
    return {
        "landlord": {k: v for k, v in dict(landlord).items() if k != "password_hash" and k != "totp_secret"},
        "has_password": True,
        "has_totp": bool(landlord["totp_enabled"] and landlord["totp_secret"]),
        "requires_password_change": bool(landlord["requires_password_change"]),
        "stats": dict(stats),
    }


@router.get("/api/landlords/{landlord_id}/creator-info")
async def get_landlord_creator_info(landlord_id: int, request: Request):
    _get_platform_admin(request)
    with get_conn() as conn:
        landlord = conn.execute(
            "SELECT id, username, full_name, created_at FROM landlord_accounts WHERE id = ?",
            (landlord_id,),
        ).fetchone()
        if not landlord:
            raise HTTPException(status_code=404, detail="Landlord not found")
        import json
        audit = conn.execute(
            """
            SELECT ip_address, created_at, meta_json
            FROM landlord_audit_logs
            WHERE landlord_id = ? AND action = 'signup_success'
            ORDER BY created_at DESC LIMIT 1
            """,
            (landlord_id,),
        ).fetchone()
        last_login = conn.execute(
            """
            SELECT created_at, ip_address
            FROM landlord_audit_logs
            WHERE landlord_id = ? AND action = 'login_success'
            ORDER BY created_at DESC LIMIT 1
            """,
            (landlord_id,),
        ).fetchone()
    meta = {}
    if audit and audit["meta_json"]:
        try:
            meta = json.loads(audit["meta_json"])
        except Exception:
            pass
    return {
        "landlord_id": landlord["id"],
        "username": landlord["username"],
        "full_name": landlord["full_name"],
        "self_registered": True,
        "created_at": landlord["created_at"],
        "signup_details": {
            "ip_address": audit["ip_address"] if audit else None,
            "timestamp": audit["created_at"] if audit else None,
            "user_agent": meta.get("user_agent"),
        },
        "last_login": {
            "timestamp": last_login["created_at"] if last_login else None,
            "ip_address": last_login["ip_address"] if last_login else None,
        },
    }


# ─── Data Previewer ─────────────────────────────────────────────────────────

@router.get("/api/preview/tenants")
async def preview_tenants(
    request: Request,
    search: str | None = None,
    landlord_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    _get_platform_admin(request)
    query = """
        SELECT
            t.id, t.name, t.phone, t.email, t.roomnumber as unit, t.status,
            t.landlord_id, t.rent as rent_amount, t.securitydeposit as deposit,
            t.tenantpin, t.failed_attempts, t.locked_until,
            la.full_name AS landlord_name, la.username AS landlord_username
        FROM tenants t
        LEFT JOIN landlord_accounts la ON t.landlord_id = la.id
        WHERE 1=1
    """
    params: list = []
    if search:
        query += " AND (t.name LIKE ? OR t.phone LIKE ? OR t.email LIKE ? OR t.roomnumber LIKE ?)"
        params.extend([f"%{search}%"] * 4)
    if landlord_id:
        query += " AND t.landlord_id = ?"
        params.append(landlord_id)
    if status:
        query += " AND t.status = ?"
        params.append(status)
    query += " ORDER BY t.id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM tenants" + (" WHERE landlord_id = ?" if landlord_id else ""),
            (landlord_id,) if landlord_id else (),
        ).fetchone()[0]
        rows = conn.execute(query, tuple(params)).fetchall()
    return {"items": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/api/preview/receipts")
async def preview_receipts(
    request: Request,
    search: str | None = None,
    landlord_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    _get_platform_admin(request)
    query = """
        SELECT
            r.billNo as id, r.total, r.paymentstatus, r.date as issued_at, r.month,
            r.rent, r.water, r.electricity, r.total as amount,
            r.landlord_id,
            la.full_name AS landlord_name,
            t.name AS tenant_name, t.roomnumber AS tenant_unit
        FROM receipts r
        LEFT JOIN landlord_accounts la ON r.landlord_id = la.id
        LEFT JOIN tenants t ON r.tenantId = t.id
        WHERE 1=1
    """
    params: list = []
    if search:
        query += " AND (t.name LIKE ? OR t.roomnumber LIKE ? OR r.billNo LIKE ?)"
        params.extend([f"%{search}%"] * 3)
    if landlord_id:
        query += " AND r.landlord_id = ?"
        params.append(landlord_id)
    if status:
        query += " AND r.paymentstatus = ?"
        params.append(status)
    query += " ORDER BY r.rowid DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM receipts" + (" WHERE landlord_id = ?" if landlord_id else ""),
            (landlord_id,) if landlord_id else (),
        ).fetchone()[0]
        rows = conn.execute(query, tuple(params)).fetchall()
    return {"items": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/api/preview/kyc")
async def preview_kyc(
    request: Request,
    search: str | None = None,
    landlord_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    _get_platform_admin(request)
    query = """
        SELECT
            o.occupantUuid as id, o.name, o.status, o.mobile, o.residentSince,
            o.aadhaar_front, o.aadhaar_back, o.aadhaar_combined,
            o.landlord_id,
            la.full_name AS landlord_name,
            t.name AS tenant_name, t.roomnumber AS tenant_unit
        FROM occupants o
        LEFT JOIN landlord_accounts la ON o.landlord_id = la.id
        LEFT JOIN tenants t ON o.tenantId = t.id
        WHERE 1=1
    """
    params: list = []
    if search:
        query += " AND (o.name LIKE ? OR t.name LIKE ? OR t.roomnumber LIKE ?)"
        params.extend([f"%{search}%"] * 3)
    if landlord_id:
        query += " AND o.landlord_id = ?"
        params.append(landlord_id)
    if status:
        query += " AND o.status = ?"
        params.append(status)
    query += " ORDER BY o.rowid DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM occupants" + (" WHERE landlord_id = ?" if landlord_id else ""),
            (landlord_id,) if landlord_id else (),
        ).fetchone()[0]
        rows = conn.execute(query, tuple(params)).fetchall()
    return {"items": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}


# ─── Admin list (for landlord assignment) ────────────────────────────────────

@router.get("/api/admins")
async def list_admins(request: Request):
    """Return a minimal list of admins for the landlord-assignment dropdown."""
    _get_platform_admin(request)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, username, email FROM admins ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


# ─── Landlord TOTP & Password Management ────────────────────────────────────

@router.post("/api/landlords/{landlord_id}/totp-toggle")
async def toggle_landlord_totp(landlord_id: int, request: Request):
    """Enable or disable TOTP for a specific landlord.

    Disable: sets totp_enabled=0 so landlord can login without TOTP.
             Keeps totp_secret intact so QR can be shown when re-enabled.
    Enable:  sets totp_enabled=1. If no totp_secret exists, generates one.
    """
    _get_platform_admin(request)
    from app.database.landlord_repository import (
        get_landlord_by_id as _get_ll,
        regenerate_landlord_totp_secret,
        generate_totp_qr_base64 as _qr,
        get_totp_uri as _uri,
    )
    landlord = _get_ll(landlord_id)
    if not landlord:
        raise HTTPException(status_code=404, detail="Landlord not found")

    now = datetime.utcnow().isoformat()
    ip = request.client.host if request.client else "Unknown"
    admin = _get_platform_admin(request)

    if landlord["totp_enabled"]:
        # Disable: flip totp_enabled to 0, keep totp_secret
        with get_conn() as conn:
            conn.execute(
                "UPDATE landlord_accounts SET totp_enabled = 0, updated_at = ? WHERE id = ?",
                (now, landlord_id),
            )
            conn.commit()
        # Broadcast TOTP state change
        try:
            from app.core.websocket_manager import sync_manager
            ll_uuid = landlord["landlord_uuid"]
            await sync_manager.broadcast(f"landlord:{ll_uuid}", {"type": "TOTP_STATE_CHANGED", "enabled": False})
            await sync_manager.broadcast("platform_admin", {"type": "TOTP_STATE_CHANGED", "landlordId": landlord_id, "enabled": False})
        except Exception:
            pass
        create_platform_admin_audit_log(
            admin["id"], "landlord_totp_toggled",
            admin_username=admin["username"], target_type="landlord", target_id=landlord_id,
            ip_address=ip, user_agent=request.headers.get("User-Agent"),
            meta={"enabled": False, "landlord_username": landlord["username"]},
        )
        return {"status": "success", "totp_enabled": False, "message": "TOTP disabled. Landlord can login without TOTP."}
    else:
        # Enable: flip totp_enabled to 1, generate secret if missing
        with get_conn() as conn:
            conn.execute(
                "UPDATE landlord_accounts SET totp_enabled = 1, updated_at = ? WHERE id = ?",
                (now, landlord_id),
            )
            conn.commit()

        landlord = _get_ll(landlord_id)
        qr_data = None
        if not landlord["totp_secret"]:
            new_secret = regenerate_landlord_totp_secret(landlord_id)
            landlord = _get_ll(landlord_id)
            qr_data = {
                "secret": new_secret,
                "qr_code_base64": _qr(landlord["username"], new_secret),
                "provisioning_uri": _uri(landlord["username"], new_secret),
            }

        # Broadcast TOTP state change
        try:
            from app.core.websocket_manager import sync_manager
            ll_uuid = landlord["landlord_uuid"]
            await sync_manager.broadcast(f"landlord:{ll_uuid}", {"type": "TOTP_STATE_CHANGED", "enabled": True})
            await sync_manager.broadcast("platform_admin", {"type": "TOTP_STATE_CHANGED", "landlordId": landlord_id, "enabled": True})
        except Exception:
            pass

        result = {"status": "success", "totp_enabled": True, "message": "TOTP enabled"}
        if qr_data:
            result.update(qr_data)
        create_platform_admin_audit_log(
            admin["id"], "landlord_totp_toggled",
            admin_username=admin["username"], target_type="landlord", target_id=landlord_id,
            ip_address=ip, user_agent=request.headers.get("User-Agent"),
            meta={"enabled": True, "landlord_username": landlord["username"]},
        )
        return result


@router.get("/api/landlords/{landlord_id}/reveal-password")
async def reveal_landlord_password(landlord_id: int, request: Request):
    """Reveal the current plaintext password from the admin vault."""
    admin = _get_platform_admin(request)
    from app.authentication.common.pin_vault import decrypt_admin_view_pin

    with get_conn() as conn:
        row = conn.execute(
            "SELECT encrypted_password, updated_at FROM landlord_password_admin_store WHERE landlord_id = ?",
            (landlord_id,),
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Password not in vault. Use 'Reset Password' to generate a new one.",
        )

    ip = request.client.host if request.client else "Unknown"
    create_platform_admin_audit_log(
        admin["id"], "password_revealed",
        admin_username=admin["username"], target_type="landlord", target_id=landlord_id,
        ip_address=ip, user_agent=request.headers.get("User-Agent"),
    )
    return {
        "status": "success",
        "password": decrypt_admin_view_pin(row["encrypted_password"]),
        "updated_at": row["updated_at"],
    }


@router.post("/api/landlords/{landlord_id}/reset-password")
async def reset_landlord_password(landlord_id: int, request: Request):
    """Generate a new random password, hash + encrypt, return once, and build WhatsApp URL."""
    admin = _get_platform_admin(request)
    import string as _string
    from urllib.parse import quote
    from app.authentication.common.pin_vault import encrypt_admin_view_pin
    from app.core.config_service import config

    with get_conn() as conn:
        landlord = conn.execute(
            "SELECT id, username, phone FROM landlord_accounts WHERE id = ?", (landlord_id,)
        ).fetchone()
        if not landlord:
            raise HTTPException(status_code=404, detail="Landlord not found")

    alphabet = _string.ascii_letters + _string.digits + "!@#$%^&*"
    new_password = "".join(secrets.choice(alphabet) for _ in range(12))

    password_hash = hash_pin(new_password)
    encrypted_pw = encrypt_admin_view_pin(new_password)
    now = datetime.utcnow().isoformat()

    with get_conn() as conn:
        conn.execute(
            """UPDATE landlord_accounts
               SET password_hash = ?,
                   requires_password_change = 1,
                   temp_password_created_at = ?,
                   temp_password_consumed = 0,
                   updated_at = ?
               WHERE id = ?""",
            (password_hash, now, now, landlord_id),
        )
        conn.execute(
            """INSERT OR REPLACE INTO landlord_password_admin_store
               (landlord_id, encrypted_password, updated_at) VALUES (?, ?, ?)""",
            (landlord_id, encrypted_pw, now),
        )
        conn.commit()

    # Build WhatsApp URL if phone number available
    whatsapp_url = None
    phone = landlord["phone"]
    if phone:
        phone_clean = __import__("re").sub(r"\D", "", str(phone))
        if len(phone_clean) == 10:
            country_code = str(
                config.get("system", {}).get("whatsapp", {}).get("country_code", "91")
            )
            phone_clean = country_code + phone_clean

        reset_template = config.get("whatsapp", {}).get("landlord_password_reset", {})
        template_msg = reset_template.get("message") or reset_template.get(
            "default_message",
            "Hello {landlordName},\n\n"
            "Your account password has been reset.\n\n"
            "*Username:* {username}\n"
            "*Temporary Password:* {tempPassword}\n\n"
            "Please log in and change your password immediately.\n\n"
            "Thank you!",
        )
        msg = template_msg.format(
            landlordName=landlord["username"],
            username=landlord["username"],
            tempPassword=new_password,
        )
        whatsapp_url = f"https://api.whatsapp.com/send?phone={phone_clean}&text={quote(msg)}"

    # Broadcast password reset event
    try:
        from app.core.websocket_manager import sync_manager
        ll_uuid = landlord["landlord_uuid"]
        await sync_manager.broadcast(f"landlord:{ll_uuid}", {"type": "PASSWORD_RESET", "landlordId": landlord_id})
        await sync_manager.broadcast("platform_admin", {"type": "PASSWORD_RESET", "landlordId": landlord_id})
        await sync_manager.broadcast(f"landlord:{ll_uuid}", {"type": "AUTH_STATE_CHANGED", "role": "landlord", "id": landlord_id})
        await sync_manager.broadcast("platform_admin", {"type": "AUTH_STATE_CHANGED", "role": "landlord", "id": landlord_id})
    except Exception:
        pass

    ip = request.client.host if request.client else "Unknown"
    create_platform_admin_audit_log(
        admin["id"], "password_reset",
        admin_username=admin["username"], target_type="landlord", target_id=landlord_id,
        ip_address=ip, user_agent=request.headers.get("User-Agent"),
        meta={"landlord_username": landlord["username"]},
    )
    return {
        "status": "success",
        "password": new_password,
        "requires_password_change": True,
        "whatsapp_url": whatsapp_url,
        "message": "Password reset. The landlord must change their password on next login.",
    }


# ─── Tenant Auth (for Data Explorer) ──────────────────────────────────────

@router.get("/api/preview/tenants/{tenant_id}/auth")
async def preview_tenant_auth(tenant_id: int, request: Request):
    """Return tenant auth details (PIN, lock status) for the Data Explorer."""
    _get_platform_admin(request)
    from app.authentication.common.pin_vault import decrypt_admin_view_pin

    with get_conn() as conn:
        tenant = conn.execute(
            """SELECT id, name, status, failed_attempts, locked_until, tenantpin
               FROM tenants WHERE id = ?""",
            (tenant_id,),
        ).fetchone()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        pin_row = conn.execute(
            "SELECT encrypted_pin, updated_at FROM tenantPin_admin_store WHERE tenantId = ?",
            (tenant_id,),
        ).fetchone()

    result = {
        "tenant_id": tenant["id"],
        "name": tenant["name"],
        "status": tenant["status"],
        "failed_attempts": tenant["failed_attempts"],
        "locked_until": tenant["locked_until"],
        "has_pin": bool(tenant["tenantpin"]),
    }

    if pin_row:
        try:
            result["pin"] = decrypt_admin_view_pin(pin_row["encrypted_pin"])
            result["pin_updated_at"] = pin_row["updated_at"]
        except Exception:
            result["pin"] = "(decryption error)"
    else:
        result["pin"] = None

    return result


# ─── Security & Ops ─────────────────────────────────────────────────────────

@router.get("/api/security/alerts")
async def security_alerts(
    request: Request,
    type: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    _get_platform_admin(request)
    with get_conn() as conn:
        # Build alerts from audit logs
        query = """
            SELECT
                id, action, ip_address, created_at, meta_json,
                'admin' AS actor_type,
                (SELECT username FROM admins WHERE id = pal.actor_id) AS actor_name
            FROM platform_admin_audit_logs pal
            WHERE action LIKE '%fail%' OR action LIKE '%block%' OR action LIKE '%invalid%'
        """
        params: list = []
        if type:
            query += " AND action LIKE ?"
            params.append(f"%{type}%")
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, tuple(params)).fetchall()

        # Also check landlord lockouts
        locked = conn.execute(
            """
            SELECT
                la.id, 'landlord_locked' AS action,
                la.locked_until AS created_at,
                'landlord' AS actor_type,
                la.username AS actor_name
            FROM landlord_accounts la
            WHERE la.locked_until IS NOT NULL AND la.locked_until > datetime('now')
            ORDER BY la.locked_until DESC LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    alerts = []
    for r in rows:
        meta = {}
        if r["meta_json"]:
            try:
                import json
                meta = json.loads(r["meta_json"])
            except Exception:
                pass
        alerts.append({
            "id": r["id"],
            "type": "failed_auth",
            "action": r["action"],
            "actor_type": r["actor_type"],
            "actor_name": r["actor_name"],
            "ip_address": r["ip_address"],
            "created_at": r["created_at"],
            "details": meta,
        })
    for r in locked:
        alerts.append({
            "id": r["id"],
            "type": "account_locked",
            "action": r["action"],
            "actor_type": r["actor_type"],
            "actor_name": r["actor_name"],
            "created_at": r["created_at"],
            "details": {"locked_until": r["created_at"]},
        })
    return alerts


@router.get("/api/sessions")
async def list_sessions(request: Request):
    """List active platform admin sessions (from audit logs)."""
    _get_platform_admin(request)
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                id, actor_id, action, ip_address, created_at, meta_json
            FROM platform_admin_audit_logs
            WHERE action LIKE 'login%' OR action LIKE 'totp%'
            ORDER BY created_at DESC
            LIMIT 20
            """
        ).fetchall()
    sessions = []
    for r in rows:
        meta = {}
        if r["meta_json"]:
            try:
                import json
                meta = json.loads(r["meta_json"])
            except Exception:
                pass
        sessions.append({
            "admin_id": r["actor_id"],
            "action": r["action"],
            "ip_address": r["ip_address"],
            "created_at": r["created_at"],
            "user_agent": meta.get("user_agent"),
        })
    return sessions


@router.get("/api/system/health")
async def system_health(request: Request):
    _get_platform_admin(request)
    with get_conn() as conn:
        db_check = conn.execute("SELECT 1").fetchone()
        stats = {
            "database": "ok" if db_check else "error",
            "total_landlords": conn.execute("SELECT COUNT(*) FROM landlord_accounts").fetchone()[0],
            "active_landlords": conn.execute(
                "SELECT COUNT(*) FROM landlord_accounts WHERE status = 'Active'"
            ).fetchone()[0],
            "total_tenants": conn.execute("SELECT COUNT(*) FROM tenants").fetchone()[0],
            "total_receipts": conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0],
            "total_kyc": conn.execute("SELECT COUNT(*) FROM occupants").fetchone()[0],
            "total_admins": conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0],
        }
    stats["status"] = "healthy" if stats["database"] == "ok" else "degraded"
    return stats


# ─── Broadcast / Maintenance Message ────────────────────────────────────────

@router.get("/api/broadcast")
async def get_broadcast():
    config = ConfigService()
    return config.get("broadcast", {"enabled": False, "message": "", "type": "info", "dismissible": True})


class BroadcastUpdateModel(BaseModel):
    enabled: bool = False
    message: str = ""
    type: str = "info"
    dismissible: bool = True


@router.post("/api/broadcast")
async def update_broadcast(data: BroadcastUpdateModel):
    config = ConfigService()
    broadcast = {
        "enabled": data.enabled,
        "message": data.message,
        "type": data.type,
        "dismissible": data.dismissible
    }
    config.save("broadcast", broadcast)
    return {"status": "success", "broadcast": broadcast}


# ─── Audit Logs (unified across all 3 apps) ────────────────────────────────

_UNIFIED_AUDIT_QUERY = """
    SELECT * FROM (
        SELECT
            pal.id,
            'platform_admin' AS app_source,
            pal.admin_id AS actor_id,
            a.username AS actor_name,
            pal.action,
            pal.target_type,
            pal.target_id,
            pal.ip_address,
            pal.meta_json,
            pal.created_at
        FROM platform_admin_audit_logs pal
        LEFT JOIN admins a ON pal.admin_id = a.id

        UNION ALL

        SELECT
            ll.id,
            'landlord' AS app_source,
            ll.landlord_id AS actor_id,
            la.username AS actor_name,
            ll.action,
            NULL AS target_type,
            NULL AS target_id,
            ll.ip_address,
            ll.meta_json,
            ll.created_at
        FROM landlord_audit_logs ll
        LEFT JOIN landlord_accounts la ON ll.landlord_id = la.id

        UNION ALL

        SELECT
            tl.id,
            'tenant' AS app_source,
            tl.tenantId AS actor_id,
            t.name AS actor_name,
            tl.action,
            NULL AS target_type,
            NULL AS target_id,
            tl.ip_address,
            tl.meta_json,
            tl.created_at
        FROM tenant_audit_logs tl
        LEFT JOIN tenants t ON tl.tenantId = t.id
    ) unified
    WHERE 1=1
"""


@router.get("/api/audit-logs")
async def list_audit_logs(
    request: Request,
    action_type: str | None = None,
    app_source: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    _get_platform_admin(request)
    query = _UNIFIED_AUDIT_QUERY
    params: list = []
    if app_source and app_source in ("platform_admin", "landlord", "tenant"):
        query += " AND app_source = ?"
        params.append(app_source)
    if action_type:
        query += " AND action LIKE ?"
        params.append(f"%{action_type}%")
    if search:
        query += " AND (action LIKE ? OR ip_address LIKE ? OR actor_name LIKE ?)"
        params.extend([f"%{search}%"] * 3)
    if date_from:
        query += " AND created_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND created_at <= ?"
        params.append(date_to + "T23:59:59")

    count_query = "SELECT COUNT(*) FROM (" + query + ")"
    with get_conn() as conn:
        total = conn.execute(count_query, tuple(params)).fetchone()[0]

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_conn() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()

    items = []
    for r in rows:
        meta = {}
        if r["meta_json"]:
            try:
                meta = json.loads(r["meta_json"])
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
            "ip_address": r["ip_address"],
            "meta": meta,
            "created_at": r["created_at"],
        })
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/api/audit-logs/actions")
async def list_audit_action_types(request: Request, app_source: str | None = None):
    """Return distinct action types for the filter dropdown."""
    _get_platform_admin(request)
    query = "SELECT DISTINCT action FROM ("
    sub_params: list = []
    if app_source and app_source in ("platform_admin", "landlord", "tenant"):
        if app_source == "platform_admin":
            query += "SELECT action FROM platform_admin_audit_logs"
        elif app_source == "landlord":
            query += "SELECT action FROM landlord_audit_logs"
        else:
            query += "SELECT action FROM tenant_audit_logs"
    else:
        query += "SELECT action FROM platform_admin_audit_logs UNION ALL SELECT action FROM landlord_audit_logs UNION ALL SELECT action FROM tenant_audit_logs"
    query += ") ORDER BY action"
    with get_conn() as conn:
        rows = conn.execute(query, tuple(sub_params)).fetchall()
    return [r["action"] for r in rows]


@router.get("/api/audit-logs/export")
async def export_audit_logs(
    request: Request,
    action_type: str | None = None,
    app_source: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    from fastapi.responses import StreamingResponse
    _get_platform_admin(request)

    query = _UNIFIED_AUDIT_QUERY
    params: list = []
    if app_source and app_source in ("platform_admin", "landlord", "tenant"):
        query += " AND app_source = ?"
        params.append(app_source)
    if action_type:
        query += " AND action LIKE ?"
        params.append(f"%{action_type}%")
    if search:
        query += " AND (action LIKE ? OR ip_address LIKE ? OR actor_name LIKE ?)"
        params.extend([f"%{search}%"] * 3)
    if date_from:
        query += " AND created_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND created_at <= ?"
        params.append(date_to + "T23:59:59")
    query += " ORDER BY created_at DESC"

    with get_conn() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()

    def generate():
        for r in rows:
            meta = {}
            if r["meta_json"]:
                try:
                    meta = json.loads(r["meta_json"])
                except Exception:
                    pass
            entry = {
                "timestamp": r["created_at"],
                "app_source": r["app_source"],
                "actor_name": r["actor_name"],
                "action": r["action"],
                "target_type": r["target_type"],
                "target_id": r["target_id"],
                "ip_address": r["ip_address"],
                "meta": meta,
            }
            yield json.dumps(entry) + "\n"

    today = datetime.utcnow().strftime("%Y-%m-%d")
    return StreamingResponse(
        generate(),
        media_type="application/jsonl",
        headers={"Content-Disposition": f'attachment; filename="audit-logs-{today}.jsonl"'},
    )


@router.post("/api/audit-logs/cleanup")
async def trigger_audit_cleanup(request: Request):
    _get_platform_admin(request)
    from app.core.config_service import config
    days = config.get("system.security.audit_log_retention_days", 30)
    removed = cleanup_old_audit_logs(days)
    return {"status": "success", "removed": removed, "retention_days": days}


# ─── Audit Settings ─────────────────────────────────────────────────────────

@router.get("/api/settings/audit")
async def get_audit_settings(request: Request):
    _get_platform_admin(request)
    from app.core.config_service import config
    days = config.get("system.security.audit_log_retention_days", 30)
    return {"retention_days": days}


class AuditSettingsRequest(BaseModel):
    retention_days: int


@router.put("/api/settings/audit")
async def update_audit_settings(request: Request, body: AuditSettingsRequest):
    _get_platform_admin(request)
    if body.retention_days < 1 or body.retention_days > 365:
        raise HTTPException(status_code=400, detail="Retention days must be between 1 and 365")
    from app.core.config_service import config
    system = config.get("system", {})
    security = system.get("security", {})
    security["audit_log_retention_days"] = body.retention_days
    system["security"] = security
    config.save("system", system)
    return {"status": "success", "retention_days": body.retention_days}


# ─── SPA serving (AFTER all API routes) ────────────────────────────────────

@router.get("", include_in_schema=False)
async def platform_admin_root_redirect(request: Request):
    url = request.url
    if not url.path.endswith("/"):
        return RedirectResponse(url=str(url.replace(path=url.path + "/")), status_code=307)
    return await _serve_platform_admin_spa()


@router.get("/", include_in_schema=False)
@router.get("/{path:path}", include_in_schema=False)
async def serve_platform_admin_app(request: Request, path: str = ""):
    if path.startswith("api"):
        raise HTTPException(status_code=404, detail="Platform admin API route not found")
    dist_dir = os.path.join("frontend", "admin-app", "dist")
    file_path = os.path.normpath(os.path.join(dist_dir, path))
    if not file_path.startswith(os.path.normpath(dist_dir)):
        raise HTTPException(status_code=404)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return await _serve_platform_admin_spa()
