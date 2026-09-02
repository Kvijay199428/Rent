"""
Migration 001: Consolidated PostgreSQL schema for PROPAURA.

Faithful port of the canonical SQLite schema (backend/app/app/database/
final_schema.py consolidated with every ALTER TABLE ADD COLUMN applied by
core/db.py init_db). Type mapping:

    SQLite                        PostgreSQL
    INTEGER PRIMARY KEY AUTOINCR  BIGSERIAL PRIMARY KEY
    INTEGER (boolean 0/1)         INTEGER            (app reads/writes 0/1)
    REAL                          DOUBLE PRECISION
    TEXT                          TEXT

ISO-8601 timestamps are stored as TEXT exactly as the application produces
them, so existing code paths behave identically.

Data backfills that depend on application logic (qr_key, payment_entries
legacy migration, settlement recompute, default admin seed) live in a later
seed migration, not here.
"""


def up(conn):
    cur = conn.cursor()

    # ---- 1. APP METADATA (schema version tracking) ----------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_metadata (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # ---- 2. ADMINS -------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id                 BIGSERIAL PRIMARY KEY,
            username           TEXT UNIQUE NOT NULL,
            password_hash      TEXT NOT NULL,
            totp_secret        TEXT,
            email              TEXT,
            is_platform_admin  INTEGER NOT NULL DEFAULT 0,
            telegram_chat_id   TEXT,
            failed_attempts    INTEGER NOT NULL DEFAULT 0,
            locked_until       TEXT,
            created_at         TEXT,
            updated_at         TEXT
        )
    """)

    # ---- 3. ADMIN LOGIN OTPS (Telegram 2FA) ------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_login_otps (
            id         BIGSERIAL PRIMARY KEY,
            admin_id   INTEGER NOT NULL,
            otp_hash   TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            attempts   INTEGER NOT NULL DEFAULT 0,
            used       INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_admin_login_otps_admin ON admin_login_otps(admin_id, used)")

    # ---- 4. ADMIN SESSIONS ----------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_sessions (
            session_id         TEXT PRIMARY KEY,
            admin_id           INTEGER NOT NULL,
            refresh_token_hash TEXT NOT NULL,
            device_name        TEXT,
            browser            TEXT,
            os                 TEXT,
            ip_address         TEXT,
            created_at         TEXT,
            last_activity      TEXT,
            expires_at         TEXT,
            revoked_at         TEXT,
            remember_me        INTEGER DEFAULT 0,
            status             TEXT DEFAULT 'Active',
            FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
        )
    """)

    # ---- 5. TENANTS ------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id                          BIGSERIAL PRIMARY KEY,
            name                        TEXT NOT NULL,
            company                     TEXT,
            phone                       TEXT,
            email                       TEXT,
            address                     TEXT,
            roomnumber                  TEXT,
            occupation                  TEXT,
            notes                       TEXT,
            status                      TEXT NOT NULL DEFAULT 'Active',
            rent                        DOUBLE PRECISION NOT NULL DEFAULT 0,
            water                       DOUBLE PRECISION NOT NULL DEFAULT 0,
            electricityrate             DOUBLE PRECISION NOT NULL DEFAULT 0,
            previousmeter               DOUBLE PRECISION NOT NULL DEFAULT 0,
            additionalpersoncharge      DOUBLE PRECISION NOT NULL DEFAULT 0,
            securitydeposit             DOUBLE PRECISION NOT NULL DEFAULT 0,
            defaulttankWatercharge      DOUBLE PRECISION NOT NULL DEFAULT 0,
            meterid                     TEXT,
            viewToken                   TEXT,
            tenantpin                   TEXT,
            failed_attempts             INTEGER NOT NULL DEFAULT 0,
            locked_until                TEXT,
            status_changed_at           TEXT,
            qr_key                      TEXT,
            tenant_username             TEXT,
            password_hash               TEXT,
            password_failed_attempts    INTEGER NOT NULL DEFAULT 0,
            password_locked_until       TEXT,
            password_reset_token_hash   TEXT,
            password_reset_expires_at   TEXT,
            password_reset_requested_at TEXT,
            password_reset_required     INTEGER NOT NULL DEFAULT 0,
            last_password_change_at     TEXT,
            landlord_id                 INTEGER REFERENCES landlord_accounts(id),
            property_id                 INTEGER REFERENCES landlord_properties(id)
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_tenants_qr_key ON tenants(qr_key)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tenants_landlord_id ON tenants(landlord_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tenants_property_id ON tenants(property_id)")
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_tenants_tenant_username
        ON tenants(tenant_username)
        WHERE tenant_username IS NOT NULL AND tenant_username <> ''
    """)

    # ---- 6. TENANT PASSWORD HISTORY --------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenant_password_history (
            id            BIGSERIAL PRIMARY KEY,
            tenantId      INTEGER NOT NULL,
            password_hash TEXT NOT NULL,
            changed_at    TEXT NOT NULL,
            changed_by    TEXT,
            FOREIGN KEY (tenantId) REFERENCES tenants(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tenant_password_history_tenantId ON tenant_password_history(tenantId)")

    # ---- 7. TENANT PASSWORD RESET EVENTS ---------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenant_password_reset_events (
            id          BIGSERIAL PRIMARY KEY,
            tenantId    INTEGER NOT NULL,
            channel     TEXT NOT NULL DEFAULT 'landlord',
            token_hash  TEXT,
            created_at  TEXT NOT NULL,
            expires_at  TEXT,
            used_at     TEXT,
            requested_ip TEXT,
            FOREIGN KEY (tenantId) REFERENCES tenants(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tenant_password_reset_tenantId ON tenant_password_reset_events(tenantId)")

    # ---- 8. TENANT PIN HISTORY -------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenantPin_history (
            id         BIGSERIAL PRIMARY KEY,
            tenantId   INTEGER NOT NULL,
            pin_hash   TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            FOREIGN KEY (tenantId) REFERENCES tenants(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tenantPin_history_tenantId ON tenantPin_history(tenantId)")

    # ---- 9. TENANT PIN ADMIN STORE ---------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenantPin_admin_store (
            tenantId      INTEGER PRIMARY KEY,
            encrypted_pin TEXT NOT NULL,
            updated_at    TEXT NOT NULL,
            FOREIGN KEY (tenantId) REFERENCES tenants(id) ON DELETE CASCADE
        )
    """)

    # ---- 10. TENANT SESSIONS ---------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenant_sessions (
            session_id         TEXT PRIMARY KEY,
            tenantId           INTEGER NOT NULL,
            refresh_token_hash TEXT NOT NULL,
            device_name        TEXT,
            browser            TEXT,
            os                 TEXT,
            ip_address         TEXT,
            created_at         TEXT,
            last_activity      TEXT,
            expires_at         TEXT,
            revoked_at         TEXT,
            remember_me        INTEGER DEFAULT 0,
            status             TEXT DEFAULT 'Active',
            FOREIGN KEY (tenantId) REFERENCES tenants(id) ON DELETE CASCADE
        )
    """)

    # ---- 11. TENANT AUDIT LOGS -------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenant_audit_logs (
            id         BIGSERIAL PRIMARY KEY,
            tenantId   INTEGER,
            action     TEXT,
            ip_address TEXT,
            created_at TEXT,
            meta_json  TEXT
        )
    """)

    # ---- 12. RECEIPTS ----------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id                   BIGSERIAL NOT NULL UNIQUE,
            billNo               TEXT PRIMARY KEY,
            date                 TEXT NOT NULL,
            month                TEXT NOT NULL,
            tenantId             INTEGER,
            tenant               TEXT NOT NULL,
            property_id          INTEGER REFERENCES landlord_properties(id),
            previous             DOUBLE PRECISION NOT NULL DEFAULT 0,
            current              DOUBLE PRECISION NOT NULL DEFAULT 0,
            units                DOUBLE PRECISION NOT NULL DEFAULT 0,
            rent                 DOUBLE PRECISION NOT NULL DEFAULT 0,
            additional           DOUBLE PRECISION NOT NULL DEFAULT 0,
            water                DOUBLE PRECISION NOT NULL DEFAULT 0,
            tankWater            DOUBLE PRECISION NOT NULL DEFAULT 0,
            electricity          DOUBLE PRECISION NOT NULL DEFAULT 0,
            total                DOUBLE PRECISION NOT NULL DEFAULT 0,
            pdf                  TEXT,
            tenantphone          TEXT,
            tenantcompany        TEXT,
            tenantaddress        TEXT,
            rate                 DOUBLE PRECISION NOT NULL DEFAULT 0,
            status               TEXT NOT NULL DEFAULT 'ACTIVE',
            archiveddate         TEXT,
            archivedby           TEXT,
            deleteddate          TEXT,
            additionalpersons    INTEGER NOT NULL DEFAULT 0,
            additionalpersonrate DOUBLE PRECISION NOT NULL DEFAULT 0,
            receiptversion       INTEGER NOT NULL DEFAULT 8,
            generatedby          TEXT NOT NULL DEFAULT 'Admin',
            paymentstatus        TEXT NOT NULL DEFAULT 'PENDING',
            maintenancecharge    DOUBLE PRECISION NOT NULL DEFAULT 0,
            maintenancedesc      TEXT,
            previousarrears      DOUBLE PRECISION NOT NULL DEFAULT 0,
            amountreceived       DOUBLE PRECISION NOT NULL DEFAULT 0,
            landlord_id          INTEGER REFERENCES landlord_accounts(id),
            settled_by_bill_no   TEXT,
            settlement_type      TEXT NOT NULL DEFAULT 'NONE',
            settled_at           TEXT,
            settlement_amount    DOUBLE PRECISION NOT NULL DEFAULT 0
        )
    """)

    # ---- 13. PAYMENT ENTRIES ---------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payment_entries (
            id           BIGSERIAL PRIMARY KEY,
            billNo       TEXT NOT NULL,
            tenantId     INTEGER NOT NULL,
            landlord_id  TEXT,
            payment_date TEXT NOT NULL,
            amount       DOUBLE PRECISION NOT NULL,
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL,
            created_by   TEXT,
            updated_by   TEXT,
            status       TEXT NOT NULL DEFAULT 'ACTIVE',
            payment_type TEXT NOT NULL DEFAULT 'BILL',
            source       TEXT NOT NULL DEFAULT 'MANUAL',
            FOREIGN KEY (billNo) REFERENCES receipts(billNo) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_payment_entries_bill ON payment_entries(billNo)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_payment_entries_tenant ON payment_entries(tenantId)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_payment_entries_date ON payment_entries(payment_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_payment_entries_landlord ON payment_entries(landlord_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_payment_entries_status ON payment_entries(status)")

    # ---- 14. PAYMENT ALLOCATIONS ------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payment_allocations (
            id               BIGSERIAL PRIMARY KEY,
            payment_entry_id INTEGER NOT NULL,
            tenant_id        INTEGER NOT NULL,
            bill_no          TEXT NOT NULL,
            allocated_amount DOUBLE PRECISION NOT NULL,
            allocation_type  TEXT NOT NULL DEFAULT 'CURRENT_BILL',
            created_at       TEXT NOT NULL,
            FOREIGN KEY (payment_entry_id) REFERENCES payment_entries(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_payment_allocations_tenant ON payment_allocations(tenant_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_payment_allocations_bill ON payment_allocations(tenant_id, bill_no)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_payment_allocations_payment ON payment_allocations(payment_entry_id)")

    # ---- 15. OCCUPANTS -----------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS occupants (
            id             BIGSERIAL NOT NULL UNIQUE,
            tenantId       INTEGER NOT NULL,
            occupantUuid   TEXT PRIMARY KEY,
            name           TEXT,
            mobile         TEXT,
            address        TEXT,
            residentSince  TEXT,
            status         TEXT NOT NULL DEFAULT 'Active',
            aadhaar_front  TEXT,
            aadhaar_back   TEXT,
            aadhaar_combined TEXT,
            emp_front      TEXT,
            emp_back       TEXT,
            uploaddate     TEXT,
            uploadmonth    TEXT,
            landlord_id    INTEGER REFERENCES landlord_accounts(id),
            FOREIGN KEY (tenantId) REFERENCES tenants(id) ON DELETE CASCADE
        )
    """)

    # ---- 16. TENANT QR FEEDBACK -------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenant_qr_feedback (
            id              BIGSERIAL PRIMARY KEY,
            tenant_id       INTEGER,
            landlord_id     INTEGER,
            property_id     INTEGER,
            tenant_name     TEXT,
            view_token      TEXT,
            qr_key          TEXT,
            message         TEXT,
            diagnostics_json TEXT,
            failed_attempts INTEGER NOT NULL DEFAULT 0,
            status          TEXT NOT NULL DEFAULT 'open',
            admin_reply     TEXT,
            resolved_at     TEXT,
            resolved_by     INTEGER,
            created_at      TEXT NOT NULL,
            ip_address      TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tenant_qr_feedback_status ON tenant_qr_feedback(status, created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tenant_qr_feedback_landlord ON tenant_qr_feedback(landlord_id)")

    # ---- 17. IMPORT JOBS ----------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS import_jobs (
            id             BIGSERIAL PRIMARY KEY,
            created_at     TEXT NOT NULL,
            created_by     TEXT NOT NULL,
            filename       TEXT NOT NULL,
            status         TEXT NOT NULL,
            preview_json   TEXT,
            resolution_json TEXT,
            result_json    TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS import_job_items (
            id               BIGSERIAL PRIMARY KEY,
            import_job_id    INTEGER NOT NULL,
            target_key       TEXT NOT NULL,
            import_tenant_id TEXT,
            import_tenant_name TEXT,
            action           TEXT NOT NULL,
            existing_tenant_id INTEGER,
            result           TEXT NOT NULL,
            message          TEXT,
            FOREIGN KEY (import_job_id) REFERENCES import_jobs(id) ON DELETE CASCADE
        )
    """)

    # ---- 18. TENANT RECOVERY SNAPSHOTS -------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenant_recovery_snapshots (
            id            TEXT PRIMARY KEY,
            tenant_id     INTEGER NOT NULL,
            tenant_name   TEXT NOT NULL,
            created_at    TEXT NOT NULL,
            expires_at    TEXT NOT NULL,
            deleted_by    INTEGER,
            status        TEXT NOT NULL DEFAULT 'AVAILABLE',
            archive_path  TEXT NOT NULL,
            sha256        TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            restored_at   TEXT,
            purged_at     TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tenant_recovery_expiry ON tenant_recovery_snapshots(expires_at, status)")

    # ---- 19. LANDLORD ACCOUNTS ----------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS landlord_accounts (
            id                        BIGSERIAL PRIMARY KEY,
            landlord_uuid             TEXT UNIQUE NOT NULL,
            full_name                 TEXT NOT NULL,
            email                     TEXT UNIQUE,
            phone                     TEXT,
            username                  TEXT UNIQUE NOT NULL,
            password_hash             TEXT NOT NULL,
            status                    TEXT NOT NULL DEFAULT 'Active',
            created_at                TEXT NOT NULL,
            updated_at                TEXT NOT NULL,
            totp_secret               TEXT,
            totp_enabled              INTEGER NOT NULL DEFAULT 0,
            privacy_consented         INTEGER NOT NULL DEFAULT 1,
            privacy_version           TEXT,
            privacy_accepted_at       TEXT,
            privacy_accepted_ip       TEXT,
            privacy_accepted_user_agent TEXT,
            requires_password_change  INTEGER NOT NULL DEFAULT 0,
            temp_password_created_at  TEXT,
            temp_password_consumed    INTEGER NOT NULL DEFAULT 0,
            failed_attempts           INTEGER NOT NULL DEFAULT 0,
            locked_until              TEXT,
            google_sub                TEXT,
            auth_provider             TEXT NOT NULL DEFAULT 'email',
            avatar_url                TEXT,
            terms_consented           INTEGER NOT NULL DEFAULT 1,
            terms_version             TEXT,
            terms_accepted_at         TEXT,
            terms_accepted_ip         TEXT,
            terms_accepted_user_agent TEXT,
            setup_completed           INTEGER NOT NULL DEFAULT 0,
            setup_skipped             INTEGER NOT NULL DEFAULT 0
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_landlord_accounts_username ON landlord_accounts(username)")
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_landlord_accounts_google_sub
        ON landlord_accounts(google_sub)
        WHERE google_sub IS NOT NULL AND google_sub <> ''
    """)

    # ---- 20. LANDLORD SESSIONS -----------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS landlord_sessions (
            session_id         TEXT PRIMARY KEY,
            landlord_id        INTEGER NOT NULL,
            refresh_token_hash TEXT NOT NULL,
            device_name        TEXT,
            browser            TEXT,
            os                 TEXT,
            ip_address         TEXT,
            created_at         TEXT NOT NULL,
            last_activity      TEXT NOT NULL,
            expires_at         TEXT NOT NULL,
            revoked_at         TEXT,
            remember_me        INTEGER DEFAULT 0,
            status             TEXT DEFAULT 'Active',
            FOREIGN KEY (landlord_id) REFERENCES landlord_accounts(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_landlord_sessions_landlord_id ON landlord_sessions(landlord_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_landlord_sessions_status ON landlord_sessions(status)")

    # ---- 21. LANDLORD AUDIT LOGS ---------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS landlord_audit_logs (
            id          BIGSERIAL PRIMARY KEY,
            landlord_id INTEGER,
            action      TEXT NOT NULL,
            ip_address  TEXT,
            created_at  TEXT NOT NULL,
            meta_json   TEXT,
            FOREIGN KEY (landlord_id) REFERENCES landlord_accounts(id) ON DELETE SET NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_landlord_audit_logs_landlord_id ON landlord_audit_logs(landlord_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_landlord_audit_logs_action ON landlord_audit_logs(action)")

    # ---- 22. LANDLORD UI CONFIG -----------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS landlord_ui_config (
            landlorduuid TEXT PRIMARY KEY,
            theme        TEXT NOT NULL DEFAULT 'system',
            updated_at   TEXT NOT NULL
        )
    """)

    # ---- 23. LEGACY LANDLORDS PROXY TABLE -------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS landlords (
            id           BIGSERIAL PRIMARY KEY,
            admin_id     INTEGER NOT NULL,
            landlordUuid TEXT UNIQUE NOT NULL,
            active       INTEGER DEFAULT 1,
            FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_landlords_uuid ON landlords(landlordUuid)")

    # ---- 24. LANDLORD PROPERTIES ------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS landlord_properties (
            id            BIGSERIAL PRIMARY KEY,
            landlord_id   INTEGER NOT NULL REFERENCES landlord_accounts(id) ON DELETE CASCADE,
            property_name TEXT NOT NULL,
            address       TEXT NOT NULL DEFAULT '',
            sort_order    INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL,
            updated_at    TEXT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_landlord_properties_landlord ON landlord_properties(landlord_id, sort_order)")

    # ---- 25. LANDLORD PROFILES ----------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS landlord_profiles (
            landlord_id INTEGER PRIMARY KEY REFERENCES landlord_accounts(id) ON DELETE CASCADE,
            config_json TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
    """)

    # ---- 26. LANDLORD PRIVACY CONSENTS ---------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS landlord_privacy_consents (
            id                BIGSERIAL PRIMARY KEY,
            landlord_id       INTEGER NOT NULL,
            privacy_version   TEXT NOT NULL,
            accepted          INTEGER NOT NULL DEFAULT 1,
            accepted_at       TEXT NOT NULL,
            accepted_ip       TEXT,
            accepted_user_agent TEXT,
            FOREIGN KEY (landlord_id) REFERENCES landlord_accounts(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_landlord_privacy_consents_landlord ON landlord_privacy_consents(landlord_id)")

    # ---- 27. LANDLORD TERMS CONSENTS ---------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS landlord_terms_consents (
            id                BIGSERIAL PRIMARY KEY,
            landlord_id       INTEGER NOT NULL,
            terms_version     TEXT NOT NULL,
            accepted          INTEGER NOT NULL DEFAULT 1,
            accepted_at       TEXT NOT NULL,
            accepted_ip       TEXT,
            accepted_user_agent TEXT,
            FOREIGN KEY (landlord_id) REFERENCES landlord_accounts(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_landlord_terms_consents_landlord ON landlord_terms_consents(landlord_id)")

    # ---- 28. LANDLORD PASSWORD ADMIN STORE ------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS landlord_password_admin_store (
            landlord_id        INTEGER PRIMARY KEY,
            encrypted_password TEXT NOT NULL,
            updated_at         TEXT NOT NULL,
            FOREIGN KEY (landlord_id) REFERENCES landlord_accounts(id) ON DELETE CASCADE
        )
    """)

    # ---- 29. PLATFORM ADMIN AUDIT LOGS -----------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS platform_admin_audit_logs (
            id          BIGSERIAL PRIMARY KEY,
            admin_id    INTEGER NOT NULL,
            action      TEXT NOT NULL,
            target_type TEXT,
            target_id   INTEGER,
            ip_address  TEXT,
            meta_json   TEXT,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_platform_audit_admin ON platform_admin_audit_logs(admin_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_platform_audit_action ON platform_admin_audit_logs(action)")

    # ---- 30. PERFORMANCE INDEXES ------------------------------------------------------
    cur.execute("CREATE INDEX IF NOT EXISTS idx_receipts_tenant ON receipts(tenant)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_receipts_status ON receipts(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_receipts_paymentstatus ON receipts(paymentstatus)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_receipts_tenantId ON receipts(tenantId)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_occupants_tenantId ON occupants(tenantId)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_receipts_landlord_id ON receipts(landlord_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_occupants_landlord_id ON occupants(landlord_id)")

    # ---- 31. INITIAL METADATA -------------------------------------------------------------
    cur.execute(
        "INSERT INTO app_metadata (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING",
        ("tenant_schema_version", "3"),
    )

    conn.commit()


def down(conn):
    cur = conn.cursor()
    tables = [
        "landlords",
        "landlord_ui_config",
        "landlord_password_admin_store",
        "landlord_profiles",
        "landlord_properties",
        "landlord_terms_consents",
        "landlord_privacy_consents",
        "landlord_audit_logs",
        "landlord_sessions",
        "landlord_accounts",
        "tenant_recovery_snapshots",
        "tenant_qr_feedback",
        "platform_admin_audit_logs",
        "occupants",
        "payment_allocations",
        "payment_entries",
        "receipts",
        "tenant_audit_logs",
        "tenant_sessions",
        "tenantPin_admin_store",
        "tenantPin_history",
        "tenant_password_reset_events",
        "tenant_password_history",
        "tenants",
        "admin_sessions",
        "admin_login_otps",
        "admins",
        "import_job_items",
        "import_jobs",
        "app_metadata",
    ]
    for t in tables:
        cur.execute(f'DROP TABLE IF EXISTS "{t}" CASCADE')
    conn.commit()
