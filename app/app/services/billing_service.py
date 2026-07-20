# //File: app\app\services\billing_service.py
# POLICY: tenantId is the only identity key for tenant-related data.
# tenantName is display-only and must never be used for joins, ownership, lookup, or mutation.

from app.core.db import get_conn
import os
import shutil
from datetime import datetime
from app.core.config_service import config
from app.services.tenant_service import load_tenants, update_tenant
from app.services.pdf_service import generate_professional_pdf

from app.core.paths import DB_DIR, BACKUPS_DIR as BACKUP_DIR, RECEIPTS_DIR

def get_bill_details(tenantId, billNo):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE tenantId = ? AND billNo = ?", (tenantId, billNo)).fetchone()
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
def update_paymentStatus(tenantId, billNo, requestedStatus, amountReceived=None):
    from app.core.db import get_conn
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE tenantId = ? AND billNo = ?", (tenantId, billNo)).fetchone()
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
            WHERE tenantId = ? AND billNo = ?
        """, (finalStatus, amountReceived, tenantId, billNo))
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

def get_active_tenant_ids() -> set:
    """Returns a set of tenant IDs that are NOT archived."""
    from app.services.tenant_service import load_tenants
    tenants = load_tenants(include_archived=False)
    return {t.id for t in tenants}

def get_all_receipts(include_archived_tenants: bool = False):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM receipts ORDER BY rowid DESC").fetchall()
    
    receipts = [_row_to_dict(r) for r in rows]
    
    if not include_archived_tenants:
        active_ids = get_active_tenant_ids()
        receipts = [r for r in receipts if int(r.get("TenantId", 0) or 0) in active_ids]
    
    return receipts

def get_receipts_for_tenant(tenant_id: int, include_archived: bool = False) -> list:
    """Fetch all receipts for a single tenant by ID.
    
    Use this everywhere instead of name-based filtering. The relationship key is
    TenantId, not the mutable tenant name, so this is rename-safe.
    """
    receipts = get_all_receipts(include_archived_tenants=True)
    result = [r for r in receipts if int(r.get("TenantId", 0) or 0) == int(tenant_id)]
    if not include_archived:
        result = [r for r in result if (r.get("Status") or "").upper() != "ARCHIVED"]
    return result

def get_receipt(tenantId, billNo):
    from app.core.db import get_conn
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE tenantId = ? AND billNo = ?", (tenantId, billNo)).fetchone()
    if row:
        return _row_to_dict(row)
    return None

def get_latest_receipt(tenantId: int, exclude_BillNo: str = None):
    with get_conn() as conn:
        query = "SELECT * FROM receipts WHERE tenantId = ? AND status != 'ARCHIVED'"
        params = [tenantId]
        if exclude_BillNo:
            query += " AND billNo != ?"
            params.append(exclude_BillNo)
        query += " ORDER BY rowid DESC LIMIT 1"
        row = conn.execute(query, tuple(params)).fetchone()
    if row:
        return _row_to_dict(row)
    return None

def resolve_previous_reading(tenantId: int, exclude_BillNo: str = None) -> float:
    from app.services.tenant_service import get_tenant
    latest = get_latest_receipt(tenantId, exclude_BillNo)
    if latest:
        return float(latest.get("Current", 0) or 0)
    tenant = get_tenant(tenantId)
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

def create_bill(tenantId, month, current_reading, additional_persons, tankWater, MaintenanceCharge, 
                MaintenanceDesc, previousArrears=0.0, amountReceived=None, paymentStatus="PENDING"):
    from app.core.db import get_conn
    from datetime import datetime
    from app.services.tenant_service import get_tenant
    import os
    from app.core.paths import RECEIPTS_DIR
    from app.services.pdf_service import generate_professional_pdf
    
    tenant = get_tenant(tenantId)
    if not tenant:
        raise ValueError("Tenant not found")
    tenantName = tenant.name

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
    
    prev = resolve_previous_reading(tenantId)
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
def update_bill(tenantId, billNo, month, current_reading, additional_persons, tankWater, MaintenanceCharge, 
                MaintenanceDesc, previousArrears=0.0, amountReceived=None, paymentStatus="PENDING"):
    from app.core.db import get_conn
    from app.services.tenant_service import get_tenant
    from app.services.pdf_service import generate_professional_pdf
    import os
    from app.core.paths import RECEIPTS_DIR
    
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE tenantId = ? AND billNo = ?", (tenantId, billNo)).fetchone()
        if not row:
            raise ValueError("Receipt not found")
        old_receipt = dict(row)

    tenant = get_tenant(tenantId)
    if not tenant:
        raise ValueError("Tenant not found")
    tenantName = tenant.name
        
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
def archive_bill(tenantId, billNo):
    from app.core.db import get_conn
    from datetime import datetime
    with get_conn() as conn:
        row = conn.execute(
            "SELECT status FROM receipts WHERE tenantId = ? AND billNo = ?",
            (tenantId, billNo),
        ).fetchone()
        if not row:
            raise ValueError("Bill not found for this tenant.")

        conn.execute("""
            UPDATE receipts SET status = 'ARCHIVED', archiveddate = ?, archivedby = 'Admin'
            WHERE tenantId = ? AND billNo = ? AND status != 'ARCHIVED'
        """, (datetime.now().strftime("%Y-%m-%d"), tenantId, billNo))
        conn.commit()
    return get_receipt(tenantId, billNo)

def restore_bill(tenantId, billNo):
    from app.core.db import get_conn
    with get_conn() as conn:
        row = conn.execute(
            "SELECT status, tenantId FROM receipts WHERE tenantId = ? AND billNo = ?",
            (tenantId, billNo),
        ).fetchone()
        if not row:
            raise ValueError("Bill not found for this tenant.")

        conn.execute("""
            UPDATE receipts SET status = 'ACTIVE', archiveddate = '', archivedby = ''
            WHERE tenantId = ? AND billNo = ? AND status != 'ACTIVE'
        """, (tenantId, billNo))
        conn.commit()
    return get_receipt(tenantId, billNo)

def delete_bill(tenantId, billNo):
    from app.core.db import get_conn
    from app.services.tenant_service import get_tenant
    with get_conn() as conn:
        row = conn.execute("SELECT status, tenantId FROM receipts WHERE tenantId = ? AND billNo = ?", (tenantId, billNo)).fetchone()
        if not row:
            raise ValueError("Receipt not found")

        is_archived = str(row["status"]).upper() == "ARCHIVED"

        # Also allow deletion if the tenant is archived
        tenant = get_tenant(tenantId)
        is_tenant_archived = tenant is not None and str(tenant.status).upper() == "ARCHIVED"

        if not (is_archived or is_tenant_archived):
            raise ValueError("Only archived receipts can be permanently deleted.")

        conn.execute("DELETE FROM receipts WHERE tenantId = ? AND billNo = ?", (tenantId, billNo))
        conn.commit()


def get_dashboard_stats():
    
    billing_conf = config.get("billing", {})
    receipts = get_all_receipts(include_archived_tenants=False)
    tenants = load_tenants(include_archived=False)
    
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
    
    active_tenants = [t for t in tenants if t.status == "Active"]
    inactive_tenants = [t for t in tenants if t.status == "Inactive"]
    total_tenants = len(tenants)

    active_receipts = [r for r in receipts if (r.get("Status") or "ACTIVE").upper() == "ACTIVE"]
    archived_receipts = [r for r in receipts if (r.get("Status") or "").upper() == "ARCHIVED"]
    total_active_receipts = len(active_receipts)
    total_archived_receipts = len(archived_receipts)
    total_receipts_all = total_active_receipts + total_archived_receipts
    
    monthly_revenue = 0.0
    prev_monthly_revenue = 0.0
    lifetime_revenue = 0.0

    pending_payments_count = 0          # unique tenants with dues
    pending_payments_amount = 0.0       # total due amount across PENDING/PARTIAL receipts
    pending_receipts_count = 0          # number of due receipts

    amount_collected = 0.0
    electricity_consumed_this_month = 0.0

    highest_meter_reading = 0.0
    highest_meter_tenant_id = 0
    highest_meter_bill_no = ""

    paid_bills_count = 0
    advance_bills_count = 0
    due_tenant_ids = set()
    
    for r in active_receipts:
        try:
            current_reading = float(r.get("Current", 0.0) or 0.0)
            if current_reading > highest_meter_reading:
                highest_meter_reading = current_reading
                highest_meter_tenant_id = int(r.get("TenantId", 0) or 0)
                highest_meter_bill_no = r.get("Bill", "")
        except Exception:
            pass

        status = str(r.get("paymentStatus", "PENDING")).upper()
        base_total = float(r.get("Total", 0) or 0)
        previous_arrears = float(r.get("previousArrears", 0) or 0)
        grand_total = round(base_total + previous_arrears, 2)

        raw_recv = r.get("amountReceived")
        if raw_recv not in (None, ""):
            received = round(float(raw_recv), 2)
        else:
            received = grand_total if status == "PAID" else 0.0

        outstanding = round(max(grand_total - received, 0.0), 2)

        amount_collected += received
        lifetime_revenue += received

        if r.get("Month") == current_month_str:
            monthly_revenue += received
            try:
                electricity_consumed_this_month += float(r.get("Units", 0.0) or 0.0)
            except Exception:
                pass

        if r.get("Month") == prev_month_str:
            prev_monthly_revenue += received

        if status in ("PENDING", "PARTIAL") and outstanding > 0:
            pending_receipts_count += 1
            pending_payments_amount += outstanding
            due_tenant_ids.add(int(r.get("TenantId", 0) or 0))

        if status in ("PAID", "ADVANCE"):
            paid_bills_count += 1
            if status == "ADVANCE":
                advance_bills_count += 1
            
    pending_payments_count = len(due_tenant_ids)

    revenue_change_str = ""
    if prev_monthly_revenue == 0.0:
        revenue_change_str = "New Month"
    else:
        diff = monthly_revenue - prev_monthly_revenue
        pct = (diff / prev_monthly_revenue) * 100
        sign = "+" if diff >= 0 else ""
        revenue_change_str = f"{sign}{pct:.2f}%"

    collection_rate = 0.0
    if total_active_receipts > 0:
        collection_rate = (paid_bills_count / total_active_receipts) * 100
        
    recent_bills = []
    for r in active_receipts[-5:][::-1]:
        recent_bills.append({
            "billNo": r.get("Bill"),
            "tenantName": r.get("Tenant"),
            "tenantId": int(r.get("TenantId", 0) or 0),
            "total": float(r.get("Total", 0) or 0),
            "amountReceived": float(r.get("amountReceived", 0) or 0),
            "month": r.get("Month"),
            "paymentStatus": r.get("paymentStatus", "PENDING"),
            "previousArrears": float(r.get("previousArrears", 0) or 0),
        })
        
    revenue_chart_data = {m: 0.0 for m in months_names}
    electricity_chart_data = {m: 0.0 for m in months_names}

    for r in active_receipts:
        try:
            r_month, r_year = str(r.get("Month", "")).split()
            if r_year == str(current_year) and r_month in revenue_chart_data:
                r_status = str(r.get("paymentStatus", "PENDING")).upper()
                r_total = float(r.get("Total", 0) or 0) + float(r.get("previousArrears", 0) or 0)
                r_received_raw = r.get("amountReceived")
                r_received = float(r_received_raw) if r_received_raw not in (None, "") else (r_total if r_status == "PAID" else 0.0)
                revenue_chart_data[r_month] += r_received
                electricity_chart_data[r_month] += float(r.get("Units", 0.0) or 0.0)
        except Exception:
            pass

    chart_months = [m for m in months_names if revenue_chart_data[m] != 0 or electricity_chart_data[m] != 0]
    if not chart_months:
        chart_months = months_names[:current_month_idx]

    revenue_list = [revenue_chart_data[m] for m in chart_months]
    electricity_list = [electricity_chart_data[m] for m in chart_months]

    return {
        "next_bill": next_bill,
        "current_month": current_month_str,

        "monthly_revenue": monthly_revenue,
        "lifetime_revenue": lifetime_revenue,
        "prev_monthly_revenue": prev_monthly_revenue,
        "revenue_change_str": revenue_change_str,

        "total_active_receipts": total_active_receipts,
        "total_archived_receipts": total_archived_receipts,
        "total_receipts_all": total_receipts_all,

        "active_tenants": len(active_tenants),
        "inactive_tenants": len(inactive_tenants),
        "total_tenants": total_tenants,

        "highest_meter_reading": highest_meter_reading,
        "highest_meter_tenant_id": highest_meter_tenant_id,
        "highest_meter_bill_no": highest_meter_bill_no,

        "electricity_consumed": electricity_consumed_this_month,

        "pending_payments_count": pending_payments_count,
        "pending_payments_amount": pending_payments_amount,
        "pending_receipts_count": pending_receipts_count,
        "pending_amount": pending_payments_amount,  # backward compat alias

        "amount_collected": amount_collected,
        "paid_bills_count": paid_bills_count,
        "advance_bills_count": advance_bills_count,
        "collection_rate": collection_rate,

        "recent_bills": recent_bills,
        "chart_labels": chart_months,
        "chart_revenue": revenue_list,
        "chart_electricity": electricity_list,
    }


def save_all_receipts(receipts_list):
    """Saves a batch of receipt dictionaries into the SQLite database.

    POLICY: TenantId is required in each receipt dict. Rows missing a valid
    TenantId are skipped — the caller must supply the correct ID. Name-based
    tenant resolution has been removed to prevent cross-tenant contamination.
    """
    import logging
    from app.core.db import get_conn
    from app.services.tenant_service import load_tenants

    # Build an ID set for fast existence checks — used only for validation,
    # not for ownership derivation.
    tenants = load_tenants(include_archived=True)
    valid_tenant_ids = {t.id for t in tenants}

    with get_conn() as conn:
        for r in receipts_list:
            billNo = r.get("Bill")
            if not billNo:
                continue

            # Require TenantId; never derive it from tenant name.
            raw_tid = r.get("TenantId") or r.get("tenantId")
            tenantId = int(raw_tid) if raw_tid is not None else None
            if not tenantId or tenantId not in valid_tenant_ids:
                logging.warning(
                    "save_all_receipts: skipping billNo=%s — missing or invalid TenantId=%s",
                    billNo, tenantId
                )
                continue

            tenantName = r.get("Tenant", "")  # display snapshot only

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

