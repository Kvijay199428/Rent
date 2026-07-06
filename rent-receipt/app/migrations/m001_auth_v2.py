from app.migrations.manager import get_schema_version, set_schema_version
import logging

logger = logging.getLogger(__name__)

def run(conn):
    version = get_schema_version(conn, "auth")
    if version < 1:
        logger.info("Running Auth migration v1: Dropping old session tables for Auth V2")
        # In development, it is safe to drop sessions. 
        # In production, you would migrate them, but since we are dropping
        # it will just force a re-login.
        conn.execute("DROP TABLE IF EXISTS admin_sessions")
        conn.execute("DROP TABLE IF EXISTS tenant_sessions")
        
        set_schema_version(conn, "auth", 1)
        logger.info("Auth migration v1 complete")
