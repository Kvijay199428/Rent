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
            ('tenant_schema_version', '3');

        -- 2. ADMINS
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            totp_secret TEXT,
            email TEXT,
            is_platform_admin INTEGER NOT NULL DEFAULT 0,
            telegram_chat_id TEXT,
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
            status_changed_at TEXT,
            qr_key TEXT,
            tenant_username TEXT,
            password_hash TEXT,
            password_failed_attempts INTEGER NOT NULL DEFAULT 0,
            password_locked_until TEXT,
            password_reset_token_hash TEXT,
            password_reset_expires_at TEXT,
            password_reset_requested_at TEXT,
            password_reset_required INTEGER NOT NULL DEFAULT 0,
            last_password_change_at TEXT
        );

        -- Portal auth support tables (tenant password history + reset events)
        CREATE TABLE IF NOT EXISTS tenant_password_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenantId INTEGER NOT NULL,
            password_hash TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            changed_by TEXT,
            FOREIGN KEY (tenantId) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_tenant_password_history_tenantId
            ON tenant_password_history(tenantId);

        CREATE TABLE IF NOT EXISTS tenant_password_reset_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenantId INTEGER NOT NULL,
            channel TEXT NOT NULL DEFAULT 'landlord',
            token_hash TEXT,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            used_at TEXT,
            requested_ip TEXT,
            FOREIGN KEY (tenantId) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_tenant_password_reset_tenantId
            ON tenant_password_reset_events(tenantId);

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
            updated_at TEXT NOT NULL,
            totp_secret TEXT,
            totp_enabled INTEGER NOT NULL DEFAULT 0,
            privacy_consented INTEGER NOT NULL DEFAULT 1,
            privacy_version TEXT,
            privacy_accepted_at TEXT,
            privacy_accepted_ip TEXT,
            privacy_accepted_user_agent TEXT
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

        # ─── Tenant portal auth + QR key columns ────────────────────────
        for col, ddl in [
            ("qr_key", "ALTER TABLE tenants ADD COLUMN qr_key TEXT"),
            ("tenant_username", "ALTER TABLE tenants ADD COLUMN tenant_username TEXT"),
            ("password_hash", "ALTER TABLE tenants ADD COLUMN password_hash TEXT"),
            ("password_failed_attempts", "ALTER TABLE tenants ADD COLUMN password_failed_attempts INTEGER NOT NULL DEFAULT 0"),
            ("password_locked_until", "ALTER TABLE tenants ADD COLUMN password_locked_until TEXT"),
            ("password_reset_token_hash", "ALTER TABLE tenants ADD COLUMN password_reset_token_hash TEXT"),
            ("password_reset_expires_at", "ALTER TABLE tenants ADD COLUMN password_reset_expires_at TEXT"),
            ("password_reset_requested_at", "ALTER TABLE tenants ADD COLUMN password_reset_requested_at TEXT"),
            ("password_reset_required", "ALTER TABLE tenants ADD COLUMN password_reset_required INTEGER NOT NULL DEFAULT 0"),
            ("last_password_change_at", "ALTER TABLE tenants ADD COLUMN last_password_change_at TEXT"),
        ]:
            if not _column_exists(conn, "tenants", col):
                conn.execute(ddl)
                conn.commit()

        # Legacy tenants tables predate status_changed_at; the app reads it in load_tenants.
        if not _column_exists(conn, "tenants", "status_changed_at"):
            conn.execute("ALTER TABLE tenants ADD COLUMN status_changed_at TEXT")
            conn.commit()

        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tenants_tenant_username ON tenants(tenant_username) WHERE tenant_username IS NOT NULL AND tenant_username != ''")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tenants_qr_key ON tenants(qr_key)")
        conn.commit()

        # Backfill qr_key for existing tenants (idempotent)
        conn.execute("UPDATE tenants SET qr_key = lower(hex(randomblob(16))) WHERE qr_key IS NULL OR qr_key = ''")
        conn.commit()

        # ─── Tenant schema drift reconciliation ───────────────────────
        # Legacy DBs created these tables with snake_case tenant_id, but the
        # canonical schema (and all application SQL) uses tenantId. Rename
        # the legacy column in place (data-preserving, idempotent).
        for _tbl in ("tenant_sessions", "tenant_audit_logs"):
            if (
                _column_exists(conn, _tbl, "tenant_id")
                and not _column_exists(conn, _tbl, "tenantId")
            ):
                conn.execute(f"ALTER TABLE {_tbl} RENAME COLUMN tenant_id TO tenantId")
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

        # Backfill: assign landlord_id to unassigned rows.
        # Receipts/occupants take the landlord of their tenant; tenants and any
        # still-unassigned receipts/occupants fall back to the first landlord.
        first_landlord = conn.execute("SELECT id FROM landlord_accounts ORDER BY id LIMIT 1").fetchone()
        lid = first_landlord["id"] if first_landlord else None

        if lid:
            conn.execute("UPDATE tenants SET landlord_id = ? WHERE landlord_id IS NULL", (lid,))

        conn.execute(
            """
            UPDATE receipts SET landlord_id = (
                SELECT landlord_id FROM tenants WHERE tenants.id = receipts.tenantId
            )
            WHERE landlord_id IS NULL
              AND tenantId IN (SELECT id FROM tenants WHERE landlord_id IS NOT NULL)
            """
        )
        # Some legacy DBs created occupants with snake_case tenant_id; the
        # canonical schema (and this backfill) uses tenantId. Pick whichever
        # column the table actually has so the backfill works on both.
        occupants_id_col = "tenant_id" if _column_exists(conn, "occupants", "tenant_id") else "tenantId"
        conn.execute(
            f"""
            UPDATE occupants SET landlord_id = (
                SELECT landlord_id FROM tenants WHERE tenants.id = occupants.{occupants_id_col}
            )
            WHERE landlord_id IS NULL
              AND {occupants_id_col} IN (SELECT id FROM tenants WHERE landlord_id IS NOT NULL)
            """
        )
        if lid:
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

        # ─── Landlord brute-force columns ────────────────────────────
        if not _column_exists(conn, "landlord_accounts", "failed_attempts"):
            conn.execute(
                "ALTER TABLE landlord_accounts ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "locked_until"):
            conn.execute(
                "ALTER TABLE landlord_accounts ADD COLUMN locked_until TEXT"
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

        # ─── Platform admin Telegram OTP columns ───────────────────────
        # Linked Telegram chat_id used to deliver login OTPs. Captured via
        # the Settings UI "Link Telegram" flow (admins.telegram_chat_id).
        if not _column_exists(conn, "admins", "telegram_chat_id"):
            conn.execute("ALTER TABLE admins ADD COLUMN telegram_chat_id TEXT")
            conn.commit()

        # ─── Platform admin login OTPs ─────────────────────────────────
        # Single-use, expiring OTP codes for the Telegram 2FA flow.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_login_otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                otp_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_admin_login_otps_admin "
                     "ON admin_login_otps(admin_id, used)")
        conn.commit()

        # ─── Tenant audit logs: add meta_json column ──
        if not _column_exists(conn, "tenant_audit_logs", "meta_json"):
            conn.execute("ALTER TABLE tenant_audit_logs ADD COLUMN meta_json TEXT")
            conn.commit()

        # ─── Google OAuth columns for landlord_accounts ────────────────
        if not _column_exists(conn, "landlord_accounts", "google_sub"):
            # SQLite cannot ADD COLUMN with UNIQUE; add plain and enforce
            # uniqueness with a partial index (matches fresh-schema UNIQUE).
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN google_sub TEXT")
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_landlord_accounts_google_sub "
                "ON landlord_accounts(google_sub) WHERE google_sub IS NOT NULL AND google_sub != ''"
            )
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "auth_provider"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN auth_provider TEXT NOT NULL DEFAULT 'email'")
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "avatar_url"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN avatar_url TEXT")
            conn.commit()

        # ─── Landlord TOTP columns (landlord_login reads them unconditionally) ──
        if not _column_exists(conn, "landlord_accounts", "totp_secret"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN totp_secret TEXT")
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "totp_enabled"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN totp_enabled INTEGER NOT NULL DEFAULT 0")
            conn.commit()

        # ─── Landlord privacy-policy consent columns ────────────────────────
        # Existing accounts are grandfathered as consenting (default 1) so the
        # upgrade does not lock out current landlords. New signups set this
        # explicitly from the accepted Privacy Policy; Google-created accounts
        # start at 0 until the consent step completes.
        if not _column_exists(conn, "landlord_accounts", "privacy_consented"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN privacy_consented INTEGER NOT NULL DEFAULT 1")
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "privacy_version"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN privacy_version TEXT")
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "privacy_accepted_at"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN privacy_accepted_at TEXT")
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "privacy_accepted_ip"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN privacy_accepted_ip TEXT")
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "privacy_accepted_user_agent"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN privacy_accepted_user_agent TEXT")
            conn.commit()

        # ─── Landlord privacy-consent audit trail ──────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS landlord_privacy_consents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                landlord_id INTEGER NOT NULL,
                privacy_version TEXT NOT NULL,
                accepted INTEGER NOT NULL DEFAULT 1,
                accepted_at TEXT NOT NULL,
                accepted_ip TEXT,
                accepted_user_agent TEXT,
                FOREIGN KEY (landlord_id) REFERENCES landlord_accounts(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_landlord_privacy_consents_landlord "
                     "ON landlord_privacy_consents(landlord_id)")
        conn.commit()

        # ─── Landlord terms-and-conditions consent columns ────────────────
        # Existing accounts are grandfathered as consenting (default 1) so the
        # upgrade does not lock out current landlords. New signups set this
        # explicitly from the accepted Terms and Conditions.
        if not _column_exists(conn, "landlord_accounts", "terms_consented"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN terms_consented INTEGER NOT NULL DEFAULT 1")
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "terms_version"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN terms_version TEXT")
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "terms_accepted_at"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN terms_accepted_at TEXT")
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "terms_accepted_ip"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN terms_accepted_ip TEXT")
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "terms_accepted_user_agent"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN terms_accepted_user_agent TEXT")
            conn.commit()

        # ─── Landlord terms consent audit trail ───────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS landlord_terms_consents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                landlord_id INTEGER NOT NULL,
                terms_version TEXT NOT NULL,
                accepted INTEGER NOT NULL DEFAULT 1,
                accepted_at TEXT NOT NULL,
                accepted_ip TEXT,
                accepted_user_agent TEXT,
                FOREIGN KEY (landlord_id) REFERENCES landlord_accounts(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_landlord_terms_consents_landlord "
                     "ON landlord_terms_consents(landlord_id)")
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

        # ─── Landlord properties (setup wizard + property-first billing) ──
        conn.execute("""
            CREATE TABLE IF NOT EXISTS landlord_properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                landlord_id INTEGER NOT NULL REFERENCES landlord_accounts(id) ON DELETE CASCADE,
                property_name TEXT NOT NULL,
                address TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_landlord_properties_landlord "
                     "ON landlord_properties(landlord_id, sort_order)")
        conn.commit()

        # ─── Landlord profile (per-landlord "landlord" config section) ──
        conn.execute("""
            CREATE TABLE IF NOT EXISTS landlord_profiles (
                landlord_id INTEGER PRIMARY KEY REFERENCES landlord_accounts(id) ON DELETE CASCADE,
                config_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()

        # ─── Landlord setup-wizard columns ─────────────────────────────
        if not _column_exists(conn, "landlord_accounts", "setup_completed"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN setup_completed INTEGER NOT NULL DEFAULT 0")
            conn.commit()
        if not _column_exists(conn, "landlord_accounts", "setup_skipped"):
            conn.execute("ALTER TABLE landlord_accounts ADD COLUMN setup_skipped INTEGER NOT NULL DEFAULT 0")
            conn.commit()

        # ─── tenants.property_id (property membership) ────────────────
        if not _column_exists(conn, "tenants", "property_id"):
            conn.execute("ALTER TABLE tenants ADD COLUMN property_id INTEGER REFERENCES landlord_properties(id)")
            conn.commit()
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tenants_property_id ON tenants(property_id)")
        conn.commit()

        # ─── Landlord setup backfill (one-time) ───────────────────────
        # Existing landlords keep working unchanged: each landlord that has
        # tenants (or exists) gets a default "Property 1" and is marked as
        # setup-complete so the wizard only appears for NEW signups.
        backfilled = conn.execute(
            "SELECT 1 FROM app_metadata WHERE key = 'landlord_setup_backfill_v1'"
        ).fetchone()
        if not backfilled:
            from datetime import datetime as _dt
            _now = _dt.utcnow().isoformat()
            _landlords = conn.execute(
                "SELECT id FROM landlord_accounts ORDER BY id"
            ).fetchall()
            for _row in _landlords:
                _lid = _row["id"]
                _existing = conn.execute(
                    "SELECT 1 FROM landlord_properties WHERE landlord_id = ? LIMIT 1",
                    (_lid,),
                ).fetchone()
                if not _existing:
                    _cur = conn.execute(
                        "INSERT INTO landlord_properties (landlord_id, property_name, address, sort_order, created_at, updated_at) "
                        "VALUES (?, ?, '', 0, ?, ?)",
                        (_lid, "Property 1", _now, _now),
                    )
                    _pid = _cur.lastrowid
                    conn.execute(
                        "UPDATE tenants SET property_id = ? WHERE landlord_id = ? AND property_id IS NULL",
                        (_pid, _lid),
                    )
            conn.execute(
                "UPDATE landlord_accounts SET setup_completed = 1, updated_at = ? WHERE setup_completed = 0",
                (_now,),
            )
            conn.execute(
                "INSERT OR REPLACE INTO app_metadata(key, value) VALUES ('landlord_setup_backfill_v1', 'done')"
            )
            conn.commit()

        # ─── tenants.property_id backfill v2 ───────────────────────────
        # v1 only assigned a property to tenants of landlords that had no
        # property yet. Tenants of landlords who already had one (setup
        # wizard, earlier data) were left NULL, which would 403 the
        # property-scoped portal deep link. Assign the landlord's first
        # property to every tenant still missing one.
        prop_filled = conn.execute(
            "SELECT 1 FROM app_metadata WHERE key = 'tenant_property_id_backfill_v2'"
        ).fetchone()
        if not prop_filled:
            conn.execute(
                """
                UPDATE tenants
                SET property_id = (
                    SELECT lp.id FROM landlord_properties lp
                    WHERE lp.landlord_id = tenants.landlord_id
                    ORDER BY lp.sort_order, lp.id LIMIT 1
                )
                WHERE property_id IS NULL AND landlord_id IS NOT NULL
                """
            )
            conn.execute(
                "INSERT OR REPLACE INTO app_metadata(key, value) VALUES ('tenant_property_id_backfill_v2', 'done')"
            )
            conn.commit()

        # ─── Tenant QR feedback (wrong qrKey reports to platform admin) ──
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tenant_qr_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER,
                landlord_id INTEGER,
                property_id INTEGER,
                tenant_name TEXT,
                view_token TEXT,
                qr_key TEXT,
                message TEXT,
                diagnostics_json TEXT,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'open',
                admin_reply TEXT,
                resolved_at TEXT,
                resolved_by INTEGER,
                created_at TEXT NOT NULL,
                ip_address TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tenant_qr_feedback_status "
                     "ON tenant_qr_feedback(status, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tenant_qr_feedback_landlord "
                     "ON tenant_qr_feedback(landlord_id)")
        conn.commit()

        # ─── Payment entries (transaction-level source of truth) ───────
        # receipts.amountreceived remains the derived cumulative value:
        #     amountreceived == SUM(payment_entries.amount WHERE status='ACTIVE')
        # This is a separate table so every individual payment transaction is
        # preserved while the existing billing/arrears engine keeps reading the
        # single amountreceived column.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payment_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                billNo TEXT NOT NULL,
                tenantId INTEGER NOT NULL,
                landlord_id TEXT,
                payment_date TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                created_by TEXT,
                updated_by TEXT,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                payment_type TEXT NOT NULL DEFAULT 'BILL',
                source TEXT NOT NULL DEFAULT 'MANUAL',
                FOREIGN KEY (billNo) REFERENCES receipts(billNo) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_entries_bill "
                     "ON payment_entries(billNo)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_entries_tenant "
                     "ON payment_entries(tenantId)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_entries_date "
                     "ON payment_entries(payment_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_entries_landlord "
                     "ON payment_entries(landlord_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_entries_status "
                     "ON payment_entries(status)")
        conn.commit()

        # ─── Payment allocations (settlement ledger) ────────────────────
        # Connects each payment transaction to the bills it actually cleared.
        # A payment recorded against the current bill can economically clear
        # earlier arrears; allocation_type records the split:
        #     CURRENT_BILL | ARREAR | ADVANCE
        # This separates HISTORICAL bill payment status (a bill may stay
        # 'PARTIAL' as a matter of record) from the tenant's CURRENT outstanding
        # balance (Σ current charges − Σ payments, never double-counting arrears
        # carried into later bills' previous_arrears).
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payment_allocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_entry_id INTEGER NOT NULL,
                tenant_id INTEGER NOT NULL,
                bill_no TEXT NOT NULL,
                allocated_amount REAL NOT NULL,
                allocation_type TEXT NOT NULL DEFAULT 'CURRENT_BILL',
                created_at TEXT NOT NULL,
                FOREIGN KEY (payment_entry_id) REFERENCES payment_entries(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_allocations_tenant "
                     "ON payment_allocations(tenant_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_allocations_bill "
                     "ON payment_allocations(tenant_id, bill_no)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_allocations_payment "
                     "ON payment_allocations(payment_entry_id)")
        conn.commit()

        # ─── Receipts: settlement fields ────────────────────────────────
        # Mark how/when a historical bill's unpaid balance was later settled
        # by a payment recorded on a subsequent (current) bill, without
        # rewriting the bill's original paymentstatus.
        if not _column_exists(conn, "receipts", "settled_by_bill_no"):
            conn.execute("ALTER TABLE receipts ADD COLUMN settled_by_bill_no TEXT")
            conn.commit()
        if not _column_exists(conn, "receipts", "settlement_type"):
            conn.execute("ALTER TABLE receipts ADD COLUMN settlement_type TEXT NOT NULL DEFAULT 'NONE'")
            conn.commit()
        if not _column_exists(conn, "receipts", "settled_at"):
            conn.execute("ALTER TABLE receipts ADD COLUMN settled_at TEXT")
            conn.commit()
        if not _column_exists(conn, "receipts", "settlement_amount"):
            conn.execute("ALTER TABLE receipts ADD COLUMN settlement_amount REAL NOT NULL DEFAULT 0")
            conn.commit()

        # ─── Legacy amountReceived backfill into payment_entries ───────
        # One-time, idempotent: only runs if payment_entries is empty and there
        # are existing receipts with amountreceived > 0. Each legacy receipt
        # becomes a single LEGACY_MIGRATION entry stamped with today's date (the
        # landlord can later correct the actual paid date + amount per
        # paymentId), so the invariant amountreceived == SUM(active entries)
        # holds going forward.
        payment_backfilled = conn.execute(
            "SELECT 1 FROM app_metadata WHERE key = 'payment_entries_backfill_v1'"
        ).fetchone()
        if not payment_backfilled:
            entries_exist = conn.execute(
                "SELECT 1 FROM payment_entries LIMIT 1"
            ).fetchone()
            if not entries_exist:
                legacy_rows = conn.execute(
                    "SELECT billNo, tenantId, landlord_id, date, amountreceived "
                    "FROM receipts WHERE amountreceived > 0"
                ).fetchall()
                for _p in legacy_rows:
                    # Legacy payments are stamped with today's date so the
                    # landlord can open each bill, see the carried-over payment,
                    # and correct the actual paid date + amount per paymentId.
                    conn.execute(
                        """
                        INSERT INTO payment_entries
                            (billNo, tenantId, landlord_id, payment_date, amount,
                             created_at, updated_at, created_by, status,
                             payment_type, source)
                        VALUES (?, ?, ?, date('now'), ?, datetime('now'), datetime('now'),
                                'LEGACY_MIGRATION', 'ACTIVE', 'BILL', 'LEGACY_MIGRATION')
                        """,
                        (
                            _p["billNo"],
                            _p["tenantId"],
                            _p["landlord_id"],
                            float(_p["amountreceived"] or 0),
                        ),
                    )
            conn.execute(
                "INSERT OR REPLACE INTO app_metadata(key, value) VALUES "
                "('payment_entries_backfill_v1', 'done')"
            )
            conn.commit()

        # Reconciliation: databases that already ran v1 with the receipt date
        # keep carried-over LEGACY_MIGRATION entries at today's date so the
        # landlord can open each bill, see the payment, and correct the actual
        # paid date + amount per paymentId. Runs every boot; idempotent and does
        # not change the amountreceived SUM (the arrears engine is unaffected).
        conn.execute(
            "UPDATE payment_entries "
            "SET payment_date = date('now'), updated_at = datetime('now'), "
            "updated_by = 'LEGACY_MIGRATION_RECONCILE' "
            "WHERE source = 'LEGACY_MIGRATION' AND status = 'ACTIVE'"
        )
        conn.commit()

        # ─── Seed payment allocations / settlement markers ────────────
        # Backfill the settlement ledger for existing tenants. Runs once
        # (key-guarded, idempotent). Recomputes each tenant's allocation and
        # settlement markers from the current receipts + payment_entries state.
        alloc_backfilled = conn.execute(
            "SELECT 1 FROM app_metadata WHERE key = 'payment_allocations_backfill_v1'"
        ).fetchone()
        if not alloc_backfilled:
            try:
                from app.services.payment_service import _recompute_tenant_settlement
                tids = [r["id"] for r in conn.execute("SELECT id FROM tenants").fetchall()]
                for _tid in tids:
                    try:
                        _recompute_tenant_settlement(conn, _tid)
                    except Exception:
                        pass
                conn.commit()
            except Exception:
                conn.rollback()
            conn.execute(
                "INSERT OR REPLACE INTO app_metadata(key, value) VALUES "
                "('payment_allocations_backfill_v1', 'done')"
            )
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