from app.core.db import get_conn
import os
import shutil
from datetime import datetime
from app.core.config_service import config
from app.services.tenant_service import load_tenants, update_tenant
from app.services.pdf_service import generate_professional_pdf

from app.core.paths import DB_DIR, BACKUPS_DIR as BACKUP_DIR, RECEIPTS_DIR

def get_bill_details(bill_no):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE billno = ?", (bill_no,)).fetchone()
    if row:
        return _row_to_dict(row)
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
    from app.core.db import get_conn
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE billno = ?", (bill_no,)).fetchone()
        if not row:
            raise ValueError("Receipt not found")
        
        current_total = float(row["total"])
        previous_arrears = float(row["previousarrears"])
        
        state = resolve_payment_state(
            current_total,
            previous_arrears=previous_arrears,
            amount_received=amount_received
        )
        status = state["payment_status"]
        final_received = state["amount_received"]
        
        if requested_status in ["PENDING", "PARTIAL"]:
            status = requested_status

        conn.execute("""
            UPDATE receipts 
            SET paymentstatus = ?, amountreceived = ?
            WHERE billno = ?
        """, (status, final_received, bill_no))
        conn.commit()
    return status
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
    if row is None:
        return None
    if not isinstance(row, dict):
        row = dict(row)
        
    return {
        "Bill": row.get("billno", ""),
        "Date": row.get("date", ""),
        "Month": row.get("month", ""),
        "Tenant": row.get("tenant", ""),
        "TenantId": row.get("tenant_id", 0) or 0,
        "Previous": _safe_float(row.get("previous")),
        "Current": _safe_float(row.get("current")),
        "Units": _safe_float(row.get("units")),
        "Rent": _safe_float(row.get("rent")),
        "Additional": _safe_float(row.get("additional")),
        "Water": _safe_float(row.get("water")),
        "Tank_Water": _safe_float(row.get("tankwater")),
        "Electricity": _safe_float(row.get("electricity")),
        "Total": _safe_float(row.get("total")),
        "PDF": row.get("pdf", "") or "",
        "Tenant_Phone": row.get("tenantphone", "") or "",
        "Tenant_Company": row.get("tenantcompany", "") or "",
        "Tenant_Address": row.get("tenantaddress", "") or "",
        "Rate": _safe_float(row.get("rate")),
        "Status": row.get("status", ""),
        "Archived_Date": row.get("archiveddate", "") or "",
        "Archived_By": row.get("archivedby", "") or "",
        "Deleted_Date": row.get("deleteddate", "") or "",
        "Additional_Persons": _safe_int(row.get("additionalpersons")),
        "Additional_Person_Rate": _safe_float(row.get("additionalpersonrate")),
        "Receipt_Version": _safe_int(row.get("receiptversion")),
        "Generated_By": row.get("generatedby", "Admin") or "Admin",
        "Payment_Status": row.get("paymentstatus", "PENDING") or "PENDING",
        "Maintenance_Charge": _safe_float(row.get("maintenancecharge")),
        "Maintenance_Desc": row.get("maintenancedesc", "") or "",
        "Previous_Arrears": _safe_float(row.get("previousarrears")),
        "Amount_Received": _safe_float(row.get("amountreceived")),
    }

def get_all_receipts():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM receipts ORDER BY rowid DESC").fetchall()
    return [_row_to_dict(r) for r in rows]

def get_receipt(bill_no):
    receipts = get_all_receipts()
    for r in receipts:
        if r["Bill"] == bill_no:
            return r
    return None

def get_latest_receipt(tenant_name: str, exclude_bill_no: str = None):
    with get_conn() as conn:
        query = "SELECT * FROM receipts WHERE tenant COLLATE NOCASE = ? AND status != 'ARCHIVED'"
        params = [tenant_name]
        if exclude_bill_no:
            query += " AND billno != ?"
            params.append(exclude_bill_no)
        query += " ORDER BY rowid DESC LIMIT 1"
        row = conn.execute(query, tuple(params)).fetchone()
    if row:
        return _row_to_dict(row)
    return None

def resolve_previous_reading(tenant_name: str, exclude_bill_no: str = None) -> float:
    from app.services.tenant_service import get_tenant_by_name
    latest = get_latest_receipt(tenant_name, exclude_bill_no)
    if latest:
        return float(latest.get("Current", 0) or 0)
    tenant = get_tenant_by_name(tenant_name)
    if tenant:
        return float(getattr(tenant, "previous_meter", 0) or 0)
    return 0.0

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

def create_bill(tenant_name, month, current_reading, additional_persons, tank_water, maintenance_charge, 
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
    
    prev = resolve_previous_reading(tenant_name)
    if prev > 0 and current_reading < prev:
        raise ValueError("Current meter reading cannot be less than previous reading.")
    
    charges = calculate_charges(
        current_reading, additional_persons, prev,
        tenant.rent, tenant.water, tank_water, maintenance_charge,
        tenant.electricity_rate, tenant.additional_person_charge
    )
    
    if payment_status == "PAID" and amount_received is None:
        amount_received = charges["total"] + previous_arrears
    elif amount_received is None:
        amount_received = 0.0
    
    pdf_filename = f"{bill_no}_{tenant_name.replace(' ', '_')}_{month.replace(' ', '_')}.pdf"
    pdf_path = os.path.join(RECEIPTS_DIR, pdf_filename)
    
    receipt_dict = {
        "Bill": bill_no,
        "Date": current_date,
        "Month": month,
        "Tenant": tenant_name,
        "Previous": prev,
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
        from app.core.config_service import config
        generate_professional_pdf(receipt_dict, config.get("landlord", {}), pdf_path)
    except BaseException as e:
        print(f"Error generating PDF: {e}")

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO receipts (
                billno, date, month, tenant_id, tenant, previous, current, units, rent,
                additional, water, tankwater, electricity, total, pdf,
                tenantphone, tenantcompany, tenantaddress, rate, status,
                archiveddate, archivedby, deleteddate, additionalpersons,
                additionalpersonrate, receiptversion, generatedby, paymentstatus,
                maintenancecharge, maintenancedesc, previousarrears, amountreceived
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bill_no, current_date, month, tenant.id, tenant_name, prev, current_reading,
            charges["units"], tenant.rent, charges["additional"], tenant.water, tank_water,
            charges["electricity"], charges["total"], pdf_filename, tenant.phone, tenant.company,
            tenant.address, tenant.electricity_rate, "ACTIVE", "", "", "",
            additional_persons, tenant.additional_person_charge, 8, "Admin",
            payment_status, maintenance_charge, maintenance_desc, previous_arrears, amount_received
        ))
        conn.commit()

    return receipt_dict
def update_bill(bill_no, tenant_name, month, current_reading, additional_persons, tank_water, maintenance_charge, 
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
        
    prev = float(old_receipt["previous"])
    if prev > 0 and current_reading < prev:
        raise ValueError("Current meter reading cannot be less than previous reading.")
        
    charges = calculate_charges(
        current_reading, additional_persons, prev,
        tenant.rent, tenant.water, tank_water, maintenance_charge,
        tenant.electricity_rate, tenant.additional_person_charge
    )
    
    if payment_status == "PAID" and amount_received is None:
        amount_received = charges["total"] + previous_arrears
    elif amount_received is None:
        amount_received = 0.0
        
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
        from app.core.config_service import config
        generate_professional_pdf(updated_dict, config.get("landlord", {}), pdf_path)
    except BaseException as e:
        print(f"Error generating PDF: {e}")

    with get_conn() as conn:
        conn.execute("""
            UPDATE receipts SET
                month = ?, tenant_id = ?, tenant = ?, current = ?, units = ?, rent = ?,
                additional = ?, water = ?, tankwater = ?, electricity = ?, total = ?,
                pdf = ?, tenantphone = ?, tenantcompany = ?, tenantaddress = ?, rate = ?,
                additionalpersons = ?, additionalpersonrate = ?, paymentstatus = ?,
                maintenancecharge = ?, maintenancedesc = ?, previousarrears = ?, amountreceived = ?
            WHERE billno = ?
        """, (
            month, tenant.id, tenant_name, current_reading, charges["units"], tenant.rent,
            charges["additional"], tenant.water, tank_water, charges["electricity"], charges["total"],
            pdf_filename, tenant.phone, tenant.company, tenant.address, tenant.electricity_rate,
            additional_persons, tenant.additional_person_charge, payment_status,
            maintenance_charge, maintenance_desc, previous_arrears, amount_received,
            bill_no
        ))
        conn.commit()

    return updated_dict
def archive_bill(bill_no):
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
    advance_bills_count = 0
    
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

        is_paid = status in ["PAID", "ADVANCE"]
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
            if status == "ADVANCE":
                advance_bills_count += 1
            
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
        "paid_bills_count": paid_bills_count,
        "advance_bills_count": advance_bills_count,
        "collection_rate": collection_rate,
        "recent_bills": recent_bills,
        "chart_labels": chart_months,
        "chart_revenue": revenue_list,
        "chart_electricity": electricity_list
    }