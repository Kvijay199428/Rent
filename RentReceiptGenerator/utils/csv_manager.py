import csv
import os
import shutil

CSV_FILE = "tenant.csv"
BACKUP_FILE = "tenant_backup.csv"

HEADERS = [
    "Bill No", "Date", "Month", "Tenant", "Rent", "Additional Persons", 
    "Additional Charge", "Previous Unit", "Current Unit", "Consumed Units", 
    "Rate", "Electricity", "Water", "Total", "PDF"
]

def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(HEADERS)

def save_receipt_data(data_dict):
    init_csv()
    
    # Backup before writing
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
