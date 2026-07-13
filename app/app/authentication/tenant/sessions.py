import uuid
import secrets
from datetime import datetime, timedelta
from app.core.db import get_conn
from app.authentication.common.utils import hash_pin

def create_tenant_session(tenantId: int, request, remember_me: bool):
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
            INSERT INTO tenant_sessions
            (session_id, tenantId, refresh_token_hash, device_name, browser, os, ip_address, created_at, last_activity, expires_at, remember_me)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, tenantId, refresh_hash, "Unknown", user_agent, "Unknown", ip, now, now, expires_at, remember_me))
        conn.commit()
        
    return session_id, refresh_token

def get_tenant_session_db(session_id: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM tenant_sessions WHERE session_id = ? AND status = 'Active'", (session_id,)).fetchone()

def revoke_tenant_session_db(session_id: str):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE tenant_sessions SET status = 'Revoked', revoked_at = ? WHERE session_id = ?", (now, session_id))
        conn.commit()

def revoke_all_tenant_sessions(tenantId: int):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE tenant_sessions SET status = 'Revoked', revoked_at = ? WHERE tenantId = ?", (now, tenantId))
        conn.commit()

