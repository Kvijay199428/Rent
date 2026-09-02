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
        row = conn.execute("SELECT * FROM receipts WHERE tenantId = %s AND billNo = %s", (tenantId, billNo)).fetchone()
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
def update_paymentStatus(tenantId, billNo, requestedStatus, amountReceived=None, landlord_id=None):
    from app.core.db import get_conn
    from app.services.tenant_service import get_tenant
    if landlord_id is not None and not get_tenant(tenantId, landlord_id):
        raise ValueError("Tenant not found")
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE tenantId = %s AND billNo = %s", (tenantId, billNo)).fetchone()
        if not row:
            raise ValueError("Receipt not found")

        # Normalize the chain first so validation and the PAID default use the
        # authoritative running balance entering this bill.
        recompute_tenant_arrear_chain(conn, tenantId)
        row = conn.execute("SELECT * FROM receipts WHERE tenantId = %s AND billNo = %s", (tenantId, billNo)).fetchone()

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
            SET paymentstatus = %s, amountreceived = %s
            WHERE tenantId = %s AND billNo = %s
        """, (finalStatus, amountReceived, tenantId, billNo))
        recompute_tenant_arrear_chain(conn, tenantId)
        conn.commit()

    # Keep the payment_entries ledger authoritative: ensure a payment entry
    # exists covering the amount set here, so the invariant
    # amountreceived == SUM(active payment_entries) holds and the settlement
    # engine sees the actual transaction.
    try:
        from app.services.payment_service import sync_bill_payment_from_receipt
        sync_bill_payment_from_receipt(tenantId, billNo, amountReceived)
    except Exception:
        pass

    # Ensure settlement/allocation markers reflect the latest state for the
    # whole tenant (a PAID on this bill may have cleared earlier arrears).
    try:
        from app.services.payment_service import get_tenant_settlement_state
        finalState = get_tenant_settlement_state(tenantId)
    except Exception:
        finalState = None

    if finalState is not None:
        return {"status": finalStatus, "settlement": finalState}
    return {"status": finalStatus}
    
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
        "settledByBill": row.get("settled_by_bill_no", "") or "",
        "settlementType": row.get("settlement_type", "") or "NONE",
        "settledAt": row.get("settled_at", "") or "",
        "settlementAmount": _safe_float(row.get("settlement_amount")),
    }

_MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"]

def _attach_payment_facts(receipts: list) -> list:
    """Attach paymentCount / lastPaymentDate to a list of receipt dicts."""
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT billNo, COUNT(*) AS cnt, MAX(payment_date) AS last_date "
                "FROM payment_entries WHERE status = 'ACTIVE' GROUP BY billNo"
            ).fetchall()
        facts = {r["billNo"]: (int(r["cnt"] or 0), r["last_date"] or "") for r in rows}
    except Exception:
        return receipts
    for r in receipts:
        cnt, last = facts.get(r.get("Bill"), (0, ""))
        r["paymentCount"] = cnt
        r["lastPaymentDate"] = last
    return receipts

def _month_sort_key(month_str: str):
    """Sort key for 'January 2026' style month strings; unknown months sort last."""
    parts = str(month_str or "").strip().split()
    if len(parts) == 2 and parts[0] in _MONTH_NAMES and parts[1].isdigit():
        return (int(parts[1]), _MONTH_NAMES.index(parts[0]))
    return (99999, 99)

def get_tenant_balance(tenant_id: int) -> float:
    """Total accumulated balance owed by a tenant across all active receipts.

    Balance = Σ Total − Σ amountReceived over non-archived receipts. In the
    running-balance model this equals the latest bill's due amount (the latest
    bill already carries all previous arrears) and is the value that must be
    carried forward as the next bill's previousArrears.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(COALESCE(total,0)),0) - COALESCE(SUM(COALESCE(amountreceived,0)),0) AS balance "
            "FROM receipts WHERE tenantId = %s AND status != 'ARCHIVED'",
            (tenant_id,),
        ).fetchone()
    return round(float(row["balance"] or 0), 2)

def recompute_tenant_arrear_chain(conn, tenant_id: int) -> list:
    """Recompute cumulative previousArrears for every active receipt of a tenant.

    Receipts are ordered chronologically (parsed month, rowid tiebreak) and each
    bill's previousArrears is set to the running balance entering it, so the
    latest bill carries the full accumulated unpaid balance from the first bill
    to the current one. Payments recorded on an earlier bill therefore cascade
    forward automatically.

    Best-effort regenerates the PDF of every bill whose previousArrears changed.

    Returns the list of bill numbers whose previousArrears changed.
    """
    from app.services.pdf_service import generate_professional_pdf
    from app.services.landlord_config_service import get_effective_landlord_config

    rows = conn.execute(
        "SELECT id AS rowid, * FROM receipts WHERE tenantId = %s AND status != 'ARCHIVED'",
        (tenant_id,),
    ).fetchall()

    ordered = sorted(rows, key=lambda r: (_month_sort_key(r["month"]), r["rowid"]))

    running = 0.0
    changed = []
    landlord_id = None
    for r in ordered:
        if landlord_id is None and "landlord_id" in r.keys():
            landlord_id = r["landlord_id"]
        total = float(r["total"] or 0)
        received = float(r["amountreceived"] or 0)
        expected_prev = round(running, 2)
        actual_prev = round(float(r["previousarrears"] or 0), 2)
        if abs(expected_prev - actual_prev) > 0.001:
            conn.execute(
                "UPDATE receipts SET previousarrears = %s WHERE billNo = %s AND tenantId = %s",
                (expected_prev, r["billNo"], tenant_id),
            )
            changed.append(r["billNo"])
        running += total - received

    if changed:
        try:
            conf = get_effective_landlord_config(landlord_id) if landlord_id else {}
            fresh = conn.execute(
                "SELECT id AS rowid, * FROM receipts WHERE tenantId = %s AND status != 'ARCHIVED'",
                (tenant_id,),
            ).fetchall()
            fresh_by_no = {r["billNo"]: r for r in fresh}
            for bill_no in changed:
                r = fresh_by_no.get(bill_no)
                if r is None:
                    continue
                try:
                    pdf_name = r["pdf"] or f"{r['billNo']}.pdf"
                    pdf_path = os.path.join(RECEIPTS_DIR, pdf_name)
                    generate_professional_pdf(_row_to_dict(r), conf, pdf_path)
                except Exception:
                    pass
        except Exception:
            pass

    # Keep the settlement/allocation ledger in sync with the (possibly changed)
    # running balances. A payment recorded on a later bill may have cleared
    # earlier arrears; this marks those historical bills as settled so they stop
    # contributing to current dues without rewriting their original status.
    try:
        from app.services.payment_service import _recompute_tenant_settlement
        _recompute_tenant_settlement(conn, tenant_id)
    except Exception:
        pass

    return changed

def get_active_tenant_ids(landlord_id=None) -> set:
    """Returns a set of tenant IDs (optionally scoped to a landlord) that are NOT archived."""
    from app.services.tenant_service import load_tenants
    tenants = load_tenants(include_archived=False, landlord_id=landlord_id)
    return {t.id for t in tenants}

def get_all_receipts(include_archived_tenants: bool = False, landlord_id=None):
    clauses = []
    params: list = []
    if landlord_id is not None:
        clauses.append("landlord_id = %s")
        params.append(landlord_id)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with get_conn() as conn:
        rows = conn.execute(f"SELECT * FROM receipts{where} ORDER BY id DESC", tuple(params)).fetchall()
    
    receipts = [_row_to_dict(r) for r in rows]
    
    if not include_archived_tenants:
        active_ids = get_active_tenant_ids(landlord_id=landlord_id)
        receipts = [r for r in receipts if int(r.get("TenantId", 0) or 0) in active_ids]
    
    return _attach_payment_facts(receipts)

def get_receipts_for_tenant(tenant_id: int, include_archived: bool = False, landlord_id=None) -> list:
    """Fetch all receipts for a single tenant by ID.
    
    Use this everywhere instead of name-based filtering. The relationship key is
    TenantId, not the mutable tenant name, so this is rename-safe.
    """
    receipts = get_all_receipts(include_archived_tenants=True, landlord_id=landlord_id)
    result = [r for r in receipts if int(r.get("TenantId", 0) or 0) == int(tenant_id)]
    if not include_archived:
        result = [r for r in result if (r.get("Status") or "").upper() != "ARCHIVED"]
    return result

def get_receipt(tenantId, billNo, landlord_id=None):
    from app.core.db import get_conn
    with get_conn() as conn:
        query = "SELECT * FROM receipts WHERE tenantId = %s AND billNo = %s"
        params: list = [tenantId, billNo]
        if landlord_id is not None:
            query += " AND tenantId IN (SELECT id FROM tenants WHERE landlord_id = %s)"
            params.append(landlord_id)
        row = conn.execute(query, tuple(params)).fetchone()
    if row:
        return _row_to_dict(row)
    return None

def _bill_sequence(bill_no: str):
    """Return the numeric sequence of a bill number for chain ordering.

    Bill numbers are formatted T{tenantId}-{sequence:03d} (e.g. T1-001, T1-002).
    The sequence is the trailing numeric component; unknown/unparseable bill
    numbers sort last so they never shadow a valid predecessor.
    """
    s = str(bill_no or "").split("-")[-1].strip()
    if s.isdigit():
        return int(s)
    return 1 << 60

def _get_bill_predecessor(conn, tenant_id: int, target_bill_no: str):
    """Return the active receipt immediately preceding a target bill.

    The chain rule: a bill's `previous` reading is the current reading of the
    bill with the highest sequence strictly below the target's own sequence.
    The target bill is excluded from the candidate set so an edit cannot resolve
    its predecessor from itself. Returns None when the target has no
    predecessor (i.e. it is the tenant's first bill), in which case the caller
    falls back to tenant.previousMeter.
    """
    rows = conn.execute(
        "SELECT id AS rowid, * FROM receipts WHERE tenantId = %s AND status != 'ARCHIVED'",
        (tenant_id,),
    ).fetchall()
    target_seq = _bill_sequence(target_bill_no)
    candidates = [
        r for r in rows
        if r["billNo"] != target_bill_no and _bill_sequence(r["billNo"]) < target_seq
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda r: _bill_sequence(r["billNo"]))
    return candidates[-1]

def get_latest_receipt(tenantId: int, exclude_BillNo: str = None):
    with get_conn() as conn:
        query = "SELECT * FROM receipts WHERE tenantId = %s AND status != 'ARCHIVED'"
        params = [tenantId]
        if exclude_BillNo:
            query += " AND billNo != %s"
            params.append(exclude_BillNo)
        rows = conn.execute(query, tuple(params)).fetchall()
    # Order by bill sequence (T{n}-{seq}) so chain resolution and create-bill
    # fallbacks follow the same canonical ordering as bill edits, rather than
    # insertion order (rowid) which can diverge.
    if rows:
        rows.sort(key=lambda r: _bill_sequence(r["billNo"]))
        return _row_to_dict(rows[-1])
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

def _rebuild_meter_chain(conn, tenant_id: int, starting_bill_no: str,
                         landlord_id=None) -> list:
    """Recompute every billing field for bills downstream of an edited bill.

    Maintains the meter-reading chain invariant:
        bill[n].previous == bill[n-1].current    (n > 1)
        bill[1].previous  == tenant.previousMeter

    When a bill's current reading changes, every subsequent bill must have its
    `previous`, `units`, `electricity`, and `total` recalculated so the chain
    stays internally consistent. Each downstream bill's previous is resolved
    from its own immediate predecessor (the single canonical rule).

    Returns the list of bill numbers whose persisted charges changed, so the
    caller can regenerate their PDFs.
    """
    from app.services.landlord_config_service import get_effective_landlord_config

    rows = conn.execute(
        "SELECT id AS rowid, * FROM receipts WHERE tenantId = %s AND status != 'ARCHIVED'",
        (tenant_id,),
    ).fetchall()
    if not rows:
        return []

    rows.sort(key=lambda r: _bill_sequence(r["billNo"]))
    bills = {r["billNo"]: r for r in rows}

    if starting_bill_no not in bills:
        return []

    changed = []
    idx = next(i for i, r in enumerate(rows) if r["billNo"] == starting_bill_no)

    for r in rows[idx + 1:]:
        prev_bill = _get_bill_predecessor(conn, tenant_id, r["billNo"])
        if prev_bill is not None:
            new_prev = float(prev_bill["current"] or 0)
        else:
            from app.services.tenant_service import get_tenant
            tenant = get_tenant(tenant_id, landlord_id)
            new_prev = float(getattr(tenant, "previousMeter", 0) or 0) if tenant else 0.0

        current = float(r["current"] or 0)
        units = max(0.0, current - new_prev)
        electricity = units * float(r["rate"] or 0)
        total = (float(r["rent"] or 0) + float(r["additional"] or 0)
                 + float(r["water"] or 0) + float(r["tankWater"] or 0)
                 + float(r["maintenancecharge"] or 0) + electricity)

        changed_fields = (
            abs(float(r["previous"] or 0) - new_prev) > 0.001
            or abs(float(r["units"] or 0) - units) > 0.001
            or abs(float(r["electricity"] or 0) - electricity) > 0.001
            or abs(float(r["total"] or 0) - total) > 0.001
        )
        if changed_fields:
            conn.execute(
                "UPDATE receipts SET previous = %s, units = %s, electricity = %s, total = %s "
                "WHERE billNo = %s AND tenantId = %s",
                (new_prev, units, electricity, total, r["billNo"], tenant_id),
            )
            changed.append(r["billNo"])

    # Regenerate PDFs for every bill whose persisted values changed.
    if changed:
        try:
            _lid = landlord_id
            if _lid is None:
                _lrow = conn.execute(
                    "SELECT landlord_id FROM tenants WHERE id = %s", (tenant_id,)
                ).fetchone()
                _lid = _lrow["landlord_id"] if _lrow else None
            conf = get_effective_landlord_config(_lid) if _lid else {}
            for bill_no in changed:
                fresh = conn.execute(
                    "SELECT id AS rowid, * FROM receipts WHERE billNo = %s AND tenantId = %s",
                    (bill_no, tenant_id),
                ).fetchone()
                if fresh is None:
                    continue
                try:
                    pdf_name = fresh["pdf"] or f"{bill_no}.pdf"
                    pdf_path = os.path.join(RECEIPTS_DIR, pdf_name)
                    generate_professional_pdf(_row_to_dict(fresh), conf, pdf_path)
                except Exception:
                    pass
        except Exception:
            pass

    return changed


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
                MaintenanceDesc, previousArrears=0.0, amountReceived=None, paymentStatus="PENDING",
                landlord_id=None):
    from app.core.db import get_conn
    from datetime import datetime
    from app.services.tenant_service import get_tenant
    import os
    from app.core.paths import RECEIPTS_DIR
    from app.services.pdf_service import generate_professional_pdf
    
    tenant = get_tenant(tenantId, landlord_id)
    if not tenant:
        raise ValueError("Tenant not found")
    tenantName = tenant.name

    # Arrears are fully auto-computed: the new bill carries the tenant's running
    # balance (Σ earlier Totals − Σ earlier payments) as its previousArrears, so
    # it reflects the accumulated unpaid amount from the first bill to now.
    previousArrears = get_tenant_balance(tenant.id)

    # FIX: Generate bill number with tenant ID prefix (T1, T2, etc.)
    # Count existing receipts for THIS specific tenant
    with get_conn() as conn:
        tenant_receipt_count = conn.execute(
            "SELECT COUNT(*) FROM receipts WHERE tenantId = %s", 
            (tenant.id,)
        ).fetchone()[0]
        # Resolve the tenant's landlord so the receipt stays visible to them
        _lrow = conn.execute(
            "SELECT landlord_id FROM tenants WHERE id = %s", (tenant.id,)
        ).fetchone()
        tenant_landlord_id = _lrow["landlord_id"] if _lrow else None
    
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
        from app.services.landlord_config_service import get_effective_landlord_config
        generate_professional_pdf(receipt_dict, get_effective_landlord_config(tenant_landlord_id), pdf_path)
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
                maintenancecharge, maintenancedesc, previousarrears, amountreceived, landlord_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            billNo, current_date, month, tenant.id, tenantName, prev, current_reading,
            charges["units"], tenant.rent, charges["additional"], tenant.water, tankWater,
            charges["electricity"], charges["total"], pdf_filename, tenant.phone, tenant.company,
            tenant.address, tenant.electricityRate, "ACTIVE", "", "", "",
            additional_persons, tenant.additionalPersonCharge, 8, "Admin",
            paymentStatus, MaintenanceCharge, MaintenanceDesc, previousArrears, amountReceived,
            tenant_landlord_id
        ))
        recompute_tenant_arrear_chain(conn, tenant.id)
        conn.commit()

    # Maintain payment-entry invariant: if the new bill carries a payment but
    # has no active payment entries yet, record one.
    try:
        from app.services.payment_service import sync_bill_payment_from_receipt
        sync_bill_payment_from_receipt(tenant.id, billNo, amountReceived)
    except Exception:
        pass

    return receipt_dict
def update_bill(tenantId, billNo, month, current_reading, additional_persons, tankWater, MaintenanceCharge, 
                MaintenanceDesc, previousArrears=0.0, amountReceived=None, paymentStatus="PENDING",
                landlord_id=None, rent=None, water=None, electricity_rate=None,
                additional_person_rate=None, property_id=None):
    from app.core.db import get_conn
    from app.services.tenant_service import get_tenant
    from app.services.pdf_service import generate_professional_pdf
    from app.database.property_repository import get_property
    import os
    from app.core.paths import RECEIPTS_DIR
    
    with get_conn() as conn:
        query = "SELECT * FROM receipts WHERE tenantId = %s AND billNo = %s"
        params: list = [tenantId, billNo]
        if landlord_id is not None:
            query += " AND tenantId IN (SELECT id FROM tenants WHERE landlord_id = %s)"
            params.append(landlord_id)
        row = conn.execute(query, tuple(params)).fetchone()
        if not row:
            raise ValueError("Receipt not found")
        old_receipt = dict(row)

    tenant = get_tenant(tenantId, landlord_id)
    if not tenant:
        raise ValueError("Tenant not found")
    tenantName = tenant.name

    # Per-receipt snapshot rates: use the edited values when provided, otherwise
    # fall back to the tenant's current billing profile (keeps existing callers
    # and legacy workflows working unchanged).
    rent = tenant.rent if rent is None else float(rent)
    water = tenant.water if water is None else float(water)
    electricity_rate = tenant.electricityRate if electricity_rate is None else float(electricity_rate)
    additional_person_rate = tenant.additionalPersonCharge if additional_person_rate is None else float(additional_person_rate)

    # Property ownership validation: only accept a property that belongs to the
    # authenticated landlord (rejects arbitrary other-landlord property IDs).
    if landlord_id is not None and property_id is not None:
        if not get_property(landlord_id, int(property_id)):
            raise ValueError("Property not found or does not belong to this landlord")

    # The previous reading is resolved from the chain — the current reading of
    # the bill immediately preceding this one — NOT the receipt's stored
    # snapshot. This preserves the invariant bill[n].previous == bill[n-1].current.
    # The bill being edited is excluded so it cannot resolve its predecessor
    # from itself; if it is the tenant's first bill, we fall back to the
    # tenant.previousMeter baseline.
    with get_conn() as conn:
        pred = _get_bill_predecessor(conn, tenantId, billNo)
    if pred is not None:
        prev = float(pred["current"])
    else:
        prev = float(tenant.previousMeter or 0)
    if prev > 0 and current_reading < prev:
        raise ValueError("Current meter reading cannot be less than previous reading.")
        
    charges = calculate_charges(
        current_reading, additional_persons, prev,
        rent, water, tankWater, MaintenanceCharge,
        electricity_rate, additional_person_rate
    )

    # Arrears are auto-computed: normalize the chain so this bill's
    # previousArrears is the running balance entering it.
    with get_conn() as conn:
        recompute_tenant_arrear_chain(conn, tenantId)
        _row = conn.execute(
            "SELECT previousarrears FROM receipts WHERE tenantId = %s AND billNo = %s",
            (tenantId, billNo),
        ).fetchone()
    previousArrears = float(_row["previousarrears"] or 0) if _row else 0.0

    if paymentStatus == "PAID" and amountReceived is None:
        amountReceived = charges["total"] + previousArrears
    elif amountReceived is None:
        amountReceived = 0.0
        
    pdf_filename = old_receipt.get("pdf") or f"{billNo}_{tenantName.replace(' ', '_')}_{month.replace(' ', '_')}.pdf"
    pdf_path = os.path.join(RECEIPTS_DIR, pdf_filename)
    
    # Resolve the receipt-level property snapshot: prefer the submitted
    # property_id (validated above), otherwise keep the receipt's existing
    # property, otherwise fall back to the tenant's current property.
    receipt_property_id = property_id if property_id is not None else old_receipt.get("property_id")
    if receipt_property_id is None:
        receipt_property_id = tenant.propertyId
    receipt_property_id = int(receipt_property_id) if receipt_property_id is not None else None

    _property_name = ""
    if receipt_property_id is not None and landlord_id is not None:
        _prop = get_property(landlord_id, receipt_property_id)
        if _prop:
            _property_name = _prop.get("property_name") or ""

    updated_dict = {
        "Bill": billNo,
        "Date": old_receipt["date"],
        "Month": month,
        "Tenant": tenantName,
        "Property": _property_name,
        "Previous": prev,
        "Current": current_reading,
        "Units": charges["units"],
        "Rent": rent,
        "Additional": charges["additional"],
        "Water": water,
        "tankWater": tankWater,
        "Electricity": charges["electricity"],
        "Total": charges["total"],
        "PDF": pdf_filename,
        "Tenant_Phone": tenant.phone,
        "Tenant_Company": tenant.company,
        "Tenant_Address": tenant.address,
        "Rate": electricity_rate,
        "Status": old_receipt["status"],
        "Archived_Date": old_receipt["archiveddate"],
        "Archived_By": old_receipt["archivedby"],
        "Deleted_Date": old_receipt["deleteddate"],
        "Additional_Persons": additional_persons,
        "additionalPersonRate": additional_person_rate,
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
        from app.services.landlord_config_service import get_effective_landlord_config
        generate_professional_pdf(updated_dict, get_effective_landlord_config(tenant.landlord_id or landlord_id), pdf_path)
    except BaseException as e:
        print(f"Error generating PDF: {e}")

    # Single atomic transaction: update the receipt snapshot (including the
    # chain-resolved previous reading), rebuild any downstream meter readings,
    # update the tenant's billing profile, and recompute the arrears chain —
    # all in one transaction so either every change commits or none does.
    old_current = float(old_receipt["current"] or 0)
    new_current = float(current_reading or 0)
    with get_conn() as conn:
        conn.execute("""
            UPDATE receipts SET
                month = %s, tenantId = %s, tenant = %s, previous = %s, current = %s, units = %s, rent = %s,
                additional = %s, water = %s, tankWater = %s, electricity = %s, total = %s,
                pdf = %s, tenantphone = %s, tenantcompany = %s, tenantaddress = %s, rate = %s,
                additionalpersons = %s, additionalpersonrate = %s, paymentstatus = %s,
                maintenancecharge = %s, maintenancedesc = %s, previousarrears = %s, amountreceived = %s,
                property_id = %s
            WHERE billNo = %s
        """, (
            month, tenant.id, tenantName, prev, current_reading, charges["units"], rent,
            charges["additional"], water, tankWater, charges["electricity"], charges["total"],
            pdf_filename, tenant.phone, tenant.company, tenant.address, electricity_rate,
            additional_persons, additional_person_rate, paymentStatus,
            MaintenanceCharge, MaintenanceDesc, previousArrears, amountReceived,
            receipt_property_id,
            billNo
        ))
        # Persist the edited rates onto the tenant's billing profile so future
        # bills inherit them. This intentionally does NOT cascade onto existing
        # receipt snapshots (those keep the per-bill values written above) and
        # does NOT touch tenants.property_id.
        conn.execute(
            "UPDATE tenants SET rent = %s, water = %s, electricityrate = %s, additionalpersoncharge = %s WHERE id = %s",
            (rent, water, electricity_rate, additional_person_rate, tenantId),
        )
        # If the edited bill's current reading changed, every downstream bill
        # must have its previous/units/electricity/total recalculated so the
        # meter chain stays consistent. Runs inside the same transaction.
        if abs(old_current - new_current) > 0.001:
            _rebuild_meter_chain(conn, tenantId, billNo, landlord_id=landlord_id)
        # Recompute arrears AFTER the meter chain so downstream totals are final.
        recompute_tenant_arrear_chain(conn, tenantId)
        conn.commit()

    # Maintain payment-entry invariant: editing a bill's owned amount should
    # reconcile a single payment entry when none exist yet (legacy bills or
    # bills created before the entries feature). Does not duplicate entries.
    try:
        from app.services.payment_service import sync_bill_payment_from_receipt
        sync_bill_payment_from_receipt(tenantId, billNo, amountReceived)
    except Exception:
        pass

    return updated_dict
def archive_bill(tenantId, billNo, landlord_id=None):
    from app.core.db import get_conn
    from datetime import datetime
    from app.services.tenant_service import get_tenant
    if landlord_id is not None and not get_tenant(tenantId, landlord_id):
        raise ValueError("Tenant not found")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT status FROM receipts WHERE tenantId = %s AND billNo = %s",
            (tenantId, billNo),
        ).fetchone()
        if not row:
            raise ValueError("Bill not found for this tenant.")

        conn.execute("""
            UPDATE receipts SET status = 'ARCHIVED', archiveddate = %s, archivedby = 'Admin'
            WHERE tenantId = %s AND billNo = %s AND status != 'ARCHIVED'
        """, (datetime.now().strftime("%Y-%m-%d"), tenantId, billNo))
        recompute_tenant_arrear_chain(conn, tenantId)
        conn.commit()
    return get_receipt(tenantId, billNo, landlord_id=landlord_id)

def restore_bill(tenantId, billNo, landlord_id=None):
    from app.core.db import get_conn
    from app.services.tenant_service import get_tenant
    if landlord_id is not None and not get_tenant(tenantId, landlord_id):
        raise ValueError("Tenant not found")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT status, tenantId FROM receipts WHERE tenantId = %s AND billNo = %s",
            (tenantId, billNo),
        ).fetchone()
        if not row:
            raise ValueError("Bill not found for this tenant.")

        conn.execute("""
            UPDATE receipts SET status = 'ACTIVE', archiveddate = '', archivedby = ''
            WHERE tenantId = %s AND billNo = %s AND status != 'ACTIVE'
        """, (tenantId, billNo))
        recompute_tenant_arrear_chain(conn, tenantId)
        conn.commit()
    return get_receipt(tenantId, billNo, landlord_id=landlord_id)

def delete_bill(tenantId, billNo, landlord_id=None):
    from app.core.db import get_conn
    from app.services.tenant_service import get_tenant
    if landlord_id is not None and not get_tenant(tenantId, landlord_id):
        raise ValueError("Tenant not found")
    with get_conn() as conn:
        row = conn.execute("SELECT status, tenantId FROM receipts WHERE tenantId = %s AND billNo = %s", (tenantId, billNo)).fetchone()
        if not row:
            raise ValueError("Receipt not found")

        is_archived = str(row["status"]).upper() == "ARCHIVED"

        # Also allow deletion if the tenant is archived
        tenant = get_tenant(tenantId)
        is_tenant_archived = tenant is not None and str(tenant.status).upper() == "ARCHIVED"

        if not (is_archived or is_tenant_archived):
            raise ValueError("Only archived receipts can be permanently deleted.")

        conn.execute("DELETE FROM receipts WHERE tenantId = %s AND billNo = %s", (tenantId, billNo))
        conn.commit()


def get_dashboard_stats(landlord_id=None):
    
    billing_conf = config.get("billing", {})
    receipts = get_all_receipts(include_archived_tenants=False, landlord_id=landlord_id)
    tenants = load_tenants(include_archived=False, landlord_id=landlord_id)
    
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
    pending_payments_amount = 0.0       # Σ current outstanding balance per due tenant
    pending_receipts_count = 0          # number of due tenants (one per tenant)
    arrears_total = 0.0                 # Σ unresolved carried-forward balance

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

        # Skip bills that were fully settled by a later payment — they are no
        # longer currently due even though their stored status is PARTIAL.
        settled_type = str(r.get("settlementType", "NONE")).upper()
        settled = bool(r.get("settledByBill")) and settled_type in ("CURRENT_PAYMENT", "ARREAR")

        if not settled and status in ("PENDING", "PARTIAL") and outstanding > 0:
            pending_receipts_count += 1
            due_tenant_ids.add(int(r.get("TenantId", 0) or 0))
            # Unresolved arrears attributed to prior periods (excluding the
            # current bill's own contribution) — used by the arrears card.
            if previous_arrears > 0 and outstanding > 0:
                arrears_total += min(outstanding, previous_arrears)

        if status in ("PAID", "ADVANCE"):
            paid_bills_count += 1
            if status == "ADVANCE":
                advance_bills_count += 1
            
    pending_payments_count = len(due_tenant_ids)
    # The authoritative pending amount is Σ per-tenant current outstanding
    # balance (never the sum of per-receipt grand totals, which would double
    # count carried-forward arrears). One due entry per tenant, not per bill.
    pending_payments_amount = 0.0
    if due_tenant_ids:
        from app.services.payment_service import get_tenant_outstanding_balance
        for _tid in due_tenant_ids:
            pending_payments_amount += get_tenant_outstanding_balance(_tid)
    pending_payments_amount = round(pending_payments_amount, 2)
    pending_receipts_count = pending_payments_count  # one due entry per tenant

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
    payment_facts = {}
    try:
        from app.core.db import get_conn as _gconn
        with _gconn() as conn:
            for row in conn.execute(
                "SELECT billNo, COUNT(*) AS cnt, MAX(payment_date) AS last_date "
                "FROM payment_entries WHERE status = 'ACTIVE' GROUP BY billNo"
            ).fetchall():
                payment_facts[row["billNo"]] = (row["cnt"], row["last_date"])
    except Exception:
        pass

    for r in active_receipts[-5:][::-1]:
        _cnt, _last = payment_facts.get(r.get("Bill"), (0, None))
        recent_bills.append({
            "billNo": r.get("Bill"),
            "tenantName": r.get("Tenant"),
            "tenantId": int(r.get("TenantId", 0) or 0),
            "total": float(r.get("Total", 0) or 0),
            "amountReceived": float(r.get("amountReceived", 0) or 0),
            "month": r.get("Month"),
            "paymentStatus": r.get("paymentStatus", "PENDING"),
            "previousArrears": float(r.get("previousArrears", 0) or 0),
            "settledByBill": r.get("settledByBill", "") or "",
            "settlementType": r.get("settlementType", "") or "NONE",
            "settlementAmount": float(r.get("settlementAmount", 0) or 0),
            "paymentCount": int(_cnt or 0) if _cnt else 0,
            "lastPaymentDate": _last or "",
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
        "arrears_amount": round(arrears_total, 2),  # Σ unresolved carried-forward balance

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

            exists = conn.execute("SELECT 1 FROM receipts WHERE billNo = %s", (billNo,)).fetchone()

            if exists:
                conn.execute("""
                    UPDATE receipts SET
                        date = %s, month = %s, tenantId = %s, tenant = %s, previous = %s, current = %s, units = %s, rent = %s,
                        additional = %s, water = %s, tankWater = %s, electricity = %s, total = %s, pdf = %s,
                        tenantphone = %s, tenantcompany = %s, tenantaddress = %s, rate = %s, status = %s,
                        archiveddate = %s, archivedby = %s, deleteddate = %s, additionalpersons = %s,
                        additionalpersonrate = %s, receiptversion = %s, generatedby = %s, paymentstatus = %s,
                        maintenancecharge = %s, maintenancedesc = %s, previousarrears = %s, amountreceived = %s
                    WHERE billNo = %s
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
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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

        # Imported previousArrears may be stale or divergent — normalize every
        # affected tenant's chain so running balances are authoritative.
        affected_tenant_ids = {
            int(r.get("TenantId") or r.get("tenantId"))
            for r in receipts_list
            if (r.get("TenantId") or r.get("tenantId")) is not None
        }
        for tid in affected_tenant_ids:
            if tid in valid_tenant_ids:
                recompute_tenant_arrear_chain(conn, tid)

        conn.commit()

    # Maintain payment-entry invariant for imported receipts that carried an
    # amountReceived (record one entry per such bill when none exists yet).
    try:
        from app.services.payment_service import sync_bill_payment_from_receipt
        for r in receipts_list:
            billNo = r.get("Bill")
            raw_tid = r.get("TenantId") or r.get("tenantId")
            tid = int(raw_tid) if raw_tid is not None else None
            amt = r.get("amountReceived", 0)
            if billNo and tid and tid in valid_tenant_ids and float(amt or 0) > 0:
                sync_bill_payment_from_receipt(tid, billNo, amt)
    except Exception:
        pass

