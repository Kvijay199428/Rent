import os
import sqlite3
from app.core.paths import DB_DIR

DB_PATH = os.path.join(DB_DIR, "rent.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def _column_exists(conn, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(r["name"] == column_name for r in rows)


def init_db():
    with get_conn() as conn:
        conn.executescript("""
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
            viewtoken TEXT,
            tenantpin TEXT
        );

        CREATE TABLE IF NOT EXISTS receipts (
            billno TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            month TEXT NOT NULL,
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

        CREATE INDEX IF NOT EXISTS idx_receipts_tenant ON receipts(tenant);
        CREATE INDEX IF NOT EXISTS idx_receipts_status ON receipts(status);
        CREATE INDEX IF NOT EXISTS idx_receipts_paymentstatus ON receipts(paymentstatus);
        CREATE INDEX IF NOT EXISTS idx_occupants_tenant_id ON occupants(tenant_id);
        """)
        conn.commit()