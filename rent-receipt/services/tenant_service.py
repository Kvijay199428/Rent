import csv
import os
import shutil
from models.tenant import Tenant

DB_DIR = "database"
os.makedirs(DB_DIR, exist_ok=True)

TENANTS_CSV = os.path.join(DB_DIR, "tenants.csv")
BACKUP_DIR = "backups"

HEADERS = [
    "ID", "Tenant Name", "Company", "Phone", "Email", 
    "Permanent Address", "Room Number", "Occupation", "Notes", "Status"
]

def init_csv():
    if not os.path.exists(TENANTS_CSV):
        with open(TENANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)

def load_tenants():
    init_csv()
    tenants = []
    try:
        with open(TENANTS_CSV, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Map CSV keys to Tenant alias keys
                t = Tenant(
                    id=int(row["ID"]) if row["ID"] else None,
                    name=row["Tenant Name"],
                    company=row["Company"],
                    phone=row["Phone"],
                    email=row["Email"],
                    address=row["Permanent Address"],
                    room_number=row["Room Number"],
                    occupation=row["Occupation"],
                    notes=row["Notes"],
                    status=row["Status"]
                )
                tenants.append(t)
    except Exception as e:
        print(f"Error loading tenants: {e}")
    return tenants

def save_all_tenants(tenants_list):
    init_csv()
    # Backup
    if os.path.exists(TENANTS_CSV):
        backup_path = os.path.join(BACKUP_DIR, "tenants.csv.bak")
        try:
            shutil.copy2(TENANTS_CSV, backup_path)
        except Exception:
            pass
            
    try:
        with open(TENANTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
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
                    "Status": t.status
                }
                writer.writerow(row)
    except Exception as e:
        print(f"Error saving tenants: {e}")

def add_tenant(t: Tenant):
    tenants = load_tenants()
    # Find next ID
    next_id = 1
    if tenants:
        next_id = max(x.id for x in tenants if x.id is not None) + 1
    t.id = next_id
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

def delete_tenant(tenant_id: int):
    tenants = load_tenants()
    tenants = [t for t in tenants if t.id != tenant_id]
    save_all_tenants(tenants)
