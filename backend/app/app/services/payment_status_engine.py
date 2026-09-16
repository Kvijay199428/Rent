"""Single authoritative payment-state engine (pure, dependency-free).

Central rules (locked design):
- grand_total      = current charge (receipts.total) + carried arrears
                     (receipts.previousarrears / bill Arrears)
- amount_received  = sum of ACTIVE payment-entry amounts, rounded to 2dp
- derived          = amount_received - grand_total
- status:
      PENDING  if amount_received <= 0
      ADVANCE  if derived > tolerance (TOLERANCE = 0.005)
      PAID     if |derived| <= tolerance
      PARTIAL  otherwise
- balance_due     = max(grand_total - amount_received, 0)
- advance_amount  = max(amount_received - grand_total, 0)

Every consumer (payment_service, billing_service, data_schema, the recalc
script, import/export) converges on this module so the bill-level
paymentstatus / amountreceived always agree with the payment ledger:

    receipts.amountreceived == SUM(payment_entries.amount WHERE status='ACTIVE')

UNPAID is not part of the canonical vocabulary.
"""

CANONICAL_PAYMENT_STATUSES = ("PENDING", "PARTIAL", "PAID", "ADVANCE")

TOLERANCE = 0.005


def round2(value) -> float:
    """Round an arbitrary value to 2dp; None/empty/bad values become 0.0."""
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _norm(value) -> float:
    """Coerce to float without rounding; bad values become 0.0."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def derive_status(grand_total, amount_received, tolerance: float = TOLERANCE) -> str:
    """Map (grand_total, received) to a canonical payment status string."""
    received = round2(amount_received)
    if received <= 0:
        return "PENDING"
    derived = round2(received - round2(grand_total))
    if derived > tolerance:
        return "ADVANCE"
    if abs(derived) <= tolerance:
        return "PAID"
    return "PARTIAL"


def calculate_payment_state(bill_total=0.0, arrears=0.0, active_amounts=()):
    """Compute the authoritative payment state for a single bill.

    bill_total      current-cycle charge (receipts.total / bill Total)
    arrears         carried-forward arrears (receipts.previousarrears / bill Arrears)
    active_amounts  iterable of ACTIVE payment-entry amounts

    Returns dict with the canonical keys:
        status, grand_total, amount_received, balance_due, advance_amount
    """
    grand_total = round2(_norm(bill_total) + _norm(arrears))
    received = round2(sum(_norm(a) for a in active_amounts))
    derived = round2(received - grand_total)

    if received <= 0:
        status = "PENDING"
    elif derived > TOLERANCE:
        status = "ADVANCE"
    elif abs(derived) <= TOLERANCE:
        status = "PAID"
    else:
        status = "PARTIAL"

    return {
        "status": status,
        "grand_total": grand_total,
        "amount_received": received,
        "balance_due": round2(max(grand_total - received, 0.0)),
        "advance_amount": round2(max(received - grand_total, 0.0)),
    }