import sys
import os
import sqlite3

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))
from app.core.db import DB_PATH  # type: ignore
db_path = DB_PATH

def backfill():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if tenantId column exists
    cursor.execute("PRAGMA table_info(receipts)")
    columns = [col["name"] for col in cursor.fetchall()]
    if "tenantId" not in columns:
        print("Adding tenantId column to receipts table...")
        cursor.execute("ALTER TABLE receipts ADD COLUMN tenantId INTEGER")
        conn.commit()

    # Get all tenants
    cursor.execute("SELECT id, name FROM tenants")
    tenants = cursor.fetchall()
    tenant_map = {t["name"].lower(): t["id"] for t in tenants}

    # Get all receipts that might be missing a tenantId
    cursor.execute("SELECT billNo, tenant, tenantId FROM receipts")
    receipts = cursor.fetchall()

    updated_count = 0
    missing_count = 0

    for r in receipts:
        # If tenantId is not set, or we just want to ensure it's correct based on name
        if not r["tenantId"]:
            t_name = (r["tenant"] or "").strip().lower()
            if t_name in tenant_map:
                t_id = tenant_map[t_name]
                cursor.execute("UPDATE receipts SET tenantId = ? WHERE billNo = ?", (t_id, r["billNo"]))
                updated_count += 1
            else:
                print(f"Warning: Tenant name '{r['tenant']}' not found for bill {r['billNo']}")
                missing_count += 1

    conn.commit()
    conn.close()

    print(f"Backfill complete. Updated {updated_count} receipts. {missing_count} receipts had unresolved tenants.")

if __name__ == "__main__":
    backfill()
