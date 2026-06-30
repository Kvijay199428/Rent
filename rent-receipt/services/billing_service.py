import csv
import os
import shutil
from datetime import datetime
from services.config_service import get_billing_config, save_billing_config, get_landlord_config
from services.tenant_service import load_tenants
from services.pdf_service import generate_professional_pdf

DB_DIR = "database"
os.makedirs(DB_DIR, exist_ok=True)

RECEIPTS_CSV = os.path.join(DB_DIR, "receipts.csv")
BACKUP_DIR = "backups"

HEADERS = [
    "Bill", "Date", "Month", "Tenant", "Previous", "Current", 
    "Units", "Rent", "Additional", "Water", "Electricity", "Total", "PDF",
    "Tenant_Phone", "Tenant_Company", "Tenant_Address"
]

def init_csv():
    if not os.path.exists(RECEIPTS_CSV):
        with open(RECEIPTS_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)

def get_all_receipts():
    init_csv()
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
    current_month_idx = now.month  # 1-12
    
    months_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    
    months_list = []
    for i in range(current_month_idx):
        months_list.append(f"{months_names[i]} {current_year}")
        
    return {
        "currentMonth": f"{months_names[current_month_idx - 1]} {current_year}",
        "months": months_list
    }

def calculate_charges(current_reading, additional_persons, prev_reading=None):
    billing_conf = get_billing_config()
    
    rent = float(billing_conf.get("rent", 8000.0))
    water = float(billing_conf.get("water", 500.0))
    rate = float(billing_conf.get("electricity_rate", 15.0))
    add_person_charge = float(billing_conf.get("additional_person_charge", 1000.0))
    
    if prev_reading is None:
        prev_reading = float(billing_conf.get("previous_meter_reading", 0.0))
        
    units = max(0.0, current_reading - prev_reading)
    electricity = units * rate
    additional = additional_persons * add_person_charge
    total = rent + additional + water + electricity
    
    return {
        "rent": rent,
        "water": water,
        "rate": rate,
        "additional": additional,
        "units": units,
        "electricity": electricity,
        "total": total,
        "previous": prev_reading
    }

def create_bill(tenant_name, month, current_reading, additional_persons):
    billing_conf = get_billing_config()
    landlord_conf = get_landlord_config()
    tenants = load_tenants()
    
    # Find tenant details
    tenant_details = next((t for t in tenants if t.name == tenant_name), None)
    t_phone = tenant_details.phone if tenant_details else ""
    t_company = tenant_details.company if tenant_details else ""
    t_address = tenant_details.address if tenant_details else ""
    
    charges = calculate_charges(current_reading, additional_persons)
    
    bill_no = str(billing_conf.get("next_bill_number", 1)).zfill(3)
    date_str = datetime.now().strftime("%d %B %Y")
    
    # Group PDF by year
    # Extract year from month ("July 2026" -> "2026")
    try:
        year_str = month.split()[-1]
    except Exception:
        year_str = datetime.now().strftime("%Y")
        
    pdf_filename = f"{bill_no}.pdf"
    pdf_path = os.path.join("receipts", year_str, pdf_filename)
    
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
        "Electricity": charges["electricity"],
        "Total": charges["total"],
        "PDF": pdf_filename,
        "Tenant_Phone": t_phone,
        "Tenant_Company": t_company,
        "Tenant_Address": t_address,
        "Rate": charges["rate"]
    }
    
    # Generate PDF
    generate_professional_pdf(data_dict, landlord_conf, pdf_path)
    
    # Save receipt info
    init_csv()
    receipts = get_all_receipts()
    receipts.append(data_dict)
    save_all_receipts(receipts)
    
    # Update configs
    billing_conf["next_bill_number"] = int(bill_no) + 1
    billing_conf["previous_meter_reading"] = current_reading
    save_billing_config(billing_conf)
    
    return data_dict

def update_bill(bill_no, tenant_name, month, current_reading, additional_persons):
    receipts = get_all_receipts()
    receipt = next((r for r in receipts if r["Bill"] == bill_no), None)
    if not receipt:
        raise ValueError("Receipt not found")
        
    landlord_conf = get_landlord_config()
    tenants = load_tenants()
    
    tenant_details = next((t for t in tenants if t.name == tenant_name), None)
    t_phone = tenant_details.phone if tenant_details else ""
    t_company = tenant_details.company if tenant_details else ""
    t_address = tenant_details.address if tenant_details else ""
    
    # Recalculate using original previous reading
    prev_reading = float(receipt["Previous"])
    charges = calculate_charges(current_reading, additional_persons, prev_reading=prev_reading)
    
    try:
        year_str = month.split()[-1]
    except Exception:
        year_str = datetime.now().strftime("%Y")
        
    pdf_filename = receipt.get("PDF", f"{bill_no}.pdf")
    pdf_path = os.path.join("receipts", year_str, pdf_filename)
    
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
        "Electricity": charges["electricity"],
        "Total": charges["total"],
        "PDF": pdf_filename,
        "Tenant_Phone": t_phone,
        "Tenant_Company": t_company,
        "Tenant_Address": t_address,
        "Rate": charges["rate"]
    }
    
    # Regenerate PDF
    generate_professional_pdf(updated_dict, landlord_conf, pdf_path)
    
    # Update CSV list
    for idx, item in enumerate(receipts):
        if item["Bill"] == bill_no:
            receipts[idx] = updated_dict
            break
    save_all_receipts(receipts)
    
    return updated_dict

def delete_bill(bill_no):
    receipts = get_all_receipts()
    receipt = next((r for r in receipts if r["Bill"] == bill_no), None)
    if not receipt:
        raise ValueError("Receipt not found")
        
    try:
        year_str = receipt["Month"].split()[-1]
    except Exception:
        year_str = datetime.now().strftime("%Y")
        
    pdf_path = os.path.join("receipts", year_str, receipt["PDF"])
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except Exception:
            pass
            
    receipts = [r for r in receipts if r["Bill"] != bill_no]
    save_all_receipts(receipts)

def get_dashboard_stats():
    billing_conf = get_billing_config()
    receipts = get_all_receipts()
    tenants = load_tenants()
    
    next_bill = str(billing_conf.get("next_bill_number", 1)).zfill(3)
    months_info = get_billing_months()
    current_month = months_info["currentMonth"]
    prev_reading = billing_conf.get("previous_meter_reading", 0.0)
    
    total_tenants = len([t for t in tenants if t.status == "Active"])
    total_receipts = len(receipts)
    
    # Revenue this month
    revenue_this_month = 0.0
    for r in receipts:
        if r["Month"] == current_month:
            revenue_this_month += float(r.get("Total", 0.0))
            
    # Recent bills (last 5)
    recent_bills = []
    for r in reversed(receipts[-5:]):
        recent_bills.append({
            "bill_no": r["Bill"],
            "tenant_name": r["Tenant"],
            "total": r["Total"],
            "month": r["Month"]
        })
        
    # Stats for Charts
    # Group revenue/electricity by month for the current year
    current_year = datetime.now().strftime("%Y")
    months_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    
    revenue_chart_data = {m: 0.0 for m in months_names}
    electricity_chart_data = {m: 0.0 for m in months_names}
    
    for r in receipts:
        try:
            r_month, r_year = r["Month"].split()
            if r_year == current_year and r_month in revenue_chart_data:
                revenue_chart_data[r_month] += float(r.get("Total", 0.0))
                electricity_chart_data[r_month] += float(r.get("Units", 0.0))
        except Exception:
            pass
            
    # Convert dict to ordered lists
    chart_months = [m for m in months_names if revenue_chart_data[m] > 0 or electricity_chart_data[m] > 0]
    if not chart_months:
        # Default to showing at least up to current month
        now_month_idx = datetime.now().month
        chart_months = months_names[:now_month_idx]
        
    revenue_list = [revenue_chart_data[m] for m in chart_months]
    electricity_list = [electricity_chart_data[m] for m in chart_months]
    
    return {
        "next_bill": next_bill,
        "current_month": current_month,
        "prev_reading": prev_reading,
        "total_tenants": total_tenants,
        "total_receipts": total_receipts,
        "revenue_this_month": revenue_this_month,
        "recent_bills": recent_bills,
        "chart_labels": chart_months,
        "chart_revenue": revenue_list,
        "chart_electricity": electricity_list
    }
