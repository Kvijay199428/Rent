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
            is_platform_admin INTEGER NOT NULL DEFAULT 0,
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
            locked_until TEXT,
            status_changed_at TEXT
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
        CREATE INDEX IF NOT EXISTS idx_occupants_tenant_id ON occupants(tenantId);
        
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

        -- 14. LANDLORD ACCOUNTS (created before migrations so ALTER TABLE works)
        CREATE TABLE IF NOT EXISTS landlord_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            landlord_uuid TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- 15. LANDLORD SESSIONS
        CREATE TABLE IF NOT EXISTS landlord_sessions (
            session_id TEXT PRIMARY KEY,
            landlord_id INTEGER NOT NULL,
            refresh_token_hash TEXT NOT NULL,
            device_name TEXT,
            browser TEXT,
            os TEXT,
            ip_address TEXT,
            created_at TEXT NOT NULL,
            last_activity TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT,
            remember_me INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Active',
            FOREIGN KEY (landlord_id) REFERENCES landlord_accounts(id) ON DELETE CASCADE
        );

        -- 16. LANDLORD AUDIT LOGS
        CREATE TABLE IF NOT EXISTS landlord_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            landlord_id INTEGER,
            action TEXT NOT NULL,
            ip_address TEXT,
            created_at TEXT NOT NULL,
            meta_json TEXT,
            FOREIGN KEY (landlord_id) REFERENCES landlord_accounts(id) ON DELETE SET NULL
        );

        -- Landlord indexes
        CREATE INDEX IF NOT EXISTS idx_landlord_accounts_username
            ON landlord_accounts(username);
        CREATE INDEX IF NOT EXISTS idx_landlord_accounts_email
            ON landlord_accounts(email);
        CREATE INDEX IF NOT EXISTS idx_landlord_sessions_landlord_id
            ON landlord_sessions(landlord_id);
        CREATE INDEX IF NOT EXISTS idx_landlord_sessions_status
            ON landlord_sessions(status);
        CREATE INDEX IF NOT EXISTS idx_landlord_audit_logs_landlord_id
            ON landlord_audit_logs(landlord_id);
        CREATE INDEX IF NOT EXISTS idx_landlord_audit_logs_action
            ON landlord_audit_logs(action);

        -- 17. LANDLORD UI CONFIG (per-landlord theme storage)
        CREATE TABLE IF NOT EXISTS landlord_ui_config (
            landlorduuid TEXT PRIMARY KEY,
            theme TEXT NOT NULL DEFAULT 'system',
            updated_at TEXT NOT NULL
        );

        -- Keep legacy landlord proxy table for landlord-alias router
        CREATE TABLE IF NOT EXISTS landlords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            landlordUuid TEXT UNIQUE NOT NULL,
            active INTEGER DEFAULT 1,
            FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_landlords_uuid ON landlords(landlordUuid);

        -- Schema version bump
        INSERT OR REPLACE INTO app_metadata(key, value) VALUES
            ('auth_schema_version', '2'),
            ('landlord_schema_version', '1');
        """)

        conn.commit()

        # ─── Migrations for existing databases ─────────────────────────
        # Add is_platform_admin column if missing (for pre-existing DBs)
        if not _column_exists(conn, "admins", "is_platform_admin"):
            conn.execute(
                "ALTER TABLE admins ADD COLUMN is_platform_admin INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()

        # ─── Multi-tenancy: Add landlord_id to core tables ──────────
        if not _column_exists(conn, "tenants", "landlord_id"):
            conn.execute("ALTER TABLE tenants ADD COLUMN landlord_id INTEGER REFERENCES landlord_accounts(id)")
            conn.commit()

        if not _column_exists(conn, "receipts", "landlord_id"):
            conn.execute("ALTER TABLE receipts ADD COLUMN landlord_id INTEGER REFERENCES landlord_accounts(id)")
            conn.commit()

        if not _column_exists(conn, "occupants", "landlord_id"):
            conn.execute("ALTER TABLE occupants ADD COLUMN landlord_id INTEGER REFERENCES landlord_accounts(id)")
            conn.commit()

        # Indexes for landlord_id lookups
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tenants_landlord_id ON tenants(landlord_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_receipts_landlord_id ON receipts(landlord_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_occupants_landlord_id ON occupants(landlord_id)")
        conn.commit()

        # Backfill: assign existing data to first landlord if unassigned
        first_landlord = conn.execute("SELECT id FROM landlord_accounts ORDER BY id LIMIT 1").fetchone()
        if first_landlord:
            lid = first_landlord["id"]
            conn.execute("UPDATE tenants SET landlord_id = ? WHERE landlord_id IS NULL", (lid,))
            conn.execute("UPDATE receipts SET landlord_id = ? WHERE landlord_id IS NULL", (lid,))
            conn.execute("UPDATE occupants SET landlord_id = ? WHERE landlord_id IS NULL", (lid,))
            conn.commit()

        # ─── Platform admin audit trail ──────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS platform_admin_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_type TEXT,
                target_id INTEGER,
                ip_address TEXT,
                meta_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_platform_audit_admin ON platform_admin_audit_logs(admin_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_platform_audit_action ON platform_admin_audit_logs(action)")
        conn.commit()

        # ─── Landlord password-change enforcement columns ──────────
        if not _column_exists(conn, "landlord_accounts", "requires_password_change"):
            conn.execute(
                "ALTER TABLE landlord_accounts ADD COLUMN requires_password_change INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "temp_password_created_at"):
            conn.execute(
                "ALTER TABLE landlord_accounts ADD COLUMN temp_password_created_at TEXT"
            )
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "temp_password_consumed"):
            conn.execute(
                "ALTER TABLE landlord_accounts ADD COLUMN temp_password_consumed INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()

        # ─── Platform admin brute-force columns ────────────────────────
        if not _column_exists(conn, "admins", "failed_attempts"):
            conn.execute(
                "ALTER TABLE admins ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
        if not _column_exists(conn, "admins", "locked_until"):
            conn.execute(
                "ALTER TABLE admins ADD COLUMN locked_until TEXT"
            )
            conn.commit()

        # ─── Tenant audit logs: add meta_json column ──
        if not _column_exists(conn, "tenant_audit_logs", "meta_json"):
            conn.execute("ALTER TABLE tenant_audit_logs ADD COLUMN meta_json TEXT")
            conn.commit()

        # ─── Google OAuth columns for landlord_accounts ────────────────
        if not _column_exists(conn, "landlord_accounts", "google_sub"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN google_sub TEXT UNIQUE")
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "auth_provider"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN auth_provider TEXT NOT NULL DEFAULT 'email'")
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "avatar_url"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN avatar_url TEXT")
            conn.commit()

        # ─── Landlord password admin store (for platform admin reveal) ──
        conn.execute("""
            CREATE TABLE IF NOT EXISTS landlord_password_admin_store (
                landlord_id INTEGER PRIMARY KEY,
                encrypted_password TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (landlord_id) REFERENCES landlord_accounts(id) ON DELETE CASCADE
            )
        """)
        conn.commit()

        # ─── Seed default platform admin ───────────────────────────────
        # Ensure at least one platform admin exists (admin/admin)
        from app.authentication.common.utils import hash_pin
        has_platform_admin = conn.execute(
            "SELECT 1 FROM admins WHERE is_platform_admin = 1 LIMIT 1"
        ).fetchone()
        if not has_platform_admin:
            conn.execute(
                """INSERT OR IGNORE INTO admins (username, password_hash, is_platform_admin, created_at)
                   SELECT 'admin', ?, 1, datetime('now')
                   WHERE NOT EXISTS (SELECT 1 FROM admins WHERE username = 'admin')""",
                (hash_pin("admin"),),
            )
            conn.commit()
