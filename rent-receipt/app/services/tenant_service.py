import csv
import os
import shutil
from app.models.tenant import Tenant
from app.core.config_service import config
from app.core.paths import DB_DIR, BACKUPS_DIR as BACKUP_DIR

TENANTS_CSV = os.path.join(DB_DIR, "tenants.csv")

HEADERS_V1 = [
    "ID", "Tenant Name", "Company", "Phone", "Email", 
    "Permanent Address", "Room Number", "Occupation", "Notes", "Status"
]

HEADERS_V2 = HEADERS_V1 + [
    "Rent", "Water", "Electricity Rate", "Previous Meter", 
    "Additional Person", "Security Deposit"
]

HEADERS_V3 = HEADERS_V2 + [
    "Default Tank Water"
]

HEADERS_V4 = HEADERS_V3 + [
    "Meter ID"
]

HEADERS_V5 = HEADERS_V4 + [
    "View Token"
]

HEADERS_V6 = HEADERS_V5 + [
    "Tenant PIN"
]

CURRENT_HEADERS = HEADERS_V6

def init_csv():
    if not os.path.exists(TENANTS_CSV):
        with open(TENANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CURRENT_HEADERS)

def _migrate_database():
    if not os.path.exists(TENANTS_CSV):
        return
        
    v1_needs_migration = False
    v2_needs_migration = False
    v3_needs_migration = False
    v4_needs_migration = False
    v5_needs_migration = False
    with open(TENANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
            if "Rent" not in headers:
                v1_needs_migration = True
            if "Default Tank Water" not in headers:
                v2_needs_migration = True
            if "Meter ID" not in headers:
                v3_needs_migration = True
            if "View Token" not in headers:
                v4_needs_migration = True
            if "Tenant PIN" not in headers:
                v5_needs_migration = True
        except StopIteration:
            return

    if v1_needs_migration or v2_needs_migration or v3_needs_migration or v4_needs_migration or v5_needs_migration:
        print("Migrating tenants database schema...")
        old_rows = []
        with open(TENANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_rows.append(row)
                
        billing_conf = config.get("billing", {})
        
        def safe_float(val):
            try:
                return float(str(val).strip() or 0.0)
            except:
                return 0.0
                
        default_rent = safe_float(billing_conf.get("rent", 0.0) or billing_conf.get("default_rent", 0.0))
        default_water = safe_float(billing_conf.get("water", 0.0) or billing_conf.get("default_water", 0.0))
        default_rate = safe_float(billing_conf.get("electricity_rate", 0.0) or billing_conf.get("default_rate", 0.0))
        default_prev = safe_float(billing_conf.get("previous_meter_reading", 0.0) or 0.0)
        default_add = safe_float(billing_conf.get("additional_person_charge", 0.0) or billing_conf.get("default_additional_person_charge", 0.0))
        
        backup_path = os.path.join(BACKUP_DIR, "tenants_migration.csv.bak")
        try:
            shutil.copy2(TENANTS_CSV, backup_path)
        except Exception:
            pass
            
        with open(TENANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CURRENT_HEADERS)
            writer.writeheader()
            for row in old_rows:
                if v1_needs_migration:
                    row["Rent"] = default_rent
                    row["Water"] = default_water
                    row["Electricity Rate"] = default_rate
                    row["Previous Meter"] = default_prev
                    row["Additional Person"] = default_add
                    row["Security Deposit"] = 0.0
                if v2_needs_migration:
                    row["Default Tank Water"] = 0.0
                if v3_needs_migration:
                    row["Meter ID"] = ""
                if v4_needs_migration:
                    row["View Token"] = ""
                if v5_needs_migration:
                    row["Tenant PIN"] = "1234"
                writer.writerow(row)
                
        print("Migration complete.")

def load_tenants():
    init_csv()
    _migrate_database()
    
    tenants = []
    try:
        with open(TENANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                def safe_float(val):
                    try:
                        return float(str(val).strip() or 0.0)
                    except:
                        return 0.0
                        
                t = Tenant(
                    id=int(row["ID"]) if row.get("ID") else None,
                    name=row.get("Tenant Name", ""),
                    company=row.get("Company", ""),
                    phone=row.get("Phone", ""),
                    email=row.get("Email", ""),
                    address=row.get("Permanent Address", ""),
                    room_number=row.get("Room Number", ""),
                    occupation=row.get("Occupation", ""),
                    notes=row.get("Notes", ""),
                    status=row.get("Status", "Active"),
                    rent=safe_float(row.get("Rent")),
                    water=safe_float(row.get("Water")),
                    electricity_rate=safe_float(row.get("Electricity Rate")),
                    previous_meter=safe_float(row.get("Previous Meter")),
                    additional_person_charge=safe_float(row.get("Additional Person")),
                    security_deposit=safe_float(row.get("Security Deposit")),
                    default_tank_water_charge=safe_float(row.get("Default Tank Water")),
                    meter_id=row.get("Meter ID", ""),
                    view_token=row.get("View Token", ""),
                    tenant_pin=row.get("Tenant PIN", "1234")
                )
                tenants.append(t)
    except Exception as e:
        print(f"Error loading tenants: {e}")
    return tenants

def save_all_tenants(tenants_list):
    init_csv()
    if os.path.exists(TENANTS_CSV):
        backup_path = os.path.join(BACKUP_DIR, "tenants.csv.bak")
        try:
            shutil.copy2(TENANTS_CSV, backup_path)
        except Exception:
            pass
            
    try:
        with open(TENANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CURRENT_HEADERS)
            writer.writeheader()
            for t in tenants_list:
                row = {
                    "ID": t.id,
                    "Tenant Name": t.name,
                    "Company": t.company,
                    "Phone": t.phone,
                    "Email": t.email,
                    "Permanent Address": t.address,
                    "Room Number": t.room_number,
                    "Occupation": t.occupation,
                    "Notes": t.notes,
                    "Status": t.status,
                    "Rent": t.rent,
                    "Water": t.water,
                    "Electricity Rate": t.electricity_rate,
                    "Previous Meter": t.previous_meter,
                    "Additional Person": t.additional_person_charge,
                    "Security Deposit": t.security_deposit,
                    "Default Tank Water": t.default_tank_water_charge,
                    "Meter ID": t.meter_id,
                    "View Token": getattr(t, "view_token", ""),
                    "Tenant PIN": getattr(t, "tenant_pin", "1234")
                }
                writer.writerow(row)
    except Exception as e:
        print(f"Error saving tenants: {e}")

def add_tenant(t: Tenant):
    tenants = load_tenants()
    next_id = 1
    if tenants:
        next_id = max(x.id for x in tenants if x.id is not None) + 1
    t.id = next_id
    
    # --- NEW: Auto-generate Meter ID if left blank ---
    if not t.meter_id:
        t.meter_id = f"MTR - F - {str(next_id).zfill(2)}"
        
    tenants.append(t)
    save_all_tenants(tenants)
    return t

def update_tenant(t: Tenant):
    tenants = load_tenants()
    for idx, item in enumerate(tenants):
        if item.id == t.id:
            tenants[idx] = t
            break
    save_all_tenants(tenants)
    return t

def delete_tenant(tenant_id: int, action: str = "archive"):
    tenants = load_tenants()
    target_tenant = next((t for t in tenants if t.id == tenant_id), None)
    if not target_tenant:
        return
        
    from app.services.billing_service import get_all_receipts, archive_bill, delete_bill
    receipts = get_all_receipts()
    tenant_receipts = [r for r in receipts if r["Tenant"] == target_tenant.name]
    
    if action == "archive":
        target_tenant.status = "Inactive"
        update_tenant(target_tenant)
        # Archive all associated receipts
        for r in tenant_receipts:
            if r.get("Status") != "ARCHIVED":
                try:
                    archive_bill(r["Bill"])
                except Exception:
                    pass
                    
    elif action == "delete":
        # Force delete all associated receipts
        for r in tenant_receipts:
            # We must archive it first to bypass the safety check in delete_bill
            if r.get("Status") != "ARCHIVED":
                try:
                    archive_bill(r["Bill"])
                except Exception:
                    pass
            try:
                delete_bill(r["Bill"])
            except Exception:
                pass
        
        # Remove tenant completely
        tenants = [t for t in tenants if t.id != tenant_id]
        save_all_tenants(tenants)

# --- OCCUPANT / KYC MANAGEMENT ---
OCCUPANTS_CSV = os.path.join(DB_DIR, "occupants.csv")
OCC_HEADERS = [
    "Tenant ID", "Occupant UUID", "Name", "Mobile", "Status",
    "Aadhaar Front", "Aadhaar Back", "Aadhaar Combined", "Emp Front", "Emp Back",
    "Upload_Date", "Upload_Month"
]

def init_occupants_csv():
    if not os.path.exists(OCCUPANTS_CSV):
        with open(OCCUPANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(OCC_HEADERS)

def get_occupants(tenant_id: int):
    init_occupants_csv()
    occupants = []
    try:
        with open(OCCUPANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if str(row["Tenant ID"]) == str(tenant_id):
                    if not row.get("Upload_Month"):
                        row["Upload_Month"] = "Legacy Uploads"
                    occupants.append(row)
    except Exception as e:
        print(f"Error loading occupants: {e}")
    return occupants

def save_occupant(tenant_id: int, occ_data: dict):
    init_occupants_csv()
    all_rows = []
    updated = False
    
    with open(OCCUPANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Occupant UUID"] == occ_data["uuid"]:
                for key in occ_data:
                    if key in OCC_HEADERS or key in row:
                        row[key] = occ_data[key]
                updated = True
            all_rows.append(row)
            
    if not updated:
        new_row = {
            "Tenant ID": tenant_id,
            "Occupant UUID": occ_data["uuid"],
            "Name": occ_data["Name"],
            "Mobile": occ_data["Mobile"],
            "Status": occ_data.get("Status", "Active"),
            "Aadhaar Front": occ_data.get("Aadhaar Front", ""),
            "Aadhaar Back": occ_data.get("Aadhaar Back", ""),
            "Aadhaar Combined": occ_data.get("Aadhaar Combined", ""),
            "Emp Front": occ_data.get("Emp Front", ""),
            "Emp Back": occ_data.get("Emp Back", ""),
            "Upload_Date": occ_data.get("Upload_Date", ""),
            "Upload_Month": occ_data.get("Upload_Month", "")
        }
        all_rows.append(new_row)
        
    with open(OCCUPANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=OCC_HEADERS)
        writer.writeheader()
        writer.writerows(all_rows)

def update_occupant_status(occupant_uuid: str, status: str):
    init_occupants_csv()
    all_rows = []
    with open(OCCUPANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Occupant UUID"] == occupant_uuid:
                row["Status"] = status
            all_rows.append(row)
            
    with open(OCCUPANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=OCC_HEADERS)
        writer.writeheader()
        writer.writerows(all_rows)

def delete_occupant(occupant_uuid: str):
    init_occupants_csv()
    all_rows = []
    with open(OCCUPANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Occupant UUID"] != occupant_uuid:
                all_rows.append(row)
                
    with open(OCCUPANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=OCC_HEADERS)
        writer.writeheader()
        writer.writerows(all_rows)
