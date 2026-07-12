-- ============================================================
-- FINAL PRODUCTION DATABASE SCHEMA
-- Rent Receipt System v3.0.0
-- Generated: 2026-07-11
-- ============================================================

-- Enable WAL mode for better concurrency
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 30000000000;
PRAGMA foreign_keys = ON;

-- ============================================================
-- 1. APP METADATA (Schema Version Tracking)
-- ============================================================
CREATE TABLE IF NOT EXISTS app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

INSERT OR REPLACE INTO app_metadata (key, value) VALUES 
    ('auth_schema_version', '1'),
    ('receipt_schema_version', '1'),
    ('tenant_schema_version', '2');

-- ============================================================
-- 2. ADMINS (Admin User Management with TOTP)
-- ============================================================
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    totp_secret TEXT,
    email TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- ============================================================
-- 3. ADMIN SESSIONS (Auth V2)
-- ============================================================
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

-- ============================================================
-- 4. TENANTS (Core Tenant Data with Security)
-- ============================================================
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
    defaulttankwatercharge REAL NOT NULL DEFAULT 0,
    meterid TEXT,
    view_token TEXT,
    tenantpin TEXT,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT
);

-- ============================================================
-- 5. TENANT PIN HISTORY (Security Audit)
-- ============================================================
CREATE TABLE IF NOT EXISTS tenant_pin_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    pin_hash TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tenant_pin_history_tenant_id 
    ON tenant_pin_history(tenant_id);

-- ============================================================
-- 6. TENANT PIN ADMIN STORE (Encrypted PIN Vault)
-- ============================================================
CREATE TABLE IF NOT EXISTS tenant_pin_admin_store (
    tenant_id INTEGER PRIMARY KEY,
    encrypted_pin TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- ============================================================
-- 7. TENANT SESSIONS (Auth V2)
-- ============================================================
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

-- ============================================================
-- 8. TENANT AUDIT LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS tenant_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER,
    action TEXT,
    ip_address TEXT,
    created_at TEXT
);

-- ============================================================
-- 9. RECEIPTS (Core Billing Data)
-- ============================================================
CREATE TABLE IF NOT EXISTS receipts (
    billno TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    month TEXT NOT NULL,
    tenant_id INTEGER,
    tenant TEXT NOT NULL,
    previous REAL NOT NULL DEFAULT 0,
    current REAL NOT NULL DEFAULT 0,
    units REAL NOT NULL DEFAULT 0,
    rent REAL NOT NULL DEFAULT 0,
    additional REAL NOT NULL DEFAULT 0,
    water REAL NOT NULL DEFAULT 0,
    tankwater REAL NOT NULL DEFAULT 0,
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

-- ============================================================
-- 10. OCCUPANTS (KYC Data)
-- ============================================================
CREATE TABLE IF NOT EXISTS occupants (
    tenant_id INTEGER NOT NULL,
    occupant_uuid TEXT PRIMARY KEY,
    name TEXT,
    mobile TEXT,
    status TEXT NOT NULL DEFAULT 'Active',
    aadhaar_front TEXT,
    aadhaar_back TEXT,
    aadhaar_combined TEXT,
    emp_front TEXT,
    emp_back TEXT,
    uploaddate TEXT,
    uploadmonth TEXT,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- ============================================================
-- 11. PERFORMANCE INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_receipts_tenant ON receipts(tenant);
CREATE INDEX IF NOT EXISTS idx_receipts_status ON receipts(status);
CREATE INDEX IF NOT EXISTS idx_receipts_paymentstatus ON receipts(paymentstatus);
CREATE INDEX IF NOT EXISTS idx_receipts_tenant_id ON receipts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_occupants_tenant_id ON occupants(tenant_id);
