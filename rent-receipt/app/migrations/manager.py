import logging
from app.core.db import get_conn

logger = logging.getLogger(__name__)

def run_migrations():
    from app.migrations.m001_auth_v2 import run as m001
    from app.migrations.m002_receipts_tenantid import run as m002
    from app.migrations.m003_tenant_pin_history import run as m003
    from app.migrations.m004_tenant_pin_admin_store import run as m004
    
    migrations = [
        (m001, "m001_auth_v2"),
        (m002, "m002_receipts_tenantid"),
        (m003, "m003_tenant_pin_history"),
        (m004, "m004_tenant_pin_admin_store"),
    ]
    
    with get_conn() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS app_metadata (key TEXT PRIMARY KEY, value TEXT)")
        conn.commit()
        
    for migration_func, name in migrations:
        try:
            with get_conn() as conn:
                logger.info(f"Checking migration: {name}")
                conn.execute("BEGIN TRANSACTION")
                migration_func(conn)
                conn.commit()
        except Exception as e:
            logger.error(f"Migration {name} failed: {e}")
            raise RuntimeError(f"Migration {name} failed") from e

def get_schema_version(conn, domain: str) -> int:
    row = conn.execute("SELECT value FROM app_metadata WHERE key = ?", (f"{domain}_schema_version",)).fetchone()
    return int(row["value"]) if row else 0

def set_schema_version(conn, domain: str, version: int):
    conn.execute("INSERT OR REPLACE INTO app_metadata (key, value) VALUES (?, ?)", (f"{domain}_schema_version", str(version)))

def validate_schema():
    expected_schema = {
        "admin_sessions": [
            "session_id", "admin_id", "refresh_token_hash", "device_name", 
            "browser", "os", "ip_address", "created_at", "last_activity", 
            "expires_at", "revoked_at", "remember_me", "status"
        ],
        "tenant_sessions": [
            "session_id", "tenant_id", "refresh_token_hash", "device_name", 
            "browser", "os", "ip_address", "created_at", "last_activity", 
            "expires_at", "revoked_at", "remember_me", "status"
        ],
        "tenants": ["failed_attempts", "locked_until"],
        "tenant_pin_history": ["id", "tenant_id", "pin_hash", "changed_at"],
        "receipts": ["tenant_id"]
    }
    
    with get_conn() as conn:
        for table, required_columns in expected_schema.items():
            # Check table exists
            row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if not row:
                raise RuntimeError(f"Startup Validation Failed: Table '{table}' is missing.")
            
            # Check columns
            cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
            col_names = [c["name"] for c in cols]
            
            for req_col in required_columns:
                if req_col not in col_names:
                    raise RuntimeError(f"Startup Validation Failed: Column '{req_col}' is missing in table '{table}'.")
