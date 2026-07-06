import os
import csv
import shutil
from app.core.paths import DB_DIR
from app.core.db import get_conn, init_db

TENANTS_CSV = os.path.join(DB_DIR, "tenants.csv")
RECEIPTS_CSV = os.path.join(DB_DIR, "receipts.csv")
OCCUPANTS_CSV = os.path.join(DB_DIR, "occupants.csv")

def _safe_float(val, default=0.0):
    try:
        return float(str(val).strip() or default)
    except Exception:
        return default

def _safe_int(val, default=0):
    try:
        return int(float(str(val).strip() or default))
    except Exception:
        return default

def migrate():
    print("Ensuring SQLite schema exists...")
    init_db()

    with get_conn() as conn:
        if os.path.exists(TENANTS_CSV):
            print(f"Migrating {TENANTS_CSV}...")
            with open(TENANTS_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # In V1 CSV, the columns might have been named things like "Rent", "Maintenance", "Water", "Tank_Water".
                    # We map them to the new schema:
                    conn.execute('''
                        INSERT OR IGNORE INTO tenants (
                            id, name, company, phone, email, address, roomnumber, occupation,
                            notes, status, rent, water, electricityrate, previousmeter,
                            additionalpersoncharge, securitydeposit, defaulttankwatercharge,
                            meterid, viewtoken, tenantpin
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        _safe_int(row.get("ID")), row.get("Name", ""), row.get("Company", ""), 
                        row.get("Phone", ""), row.get("Email", ""), row.get("Address", ""), 
                        row.get("Room_Number", ""), row.get("Occupation", ""), row.get("Notes", ""), 
                        row.get("Status", "Active"), _safe_float(row.get("Rent")), 
                        _safe_float(row.get("Water")), _safe_float(row.get("Electricity_Rate")), 
                        _safe_float(row.get("Previous_Meter", row.get("Previous", 0.0))), 
                        _safe_float(row.get("Additional_Person_Rate")), _safe_float(row.get("Deposit", row.get("Security_Deposit", 0.0))), 
                        _safe_float(row.get("Tank_Water", row.get("Default_Tank_Water_Charge", 0.0))), 
                        row.get("Meter_ID", ""), row.get("View_Token", ""), row.get("Tenant_Pin", "1234")
                    ))
            shutil.move(TENANTS_CSV, TENANTS_CSV + ".archived")
            print("Tenants migrated and archived.")

        if os.path.exists(OCCUPANTS_CSV):
            print(f"Migrating {OCCUPANTS_CSV}...")
            with open(OCCUPANTS_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    conn.execute('''
                        INSERT OR IGNORE INTO occupants (
                            tenant_id, occupant_uuid, name, mobile, status, aadhaar_front, aadhaar_back, 
                            aadhaar_combined, emp_front, emp_back, uploaddate, uploadmonth
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        _safe_int(row.get("tenant_id")), row.get("uuid", ""), row.get("name", ""), 
                        row.get("mobile", row.get("phone", "")), row.get("status", "Active"), 
                        row.get("aadhaar_front", ""), row.get("aadhaar_back", ""), 
                        row.get("aadhaar_combined", ""), row.get("emp_front", ""), 
                        row.get("emp_back", ""), row.get("uploaddate", row.get("joined", "")), 
                        row.get("uploadmonth", "")
                    ))
            shutil.move(OCCUPANTS_CSV, OCCUPANTS_CSV + ".archived")
            print("Occupants migrated and archived.")

        if os.path.exists(RECEIPTS_CSV):
            print(f"Migrating {RECEIPTS_CSV}...")
            with open(RECEIPTS_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    conn.execute('''
                        INSERT OR IGNORE INTO receipts (
                            billno, date, month, tenant, previous, current, units, rent,
                            additional, water, tankwater, electricity, total, pdf,
                            tenantphone, tenantcompany, tenantaddress, rate, status,
                            archiveddate, archivedby, deleteddate, additionalpersons,
                            additionalpersonrate, receiptversion, generatedby, paymentstatus,
                            maintenancecharge, maintenancedesc, previousarrears, amountreceived
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row.get("Bill"), row.get("Date", ""), row.get("Month", ""), row.get("Tenant", ""),
                        _safe_float(row.get("Previous")), _safe_float(row.get("Current")), _safe_float(row.get("Units")),
                        _safe_float(row.get("Rent")), _safe_float(row.get("Additional")), _safe_float(row.get("Water")),
                        _safe_float(row.get("Tank_Water")), _safe_float(row.get("Electricity")), _safe_float(row.get("Total")),
                        row.get("PDF", ""), row.get("Tenant_Phone", ""), row.get("Tenant_Company", ""), row.get("Tenant_Address", ""),
                        _safe_float(row.get("Rate")), row.get("Status", "ACTIVE"), row.get("Archived_Date", ""),
                        row.get("Archived_By", ""), row.get("Deleted_Date", ""), _safe_int(row.get("Additional_Persons")),
                        _safe_float(row.get("Additional_Person_Rate")), _safe_int(row.get("Receipt_Version", 8)),
                        row.get("Generated_By", "Admin"), row.get("Payment_Status", "PENDING"),
                        _safe_float(row.get("Maintenance_Charge")), row.get("Maintenance_Desc", ""),
                        _safe_float(row.get("Previous_Arrears")), _safe_float(row.get("Amount_Received"))
                    ))
            shutil.move(RECEIPTS_CSV, RECEIPTS_CSV + ".archived")
            print("Receipts migrated and archived.")
        
        conn.commit()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
