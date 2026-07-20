import os
import sqlite3
from app.core.paths import DB_DIR

DB_PATH = os.path.join(DB_DIR, "rent.db")


def get_conn():
    """
    Get a SQLite connection with proper settings for production use.
    Uses WAL mode for better concurrency and enables foreign keys.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30.0)  # 30s timeout for locks
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")  # Balanced safety/performance
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA mmap_size = 30000000000;")  # Enable memory-mapped I/O
    return conn


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    """
    Check if a column exists in a table. Case-insensitive for SQLite.
    """
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        # SQLite PRAGMA returns lowercase column names, so compare case-insensitively
        return any(
            str(r["name"]).lower() == column_name.lower() for r in rows
        )
    except sqlite3.Error:
        return False


def _table_exists(conn, table_name: str) -> bool:
    """Check if a table exists in the database."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    ).fetchone()
    return row is not None


def init_db():
    """
    Initialize the core database schema. 
    This is the FINAL production schema - all migrations consolidated.
    """
    with get_conn() as conn:
        conn.executescript("""
        -- 1. APP METADATA
        CREATE TABLE IF NOT EXISTS app_metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        INSERT OR REPLACE INTO app_metadata (key, value) VALUES 
            ('auth_schema_version', '1'),
            ('receipt_schema_version', '1'),
            ('tenant_schema_version', '2');

        -- 2. ADMINS
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            totp_secret TEXT,
            email TEXT,
            created_at TEXT,
            updated_at TEXT
        );

        -- 3. ADMIN SESSIONS (Auth V2)
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

        -- 4. TENANTS (with viewToken, tenantpin, failed_attempts, locked_until)
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            company TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            roomnumber TEXT,
            occupation TEXT,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'Active',
            rent REAL NOT NULL DEFAULT 0,
            water REAL NOT NULL DEFAULT 0,
            electricityrate REAL NOT NULL DEFAULT 0,
            previousmeter REAL NOT NULL DEFAULT 0,
            additionalpersoncharge REAL NOT NULL DEFAULT 0,
            securitydeposit REAL NOT NULL DEFAULT 0,
            defaulttankWatercharge REAL NOT NULL DEFAULT 0,
            meterid TEXT,
            viewToken TEXT,
            tenantpin TEXT,
            failed_attempts INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT
        );

        -- 5. TENANT PIN HISTORY
        CREATE TABLE IF NOT EXISTS tenantPin_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenantId INTEGER NOT NULL,
            pin_hash TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            FOREIGN KEY (tenantId) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_tenantPin_history_tenantId 
            ON tenantPin_history(tenantId);

        -- 6. TENANT PIN ADMIN STORE
        CREATE TABLE IF NOT EXISTS tenantPin_admin_store (
            tenantId INTEGER PRIMARY KEY,
            encrypted_pin TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (tenantId) REFERENCES tenants(id) ON DELETE CASCADE
        );

        -- 7. TENANT SESSIONS (Auth V2)
        CREATE TABLE IF NOT EXISTS tenant_sessions (
            session_id TEXT PRIMARY KEY,
            tenantId INTEGER NOT NULL,
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
            FOREIGN KEY (tenantId) REFERENCES tenants(id) ON DELETE CASCADE
        );

        -- 8. TENANT AUDIT LOGS
        CREATE TABLE IF NOT EXISTS tenant_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenantId INTEGER,
            action TEXT,
            ip_address TEXT,
            created_at TEXT
        );

        -- 9. RECEIPTS (with tenantId, paymentstatus, maintenance, arrears, amountreceived)
        CREATE TABLE IF NOT EXISTS receipts (
            billNo TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            month TEXT NOT NULL,
            tenantId INTEGER,
            tenant TEXT NOT NULL,
            previous REAL NOT NULL DEFAULT 0,
            current REAL NOT NULL DEFAULT 0,
            units REAL NOT NULL DEFAULT 0,
            rent REAL NOT NULL DEFAULT 0,
            additional REAL NOT NULL DEFAULT 0,
            water REAL NOT NULL DEFAULT 0,
            tankWater REAL NOT NULL DEFAULT 0,
            electricity REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL DEFAULT 0,
            pdf TEXT,
            tenantphone TEXT,
            tenantcompany TEXT,
            tenantaddress TEXT,
            rate REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            archiveddate TEXT,
            archivedby TEXT,
            deleteddate TEXT,
            additionalpersons INTEGER NOT NULL DEFAULT 0,
            additionalpersonrate REAL NOT NULL DEFAULT 0,
            receiptversion INTEGER NOT NULL DEFAULT 8,
            generatedby TEXT NOT NULL DEFAULT 'Admin',
            paymentstatus TEXT NOT NULL DEFAULT 'PENDING',
            maintenancecharge REAL NOT NULL DEFAULT 0,
            maintenancedesc TEXT,
            previousarrears REAL NOT NULL DEFAULT 0,
            amountreceived REAL NOT NULL DEFAULT 0
        );

        -- 10. OCCUPANTS
        CREATE TABLE IF NOT EXISTS occupants (
            tenantId INTEGER NOT NULL,
            occupantUuid TEXT PRIMARY KEY,
            name TEXT,
            mobile TEXT,
            address TEXT,
            residentSince TEXT,
            status TEXT NOT NULL DEFAULT 'Active',
            aadhaar_front TEXT,
            aadhaar_back TEXT,
            aadhaar_combined TEXT,
            emp_front TEXT,
            emp_back TEXT,
            uploaddate TEXT,
            uploadmonth TEXT,
            FOREIGN KEY (tenantId) REFERENCES tenants(id) ON DELETE CASCADE
        );

        -- 11. PERFORMANCE INDEXES
        CREATE INDEX IF NOT EXISTS idx_receipts_tenant ON receipts(tenant);
        CREATE INDEX IF NOT EXISTS idx_receipts_status ON receipts(status);
        CREATE INDEX IF NOT EXISTS idx_receipts_paymentstatus ON receipts(paymentstatus);
        CREATE INDEX IF NOT EXISTS idx_receipts_tenantId ON receipts(tenantId);
        CREATE INDEX IF NOT EXISTS idx_occupants_tenantId ON occupants(tenantId);
        
        -- 12. IMPORT AUDIT LOGS
        CREATE TABLE IF NOT EXISTS import_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            filename TEXT NOT NULL,
            status TEXT NOT NULL,
            preview_json TEXT,
            resolution_json TEXT,
            result_json TEXT
        );

        CREATE TABLE IF NOT EXISTS import_job_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_job_id INTEGER NOT NULL,
            target_key TEXT NOT NULL,
            import_tenant_id TEXT,
            import_tenant_name TEXT,
            action TEXT NOT NULL,
            existing_tenant_id INTEGER,
            result TEXT NOT NULL,
            message TEXT,
            FOREIGN KEY (import_job_id) REFERENCES import_jobs(id) ON DELETE CASCADE
        );

        -- 13. TENANT RECOVERY SNAPSHOTS
        -- Stores per-tenant recovery archives created before permanent deletion.
        -- Only recoverable until expires_at; after that, status = PURGED.
        CREATE TABLE IF NOT EXISTS tenant_recovery_snapshots (
            id TEXT PRIMARY KEY,
            tenant_id INTEGER NOT NULL,
            tenant_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            deleted_by INTEGER,
            status TEXT NOT NULL DEFAULT 'AVAILABLE',
            archive_path TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            restored_at TEXT,
            purged_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_tenant_recovery_expiry
            ON tenant_recovery_snapshots(expires_at, status);
        """)

        # Migrations for existing databases — safe to run multiple times
        if not _column_exists(conn, "occupants", "address"):
            conn.execute("ALTER TABLE occupants ADD COLUMN address TEXT")
        if not _column_exists(conn, "occupants", "residentSince"):
            conn.execute("ALTER TABLE occupants ADD COLUMN residentSince TEXT")

        conn.commit()