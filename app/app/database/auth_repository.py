from app.core.db import get_conn
from datetime import datetime
from app.authentication.common.utils import hash_pin
import pyotp
import qrcode
import io
import base64



def create_session_db(session_id, tenant_id, refresh_hash, device, ip, expires_at):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO tenant_sessions 
            (session_id, tenant_id, refresh_token_hash, device_name, ip_address, created_at, last_activity, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, tenant_id, refresh_hash, device, ip, now, now, expires_at))
        conn.commit()

def get_session_db(session_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM tenant_sessions WHERE session_id = ? AND status = 'Active'", (session_id,)).fetchone()

def revoke_session_db(session_id):
    with get_conn() as conn:
        conn.execute("UPDATE tenant_sessions SET status = 'Revoked' WHERE session_id = ?", (session_id,))
        conn.commit()

def revoke_all_tenant_sessions(tenant_id):
    with get_conn() as conn:
        conn.execute("UPDATE tenant_sessions SET status = 'Revoked' WHERE tenant_id = ?", (tenant_id,))
        conn.commit()

def log_audit(tenant_id: int, action: str, ip: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO tenant_audit_logs (tenant_id, action, ip_address, created_at) VALUES (?, ?, ?, ?)",
            (tenant_id, action, ip, datetime.utcnow().isoformat())
        )
        conn.commit()

def create_admin_session_db(session_id, admin_id, refresh_hash, device, ip, expires_at):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO admin_sessions
            (session_id, admin_id, refresh_token_hash, device_name, ip_address, created_at, last_activity, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, admin_id, refresh_hash, device, ip, now, now, expires_at))
        conn.commit()

def get_admin_session_db(session_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM admin_sessions WHERE session_id = ? AND status = 'Active'",
            (session_id,)
        ).fetchone()

# Admin user management functions
def get_admin_by_username(username: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM admins WHERE username = ?", (username,)
        ).fetchone()

def get_admin_by_id(admin_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM admins WHERE id = ?", (admin_id,)
        ).fetchone()

def admin_exists() -> bool:
    """Check if any admin user exists in the system."""
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
        return count > 0

def create_admin(username: str, password_hash: str, email: str = None) -> dict:
    """Create a new admin user with TOTP secret."""
    totp_secret = pyotp.random_base32()
    now = datetime.utcnow().isoformat()
    
    with get_conn() as conn:
        cursor = conn.execute(
            """INSERT INTO admins (username, password_hash, totp_secret, email, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username, password_hash, totp_secret, email, now, now)
        )
        conn.commit()
        admin_id = cursor.lastrowid
        
    return {
        "id": admin_id,
        "username": username,
        "totp_secret": totp_secret,
        "email": email,
        "created_at": now
    }

def update_admin_password(admin_id: int, new_password_hash: str):
    """Update admin password after TOTP verification."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE admins SET password_hash = ?, updated_at = ? WHERE id = ?",
            (new_password_hash, now, admin_id)
        )
        conn.commit()

def get_totp_uri(username: str, totp_secret: str, issuer: str = "Rent Receipt System") -> str:
    """Generate TOTP provisioning URI for QR code."""
    return pyotp.totp.TOTP(totp_secret).provisioning_uri(
        name=username,
        issuer_name=issuer
    )

def generate_totp_qr_base64(username: str, totp_secret: str, issuer: str = "Rent Receipt System") -> str:
    """Generate base64 encoded QR code for TOTP setup."""
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

def regenerate_totp_secret(admin_id: int) -> str:
    """Regenerate TOTP secret for an admin (requires password re-verification)."""
    new_secret = pyotp.random_base32()
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE admins SET totp_secret = ?, updated_at = ? WHERE id = ?",
            (new_secret, now, admin_id)
        )
        conn.commit()
    return new_secret

