import uuid
import secrets
from datetime import datetime, timedelta
from app.core.db import get_conn
from app.authentication.common.utils import hash_pin

def create_admin_session(admin_id: int, request, remember_me: bool):
    refresh_token = secrets.token_urlsafe(64)
    refresh_hash = hash_pin(refresh_token)
    
    session_id = str(uuid.uuid4())
    days = 180 if remember_me else 1
    expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()
    
    user_agent = request.headers.get("User-Agent", "Unknown")
    ip = request.client.host if request.client else "Unknown IP"
    
    now = datetime.utcnow().isoformat()
    
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO admin_sessions
            (session_id, admin_id, refresh_token_hash, device_name, browser, os, ip_address, created_at, last_activity, expires_at, remember_me)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, admin_id, refresh_hash, "Unknown", user_agent, "Unknown", ip, now, now, expires_at, remember_me))
        conn.commit()
        
    return session_id, refresh_token

def get_admin_session_db(session_id: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM admin_sessions WHERE session_id = ? AND status = 'Active'", (session_id,)).fetchone()

def revoke_admin_session_db(session_id: str):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE admin_sessions SET status = 'Revoked', revoked_at = ? WHERE session_id = ?", (now, session_id))
        conn.commit()
