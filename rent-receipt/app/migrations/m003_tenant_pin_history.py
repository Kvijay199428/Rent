from app.migrations.manager import get_schema_version, set_schema_version
from app.core.db import _column_exists
import logging

logger = logging.getLogger(__name__)

def run(conn):
    version = get_schema_version(conn, "tenant")
    if version < 1:
        logger.info("Running Tenant migration v1: Adding PIN security and brute force protection")
        
        if not _column_exists(conn, "tenants", "failed_attempts"):
            conn.execute("ALTER TABLE tenants ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0")
        if not _column_exists(conn, "tenants", "locked_until"):
            conn.execute("ALTER TABLE tenants ADD COLUMN locked_until TEXT")
            
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tenant_pin_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                pin_hash TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tenant_pin_history_tenant_id ON tenant_pin_history(tenant_id)")
        
        set_schema_version(conn, "tenant", 1)
        logger.info("Tenant migration v1 complete")
