import csv
import os
import shutil
from datetime import datetime
from app.core.config_service import config
from app.services.tenant_service import load_tenants, update_tenant
from app.services.pdf_service import generate_professional_pdf

from app.core.paths import DB_DIR, BACKUPS_DIR as BACKUP_DIR, RECEIPTS_DIR

RECEIPTS_CSV = os.path.join(DB_DIR, "receipts.csv")

HEADERS = [
    "Bill", "Date", "Month", "Tenant", "Previous", "Current", 
    "Units", "Rent", "Additional", "Water", "Tank_Water", "Electricity", "Total", "PDF",
    "Tenant_Phone", "Tenant_Company", "Tenant_Address", "Rate",
    "Status", "Archived_Date", "Archived_By", "Deleted_Date",
    "Additional_Persons", "Additional_Person_Rate", "Receipt_Version", "Generated_By",
    "Payment_Status", "Maintenance_Charge", "Maintenance_Desc",
    "Previous_Arrears", "Amount_Received" # --- NEW COLUMNS ---
]

def migrate_receipts_schema():
    schema_conf = config.get("schema", {})
    current_version = schema_conf.get("receipt_schema", 1)
    
    if current_version < 2:
        # V1 to V2 Migration: Add lifecycle columns
        print("Migrating receipts.csv from V1 to V2...")
        if os.path.exists(RECEIPTS_CSV):
            receipts = []
            try:
                with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["Status"] = "ACTIVE"
                        row["Archived_Date"] = ""
                        row["Archived_By"] = ""
                        row["Deleted_Date"] = ""
                        receipts.append(row)
                
                backup_path = os.path.join(BACKUP_DIR, "receipts_v1_migration.bak")
                shutil.copy2(RECEIPTS_CSV, backup_path)
                
                with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(receipts)
                    
                print("Migrating PDFs to active directory structure...")
                for row in receipts:
                    try:
                        year_str = row["Month"].split()[-1]
                    except Exception:
                        year_str = datetime.now().strftime("%Y")
                    
                    old_pdf_path = os.path.join(RECEIPTS_DIR, year_str, row["PDF"])
                    new_dir = os.path.join(RECEIPTS_DIR, "active", year_str)
                    new_pdf_path = os.path.join(new_dir, row["PDF"])
                    
                    if os.path.exists(old_pdf_path):
                        os.makedirs(new_dir, exist_ok=True)
                        shutil.move(old_pdf_path, new_pdf_path)
            except Exception as e:
                print(f"Error migrating receipts to V2: {e}")
        
        schema_conf["receipt_schema"] = 2
        config.save("schema", schema_conf)

    if current_version < 3:
        # V2 to V3 Migration: Add Additional_Persons, Additional_Person_Rate, Receipt_Version
        print("Migrating receipts.csv from V2 to V3...")
        if os.path.exists(RECEIPTS_CSV):
            receipts = []
            try:
                with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["Additional_Persons"] = "0"
                        row["Additional_Person_Rate"] = "0.0"
                        row["Receipt_Version"] = "3"
                        receipts.append(row)
                        
                backup_path = os.path.join(BACKUP_DIR, "receipts_v2_migration.bak")
                shutil.copy2(RECEIPTS_CSV, backup_path)
                
                with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(receipts)
            except Exception as e:
                print(f"Error migrating receipts to V3: {e}")
                
        schema_conf["receipt_schema"] = 3
        config.save("schema", schema_conf)
        current_version = 3

    if current_version < 4:
        # V3 to V4 Migration: Add Tank_Water and Generated_By
        print("Migrating receipts.csv from V3 to V4...")
        if os.path.exists(RECEIPTS_CSV):
            receipts = []
            try:
                with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["Tank_Water"] = "0.0"
                        row["Generated_By"] = "Admin"
                        row["Receipt_Version"] = "4"
                        receipts.append(row)
                        
                backup_path = os.path.join(BACKUP_DIR, "receipts_v3_migration.bak")
                shutil.copy2(RECEIPTS_CSV, backup_path)
                
                with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(receipts)
            except Exception as e:
                print(f"Error migrating receipts to V4: {e}")
                
        schema_conf["receipt_schema"] = 4
        config.save("schema", schema_conf)
        current_version = 4

    if current_version < 5:
        # V4 to V5 Migration: Bump Receipt_Version for Bank Details layout
        print("Migrating receipts.csv from V4 to V5...")
        if os.path.exists(RECEIPTS_CSV):
            receipts = []
            try:
                with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["Receipt_Version"] = "5"
                        receipts.append(row)
                        
                backup_path = os.path.join(BACKUP_DIR, "receipts_v4_migration.bak")
                shutil.copy2(RECEIPTS_CSV, backup_path)
                
                with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(receipts)
            except Exception as e:
                print(f"Error migrating receipts to V5: {e}")
                
        schema_conf["receipt_schema"] = 5
        config.save("schema", schema_conf)
        current_version = 5

    if current_version < 6:
        # V5 to V6 Migration: Add Payment_Status column
        print("Migrating receipts.csv from V5 to V6...")
        if os.path.exists(RECEIPTS_CSV):
            receipts = []
            try:
                with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["Payment_Status"] = "PENDING"
                        receipts.append(row)
                        
                backup_path = os.path.join(BACKUP_DIR, "receipts_v5_migration.bak")
                shutil.copy2(RECEIPTS_CSV, backup_path)
                
                with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(receipts)
            except Exception as e:
                print(f"Error migrating receipts to V6: {e}")
                
        schema_conf["receipt_schema"] = 6
        config.save("schema", schema_conf)
        current_version = 6

    if current_version < 7:
        # V6 to V7 Migration: Add Maintenance_Charge and Maintenance_Desc
        print("Migrating receipts.csv from V6 to V7...")
        if os.path.exists(RECEIPTS_CSV):
            receipts = []
            try:
                with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["Maintenance_Charge"] = "0.0"
                        row["Maintenance_Desc"] = ""
                        receipts.append(row)
                        
                backup_path = os.path.join(BACKUP_DIR, "receipts_v6_migration.bak")
                shutil.copy2(RECEIPTS_CSV, backup_path)
                
                with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(receipts)
            except Exception as e:
                print(f"Error migrating receipts to V7: {e}")
                
        schema_conf["receipt_schema"] = 7
        config.save("schema", schema_conf)
        current_version = 7

    if current_version < 8:
        # V7 to V8 Migration: Add Previous_Arrears and Amount_Received columns
        print("Migrating receipts.csv from V7 to V8 (Arrears & Payments)...")
        if os.path.exists(RECEIPTS_CSV):
            receipts = []
            try:
                with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["Previous_Arrears"] = "0.0"
                        # Assume historically that all total bills were fully received.
                        row["Amount_Received"] = row.get("Total", "0.0")
                        row["Receipt_Version"] = "8"
                        receipts.append(row)
                        
                backup_path = os.path.join(BACKUP_DIR, "receipts_v7_migration.bak")
                shutil.copy2(RECEIPTS_CSV, backup_path)
                
                with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(receipts)
            except Exception as e:
                print(f"Error migrating receipts to V8: {e}")
                
        schema_conf["receipt_schema"] = 8
        config.save("schema", schema_conf)
        current_version = 8

def init_csv():
    if not os.path.exists(RECEIPTS_CSV):
        with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)

def get_bill_details(bill_no):
    init_csv()
    with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Bill"] == bill_no:
                return row
    return None

def resolve_payment_state(current_total, previous_arrears=0.0, amount_received=None):
    current_total = float(current_total or 0)
    previous_arrears = float(previous_arrears or 0)
    grand_total = round(current_total + previous_arrears, 2)
    received = round(float(amount_received or 0), 2)

    if received <= 0:
        return {
            "payment_status": "PENDING",
            "grand_total": grand_total,
            "amount_received": 0.0,
            "balance_due": max(grand_total, 0.0),
            "advance_amount": max(-grand_total, 0.0) if grand_total < 0 else 0.0
        }

    if received < grand_total:
        return {
            "payment_status": "PARTIAL",
            "grand_total": grand_total,
            "amount_received": received,
            "balance_due": round(grand_total - received, 2),
            "advance_amount": 0.0
        }

    if received == grand_total:
        return {
            "payment_status": "PAID",
            "grand_total": grand_total,
            "amount_received": received,
            "balance_due": 0.0,
            "advance_amount": 0.0
        }

    return {
        "payment_status": "ADVANCE",
        "grand_total": grand_total,
        "amount_received": received,
        "balance_due": 0.0,
        "advance_amount": round(received - grand_total, 2)
    }

def update_payment_status(bill_no, requested_status, amount_received=None):
    receipts = get_all_receipts()
    receipt = next((r for r in receipts if r.get("Bill") == bill_no), None)
    if not receipt:
        raise ValueError("Bill not found")

    grand_total = round(
        float(receipt.get("Total", 0) or 0) +
        float(receipt.get("Previous_Arrears", 0) or 0), 2
    )

    if requested_status == "PENDING":
        receipt["Payment_Status"] = "PENDING"
        receipt["Amount_Received"] = 0.0
        save_all_receipts(receipts)
        return receipt

    resolved = resolve_payment_state(
        current_total=float(receipt.get("Total", 0) or 0),
        previous_arrears=float(receipt.get("Previous_Arrears", 0) or 0),
        amount_received=amount_received
    )

    receipt["Payment_Status"] = resolved["payment_status"]
    receipt["Amount_Received"] = resolved["amount_received"]
    save_all_receipts(receipts)
    return receipt

def get_all_receipts():
    init_csv()
    migrate_receipts_schema()
    receipts = []
    try:
        with open(RECEIPTS_CSV, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                receipts.append(row)
    except Exception as e:
        print(f"Error loading receipts: {e}")
    return receipts

def get_receipt(bill_no):
    receipts = get_all_receipts()
    for r in receipts:
        if r["Bill"] == bill_no:
            return r
    return None

def save_all_receipts(receipts_list):
    init_csv()
    if os.path.exists(RECEIPTS_CSV):
        backup_path = os.path.join(BACKUP_DIR, "receipts.csv.bak")
        try:
            shutil.copy2(RECEIPTS_CSV, backup_path)
        except Exception:
            pass
            
    try:
        with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            writer.writeheader()
            writer.writerows(receipts_list)
    except Exception as e:
        print(f"Error saving receipts: {e}")

def get_billing_months():
    now = datetime.now()
    current_year = now.year
    current_month_idx = now.month 
    
    months_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    
    months_list = []
    for i in range(current_month_idx):
        months_list.append(f"{months_names[i]} {current_year}")
        
    return {
        "currentMonth": f"{months_names[current_month_idx - 1]} {current_year}",
        "months": months_list
    }

def calculate_charges(current_reading, additional_persons, prev_reading, rent, water, tank_water, maintenance_charge, rate, add_person_charge):
    units = max(0.0, current_reading - prev_reading)
    electricity = units * rate
    additional = additional_persons * add_person_charge
    total = rent + additional + water + tank_water + maintenance_charge + electricity
    
    return {
        "rent": rent,
        "water": water,
        "tank_water": tank_water,
        "maintenance_charge": maintenance_charge,
        "rate": rate,
        "additional": additional,
        "units": units,
        "electricity": electricity,
        "total": total,
        "previous": prev_reading
    }

def create_bill(tenant_name, month, current_reading, additional_persons, tank_water, maintenance_charge, maintenance_desc, previous_arrears=0.0, amount_received=None, payment_status="PENDING"):
    receipts = get_all_receipts()
    for r in receipts:
        if r["Tenant"] == tenant_name and r["Month"] == month and r.get("Status", "ACTIVE") == "ACTIVE":
            raise ValueError(f"A receipt for '{tenant_name}' for '{month}' already exists (Bill #{r['Bill']}). Please edit the existing bill instead.")
            
    billing_conf = config.get("billing", {})
    tenants = load_tenants()
    
    tenant_details = next((t for t in tenants if t.name == tenant_name), None)
    if not tenant_details:
        raise ValueError("Tenant not found")
        
    t_phone = tenant_details.phone
    t_company = tenant_details.company
    t_address = tenant_details.address
    
    charges = calculate_charges(
        current_reading, 
        additional_persons,
        prev_reading=tenant_details.previous_meter,
        rent=tenant_details.rent,
        water=tenant_details.water,
        tank_water=tank_water,
        maintenance_charge=maintenance_charge,
        rate=tenant_details.electricity_rate,
        add_person_charge=tenant_details.additional_person_charge
    )
    
    tenant_receipts = [r for r in receipts if r["Tenant"] == tenant_name]
    max_seq = 0
    for r in tenant_receipts:
        try:
            bill_str = r["Bill"]
            seq = int(bill_str.split('-')[-1]) if '-' in bill_str else int(bill_str)
            max_seq = max(max_seq, seq)
        except ValueError:
            pass
            
    bill_no = f"T{tenant_details.id}-{str(max_seq + 1).zfill(3)}"
    date_str = datetime.now().strftime("%d %B %Y")
    
    try:
        year_str = month.split()[-1]
    except Exception:
        year_str = datetime.now().strftime("%Y")
        
    pdf_filename = f"{bill_no}.pdf"
    
    grand_total = charges["total"] + previous_arrears
    if amount_received is None:
        amount_received = grand_total if payment_status == "PAID" else 0.0
        
    resolved = resolve_payment_state(
        current_total=charges["total"],
        previous_arrears=previous_arrears,
        amount_received=amount_received
    )
    payment_status = resolved["payment_status"]
    amount_received = resolved["amount_received"]
    
    data_dict = {
        "Bill": bill_no,
        "Date": date_str,
        "Month": month,
        "Tenant": tenant_name,
        "Previous": charges["previous"],
        "Current": current_reading,
        "Units": charges["units"],
        "Rent": charges["rent"],
        "Additional": charges["additional"],
        "Water": charges["water"],
        "Tank_Water": charges["tank_water"],
        "Electricity": charges["electricity"],
        "Total": charges["total"],
        "PDF": pdf_filename,
        "Tenant_Phone": t_phone,
        "Tenant_Company": t_company,
        "Tenant_Address": t_address,
        "Rate": charges["rate"],
        "Status": "ACTIVE",
        "Archived_Date": "",
        "Archived_By": "",
        "Deleted_Date": "",
        "Additional_Persons": additional_persons,
        "Additional_Person_Rate": tenant_details.additional_person_charge,
        "Receipt_Version": 8,
        "Generated_By": "Admin",
        "Payment_Status": payment_status,
        "Maintenance_Charge": maintenance_charge,
        "Maintenance_Desc": maintenance_desc,
        "Previous_Arrears": previous_arrears,
        "Amount_Received": amount_received
    }
    
    init_csv()
    receipts = get_all_receipts()
    receipts.append(data_dict)
    save_all_receipts(receipts)
    
    config.save("billing", billing_conf)
    
    tenant_details.previous_meter = float(current_reading)
    update_tenant(tenant_details)
    
    return data_dict

def update_bill(bill_no, tenant_name, month, current_reading, additional_persons, tank_water, maintenance_charge, maintenance_desc, previous_arrears=0.0, amount_received=None, payment_status="PENDING"):
    receipts = get_all_receipts()
    receipt = next((r for r in receipts if r["Bill"] == bill_no), None)
    if not receipt:
        raise ValueError("Receipt not found")
        
    tenants = load_tenants()
    tenant_details = next((t for t in tenants if t.name == tenant_name), None)
    
    prev_reading = float(receipt["Previous"])
    snap_rent = float(receipt.get("Rent", 0.0))
    snap_water = float(receipt.get("Water", 0.0))
    snap_tank_water = float(receipt.get("Tank_Water", 0.0))
    snap_rate = float(receipt.get("Rate", 0.0))
    
    snap_add_rate = float(receipt.get("Additional_Person_Rate", 0.0))
    if snap_add_rate == 0.0 and int(receipt.get("Receipt_Version", 2)) < 3 and tenant_details:
        snap_add_rate = tenant_details.additional_person_charge
    
    charges = calculate_charges(
        current_reading, 
        additional_persons, 
        prev_reading=prev_reading,
        rent=snap_rent,
        water=snap_water,
        tank_water=tank_water,
        maintenance_charge=maintenance_charge,
        rate=snap_rate,
        add_person_charge=snap_add_rate
    )
    
    pdf_filename = receipt.get("PDF", f"{bill_no}.pdf")
    status = receipt.get("Status", "ACTIVE")
    
    grand_total = charges["total"] + previous_arrears
    if amount_received is None:
        amount_received = grand_total if payment_status == "PAID" else 0.0
        
    resolved = resolve_payment_state(
        current_total=charges["total"],
        previous_arrears=previous_arrears,
        amount_received=amount_received
    )
    payment_status = resolved["payment_status"]
    amount_received = resolved["amount_received"]
    
    updated_dict = {
        "Bill": bill_no,
        "Date": receipt["Date"],
        "Month": month,
        "Tenant": tenant_name,
        "Previous": prev_reading,
        "Current": current_reading,
        "Units": charges["units"],
        "Rent": charges["rent"],
        "Additional": charges["additional"],
        "Water": charges["water"],
        "Tank_Water": charges["tank_water"],
        "Electricity": charges["electricity"],
        "Total": charges["total"],
        "PDF": pdf_filename,
        "Tenant_Phone": receipt.get("Tenant_Phone", ""),
        "Tenant_Company": receipt.get("Tenant_Company", ""),
        "Tenant_Address": receipt.get("Tenant_Address", ""),
        "Rate": charges["rate"],
        "Status": status,
        "Archived_Date": receipt.get("Archived_Date", ""),
        "Archived_By": receipt.get("Archived_By", ""),
        "Deleted_Date": receipt.get("Deleted_Date", ""),
        "Additional_Persons": receipt.get("Additional_Persons", 0),
        "Additional_Person_Rate": receipt.get("Additional_Person_Rate", 0.0),
        "Receipt_Version": receipt.get("Receipt_Version", 8),
        "Generated_By": receipt.get("Generated_By", "Admin"),
        "Payment_Status": payment_status,
        "Maintenance_Charge": maintenance_charge,
        "Maintenance_Desc": maintenance_desc,
        "Previous_Arrears": previous_arrears,
        "Amount_Received": amount_received
    }
    
    for idx, item in enumerate(receipts):
        if item["Bill"] == bill_no:
            receipts[idx] = updated_dict
            break
    save_all_receipts(receipts)
    
    return updated_dict

def archive_bill(bill_no):
    receipts = get_all_receipts()
    receipt = next((r for r in receipts if r["Bill"] == bill_no), None)
    if not receipt:
        raise ValueError("Receipt not found")
        
    if receipt.get("Status") == "ARCHIVED":
        return receipt

    for idx, r in enumerate(receipts):
        if r["Bill"] == bill_no:
            receipts[idx]["Status"] = "ARCHIVED"
            receipts[idx]["Archived_Date"] = datetime.now().strftime("%Y-%m-%d")
            receipts[idx]["Archived_By"] = "Admin"
            break
            
    save_all_receipts(receipts)
    return receipt

def restore_bill(bill_no):
    receipts = get_all_receipts()
    receipt = next((r for r in receipts if r["Bill"] == bill_no), None)
    if not receipt:
        raise ValueError("Receipt not found")
        
    if receipt.get("Status") == "ACTIVE":
        return receipt

    for idx, r in enumerate(receipts):
        if r["Bill"] == bill_no:
            receipts[idx]["Status"] = "ACTIVE"
            receipts[idx]["Archived_Date"] = ""
            receipts[idx]["Archived_By"] = ""
            break
            
    save_all_receipts(receipts)
    return receipt

def delete_bill(bill_no):
    receipts = get_all_receipts()
    receipt = next((r for r in receipts if r["Bill"] == bill_no), None)
    if not receipt:
        raise ValueError("Receipt not found")
        
    if receipt.get("Status") != "ARCHIVED":
        raise ValueError("Only archived receipts can be permanently deleted.")
        
    receipts = [r for r in receipts if r["Bill"] != bill_no]
    save_all_receipts(receipts)

def get_dashboard_stats():
    billing_conf = config.get("billing", {})
    receipts = get_all_receipts()
    tenants = load_tenants()
    
    next_bill = str(billing_conf.get("next_bill_number", 1)).zfill(3)
    
    now = datetime.now()
    current_year = now.year
    current_month_idx = now.month
    months_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    current_month_str = f"{months_names[current_month_idx - 1]} {current_year}"
    
    if current_month_idx == 1:
        prev_month_idx = 12
        prev_year = current_year - 1
    else:
        prev_month_idx = current_month_idx - 1
        prev_year = current_year
    prev_month_str = f"{months_names[prev_month_idx - 1]} {prev_year}"
    
    active_tenants = len([t for t in tenants if t.status == "Active"])
    inactive_tenants = len([t for t in tenants if t.status == "Inactive"])
    total_tenants = len(tenants)
    
    active_receipts = [r for r in receipts if r.get("Status", "ACTIVE") == "ACTIVE"]
    archived_receipts = [r for r in receipts if r.get("Status") == "ARCHIVED"]
    total_active_receipts = len(active_receipts)
    total_archived_receipts = len(archived_receipts)
    total_receipts_all = total_active_receipts + total_archived_receipts
    
    monthly_revenue = 0.0
    prev_monthly_revenue = 0.0
    pending_payments_count = 0
    pending_amount = 0.0
    amount_collected = 0.0
    electricity_consumed_this_month = 0.0
    highest_meter_reading = 0.0
    paid_bills_count = 0
    
    for r in active_receipts:
        try:
            current_reading = float(r.get("Current", 0.0))
            if current_reading > highest_meter_reading:
                highest_meter_reading = current_reading
        except ValueError:
            pass
            
        status = r.get("Payment_Status", "PENDING")
        gross_amount = float(r.get("Total", 0) or 0) + float(r.get("Previous_Arrears", 0) or 0)

        raw_recv = r.get("Amount_Received")
        received = float(raw_recv) if raw_recv not in (None, "") else (gross_amount if status == "PAID" else 0.0)
        outstanding = max(gross_amount - received, 0.0)

        is_paid = status == "PAID"
        is_partial = status == "PARTIAL"
        is_due = status in ["PENDING", "PARTIAL"]

        amount_collected += received

        if r.get("Month") == current_month_str:
            monthly_revenue += received

        if r.get("Month") == prev_month_str:
            prev_monthly_revenue += received

        if is_due:
            pending_payments_count += 1
            if outstanding > 0:
                pending_amount += outstanding

        if is_paid:
            paid_bills_count += 1
            

            
        if r.get("Month") == current_month_str:
            try:
                electricity_consumed_this_month += float(r.get("Units", 0.0))
            except ValueError:
                pass
            
    revenue_change_str = ""
    if prev_monthly_revenue == 0.0:
        revenue_change_str = "New Month"
    else:
        diff = monthly_revenue - prev_monthly_revenue
        pct = (diff / prev_monthly_revenue) * 100
        sign = "+" if diff > 0 else ""
        revenue_change_str = f"{sign}{pct:.2f}%"
        
    collection_rate = 0.0
    if total_active_receipts > 0:
        collection_rate = (paid_bills_count / total_active_receipts) * 100
        
    recent_bills = []
    for r in reversed(active_receipts[-5:]):
        recent_bills.append({
            "bill_no": r["Bill"],
            "tenant_name": r["Tenant"],
            "total": float(r.get("Total", 0)) + float(r.get("Previous_Arrears", 0)),
            "amount_received": float(r.get("Amount_Received", 0) or 0),
            "month": r["Month"],
            "payment_status": r.get("Payment_Status", "PENDING")
        })
        
    revenue_chart_data = {m: 0.0 for m in months_names}
    electricity_chart_data = {m: 0.0 for m in months_names}
    
    for r in active_receipts:
        try:
            r_month, r_year = r["Month"].split()
            if r_year == str(current_year) and r_month in revenue_chart_data:
                revenue_chart_data[r_month] += float(r.get("Amount_Received", r.get("Total", 0)))
                electricity_chart_data[r_month] += float(r.get("Units", 0.0))
        except Exception:
            pass
            
    chart_months = [m for m in months_names if revenue_chart_data[m] > 0 or electricity_chart_data[m] > 0]
    if not chart_months:
        chart_months = months_names[:current_month_idx]
        
    revenue_list = [revenue_chart_data[m] for m in chart_months]
    electricity_list = [electricity_chart_data[m] for m in chart_months]
    
    return {
        "next_bill": next_bill,
        "current_month": current_month_str,
        "monthly_revenue": monthly_revenue,
        "prev_monthly_revenue": prev_monthly_revenue,
        "revenue_change_str": revenue_change_str,
        "total_active_receipts": total_active_receipts,
        "total_archived_receipts": total_archived_receipts,
        "total_receipts_all": total_receipts_all,
        "active_tenants": active_tenants,
        "inactive_tenants": inactive_tenants,
        "total_tenants": total_tenants,
        "highest_meter_reading": highest_meter_reading,
        "electricity_consumed": electricity_consumed_this_month,
        "pending_payments_count": pending_payments_count,
        "pending_amount": pending_amount,
        "amount_collected": amount_collected,
        "collection_rate": collection_rate,
        "recent_bills": recent_bills,
        "chart_labels": chart_months,
        "chart_revenue": revenue_list,
        "chart_electricity": electricity_list
    }