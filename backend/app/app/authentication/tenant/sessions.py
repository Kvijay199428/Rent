import uuid
import secrets
from datetime import datetime, timedelta
from app.core.db import get_conn
from app.authentication.common.utils import hash_pin

def create_tenant_session(tenantId: int, request, remember_me: bool):
    refresh_token = secrets.token_urlsafe(64)
    refresh_hash = hash_pin(refresh_token)
    
    session_id = str(uuid.uuid4())
    days = 180 if remember_me else 30
    expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()
    
    user_agent = request.headers.get("User-Agent", "Unknown")
    ip = request.client.host if request.client else "Unknown IP"
    
    now = datetime.utcnow().isoformat()
    
    with get_conn() as conn:
        conn.execute('''
            INSERT INTO "tenantSessions"
            ("sessionId", "tenantId", "refreshTokenHash", "deviceName", browser, os, "ipAddress", "createdAt", "lastActivity", "expiresAt", "rememberMe")
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (session_id, tenantId, refresh_hash, "Unknown", user_agent, "Unknown", ip, now, now, expires_at, remember_me))
        conn.commit()
        
    return session_id, refresh_token

def get_tenant_session_db(session_id: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM \"tenantSessions\" WHERE \"sessionId\" = %s AND status = 'Active'", (session_id,)).fetchone()

def revoke_tenant_session_db(session_id: str):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE \"tenantSessions\" SET status = 'Revoked', \"revokedAt\" = %s WHERE \"sessionId\" = %s", (now, session_id))
        conn.commit()

def revoke_all_tenant_sessions(tenantId: int):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute('''UPDATE \"tenantSessions\" SET status = 'Revoked', \"revokedAt\" = %s WHERE "tenantId" = %s''', (now, tenantId))
        conn.commit()

