from app.migrations.manager import get_schema_version, set_schema_version
from app.core.db import _column_exists
import logging

logger = logging.getLogger(__name__)

def run(conn):
    version = get_schema_version(conn, "receipt")
    if version < 1:
        logger.info("Running Receipt migration v1: Adding tenant_id to receipts")
        if not _column_exists(conn, "receipts", "tenant_id"):
            conn.execute("ALTER TABLE receipts ADD COLUMN tenant_id INTEGER")
            
        conn.execute("""
            UPDATE receipts
            SET tenant_id = (
                SELECT t.id
                FROM tenants t
                WHERE lower(trim(t.name)) = lower(trim(receipts.tenant))
                LIMIT 1
            )
            WHERE tenant_id IS NULL
        """)
        
        conn.execute("CREATE INDEX IF NOT EXISTS idx_receipts_tenant_id ON receipts(tenant_id)")
        
        set_schema_version(conn, "receipt", 1)
        logger.info("Receipt migration v1 complete")
