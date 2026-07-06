import sqlite3
import logging

logger = logging.getLogger(__name__)

def run(conn: sqlite3.Connection):
    try:
        # Check if table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tenant_pin_admin_store'")
        if not cursor.fetchone():
            logger.info("Creating tenant_pin_admin_store table")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS tenant_pin_admin_store (
                tenant_id INTEGER PRIMARY KEY,
                encrypted_pin TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
            )
            """)
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to migrate m004_tenant_pin_admin_store: {e}")
        raise e
