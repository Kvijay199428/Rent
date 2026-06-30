import csv
import os
import shutil

CSV_FILE = "tenant.csv"
BACKUP_FILE = "tenant_backup.csv"

HEADERS = [
    "Bill", "Date", "Month", "Tenant", "Previous", "Current", 
    "Units", "Rent", "Additional", "Water", "Electricity", "Total", "PDF"
]

def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(HEADERS)

def save_receipt_data(data_dict):
    init_csv()
    
    if os.path.exists(CSV_FILE):
        try:
            shutil.copy2(CSV_FILE, BACKUP_FILE)
        except Exception:
            pass

    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        writer.writerow(data_dict)

def get_all_receipts():
    init_csv()
    receipts = []
    with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            receipts.append(row)
    return receipts

def get_receipt(bill_no):
    receipts = get_all_receipts()
    for r in receipts:
        if r["Bill"] == bill_no:
            return r
    return None

def update_receipt(bill_no, updated_data):
    receipts = get_all_receipts()
    for i, r in enumerate(receipts):
        if r["Bill"] == bill_no:
            receipts[i] = updated_data
            break
            
    if os.path.exists(CSV_FILE):
        try:
            shutil.copy2(CSV_FILE, BACKUP_FILE)
        except Exception:
            pass

    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(receipts)

