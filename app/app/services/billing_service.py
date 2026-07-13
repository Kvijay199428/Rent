# //File: app\app\services\billing_service.py

from app.core.db import get_conn
import os
import shutil
from datetime import datetime
from app.core.config_service import config
from app.services.tenant_service import load_tenants, update_tenant
from app.services.pdf_service import generate_professional_pdf

from app.core.paths import DB_DIR, BACKUPS_DIR as BACKUP_DIR, RECEIPTS_DIR

def get_bill_details(billNo):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE billNo = ?", (billNo,)).fetchone()
    if row:
        return _row_to_dict(row)
    return None

def resolve_payment_state(currentTotal, previousArrears=0.0, amountReceived=None):
    currentTotal = float(currentTotal or 0)
    previousArrears = float(previousArrears or 0)
    grandTotal = round(currentTotal + previousArrears, 2)
    received = round(float(amountReceived or 0), 2)

    if received <= 0:
        return {
            "paymentStatus": "PENDING",
            "grandTotal": grandTotal,
            "amountReceived": 0.0,
            "balanceDue": max(grandTotal, 0.0),
            "advanceAmount": max(-grandTotal, 0.0) if grandTotal < 0 else 0.0
        }

    if received < grandTotal:
        return {
            "paymentStatus": "PARTIAL",
            "grandTotal": grandTotal,
            "amountReceived": received,
            "balanceDue": round(grandTotal - received, 2),
            "advanceAmount": 0.0
        }

    if received == grandTotal:
        return {
            "paymentStatus": "PAID",
            "grandTotal": grandTotal,
            "amountReceived": received,
            "balanceDue": 0.0,
            "advanceAmount": 0.0
        }

    return {
        "paymentStatus": "ADVANCE",
        "grandTotal": grandTotal,
        "amountReceived": received,
        "balanceDue": 0.0,
        "advanceAmount": round(received - grandTotal, 2)
    }

# def update_paymentStatus(billNo, requestedStatus, amountReceived=None):
#     from app.core.db import get_conn
#     with get_conn() as conn:
#         row = conn.execute("SELECT * FROM receipts WHERE billNo = ?", (billNo,)).fetchone()
#         if not row:
#             raise ValueError("Receipt not found")
        
#         currentTotal = float(row["total"])
#         previousArrears = float(row["previousarrears"])
        
#         state = resolve_payment_state(
#             currentTotal,
#             previousArrears=previousArrears,
#             amountReceived=amountReceived
#         )
#         status = state["paymentStatus"]
#         final_received = state["amountReceived"]
        
#         if requestedStatus in ["PENDING", "PARTIAL"]:
#             status = requestedStatus

#         conn.execute("""
#             UPDATE receipts 
#             SET paymentstatus = ?, amountreceived = ?
#             WHERE billNo = ?
#         """, (status, final_received, billNo))
#         conn.commit()
#     return status
def update_paymentStatus(billNo, requestedStatus, amountReceived=None):
    from app.core.db import get_conn
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE billNo = ?", (billNo,)).fetchone()
        if not row:
            raise ValueError("Receipt not found")
        
        currentTotal = float(row["total"])
        previousArrears = float(row["previousarrears"])
        grandTotal = round(currentTotal + previousArrears, 2)
        
        # Determine final amount
        if amountReceived is None:
            amountReceived = grandTotal if requestedStatus == "PAID" else 0.0
        
        amountReceived = round(float(amountReceived), 2)
        
        # VALIDATE: requestedStatus must match amount logic, OR auto-calculate
        calculatedStatus = "PENDING"
        if amountReceived <= 0:
            calculatedStatus = "PENDING"
        elif amountReceived < grandTotal:
            calculatedStatus = "PARTIAL"
        elif amountReceived == grandTotal:
            calculatedStatus = "PAID"
        else:
            calculatedStatus = "ADVANCE"
        
        # Use requested status if it matches the amount logic, otherwise use calculated
        # This allows explicit control while preventing invalid combinations
        finalStatus = requestedStatus
        
        # Validate consistency (optional strict mode)
        if requestedStatus == "PAID" and amountReceived != grandTotal:
            raise ValueError(f"PAID status requires amount = {grandTotal}, got {amountReceived}")
        if requestedStatus == "PARTIAL" and (amountReceived <= 0 or amountReceived >= grandTotal):
            raise ValueError(f"PARTIAL status requires 0 < amount < {grandTotal}")
        if requestedStatus == "ADVANCE" and amountReceived <= grandTotal:
            raise ValueError(f"ADVANCE status requires amount > {grandTotal}")
        if requestedStatus == "PENDING" and amountReceived != 0:
            raise ValueError("PENDING status requires amount = 0")
        
        conn.execute("""
            UPDATE receipts 
            SET paymentstatus = ?, amountreceived = ?
            WHERE billNo = ?
        """, (finalStatus, amountReceived, billNo))
        conn.commit()
    
    return finalStatus
    
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
        "Bill": row.get("billNo", ""),
        "Date": row.get("date", ""),
        "Month": row.get("month", ""),
        "Tenant": row.get("tenant", ""),
        "TenantId": row.get("tenantId", 0) or 0,
        "Previous": _safe_float(row.get("previous")),
        "Current": _safe_float(row.get("current")),
        "Units": _safe_float(row.get("units")),
        "Rent": _safe_float(row.get("rent")),
        "Additional": _safe_float(row.get("additional")),
        "Water": _safe_float(row.get("water")),
        "tankWater": _safe_float(row.get("tankWater")),
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
        "additionalPersonRate": _safe_float(row.get("additionalpersonrate")),
        "Receipt_Version": _safe_int(row.get("receiptversion")),
        "Generated_By": row.get("generatedby", "Admin") or "Admin",
        "paymentStatus": row.get("paymentstatus", "PENDING") or "PENDING",
        "MaintenanceCharge": _safe_float(row.get("maintenancecharge")),
        "MaintenanceDesc": row.get("maintenancedesc", "") or "",
        "previousArrears": _safe_float(row.get("previousarrears")),
        "amountReceived": _safe_float(row.get("amountreceived")),
    }

def get_all_receipts():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM receipts ORDER BY rowid DESC").fetchall()
    return [_row_to_dict(r) for r in rows]

def get_receipt(billNo):
    receipts = get_all_receipts()
    for r in receipts:
        if r["Bill"] == billNo:
            return r
    return None

def get_latest_receipt(tenantName: str, exclude_BillNo: str = None):
    with get_conn() as conn:
        query = "SELECT * FROM receipts WHERE tenant COLLATE NOCASE = ? AND status != 'ARCHIVED'"
        params = [tenantName]
        if exclude_BillNo:
            query += " AND billNo != ?"
            params.append(exclude_BillNo)
        query += " ORDER BY rowid DESC LIMIT 1"
        row = conn.execute(query, tuple(params)).fetchone()
    if row:
        return _row_to_dict(row)
    return None

def resolve_previous_reading(tenantName: str, exclude_BillNo: str = None) -> float:
    from app.services.tenant_service import get_tenant_by_name
    latest = get_latest_receipt(tenantName, exclude_BillNo)
    if latest:
        return float(latest.get("Current", 0) or 0)
    tenant = get_tenant_by_name(tenantName)
    if tenant:
        return float(getattr(tenant, "previousMeter", 0) or 0)
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

def calculate_charges(current_reading, additional_persons, prev_reading, rent, water, tankWater, MaintenanceCharge, rate, add_person_charge):
    units = max(0.0, current_reading - prev_reading)
    electricity = units * rate
    additional = additional_persons * add_person_charge
    total = rent + additional + water + tankWater + MaintenanceCharge + electricity
    
    return {
        "rent": rent,
        "water": water,
        "tankWater": tankWater,
        "MaintenanceCharge": MaintenanceCharge,
        "rate": rate,
        "additional": additional,
        "units": units,
        "electricity": electricity,
        "total": total,
        "previous": prev_reading
    }

def create_bill(tenantName, month, current_reading, additional_persons, tankWater, MaintenanceCharge, 
                MaintenanceDesc, previousArrears=0.0, amountReceived=None, paymentStatus="PENDING"):
    from app.core.db import get_conn
    from datetime import datetime
    from app.services.tenant_service import load_tenants
    import os
    from app.core.paths import RECEIPTS_DIR
    from app.services.pdf_service import generate_professional_pdf
    
    tenants = load_tenants()
    tenant = next((t for t in tenants if t.name == tenantName), None)
    if not tenant:
        raise ValueError("Tenant not found")

    # FIX: Generate bill number with tenant ID prefix (T1, T2, etc.)
    # Count existing receipts for THIS specific tenant
    with get_conn() as conn:
        tenant_receipt_count = conn.execute(
            "SELECT COUNT(*) FROM receipts WHERE tenantId = ?", 
            (tenant.id,)
        ).fetchone()[0]
    
    # Format: T{tenantId}-{sequence:03d}  e.g., T1-001, T1-002, T2-001
    receipt_seq = tenant_receipt_count + 1
    billNo = f"T{tenant.id}-{receipt_seq:03d}"
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    prev = resolve_previous_reading(tenantName)
    if prev > 0 and current_reading < prev:
        raise ValueError("Current meter reading cannot be less than previous reading.")
    
    charges = calculate_charges(
        current_reading, additional_persons, prev,
        tenant.rent, tenant.water, tankWater, MaintenanceCharge,
        tenant.electricityRate, tenant.additionalPersonCharge
    )
    
    if paymentStatus == "PAID" and amountReceived is None:
        amountReceived = charges["total"] + previousArrears
    elif amountReceived is None:
        amountReceived = 0.0
    
    pdf_filename = f"{billNo}_{tenantName.replace(' ', '_')}_{month.replace(' ', '_')}.pdf"
    pdf_path = os.path.join(RECEIPTS_DIR, pdf_filename)
    
    receipt_dict = {
        "Bill": billNo,
        "Date": current_date,
        "Month": month,
        "Tenant": tenantName,
        "Previous": prev,
        "Current": current_reading,
        "Units": charges["units"],
        "Rent": tenant.rent,
        "Additional": charges["additional"],
        "Water": tenant.water,
        "tankWater": tankWater,
        "Electricity": charges["electricity"],
        "Total": charges["total"],
        "PDF": pdf_filename,
        "Tenant_Phone": tenant.phone,
        "Tenant_Company": tenant.company,
        "Tenant_Address": tenant.address,
        "Rate": tenant.electricityRate,
        "Status": "ACTIVE",
        "Archived_Date": "",
        "Archived_By": "",
        "Deleted_Date": "",
        "Additional_Persons": additional_persons,
        "additionalPersonRate": tenant.additionalPersonCharge,
        "Receipt_Version": 8,
        "Generated_By": "Admin",
        "paymentStatus": paymentStatus,
        "MaintenanceCharge": MaintenanceCharge,
        "MaintenanceDesc": MaintenanceDesc,
        "previousArrears": previousArrears,
        "amountReceived": amountReceived
    }
    
    try:
        from app.core.config_service import config
        generate_professional_pdf(receipt_dict, config.get("landlord", {}), pdf_path)
    except BaseException as e:
        print(f"Error generating PDF: {e}")

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO receipts (
                billNo, date, month, tenantId, tenant, previous, current, units, rent,
                additional, water, tankWater, electricity, total, pdf,
                tenantphone, tenantcompany, tenantaddress, rate, status,
                archiveddate, archivedby, deleteddate, additionalpersons,
                additionalpersonrate, receiptversion, generatedby, paymentstatus,
                maintenancecharge, maintenancedesc, previousarrears, amountreceived
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            billNo, current_date, month, tenant.id, tenantName, prev, current_reading,
            charges["units"], tenant.rent, charges["additional"], tenant.water, tankWater,
            charges["electricity"], charges["total"], pdf_filename, tenant.phone, tenant.company,
            tenant.address, tenant.electricityRate, "ACTIVE", "", "", "",
            additional_persons, tenant.additionalPersonCharge, 8, "Admin",
            paymentStatus, MaintenanceCharge, MaintenanceDesc, previousArrears, amountReceived
        ))
        conn.commit()

    return receipt_dict
def update_bill(billNo, tenantName, month, current_reading, additional_persons, tankWater, MaintenanceCharge, 
                MaintenanceDesc, previousArrears=0.0, amountReceived=None, paymentStatus="PENDING"):
    from app.core.db import get_conn
    from app.services.tenant_service import load_tenants
    from app.services.pdf_service import generate_professional_pdf
    import os
    from app.core.paths import RECEIPTS_DIR
    
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE billNo = ?", (billNo,)).fetchone()
        if not row:
            raise ValueError("Receipt not found")
        old_receipt = dict(row)

    tenants = load_tenants()
    tenant = next((t for t in tenants if t.name == tenantName), None)
    if not tenant:
        raise ValueError("Tenant not found")
        
    prev = float(old_receipt["previous"])
    if prev > 0 and current_reading < prev:
        raise ValueError("Current meter reading cannot be less than previous reading.")
        
    charges = calculate_charges(
        current_reading, additional_persons, prev,
        tenant.rent, tenant.water, tankWater, MaintenanceCharge,
        tenant.electricityRate, tenant.additionalPersonCharge
    )
    
    if paymentStatus == "PAID" and amountReceived is None:
        amountReceived = charges["total"] + previousArrears
    elif amountReceived is None:
        amountReceived = 0.0
        
    pdf_filename = old_receipt.get("pdf", f"{billNo}_{tenantName.replace(' ', '_')}_{month.replace(' ', '_')}.pdf")
    pdf_path = os.path.join(RECEIPTS_DIR, pdf_filename)
    
    updated_dict = {
        "Bill": billNo,
        "Date": old_receipt["date"],
        "Month": month,
        "Tenant": tenantName,
        "Previous": old_receipt["previous"],
        "Current": current_reading,
        "Units": charges["units"],
        "Rent": tenant.rent,
        "Additional": charges["additional"],
        "Water": tenant.water,
        "tankWater": tankWater,
        "Electricity": charges["electricity"],
        "Total": charges["total"],
        "PDF": pdf_filename,
        "Tenant_Phone": tenant.phone,
        "Tenant_Company": tenant.company,
        "Tenant_Address": tenant.address,
        "Rate": tenant.electricityRate,
        "Status": old_receipt["status"],
        "Archived_Date": old_receipt["archiveddate"],
        "Archived_By": old_receipt["archivedby"],
        "Deleted_Date": old_receipt["deleteddate"],
        "Additional_Persons": additional_persons,
        "additionalPersonRate": tenant.additionalPersonCharge,
        "Receipt_Version": old_receipt.get("receiptversion", 8),
        "Generated_By": old_receipt.get("generatedby", "Admin"),
        "paymentStatus": paymentStatus,
        "MaintenanceCharge": MaintenanceCharge,
        "MaintenanceDesc": MaintenanceDesc,
        "previousArrears": previousArrears,
        "amountReceived": amountReceived
    }
    
    try:
        from app.core.config_service import config
        generate_professional_pdf(updated_dict, config.get("landlord", {}), pdf_path)
    except BaseException as e:
        print(f"Error generating PDF: {e}")

    with get_conn() as conn:
        conn.execute("""
            UPDATE receipts SET
                month = ?, tenantId = ?, tenant = ?, current = ?, units = ?, rent = ?,
                additional = ?, water = ?, tankWater = ?, electricity = ?, total = ?,
                pdf = ?, tenantphone = ?, tenantcompany = ?, tenantaddress = ?, rate = ?,
                additionalpersons = ?, additionalpersonrate = ?, paymentstatus = ?,
                maintenancecharge = ?, maintenancedesc = ?, previousarrears = ?, amountreceived = ?
            WHERE billNo = ?
        """, (
            month, tenant.id, tenantName, current_reading, charges["units"], tenant.rent,
            charges["additional"], tenant.water, tankWater, charges["electricity"], charges["total"],
            pdf_filename, tenant.phone, tenant.company, tenant.address, tenant.electricityRate,
            additional_persons, tenant.additionalPersonCharge, paymentStatus,
            MaintenanceCharge, MaintenanceDesc, previousArrears, amountReceived,
            billNo
        ))
        conn.commit()

    return updated_dict
def archive_bill(billNo):
    from app.core.db import get_conn
    from datetime import datetime
    with get_conn() as conn:
        conn.execute("""
            UPDATE receipts SET status = 'ARCHIVED', archiveddate = ?, archivedby = 'Admin'
            WHERE billNo = ? AND status != 'ARCHIVED'
        """, (datetime.now().strftime("%Y-%m-%d"), billNo))
        conn.commit()
    return get_receipt(billNo)

def restore_bill(billNo):
    from app.core.db import get_conn
    with get_conn() as conn:
        conn.execute("""
            UPDATE receipts SET status = 'ACTIVE', archiveddate = '', archivedby = ''
            WHERE billNo = ? AND status != 'ACTIVE'
        """, (billNo,))
        conn.commit()
    return get_receipt(billNo)

def delete_bill(billNo):
    from app.core.db import get_conn
    with get_conn() as conn:
        row = conn.execute("SELECT status FROM receipts WHERE billNo = ?", (billNo,)).fetchone()
        if not row:
            raise ValueError("Receipt not found")
        if row["status"] != "ARCHIVED":
            raise ValueError("Only archived receipts can be permanently deleted.")
        conn.execute("DELETE FROM receipts WHERE billNo = ?", (billNo,))
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
            
        status = r.get("paymentStatus", "PENDING")
        gross_amount = float(r.get("Total", 0) or 0) + float(r.get("previousArrears", 0) or 0)

        raw_recv = r.get("amountReceived")
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
            "billNo": r["Bill"],
            "tenantName": r["Tenant"],
            "total": float(r.get("Total", 0)) + float(r.get("previousArrears", 0)),
            "amountReceived": float(r.get("amountReceived", 0) or 0),
            "month": r["Month"],
            "paymentStatus": r.get("paymentStatus", "PENDING"),
            "previousArrears": float(r.get("previousArrears", 0))
        })
        
    revenue_chart_data = {m: 0.0 for m in months_names}
    electricity_chart_data = {m: 0.0 for m in months_names}
    
    for r in active_receipts:
        try:
            r_month, r_year = r["Month"].split()
            if r_year == str(current_year) and r_month in revenue_chart_data:
                revenue_chart_data[r_month] += float(r.get("amountReceived", r.get("Total", 0)))
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

def save_all_receipts(receipts_list):
    """Saves a batch of receipt dictionaries into the SQLite database. Used for imports."""
    from app.core.db import get_conn
    from app.services.tenant_service import load_tenants
    
    tenants = load_tenants()
    tenant_map = {t.name.lower(): t for t in tenants}
    
    with get_conn() as conn:
        for r in receipts_list:
            tenantName = r.get("Tenant", "")
            tenant = tenant_map.get(tenantName.lower())
            tenantId = tenant.id if tenant else None
            
            billNo = r.get("Bill")
            if not billNo:
                continue
                
            exists = conn.execute("SELECT 1 FROM receipts WHERE billNo = ?", (billNo,)).fetchone()
            
            if exists:
                conn.execute("""
                    UPDATE receipts SET
                        date = ?, month = ?, tenantId = ?, tenant = ?, previous = ?, current = ?, units = ?, rent = ?,
                        additional = ?, water = ?, tankWater = ?, electricity = ?, total = ?, pdf = ?,
                        tenantphone = ?, tenantcompany = ?, tenantaddress = ?, rate = ?, status = ?,
                        archiveddate = ?, archivedby = ?, deleteddate = ?, additionalpersons = ?,
                        additionalpersonrate = ?, receiptversion = ?, generatedby = ?, paymentstatus = ?,
                        maintenancecharge = ?, maintenancedesc = ?, previousarrears = ?, amountreceived = ?
                    WHERE billNo = ?
                """, (
                    r.get("Date", ""), r.get("Month", ""), tenantId, tenantName, r.get("Previous", 0), r.get("Current", 0),
                    r.get("Units", 0), r.get("Rent", 0), r.get("Additional", 0), r.get("Water", 0), r.get("tankWater", 0),
                    r.get("Electricity", 0), r.get("Total", 0), r.get("PDF", ""), r.get("Tenant_Phone", ""),
                    r.get("Tenant_Company", ""), r.get("Tenant_Address", ""), r.get("Rate", 0), r.get("Status", "ACTIVE"),
                    r.get("Archived_Date", ""), r.get("Archived_By", ""), r.get("Deleted_Date", ""), r.get("Additional_Persons", 0),
                    r.get("additionalPersonRate", 0), r.get("Receipt_Version", 8), r.get("Generated_By", "Import"),
                    r.get("paymentStatus", "PENDING"), r.get("MaintenanceCharge", 0), r.get("MaintenanceDesc", ""),
                    r.get("previousArrears", 0), r.get("amountReceived", 0), billNo
                ))
            else:
                conn.execute("""
                    INSERT INTO receipts (
                        billNo, date, month, tenantId, tenant, previous, current, units, rent,
                        additional, water, tankWater, electricity, total, pdf,
                        tenantphone, tenantcompany, tenantaddress, rate, status,
                        archiveddate, archivedby, deleteddate, additionalpersons,
                        additionalpersonrate, receiptversion, generatedby, paymentstatus,
                        maintenancecharge, maintenancedesc, previousarrears, amountreceived
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    billNo, r.get("Date", ""), r.get("Month", ""), tenantId, tenantName, r.get("Previous", 0), r.get("Current", 0),
                    r.get("Units", 0), r.get("Rent", 0), r.get("Additional", 0), r.get("Water", 0), r.get("tankWater", 0),
                    r.get("Electricity", 0), r.get("Total", 0), r.get("PDF", ""), r.get("Tenant_Phone", ""),
                    r.get("Tenant_Company", ""), r.get("Tenant_Address", ""), r.get("Rate", 0), r.get("Status", "ACTIVE"),
                    r.get("Archived_Date", ""), r.get("Archived_By", ""), r.get("Deleted_Date", ""), r.get("Additional_Persons", 0),
                    r.get("additionalPersonRate", 0), r.get("Receipt_Version", 8), r.get("Generated_By", "Import"),
                    r.get("paymentStatus", "PENDING"), r.get("MaintenanceCharge", 0), r.get("MaintenanceDesc", ""),
                    r.get("previousArrears", 0), r.get("amountReceived", 0)
                ))
        conn.commit()

