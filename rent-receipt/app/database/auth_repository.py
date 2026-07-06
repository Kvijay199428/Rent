from app.core.db import get_conn
from datetime import datetime
from app.authentication.common.utils import hash_pin

def init_auth_tables():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS tenant_sessions (
            session_id TEXT PRIMARY KEY,
            tenant_id INTEGER NOT NULL,
            refresh_token_hash TEXT NOT NULL,
            device_name TEXT,
            browser TEXT,
            os TEXT,
            ip_address TEXT,
            created_at TEXT,
            last_activity TEXT,
            expires_at TEXT,
            revoked_at TEXT,
            remember_me INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Active',
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS tenant_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            action TEXT,
            ip_address TEXT,
            created_at TEXT
        );
        
        CREATE TABLE IF NOT EXISTS admin_sessions (
            session_id TEXT PRIMARY KEY,
            admin_id INTEGER NOT NULL,
            refresh_token_hash TEXT NOT NULL,
            device_name TEXT,
            browser TEXT,
            os TEXT,
            ip_address TEXT,
            created_at TEXT,
            last_activity TEXT,
            expires_at TEXT,
            revoked_at TEXT,
            remember_me INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Active',
            FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
        );
        
        -- Create Admins Table
        
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
        """)
        
        # 2. Inject default admin if table is empty (Username: admin / Password: admin123)
        admin_exists = conn.execute("SELECT count(*) FROM admins").fetchone()[0]
        if admin_exists == 0:
            default_hash = hash_pin("admin123")
            conn.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", ("admin", default_hash))
        conn.commit()

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