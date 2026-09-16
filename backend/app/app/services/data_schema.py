"""Canonical import/export schema v2.

Central definitions shared by the import pipeline, the export engine and the
template builder:

- the 40-column flat CSV layout (one row per payment transaction)
- the 3 XLSX sheet layouts (Tenant_Profile / Rent_Receipts / Payment_Entries)
- the locked payment-method vocabulary
- small, dependency-free parsing/normalization helpers

Flat CSV column layout (40 columns):

    tenant   15 columns  -> PROFILE_HEADERS
    bill     16 columns  -> BILL_FLAT_HEADERS
    payment   9 columns  -> PAYMENT_FLAT_HEADERS

`amountReceived` and `paymentStatus` on the bill block are DERIVED values kept
for human readability only: the import engine always recomputes them from the
sum of ACTIVE payment entries and never trusts the file.
"""

from __future__ import annotations

import datetime as _datetime
import re as _re

from app.services.payment_status_engine import calculate_payment_state

# ----------------------------------------------------------------------------
# XLSX sheets
# ----------------------------------------------------------------------------

SHEET_PROFILE = "Tenant_Profile"
SHEET_RECEIPTS = "Rent_Receipts"
SHEET_PAYMENTS = "Payment_Entries"

PROFILE_HEADERS = [
    "tenantId", "tenantName", "Phone", "Email", "Company", "Address", "Room",
    "meterId", "PIN", "Rent", "Water", "electricityRate", "additionalPersonRate",
    "tankWater", "Status",
]

RECEIPT_HEADERS = [
    "BillNo", "tenantId", "Month", "Date", "Previous", "Current", "Units", "Rent",
    "Water", "Electricity", "Additional", "tankWater", "Maintenance", "Arrears",
    "amountReceived", "Total", "paymentStatus", "receiptStatus",
]

PAYMENT_HEADERS = [
    "paymentId", "billNo", "tenantId", "paymentDate", "paymentAmount",
    "paymentMethod", "paymentReference", "paymentNotes", "paymentStatus",
    "paymentSource", "paymentCreatedBy",
]

# ----------------------------------------------------------------------------
# Flat CSV (40 columns)
# ----------------------------------------------------------------------------

BILL_FLAT_HEADERS = [
    "BillNo", "Month", "Date", "Previous", "Current", "Units", "Rent",
    "Water", "Electricity", "Additional", "tankWater", "Maintenance",
    "MaintenanceDesc", "Arrears", "amountReceived", "paymentStatus",
]

PAYMENT_FLAT_HEADERS = [
    "paymentId", "paymentDate", "paymentAmount", "paymentMethod",
    "paymentReference", "paymentNotes", "paymentStatus", "paymentSource",
    "paymentCreatedBy",
]

#: The canonical, ordered 40-column flat CSV layout.
FLAT_HEADERS = PROFILE_HEADERS + BILL_FLAT_HEADERS + PAYMENT_FLAT_HEADERS
assert len(FLAT_HEADERS) == 40

BLANK_FLAT_ROW = {h: "" for h in FLAT_HEADERS}

# ----------------------------------------------------------------------------
# Vocabulary (locked)
# ----------------------------------------------------------------------------

PAYMENT_METHODS = ("CASH", "UPI", "BANK_TRANSFER", "CHEQUE", "CARD", "ONLINE", "OTHER")

VALID_TENANT_STATUSES = {"Active", "Inactive", "Archived"}

#: DB payment_entries.source vocabulary.
PAYMENT_SOURCES = ("MANUAL", "IMPORT", "LEGACY_IMPORT")

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def clean(value) -> str:
    """Return a stripped string ('' for None)."""
    if value is None:
        return ""
    return str(value).strip()


def to_float(value, default: float = 0.0) -> float:
    """Tolerant float coercion ('' / None / junk -> default)."""
    if value is None:
        return default
    try:
        return float(str(value).strip() or default)
    except (TypeError, ValueError):
        return default


def normalize_tenant_status(value, default: str = "Active") -> str:
    candidate = clean(value).title()
    return candidate if candidate in VALID_TENANT_STATUSES else default


def parse_tenant_id(value) -> int:
    """Extract numeric tenant id from 'T001', '001', 1, '1.0', 'T1-001'."""
    s = clean(value)
    if not s:
        return 0
    s = _re.sub(r"[^0-9.]", "", s.split("-")[0])
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return 0


def format_tenant_id(num_id: int) -> str:
    """Format a numeric tenant id as 'T001'."""
    return f"T{int(num_id):03d}"


def normalize_payment_method(value, default: str = "OTHER") -> str:
    candidate = clean(value).upper().replace(" ", "_")
    if candidate in PAYMENT_METHODS:
        return candidate
    return default


def make_payment_id(tenant_id: int, bill_no: str, seq: int) -> str:
    """Portable external payment identity: PAY-{tenantId}-{BillNo}-{seq}."""
    return f"PAY-{int(tenant_id)}-{clean(bill_no)}-{int(seq):02d}"


def normalize_payment_date(value) -> str:
    """Coerce a payment date to ISO 'YYYY-MM-DD' (export + import identity)."""
    if value is None:
        return ""
    if isinstance(value, (_datetime.datetime, _datetime.date)):
        return value.isoformat()[:10]
    s = clean(value)
    if not s:
        return ""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return _datetime.datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    for fmt in ("%d %B %Y", "%d %b %Y", "%B %d, %Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return _datetime.datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    try:
        serial = float(s)
        return (_datetime.datetime(1899, 12, 30) + _datetime.timedelta(days=serial)).strftime("%Y-%m-%d")
    except (ValueError, OverflowError):
        return s


def format_receipt_date(value) -> str:
    """Coerce a bill date to the receipt store format 'dd MMMM yyyy'."""
    if value is None:
        return ""
    if isinstance(value, (_datetime.datetime, _datetime.date)):
        return value.strftime("%d %B %Y")
    s = clean(value)
    if not s:
        return ""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return _datetime.datetime.strptime(s, fmt).strftime("%d %B %Y")
        except ValueError:
            continue
    for fmt in ("%d %B %Y", "%d %b %Y", "%B %d, %Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return _datetime.datetime.strptime(s, fmt).strftime("%d %B %Y")
        except ValueError:
            continue
    try:
        serial = float(s)
        return (_datetime.datetime(1899, 12, 30) + _datetime.timedelta(days=serial)).strftime("%d %B %Y")
    except (ValueError, OverflowError):
        return s


def format_receipt_month(value) -> str:
    """Coerce a bill month to 'MMMM yyyy' (e.g. 'June 2026')."""
    if value is None:
        return ""
    if isinstance(value, (_datetime.datetime, _datetime.date)):
        return value.strftime("%B %Y")
    s = clean(value)
    if not s:
        return ""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y-%m"):
        try:
            return _datetime.datetime.strptime(s, fmt).strftime("%B %Y")
        except ValueError:
            continue
    for fmt in ("%B %Y", "%b %Y", "%B %Y"):
        try:
            return _datetime.datetime.strptime(s, fmt).strftime("%B %Y")
        except ValueError:
            continue
    try:
        serial = float(s)
        return (_datetime.datetime(1899, 12, 30) + _datetime.timedelta(days=serial)).strftime("%B %Y")
    except (ValueError, OverflowError):
        return s


def detect_flat_headers(headers) -> tuple[str, list[str]]:
    """Classify a flat CSV header row.

    Returns ``(version, missing)`` where ``version`` is 'v2' when every column
    of the 40-column layout is present (case-insensitive) and 'v1' otherwise.
    """
    present = {h.strip().lower() for h in headers if clean(h)}
    required = {h.lower() for h in FLAT_HEADERS}
    missing = [h for h in FLAT_HEADERS if h.lower() not in present]
    return ("v2" if not missing else "v1", missing)


def recompute_bill_derived(bill: dict, payments: list[dict]) -> dict:
    """Set amountReceived / paymentStatus on a canonical bill from its ACTIVE
    payment entries. Never trusts the file-provided values. Status is computed
    against the grand total (charge + carried arrears) via the shared engine."""
    state = calculate_payment_state(
        bill_total=bill.get("Total"),
        arrears=bill.get("Arrears"),
        active_amounts=[p["amount"] for p in payments],
    )
    bill["amountReceived"] = state["amount_received"]
    bill["paymentStatus"] = state["status"]
    return bill