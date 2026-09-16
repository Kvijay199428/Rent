"""Recalculate bill-level payment status / received amounts from the payment ledger.

Central authority = app.services.payment_status_engine.calculate_payment_state,
the SAME function the live update/recalc path uses (payment_service
._recalculate_and_apply). Invariant recomputed per bill:

    receipts.amountreceived == SUM(payment_entries.amount WHERE status='ACTIVE')
    receipts.paymentstatus == engine-derived status (PENDING | PARTIAL | PAID | ADVANCE)

Usage:
    python scripts/recalculate_payment_status.py                 # dry run, all tenants
    python scripts/recalculate_payment_status.py --tenant T101   # dry run, one tenant
    python scripts/recalculate_payment_status.py --bill BILL-001 # dry run, one bill
    python scripts/recalculate_payment_status.py --apply         # persist changes

Notes:
    - Default is a dry run: nothing is written to the database. The whole run is
      wrapped in a single transaction that is only committed on --apply; dry-run
      rolls back.
    - --apply, per affected tenant, repeats:
        1) fix each bill's amountreceived / paymentstatus from the ledger,
        2) recompute_tenant_arrear_chain (re-normalises previousarrears from the
           now-corrected amounts; best-effort refreshes PDFs only for bills whose
           previousArrears changed, and re-syncs the settlement ledger),
        3) re-fix statuses once more against the canonical previousarrears
      so the result is idempotent.
    - PDFs are only ever re-rendered by the shared chain function, never
      wholesale by this script (--regen-pdfs is intentionally not offered).
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))


def _parse_tenant_id(raw: str):
    """Accept '101', 'T101', 't101' -> 101. None if not parseable."""
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    return int(digits) if digits else None


def _safe_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _bills(conn, tenant_id=None, bill_no=None):
    """Return receipt rows ordered chronologically (tenant, date, rowid)."""
    sql = (
        "SELECT tenantId, billNo, \"billTotal\", \"previousArrears\", \"amountReceived\", \"paymentStatus\" "
        "FROM receipts WHERE status != 'ARCHIVED'"
    )
    params = []
    if tenant_id is not None:
        sql += " AND tenantId = %s"
        params.append(tenant_id)
    if bill_no is not None:
        sql += " AND billNo = %s"
        params.append(bill_no)
    sql += " ORDER BY tenantId ASC, date ASC, id ASC"
    return conn.execute(sql, tuple(params)).fetchall()


def _active_amounts(conn, tenant_id, bill_no):
    rows = conn.execute(
        "SELECT \"paymentAmount\" FROM \"paymentEntries\" "
        "WHERE tenantId = %s AND billNo = %s AND status = 'ACTIVE'",
        (tenant_id, bill_no),
    ).fetchall()
    return [_safe_float(r["paymentAmount"]) for r in rows]


def _compute_state(calculate_payment_state, conn, row):
    return calculate_payment_state(
        bill_total=_safe_float(row["billTotal"]),
        arrears=_safe_float(row["previousArrears"]),
        active_amounts=_active_amounts(conn, row["tenantId"], row["billNo"]),
    )


def _fix_bill_statuses(conn, calculate_payment_state, tenant_id):
    """Recompute and persist engine-derived status/amount for every bill of one
    tenant. Returns the number of bills whose stored values changed."""
    changed = 0
    for row in _bills(conn, tenant_id=tenant_id):
        state = _compute_state(calculate_payment_state, conn, row)
        if _safe_float(row["amountReceived"]) != state["amount_received"] or (
            row["paymentStatus"] or "PENDING"
        ) != state["status"]:
            conn.execute(
                "UPDATE receipts SET \"amountReceived\" = %s, \"paymentStatus\" = %s "
                "WHERE tenantId = %s AND billNo = %s",
                (state["amount_received"], state["status"], tenant_id, row["billNo"]),
            )
            changed += 1
    return changed


def main():
    from app.core.db import get_conn, init_pool
    from app.db.connection import close_pool
    from app.services.payment_status_engine import calculate_payment_state
    from app.services.billing_service import recompute_tenant_arrear_chain

    try:
        return _main(init_pool, get_conn, calculate_payment_state, recompute_tenant_arrear_chain)
    finally:
        close_pool()


def _main(init_pool, get_conn, calculate_payment_state, recompute_tenant_arrear_chain):
    init_pool()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", help="Tenant ID filter (e.g. 101 or T101).")
    parser.add_argument("--bill", help="Bill number filter (e.g. BILL-001).")
    parser.add_argument("--apply", action="store_true", help="Persist changes (default: dry run).")
    args = parser.parse_args()

    tenant_id = _parse_tenant_id(args.tenant) if args.tenant else None
    if args.tenant and tenant_id is None:
        print(f"ERROR: could not parse --tenant value {args.tenant!r}")
        return 1

    with get_conn() as conn:
        affected_tenants = set()
        examined = changed = 0

        for row in _bills(conn, tenant_id=tenant_id, bill_no=args.bill):
            state = _compute_state(calculate_payment_state, conn, row)
            stored_amount = _safe_float(row["amountReceived"])
            stored_status = row["paymentStatus"] or "PENDING"
            differs = (stored_amount != state["amount_received"]) or (stored_status != state["status"])

            examined += 1
            if differs:
                changed += 1
                affected_tenants.add(row["tenantId"])
                flag = "NEEDS UPDATE"
            else:
                flag = "OK"

            print(
                f"[{flag}] tenant={row['tenantId']} bill={row['billNo']} "
                f"stored(status={stored_status}, amount={stored_amount}) -> "
                f"computed(status={state['status']}, amount={state['amount_received']}) "
                f"(grandTotal={state['grand_total']}, balanceDue={state['balance_due']}, "
                f"advanceAmount={state['advance_amount']})"
            )

        print(f"\nExamined {examined} bills, {changed} need update, {examined - changed} OK.")

        if not args.apply:
            print("DRY RUN: no changes written. Re-run with --apply to persist.")
            return 0

        if not changed:
            print("Nothing to apply.")
            return 0

        applied = 0
        for t_id in sorted(affected_tenants):
            applied += _fix_bill_statuses(conn, calculate_payment_state, t_id)
            recompute_tenant_arrear_chain(conn, t_id)
            applied += _fix_bill_statuses(conn, calculate_payment_state, t_id)

        conn.commit()
        print(f"APPLIED {applied} status update(s) across {len(affected_tenants)} tenant(s): "
              f"{sorted(affected_tenants)}")
        return 0


if __name__ == "__main__":
    sys.exit(main())