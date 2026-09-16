# // File: app\app\services\payment_service.py
# POLICY: tenantId is the only identity key for tenant-related data.
# tenantName is display-only and must never be used for joins, ownership, lookup, or mutation.
#
# payment_entries is the transaction-level source of truth for payments.
# receipts.amountreceived is the derived aggregate of active payment entries:
#
#     receipts.amountreceived == SUM(payment_entries.amount WHERE status='ACTIVE')
#
# Every add/modify/delete of a payment entry recomputes the bill from its active
# entries (recalculate_bill_payment_state) and then propagates the resulting
# running balance forward through the existing recompute_tenant_arrear_chain.
# This keeps the arrears engine working against receipts.amountreceived without
# needing to understand individual payment transactions.

from datetime import date as _date, datetime as _datetime

from app.core.db import get_conn
from app.services.payment_status_engine import calculate_payment_state

_MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _month_sort_key(month_str: str):
    """Sort key for 'January 2026' style month strings; unknown months sort last.
    Matches billing_service so allocations and the arrears engine agree."""
    parts = str(month_str or "").strip().split()
    if len(parts) == 2 and parts[0] in _MONTH_NAMES and parts[1].isdigit():
        return (int(parts[1]), _MONTH_NAMES.index(parts[0]))
    return (99999, 99)

def _safe_float(val, default=0.0) -> float:
    try:
        return round(float(str(val).strip() or default), 2)
    except Exception:
        return default

_VALID_PAYMENT_METHODS = ("CASH", "UPI", "BANK_TRANSFER", "CHEQUE", "CARD", "ONLINE", "OTHER")


def _normalize_method(method):
    """Normalize (and validate) a payment method for storage / import."""
    m = str(method or "OTHER").strip().upper() or "OTHER"
    if m not in _VALID_PAYMENT_METHODS:
        raise ValueError(
            f"Invalid payment method '{m}'. Valid: {sorted(_VALID_PAYMENT_METHODS)}"
        )
    return m


def _row_to_entry(row) -> dict:
    return {
        "id": int(row["id"]),
        "billNo": row["billNo"],
        "tenantId": int(row["tenantId"] or 0),
        "paymentDate": row["paymentDate"],
        "amount": _safe_float(row["paymentAmount"]),
        "createdAt": row["createdAt"],
        "updatedAt": row["updatedAt"],
        "status": row["status"],
        "paymentType": row["paymentType"],
        "source": row["source"],
        "paymentMethod": _normalize_method(row.get("paymentMethod") or "OTHER"),
        "externalId": row.get("externalId"),
        "reference": row.get("reference"),
        "notes": row.get("notes"),
    }


def _get_active_rows(conn, tenant_id, bill_no):
    return conn.execute(
        "SELECT * FROM \"paymentEntries\" "
        '''WHERE "tenantId" = %s AND "billNo" = %s AND status = 'ACTIVE' '''
        "ORDER BY \"paymentDate\" ASC, id ASC",
        (tenant_id, bill_no),
    ).fetchall()


def get_tenant_outstanding_balance(tenant_id: int) -> float:
    """The tenant's CURRENT outstanding amount across all non-archived bills.

    Policy: outstanding = Σ(current charge, `total`) − Σ(payments received)
    over non-archived receipts. `total` is the current-cycle charge and never
    includes previousArrears, so carried-forward arrears are never double
    counted. This equals the running balance carried past the latest bill and is
    the authoritative value all screens should display.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(COALESCE(\"billTotal\",0)),0) - COALESCE(SUM(COALESCE(\"amountReceived\",0)),0) AS bal "
            """FROM receipts WHERE "tenantId" = %s AND status != 'ARCHIVED'""",
            (tenant_id,),
        ).fetchone()
    return round(float(row["bal"] or 0), 2)


def _ordered_bills(conn, tenant_id):
    rows = conn.execute(
        """SELECT id AS rowid, * FROM receipts WHERE "tenantId" = %s AND status != 'ARCHIVED'""",
        (tenant_id,),
    ).fetchall()
    return sorted(rows, key=lambda r: (_month_sort_key(r["billMonth"]), r["rowid"]))


def _recompute_tenant_settlement(conn, tenant_id):
    """Recompute the tenant's payment allocation + settlement ledger.

    This is the single allocation authority. It:
      * clears prior allocations / settlement markers for the tenant,
      * walks ACTIVE payment entries chronologically and, per the policy
        "current bill first, then oldest arrears, remainder -> ADVANCE",
        allocates each payment to the specific bills it cleared,
      * marks historical bills that were only settled by a later bill's payment
        with settled_by_bill_no / settlement_type so they stop appearing as
        currently due WITHOUT rewriting their original paymentstatus.

    Call this inside the same transaction that mutated payments/bills so
    allocations always reflect the source of truth.
    """
    now = _datetime.utcnow().isoformat(timespec="seconds")
    ordered = _ordered_bills(conn, tenant_id)
    conn.execute("DELETE FROM \"paymentAllocations\" WHERE \"tenantId\" = %s", (tenant_id,))
    for r in ordered:
        conn.execute(
            "UPDATE receipts SET \"settledByBillNo\" = NULL, \"settlementType\" = 'NONE', "
            "\"settledAt\" = NULL, \"settlementAmount\" = 0 "
            'WHERE "tenantId" = %s AND "billNo" = %s',
            (tenant_id, r["billNo"]),
        )
    if not ordered:
        return

    # Per-bill unpaid current charge (never includes carried arrears, so the
    # oldest-bills-first pass resolves an earlier bill's arrears exactly once).
    bills = [
        {"billNo": r["billNo"], "month": r["billMonth"], "current_total": _safe_float(r["billTotal"]),
         "unpaid_current": _safe_float(r["billTotal"])}
        for r in ordered
    ]
    bill_by_no = {b["billNo"]: b for b in bills}

    entries = conn.execute(
        '''SELECT * FROM \"paymentEntries\" WHERE "tenantId" = %s AND status = 'ACTIVE' '''
        "ORDER BY \"paymentDate\" ASC, id ASC",
        (tenant_id,),
    ).fetchall()

    for e in entries:
        amt = _safe_float(e["paymentAmount"])
        if amt <= 0:
            continue
        rec_bill = e["billNo"]
        remaining = amt
        current = bill_by_no.get(rec_bill)

        # 1. Current bill first.
        if current is not None and current["unpaid_current"] > 0 and remaining > 0.001:
            take = round(min(remaining, current["unpaid_current"]), 2)
            current["unpaid_current"] = round(current["unpaid_current"] - take, 2)
            remaining = round(remaining - take, 2)
            conn.execute(
                "INSERT INTO \"paymentAllocations\" "
                "(\"paymentEntryId\", \"tenantId\", \"billNo\", \"allocatedAmount\", \"allocationType\", \"createdAt\") "
                "VALUES (%s, %s, %s, %s, 'CURRENT_BILL', %s)",
                (e["id"], tenant_id, rec_bill, take, now),
            )

        # 2. Oldest arrears first (oldest bills with unpaid balance).
        if remaining > 0.001:
            for b in bills:
                if remaining <= 0.001:
                    break
                if b["billNo"] == rec_bill or b["unpaid_current"] <= 0:
                    continue
                take = round(min(remaining, b["unpaid_current"]), 2)
                b["unpaid_current"] = round(b["unpaid_current"] - take, 2)
                remaining = round(remaining - take, 2)
                conn.execute(
                    "INSERT INTO \"paymentAllocations\" "
                    "(\"paymentEntryId\", \"tenantId\", \"billNo\", \"allocatedAmount\", \"allocationType\", \"createdAt\") "
                    "VALUES (%s, %s, %s, %s, 'ARREAR', %s)",
                    (e["id"], tenant_id, b["billNo"], take, now),
                )

        # 3. Remainder -> advance against the recorded bill.
        if remaining > 0.001:
            conn.execute(
                "INSERT INTO \"paymentAllocations\" "
                "(\"paymentEntryId\", \"tenantId\", \"billNo\", \"allocatedAmount\", \"allocationType\", \"createdAt\") "
                "VALUES (%s, %s, %s, %s, 'ADVANCE', %s)",
                (e["id"], tenant_id, rec_bill, round(remaining, 2), now),
            )

    # Settlement markers on historical bills. A bill is "settled by" a later
    # payment when it did not self-pay in full (own received < own grand total)
    # but its unpaid current charge has since been reduced to zero by later
    # payments. Its paymentstatus stays unchanged; we only record the fact that
    # its outstanding balance no longer contributes to current dues.
    settled_latest = ordered[-1]["billNo"] if ordered else None
    own_received = {}
    for e in entries:
        own_received[e["billNo"]] = round(own_received.get(e["billNo"], 0.0) + _safe_float(e["paymentAmount"]), 2)
    for b in bills:
        grand = round(b["current_total"] + _safe_float(_prev_arrears_of(conn, tenant_id, b["billNo"])), 2)
        recv = own_received.get(b["billNo"], 0.0)
        if b["unpaid_current"] <= 0.001 and recv < grand - 0.001:
            # Fully settled now, but historically partial -> cleared by a later payment.
            conn.execute(
                "UPDATE receipts SET \"settledByBillNo\" = %s, \"settlementType\" = 'CURRENT_PAYMENT', "
                '\"settledAt\" = %s, \"settlementAmount\" = %s WHERE "tenantId" = %s AND "billNo" = %s',
                (settled_latest, now, round(grand - recv, 2), tenant_id, b["billNo"]),
            )


def _prev_arrears_of(conn, tenant_id, bill_no):
    row = conn.execute(
        'SELECT \"previousArrears\" FROM receipts WHERE "tenantId" = %s AND "billNo" = %s',
        (tenant_id, bill_no),
    ).fetchone()
    return _safe_float(row["previousArrears"]) if row else 0.0


def get_tenant_settlement_state(tenant_id: int, conn=None):
    """Canonical per-tenant financial view model shared by every screen.

    Returns the authoritative current-bill, outstanding, arrears, settlement and
    advance values so the frontend never has to derive them itself. Pass an
    active `conn` when called inside an open transaction (avoids a second
    connection seeing uncommitted data).
    """
    from app.core.db import get_conn as _get_conn
    _owns = conn is None
    conn = conn if conn is not None else _get_conn()
    try:
        ordered = _ordered_bills(conn, tenant_id)
        if not ordered:
            return {
                "tenantId": tenant_id,
                "outstandingBalance": 0.0,
                "advance": 0.0,
                "currentBill": None,
                "currentBillDue": 0.0,
                "arrears": [],
                "settlements": [],
            }
        latest = ordered[-1]
        current_total = _safe_float(latest["billTotal"])
        prev_arrears = _safe_float(latest["previousArrears"])
        grand = round(current_total + prev_arrears, 2)
        received = _safe_float(latest["amountReceived"])
        outstanding = _tenant_outstanding(conn, tenant_id)

        bill_by_no = {r["billNo"]: r for r in ordered}
        current = bill_by_no.get(latest["billNo"])

        # advance = any allocations marked ADVANCE (or received > grand on current bill)
        adv = conn.execute(
            "SELECT COALESCE(SUM(\"allocatedAmount\"),0) AS a FROM \"paymentAllocations\" "
            "WHERE \"tenantId\" = %s AND \"allocationType\" = 'ADVANCE' AND \"billNo\" = %s",
            (tenant_id, latest["billNo"]),
        ).fetchone()["a"] or 0.0

        # arrears list: older bills still with unpaid balance
        arrears = []
        if current is not None:
            current_unpaid = round(current_total + prev_arrears - received, 2)
            if current_unpaid > 0.001:
                arrears.append({
                    "billNo": latest["billNo"],
                    "month": latest["billMonth"],
                    "amount": round(current_unpaid, 2),
                })

        settlements = []
        for r in ordered:
            st = r["settlementType"] if "settlementType" in r.keys() else None
            if st and st != "NONE":
                settlements.append({
                    "billNo": r["billNo"],
                    "settledByBillNo": r["settledByBillNo"] if "settledByBillNo" in r.keys() else "",
                    "amount": _safe_float(r["settlementAmount"]),
                    "type": st,
                })

        return {
            "tenantId": tenant_id,
            "outstandingBalance": outstanding,
            "advance": round(float(adv), 2),
            "currentBill": {
                "billNo": latest["billNo"],
                "month": latest["billMonth"],
                "currentAmount": current_total,
                "previousArrears": prev_arrears,
                "grandTotal": grand,
                "amountReceived": received,
            },
            "currentBillDue": round(max(grand - received, 0.0), 2),
            "arrears": arrears,
            "settlements": settlements,
        }
    finally:
        if _owns:
            conn.close()


def _regenerate_bill_pdf(conn, tenant_id, bill_no):
    """Best-effort regenerate the PDF of a single bill (its payment state or
    payment history just changed). Future bills whose previousArrears changed
    are already regenerated by recompute_tenant_arrear_chain(), so we only
    handle the operator's bill here."""
    try:
        import os
        from app.core.paths import RECEIPTS_DIR
        from app.services.billing_service import _row_to_dict
        from app.services.pdf_service import generate_professional_pdf
        from app.services.landlord_config_service import get_effective_landlord_config

        row = conn.execute(
            'SELECT * FROM receipts WHERE "tenantId" = %s AND "billNo" = %s',
            (tenant_id, bill_no),
        ).fetchone()
        if row is None:
            return
        rec = _row_to_dict(row)
        landlord_id = row["landlordId"]
        entries = [e for e in _get_active_rows(conn, tenant_id, bill_no)]
        pdf_name = row["pdf"] or f"{bill_no}.pdf"
        pdf_path = os.path.join(RECEIPTS_DIR, pdf_name)
        generate_professional_pdf(
            rec, get_effective_landlord_config(landlord_id) if landlord_id else {}, pdf_path,
            payment_entries=entries,
        )
    except Exception:
        pass


def _recalculate_and_apply(conn, tenant_id, bill_no):
    """Central authority for a bill's payment status / received amount.

    Invariant enforced:
        receipts.amountreceived == SUM(payment_entries.amount WHERE status='ACTIVE')

    Returns the resolved dict for the bill after recalculation.
    """
    row = conn.execute(
        'SELECT * FROM receipts WHERE "tenantId" = %s AND "billNo" = %s',
        (tenant_id, bill_no),
    ).fetchone()
    if row is None:
        raise ValueError("Receipt not found")

    current_total = _safe_float(row["billTotal"])
    previous_arrears = _safe_float(row["previousArrears"])
    entries = _get_active_rows(conn, tenant_id, bill_no)
    state = calculate_payment_state(
        bill_total=current_total,
        arrears=previous_arrears,
        active_amounts=[_safe_float(e["paymentAmount"]) for e in entries],
    )

    conn.execute(
        "UPDATE receipts SET \"amountReceived\" = %s, \"paymentStatus\" = %s "
        'WHERE "tenantId" = %s AND "billNo" = %s',
        (state["amount_received"], state["status"], tenant_id, bill_no),
    )

    return {
        "billNo": bill_no,
        "tenantId": tenant_id,
        "grandTotal": state["grand_total"],
        "totalReceived": state["amount_received"],
        "balanceDue": state["balance_due"],
        "advanceAmount": state["advance_amount"],
        "paymentStatus": state["status"],
        "paymentCount": len(entries),
        "payments": [_row_to_entry(e) for e in entries],
        "outstandingBalance": round(_tenant_outstanding(conn, tenant_id), 2),
        "arrearsCleared": state["status"] in ("PAID", "ADVANCE") and _tenant_outstanding(conn, tenant_id) <= 0.001,
    }


def _tenant_outstanding(conn, tenant_id) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(COALESCE(\"billTotal\",0)),0) - COALESCE(SUM(COALESCE(\"amountReceived\",0)),0) AS bal "
        """FROM receipts WHERE "tenantId" = %s AND status != 'ARCHIVED'""",
        (tenant_id,),
    ).fetchone()
    return round(float(row["bal"] or 0), 2)


def _validate_owner(conn, tenant_id, bill_no, landlord_id):
    """Verify the tenant belongs to the landlord and the bill exists."""
    from app.services.tenant_service import get_tenant
    if landlord_id is not None and not get_tenant(tenant_id, landlord_id):
        raise ValueError("Tenant not found")
    row = conn.execute(
        'SELECT 1 FROM receipts WHERE "tenantId" = %s AND "billNo" = %s',
        (tenant_id, bill_no),
    ).fetchone()
    if row is None:
        raise ValueError("Receipt not found")


def _validate_date(payment_date: str):
    try:
        d = _date.fromisoformat(payment_date)
    except (TypeError, ValueError):
        raise ValueError("Invalid payment date. Use YYYY-MM-DD.")
    if d > _date.today():
        raise ValueError("Payment date cannot be in the future.")


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def get_payment_entries(tenant_id, bill_no, landlord_id=None):
    """Return the authoritative current payment state for a bill (read-only)."""
    with get_conn() as conn:
        _validate_owner(conn, tenant_id, bill_no, landlord_id)
        row = conn.execute(
            'SELECT * FROM receipts WHERE "tenantId" = %s AND "billNo" = %s',
            (tenant_id, bill_no),
        ).fetchone()
        if row is None:
            raise ValueError("Receipt not found")
        current_total = _safe_float(row["billTotal"])
        previous_arrears = _safe_float(row["previousArrears"])
        ordered = [
            e for e in conn.execute(
                "SELECT * FROM \"paymentEntries\" "
                '''WHERE "tenantId" = %s AND "billNo" = %s AND status = 'ACTIVE' '''
                "ORDER BY \"paymentDate\" ASC, id ASC",
                (tenant_id, bill_no),
            ).fetchall()
        ]
        state = calculate_payment_state(
            bill_total=current_total,
            arrears=previous_arrears,
            active_amounts=[_safe_float(e["paymentAmount"]) for e in ordered],
        )
        return {
            "billNo": bill_no,
            "tenantId": tenant_id,
            "grandTotal": state["grand_total"],
            "totalReceived": state["amount_received"],
            "balanceDue": state["balance_due"],
            "advanceAmount": state["advance_amount"],
            "paymentStatus": state["status"],
            "paymentCount": len(ordered),
            "payments": [_row_to_entry(e) for e in ordered],
            "outstandingBalance": _tenant_outstanding(conn, tenant_id),
            "arrearsCleared": state["status"] in ("PAID", "ADVANCE") and _tenant_outstanding(conn, tenant_id) <= 0.001,
            "settlement": get_tenant_settlement_state(tenant_id, conn=conn),
        }


def create_payment_entry(tenant_id, bill_no, payment_date, amount, landlord_id=None, source="MANUAL",
                         payment_method="OTHER", reference=None, notes=None, external_id=None):
    """Record a new payment transaction against a bill and recompute state.

    amount is the amount received in THIS transaction (not cumulative). The
    backend derives the bill's total received from all active entries.

    payment_method, reference, notes describe the transaction itself;
    external_id carries the portable import/export identity (PAY-...).
    """
    amount = _safe_float(amount)
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    _validate_date(payment_date)
    payment_method = _normalize_method(payment_method)

    with get_conn() as conn:
        _validate_owner(conn, tenant_id, bill_no, landlord_id)
        now = _datetime.utcnow().isoformat(timespec="seconds")
        conn.execute(
            '''
            INSERT INTO "paymentEntries"
                ("billNo", "tenantId", "landlordId", "paymentDate", "paymentAmount",
                 "createdAt", "updatedAt", "createdBy", status, "paymentType", source,
                 "paymentMethod", "externalId", reference, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE', 'BILL', %s, %s, %s, %s, %s)
            ''',
            (bill_no, tenant_id, landlord_id, payment_date, amount, now, now, "Landlord", source,
             payment_method, external_id, reference, notes),
        )
        result = _recalculate_and_apply(conn, tenant_id, bill_no)
        _apply_chain_and_pdfs(conn, tenant_id, bill_no)
        conn.commit()
    return result


def update_payment_entry(tenant_id, bill_no, payment_id, payment_date, amount, landlord_id=None,
                         payment_method="OTHER", reference=None, notes=None):
    """Modify an existing payment entry, then recompute from the affected bill
    forward (editing an old payment can change later bills' previousArrears)."""
    amount = _safe_float(amount)
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    _validate_date(payment_date)
    payment_method = _normalize_method(payment_method)

    with get_conn() as conn:
        _validate_owner(conn, tenant_id, bill_no, landlord_id)
        row = conn.execute(
            """SELECT 1 FROM \"paymentEntries\" WHERE id = %s AND "billNo" = %s AND "tenantId" = %s AND status = 'ACTIVE'""",
            (payment_id, bill_no, tenant_id),
        ).fetchone()
        if row is None:
            raise ValueError("Payment entry not found")
        now = _datetime.utcnow().isoformat(timespec="seconds")
        conn.execute(
            "UPDATE \"paymentEntries\" SET \"paymentDate\" = %s, \"paymentAmount\" = %s, \"paymentMethod\" = %s, "
            "reference = %s, notes = %s, \"updatedAt\" = %s, \"updatedBy\" = %s WHERE id = %s",
            (payment_date, amount, payment_method, reference, notes, now, "Landlord", payment_id),
        )
        result = _recalculate_and_apply(conn, tenant_id, bill_no)
        _apply_chain_and_pdfs(conn, tenant_id, bill_no)
        conn.commit()
    return result


def delete_payment_entry(tenant_id, bill_no, payment_id, landlord_id=None):
    """Remove an active payment entry, then recompute from the affected bill
    forward."""
    with get_conn() as conn:
        _validate_owner(conn, tenant_id, bill_no, landlord_id)
        row = conn.execute(
            """SELECT 1 FROM \"paymentEntries\" WHERE id = %s AND "billNo" = %s AND "tenantId" = %s AND status = 'ACTIVE'""",
            (payment_id, bill_no, tenant_id),
        ).fetchone()
        if row is None:
            raise ValueError("Payment entry not found")
        now = _datetime.utcnow().isoformat(timespec="seconds")
        conn.execute(
            "UPDATE \"paymentEntries\" SET status = 'DELETED', \"updatedAt\" = %s, \"updatedBy\" = %s WHERE id = %s",
            (now, "Landlord", payment_id),
        )
        result = _recalculate_and_apply(conn, tenant_id, bill_no)
        _apply_chain_and_pdfs(conn, tenant_id, bill_no)
        conn.commit()
    return result


def import_payment_entries(entries, landlord_id=None, source="IMPORT"):
    """Idempotently upsert a batch of payment transactions (import engine).

    `entries` is an iterable of dicts with keys:
        tenantId, billNo, paymentDate, amount, paymentMethod, reference, notes, externalId

    Keyed by `external_id`: when the id matches an existing ACTIVE entry the
    entry is updated to mirror the file (full sync); otherwise a new entry is
    created. Each bill is recomputed (amountreceived / paymentStatus derived from
    SUM of ACTIVE entries) and the arrears + allocation chain propagates once per
    affected bill. Returns the recomputed per-bill state dicts.
    """
    if not entries:
        return []

    with get_conn() as conn:
        now = _datetime.utcnow().isoformat(timespec="seconds")
        affected = {}  # (tenant_id, bill_no) -> True, preserves first-seen order
        for e in entries:
            tenant_id = int(e.get("tenantId") or 0)
            bill_no = e.get("billNo")
            amount = _safe_float(e.get("amount"))
            payment_date = e.get("paymentDate") or _date.today().isoformat()
            if not bill_no or amount <= 0:
                continue
            payment_method = _normalize_method(e.get("paymentMethod") or "OTHER")
            reference = (e.get("reference") or "").strip() or None
            notes = (e.get("notes") or "").strip() or None
            external_id = (e.get("externalId") or "").strip() or None

            existing = None
            if external_id:
                existing = conn.execute(
                    "SELECT id FROM \"paymentEntries\" "
                    "WHERE \"externalId\" = %s AND status = 'ACTIVE'",
                    (external_id,),
                ).fetchone()
            if existing is not None:
                conn.execute(
                    "UPDATE \"paymentEntries\" SET \"paymentDate\" = %s, \"paymentAmount\" = %s, "
                    "\"paymentMethod\" = %s, reference = %s, notes = %s, "
                    "\"updatedAt\" = %s, \"updatedBy\" = %s WHERE id = %s",
                    (payment_date, amount, payment_method, reference, notes, now, "Import", existing["id"]),
                )
            else:
                conn.execute(
                    '''
                    INSERT INTO "paymentEntries"
                        ("billNo", "tenantId", "landlordId", "paymentDate", "paymentAmount",
                         "createdAt", "updatedAt", "createdBy", status, "paymentType", source,
                         "paymentMethod", "externalId", reference, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE', 'BILL', %s, %s, %s, %s, %s)
                    ''',
                    (bill_no, tenant_id, landlord_id, payment_date, amount, now, now, "Import",
                     source, payment_method, external_id, reference, notes),
                )
            affected[(tenant_id, bill_no)] = True

        results = []
        for (tenant_id, bill_no) in affected:
            result = _recalculate_and_apply(conn, tenant_id, bill_no)
            _apply_chain_and_pdfs(conn, tenant_id, bill_no)
            results.append(result)
        conn.commit()
    return results


def _apply_chain_and_pdfs(conn, tenant_id, bill_no):
    """Propagate the recomputed running balance forward, then regenerate the
    operator's own bill PDF (whose payment history changed).

    Note: recompute_tenant_arrear_chain also recomputes the settlement ledger,
    so allocations/settlements are always up to date on every mutation path.
    """
    from app.services.billing_service import recompute_tenant_arrear_chain
    recompute_tenant_arrear_chain(conn, tenant_id)
    # recompute regenerates future bills whose arrears changed; the operated
    # bill's own PDF must be refreshed regardless (payment history changed).
    _regenerate_bill_pdf(conn, tenant_id, bill_no)


def sync_bill_payment_from_receipt(tenant_id, bill_no, amount_received):
    """Backfill a single bill's amount_received into a payment entry when it has
    no active entries yet (used when a bill is created/edited with a payment).
    Keeps the invariant without duplicating existing legacy entries."""
    amount_received = _safe_float(amount_received)
    if amount_received <= 0:
        return
    with get_conn() as conn:
        exists = conn.execute(
            '''SELECT 1 FROM \"paymentEntries\" WHERE "billNo" = %s AND "tenantId" = %s AND status = 'ACTIVE' LIMIT 1''',
            (bill_no, tenant_id),
        ).fetchone()
        if exists:
            return
        row = conn.execute(
            'SELECT \"billDate\" FROM receipts WHERE "tenantId" = %s AND "billNo" = %s',
            (tenant_id, bill_no),
        ).fetchone()
        if row is None:
            return
        now = _datetime.utcnow().isoformat(timespec="seconds")
        conn.execute(
            '''
            INSERT INTO "paymentEntries"
                ("billNo", "tenantId", "paymentDate", "paymentAmount", "createdAt", "updatedAt",
                 "createdBy", status, "paymentType", source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE', 'BILL', 'MANUAL')
            ''',
            (bill_no, tenant_id, row["billDate"] or _date.today().isoformat(), amount_received, now, now, "Landlord"),
        )
        conn.commit()
