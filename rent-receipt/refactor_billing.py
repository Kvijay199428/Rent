import re

with open(r"d:\VEGA\RENT\rent-receipt\app\services\billing_service.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove `save_all_receipts`
content = re.sub(r'def save_all_receipts\(.*?return\n', '', content, flags=re.DOTALL)
content = re.sub(r'def save_all_receipts\(.*?(?=def )', '', content, flags=re.DOTALL)

# Let's replace update_payment_status
update_payment_status_new = '''def update_payment_status(bill_no, requested_status, amount_received=None):
    from app.core.db import get_conn
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE billno = ?", (bill_no,)).fetchone()
        if not row:
            raise ValueError("Receipt not found")
        
        current_total = float(row["total"])
        previous_arrears = float(row["previousarrears"])
        
        status, final_received = resolve_payment_state(
            current_total,
            previous_arrears=previous_arrears,
            amount_received=amount_received
        )
        
        if requested_status in ["PENDING", "PARTIAL"]:
            status = requested_status

        conn.execute("""
            UPDATE receipts 
            SET paymentstatus = ?, amountreceived = ?
            WHERE billno = ?
        """, (status, final_received, bill_no))
        conn.commit()
    return status
'''
content = re.sub(r'def update_payment_status\(.*?(?=def _safe_float)', update_payment_status_new, content, flags=re.DOTALL)

# Replace create_bill
create_bill_new = '''def create_bill(tenant_name, month, current_reading, additional_persons, tank_water, maintenance_charge, 
                maintenance_desc, previous_arrears=0.0, amount_received=None, payment_status="PENDING"):
    from app.core.db import get_conn
    from datetime import datetime
    from app.services.tenant_service import load_tenants
    import os
    from app.core.paths import RECEIPTS_DIR
    from app.services.pdf_service import generate_professional_pdf
    
    tenants = load_tenants()
    tenant = next((t for t in tenants if t.name == tenant_name), None)
    if not tenant:
        raise ValueError("Tenant not found")

    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
    new_bill_num = count + 1
    bill_no = f"REC-{new_bill_num:03d}"
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    charges = calculate_charges(
        current_reading, additional_persons, tenant.previous_meter,
        tenant.rent, tenant.water, tank_water, maintenance_charge,
        tenant.electricity_rate, tenant.additional_person_charge
    )
    
    if payment_status == "PAID" and amount_received is None:
        amount_received = charges["total"] + previous_arrears
    
    pdf_filename = f"{bill_no}_{tenant_name.replace(' ', '_')}_{month.replace(' ', '_')}.pdf"
    pdf_path = os.path.join(RECEIPTS_DIR, pdf_filename)
    
    receipt_dict = {
        "Bill": bill_no,
        "Date": current_date,
        "Month": month,
        "Tenant": tenant_name,
        "Previous": tenant.previous_meter,
        "Current": current_reading,
        "Units": charges["units"],
        "Rent": tenant.rent,
        "Additional": charges["additional"],
        "Water": tenant.water,
        "Tank_Water": tank_water,
        "Electricity": charges["electricity"],
        "Total": charges["total"],
        "PDF": pdf_filename,
        "Tenant_Phone": tenant.phone,
        "Tenant_Company": tenant.company,
        "Tenant_Address": tenant.address,
        "Rate": tenant.electricity_rate,
        "Status": "ACTIVE",
        "Archived_Date": "",
        "Archived_By": "",
        "Deleted_Date": "",
        "Additional_Persons": additional_persons,
        "Additional_Person_Rate": tenant.additional_person_charge,
        "Receipt_Version": 8,
        "Generated_By": "Admin",
        "Payment_Status": payment_status,
        "Maintenance_Charge": maintenance_charge,
        "Maintenance_Desc": maintenance_desc,
        "Previous_Arrears": previous_arrears,
        "Amount_Received": amount_received
    }
    
    try:
        generate_professional_pdf(receipt_dict, pdf_path, tenant)
    except BaseException as e:
        print(f"Error generating PDF: {e}")

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO receipts (
                billno, date, month, tenant, previous, current, units, rent,
                additional, water, tankwater, electricity, total, pdf,
                tenantphone, tenantcompany, tenantaddress, rate, status,
                archiveddate, archivedby, deleteddate, additionalpersons,
                additionalpersonrate, receiptversion, generatedby, paymentstatus,
                maintenancecharge, maintenancedesc, previousarrears, amountreceived
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bill_no, current_date, month, tenant_name, tenant.previous_meter, current_reading,
            charges["units"], tenant.rent, charges["additional"], tenant.water, tank_water,
            charges["electricity"], charges["total"], pdf_filename, tenant.phone, tenant.company,
            tenant.address, tenant.electricity_rate, "ACTIVE", "", "", "",
            additional_persons, tenant.additional_person_charge, 8, "Admin",
            payment_status, maintenance_charge, maintenance_desc, previous_arrears, amount_received
        ))
        conn.commit()

    return receipt_dict
'''
content = re.sub(r'def create_bill\(.*?(?=def update_bill)', create_bill_new, content, flags=re.DOTALL)

# Replace update_bill
update_bill_new = '''def update_bill(bill_no, tenant_name, month, current_reading, additional_persons, tank_water, maintenance_charge, 
                maintenance_desc, previous_arrears=0.0, amount_received=None, payment_status="PENDING"):
    from app.core.db import get_conn
    from app.services.tenant_service import load_tenants
    from app.services.pdf_service import generate_professional_pdf
    import os
    from app.core.paths import RECEIPTS_DIR
    
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE billno = ?", (bill_no,)).fetchone()
        if not row:
            raise ValueError("Receipt not found")
        old_receipt = dict(row)

    tenants = load_tenants()
    tenant = next((t for t in tenants if t.name == tenant_name), None)
    if not tenant:
        raise ValueError("Tenant not found")
        
    charges = calculate_charges(
        current_reading, additional_persons, old_receipt["previous"],
        tenant.rent, tenant.water, tank_water, maintenance_charge,
        tenant.electricity_rate, tenant.additional_person_charge
    )
    
    if payment_status == "PAID" and amount_received is None:
        amount_received = charges["total"] + previous_arrears
        
    pdf_filename = old_receipt.get("pdf", f"{bill_no}_{tenant_name.replace(' ', '_')}_{month.replace(' ', '_')}.pdf")
    pdf_path = os.path.join(RECEIPTS_DIR, pdf_filename)
    
    updated_dict = {
        "Bill": bill_no,
        "Date": old_receipt["date"],
        "Month": month,
        "Tenant": tenant_name,
        "Previous": old_receipt["previous"],
        "Current": current_reading,
        "Units": charges["units"],
        "Rent": tenant.rent,
        "Additional": charges["additional"],
        "Water": tenant.water,
        "Tank_Water": tank_water,
        "Electricity": charges["electricity"],
        "Total": charges["total"],
        "PDF": pdf_filename,
        "Tenant_Phone": tenant.phone,
        "Tenant_Company": tenant.company,
        "Tenant_Address": tenant.address,
        "Rate": tenant.electricity_rate,
        "Status": old_receipt["status"],
        "Archived_Date": old_receipt["archiveddate"],
        "Archived_By": old_receipt["archivedby"],
        "Deleted_Date": old_receipt["deleteddate"],
        "Additional_Persons": additional_persons,
        "Additional_Person_Rate": tenant.additional_person_charge,
        "Receipt_Version": old_receipt.get("receiptversion", 8),
        "Generated_By": old_receipt.get("generatedby", "Admin"),
        "Payment_Status": payment_status,
        "Maintenance_Charge": maintenance_charge,
        "Maintenance_Desc": maintenance_desc,
        "Previous_Arrears": previous_arrears,
        "Amount_Received": amount_received
    }
    
    try:
        generate_professional_pdf(updated_dict, pdf_path, tenant)
    except BaseException as e:
        print(f"Error generating PDF: {e}")

    with get_conn() as conn:
        conn.execute("""
            UPDATE receipts SET
                month = ?, tenant = ?, current = ?, units = ?, rent = ?,
                additional = ?, water = ?, tankwater = ?, electricity = ?, total = ?,
                pdf = ?, tenantphone = ?, tenantcompany = ?, tenantaddress = ?, rate = ?,
                additionalpersons = ?, additionalpersonrate = ?, paymentstatus = ?,
                maintenancecharge = ?, maintenancedesc = ?, previousarrears = ?, amountreceived = ?
            WHERE billno = ?
        """, (
            month, tenant_name, current_reading, charges["units"], tenant.rent,
            charges["additional"], tenant.water, tank_water, charges["electricity"], charges["total"],
            pdf_filename, tenant.phone, tenant.company, tenant.address, tenant.electricity_rate,
            additional_persons, tenant.additional_person_charge, payment_status,
            maintenance_charge, maintenance_desc, previous_arrears, amount_received,
            bill_no
        ))
        conn.commit()

    return updated_dict
'''
content = re.sub(r'def update_bill\(.*?(?=def archive_bill)', update_bill_new, content, flags=re.DOTALL)

# Replace archive_bill, restore_bill, delete_bill
archive_restore_delete_new = '''def archive_bill(bill_no):
    from app.core.db import get_conn
    from datetime import datetime
    with get_conn() as conn:
        conn.execute("""
            UPDATE receipts SET status = 'ARCHIVED', archiveddate = ?, archivedby = 'Admin'
            WHERE billno = ? AND status != 'ARCHIVED'
        """, (datetime.now().strftime("%Y-%m-%d"), bill_no))
        conn.commit()
    return get_receipt(bill_no)

def restore_bill(bill_no):
    from app.core.db import get_conn
    with get_conn() as conn:
        conn.execute("""
            UPDATE receipts SET status = 'ACTIVE', archiveddate = '', archivedby = ''
            WHERE billno = ? AND status != 'ACTIVE'
        """, (bill_no,))
        conn.commit()
    return get_receipt(bill_no)

def delete_bill(bill_no):
    from app.core.db import get_conn
    with get_conn() as conn:
        row = conn.execute("SELECT status FROM receipts WHERE billno = ?", (bill_no,)).fetchone()
        if not row:
            raise ValueError("Receipt not found")
        if row["status"] != "ARCHIVED":
            raise ValueError("Only archived receipts can be permanently deleted.")
        conn.execute("DELETE FROM receipts WHERE billno = ?", (bill_no,))
        conn.commit()
'''
content = re.sub(r'def archive_bill\(.*?(?=def get_dashboard_stats)', archive_restore_delete_new, content, flags=re.DOTALL)

with open(r"d:\VEGA\RENT\rent-receipt\app\services\billing_service.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Billing refactored.")
