import re

with open(r"d:\VEGA\RENT\rent-receipt\app\services\billing_service.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove `import csv`
content = re.sub(r"import csv\n", "", content)

# 2. Remove RECEIPTS_CSV and HEADERS definitions
content = re.sub(r'RECEIPTS_CSV = os\.path\.join\(DB_DIR, "receipts\.csv"\)\n+', '', content)
content = re.sub(r'HEADERS = \[.*?\]\n+', '', content, flags=re.DOTALL)

# 3. Remove migrate_receipts_schema() entirely
# It spans from `def migrate_receipts_schema():` to the `init_csv()` function.
content = re.sub(r'def migrate_receipts_schema\(\):.*?def init_csv\(\):', 'def init_csv():', content, flags=re.DOTALL)

# 4. Remove init_csv() entirely
# It spans from `def init_csv():` to `def get_bill_details(bill_no):`
content = re.sub(r'def init_csv\(\):.*?def get_bill_details\(bill_no\):', 'def get_bill_details(bill_no):', content, flags=re.DOTALL)

# Write it back
with open(r"d:\VEGA\RENT\rent-receipt\app\services\billing_service.py", "w", encoding="utf-8") as f:
    f.write(content)
print("billing_service.py cleaned")
