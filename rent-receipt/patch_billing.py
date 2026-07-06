import re

with open(r"d:\VEGA\RENT\rent-receipt\app\services\billing_service.py", "r", encoding="utf-8") as f:
    content = f.read()

# We want to replace these functions with our new implementations:
# - get_all_receipts
# - get_receipt (Wait, get_receipt doesn't exist, get_bill_details does)
# - save_all_receipts

# First, add the new imports
if "from app.core.db import get_conn" not in content:
    content = content.replace("import csv\n", "import csv\nfrom app.core.db import get_conn\n")

# Replace get_all_receipts
new_get_all_receipts = """
def _safe_float(val, default=0.0) -> float:
    try:
        return float(str(val).strip() or default)
    except Exception:
        return default

def _safe_int(val, default=0) -> int:
    try:
        return int(float(str(val).strip() or default))
    except Exception:
        return default

def _row_to_dict(row):
    return {
        "Bill": row["billno"],
        "Date": row["date"],
        "Month": row["month"],
        "Tenant": row["tenant"],
        "Previous": _safe_float(row["previous"]),
        "Current": _safe_float(row["current"]),
        "Units": _safe_float(row["units"]),
        "Rent": _safe_float(row["rent"]),
        "Additional": _safe_float(row["additional"]),
        "Water": _safe_float(row["water"]),
        "Tank_Water": _safe_float(row["tankwater"]),
        "Electricity": _safe_float(row["electricity"]),
        "Total": _safe_float(row["total"]),
        "PDF": row["pdf"] or "",
        "Tenant_Phone": row["tenantphone"] or "",
        "Tenant_Company": row["tenantcompany"] or "",
        "Tenant_Address": row["tenantaddress"] or "",
        "Rate": _safe_float(row["rate"]),
        "Status": row["status"],
        "Archived_Date": row["archiveddate"] or "",
        "Archived_By": row["archivedby"] or "",
        "Deleted_Date": row["deleteddate"] or "",
        "Additional_Persons": _safe_int(row["additionalpersons"]),
        "Additional_Person_Rate": _safe_float(row["additionalpersonrate"]),
        "Receipt_Version": _safe_int(row["receiptversion"]),
        "Generated_By": row["generatedby"] or "Admin",
        "Payment_Status": row["paymentstatus"] or "PENDING",
        "Maintenance_Charge": _safe_float(row["maintenancecharge"]),
        "Maintenance_Desc": row["maintenancedesc"] or "",
        "Previous_Arrears": _safe_float(row["previousarrears"]),
        "Amount_Received": _safe_float(row["amountreceived"]),
    }

def get_all_receipts():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM receipts ORDER BY rowid DESC").fetchall()
    return [_row_to_dict(r) for r in rows]
"""

content = re.sub(
    r"def get_all_receipts\(\):.*?return receipts",
    new_get_all_receipts.strip(),
    content,
    flags=re.DOTALL
)

# Replace get_bill_details
new_get_bill_details = """def get_bill_details(bill_no):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE billno = ?", (bill_no,)).fetchone()
    if row:
        return _row_to_dict(row)
    return None"""

content = re.sub(
    r"def get_bill_details\(bill_no\):.*?return None",
    new_get_bill_details,
    content,
    flags=re.DOTALL
)

# Replace save_all_receipts
new_save_all_receipts = """def save_all_receipts(receipts_list):
    with get_conn() as conn:
        for receipt in receipts_list:
            exists = conn.execute("SELECT 1 FROM receipts WHERE billno = ?", (receipt.get("Bill"),)).fetchone()
            params = (
                receipt.get("Bill"),
                receipt.get("Date", ""),
                receipt.get("Month", ""),
                receipt.get("Tenant", ""),
                _safe_float(receipt.get("Previous")),
                _safe_float(receipt.get("Current")),
                _safe_float(receipt.get("Units")),
                _safe_float(receipt.get("Rent")),
                _safe_float(receipt.get("Additional")),
                _safe_float(receipt.get("Water")),
                _safe_float(receipt.get("Tank_Water")),
                _safe_float(receipt.get("Electricity")),
                _safe_float(receipt.get("Total")),
                receipt.get("PDF", ""),
                receipt.get("Tenant_Phone", ""),
                receipt.get("Tenant_Company", ""),
                receipt.get("Tenant_Address", ""),
                _safe_float(receipt.get("Rate")),
                receipt.get("Status", "ACTIVE"),
                receipt.get("Archived_Date", ""),
                receipt.get("Archived_By", ""),
                receipt.get("Deleted_Date", ""),
                _safe_int(receipt.get("Additional_Persons")),
                _safe_float(receipt.get("Additional_Person_Rate")),
                _safe_int(receipt.get("Receipt_Version", 8)),
                receipt.get("Generated_By", "Admin"),
                receipt.get("Payment_Status", "PENDING"),
                _safe_float(receipt.get("Maintenance_Charge")),
                receipt.get("Maintenance_Desc", ""),
                _safe_float(receipt.get("Previous_Arrears")),
                _safe_float(receipt.get("Amount_Received")),
            )
            if exists:
                conn.execute(
                    \"\"\"
                    UPDATE receipts SET
                        date = ?, month = ?, tenant = ?, previous = ?, current = ?,
                        units = ?, rent = ?, additional = ?, water = ?, tankwater = ?,
                        electricity = ?, total = ?, pdf = ?, tenantphone = ?,
                        tenantcompany = ?, tenantaddress = ?, rate = ?, status = ?,
                        archiveddate = ?, archivedby = ?, deleteddate = ?,
                        additionalpersons = ?, additionalpersonrate = ?, receiptversion = ?,
                        generatedby = ?, paymentstatus = ?, maintenancecharge = ?,
                        maintenancedesc = ?, previousarrears = ?, amountreceived = ?
                    WHERE billno = ?
                    \"\"\",
                    params[1:] + (params[0],),
                )
            else:
                conn.execute(
                    \"\"\"
                    INSERT INTO receipts (
                        billno, date, month, tenant, previous, current, units, rent,
                        additional, water, tankwater, electricity, total, pdf,
                        tenantphone, tenantcompany, tenantaddress, rate, status,
                        archiveddate, archivedby, deleteddate, additionalpersons,
                        additionalpersonrate, receiptversion, generatedby, paymentstatus,
                        maintenancecharge, maintenancedesc, previousarrears, amountreceived
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    \"\"\",
                    params,
                )
        conn.commit()"""

content = re.sub(
    r"def save_all_receipts\(receipts_list\):.*?writer\.writerows\(receipts_list\)",
    new_save_all_receipts,
    content,
    flags=re.DOTALL
)

with open(r"d:\VEGA\RENT\rent-receipt\app\services\billing_service.py", "w", encoding="utf-8") as f:
    f.write(content)
print("billing patched")
