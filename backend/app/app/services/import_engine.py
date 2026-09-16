"""Import engine v2: canonical (flat CSV / 3-sheet XLSX / full ZIP) → database.

Owns the V2 import pipeline that also persists payment transactions:

- ``parse_import_file`` dispatches by extension to the canonical in-memory model
- ``detect_conflicts`` / ``detect_encrypted_pins`` reuse the v1 conflict rules
  (tenant identity is the numeric tenantId only; name is never an identity key)
- ``apply_import`` mirrors the v1 single-transaction execute flow (tenant upsert,
  PIN handling, receipt merge/replace) and additionally upserts payment entries
  idempotently by ``external_id``, then recomputes every affected bill's derived
  fields (amountReceived / paymentStatus) and the tenant arrears chain.

Design invariants (locked):
- ``external_id`` is the identity key for payment entries (unique partial index
  over ACTIVE rows); a blank id is auto-generated as PAY-{tenantId}-{BillNo}-{seq}.
- amountReceived / paymentStatus are DERIVED (never trusted from the file).
- v1 (2-sheet, no payment sheet) files get exactly one LEGACY_IMPORT payment per
  bill whose file amountReceived > 0 (performed by the canonicalizer).
"""

from __future__ import annotations

import datetime
import json
import re
import secrets
import uuid

from fastapi import HTTPException

from . import data_schema as S
from .canonicalizer import canonicalize_flat, canonicalize_xlsx
from .csv_parser import parse_csv_bytes
from .xlsx_parser import is_zip, parse_xlsx_bytes


# ---------------------------------------------------------------------------
# Small helpers ported from the v1 engine (kept local to avoid a sync import
# cycle; the v1 engine and this module never import each other).
# ---------------------------------------------------------------------------


def _parse_excel_date(val: str) -> str:
    if not val or not str(val).strip():
        return ""
    val_str = str(val).strip()

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(val_str, fmt).strftime("%d %B %Y")
        except ValueError:
            continue

    try:
        serial = float(val_str)
        excel_epoch = datetime.datetime(1899, 12, 30)
        dt = excel_epoch + datetime.timedelta(days=serial)
        return dt.strftime("%d %B %Y")
    except (ValueError, OverflowError):
        pass

    return val_str


def _parse_month_date(val: str) -> str:
    """Parse Excel month value to 'Month Year' format."""
    if not val or not str(val).strip():
        return ""
    val_str = str(val).strip()

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(val_str, fmt)
            return dt.strftime("%B %Y")  # e.g., "June 2026"
        except ValueError:
            continue

    try:
        serial = float(val_str)
        excel_epoch = datetime.datetime(1899, 12, 30)
        dt = excel_epoch + datetime.timedelta(days=serial)
        return dt.strftime("%B %Y")
    except (ValueError, OverflowError):
        pass

    return val_str


def _is_encrypted_pin(pin_value: str) -> bool:
    """Detect if a PIN value appears to be encrypted rather than a plain 4-digit PIN."""
    if not pin_value or not str(pin_value).strip():
        return False

    pin_str = str(pin_value).strip()

    # If it's exactly 4 digits, it's a plain PIN
    if len(pin_str) == 4 and pin_str.isdigit():
        return False

    # If it's longer than 20 chars and contains base64-like characters, likely encrypted
    if len(pin_str) > 20:
        base64_pattern = re.compile(r"^[A-Za-z0-9+/=]+$")
        if base64_pattern.match(pin_str):
            return True

    # If it's not 4 digits but has alphanumeric/special chars, likely encrypted
    if len(pin_str) > 4:
        return True

    return False


def _generate_random_pin() -> str:
    """Generate a random 4-digit PIN for auto-assignment."""
    return f"{secrets.randbelow(10000):04d}"


def _extract_numeric_tenant_id(tenant_id_str: str) -> int:
    """Extract numeric tenant ID from format like 'T001' -> 1."""
    cleaned = re.sub(r"^[Tt]", "", str(tenant_id_str).strip())
    try:
        return int(cleaned)
    except ValueError:
        return 0


def _get_next_available_tenant_id() -> int:
    """Get the next available tenant ID number (global ID space across all landlords)."""
    from app.services.tenant_service import load_tenants as _load_all_tenants

    tenants = _load_all_tenants(include_archived=True)
    if not tenants:
        return 1
    max_id = max(t.id for t in tenants)
    return max_id + 1


def _remap_bill_no(original_bill_no: str, old_tenant_id_str: str, new_tenant_id: int) -> str:
    """
    Remap a receipt bill number from the old tenant prefix to a new one.
    Example: 'T1-001' with old_tenant_id_str='T001' and new_tenant_id=2 → 'T2-001'
    Falls back to the original value if the pattern doesn't match.
    """
    if not original_bill_no:
        return original_bill_no
    old_numeric = _extract_numeric_tenant_id(old_tenant_id_str)
    old_prefix = f"T{old_numeric}-"
    if original_bill_no.startswith(old_prefix):
        seq_part = original_bill_no[len(old_prefix):]
        return f"T{new_tenant_id}-{seq_part}"
    return original_bill_no


# ---------------------------------------------------------------------------
# Canonical <-> v1 parsed shape
# ---------------------------------------------------------------------------


def _build_v1_parsed(canonical: dict) -> dict:
    """Rebuild the v1 ``{t_id_str: {"profile":..., "receipts": [...]}}`` shape so
    the conflict detector / encrypted-PIN rules operate on unchanged semantics."""
    data: dict = {}
    for num_id, profile in canonical["tenants"].items():
        t_id = profile.get("tenantId") or S.format_tenant_id(num_id)
        receipts = [b for b in canonical["bills"] if b.get("tenantId") == num_id]
        data[t_id] = {"profile": profile, "receipts": receipts}
    return data


# ---------------------------------------------------------------------------
# File ingestion
# ---------------------------------------------------------------------------


def parse_import_file(filename: str, content) -> dict:
    """Dispatch an uploaded file to a canonical import model.

    Supported::
        .zip   full-export archive (first .xlsx inside)
        .xlsx  3-sheet v2 workbook (or 2-sheet v1 workbook)
        .csv   single flat 40-column v2 file (one row per payment)

    Raises ValueError on unsupported types / structurally invalid payloads.
    """
    low = (filename or "").lower()
    if low.endswith(".zip"):
        from .xlsx_parser import extract_zip_xlsx

        sheets = extract_zip_xlsx(content)
        return canonicalize_xlsx(sheets)
    if low.endswith(".xlsx"):
        sheets = parse_xlsx_bytes(content)
        return canonicalize_xlsx(sheets)
    if low.endswith(".csv"):
        headers, rows = parse_csv_bytes(content)
        version, _missing = S.detect_flat_headers(headers)
        if version != "v2":
            raise ValueError(
                "CSV must use the canonical 40-column flat layout (one row per payment)."
            )
        return canonicalize_flat(headers, rows)
    raise ValueError(f"Unsupported import file type: '{filename}'. Use .xlsx, .csv or .zip.")


def merge_canonical(canonicals: list) -> dict:
    """Merge multiple canonical models: tenants and bills are first-wins by their
    identity keys, payments are first-wins by external_id. The resulting version
    is the highest among inputs (v2 supersedes v1)."""
    tenants: dict = {}
    bills: dict = {}
    payments: dict = {}
    warnings: list = []
    version = "v1"
    legacy = 0

    for canonical in canonicals or []:
        for num_id, profile in canonical.get("tenants", {}).items():
            tenants.setdefault(num_id, profile)
        for bill in canonical.get("bills", []):
            bills.setdefault((bill.get("tenantId"), bill.get("billNo")), bill)
        for pay in canonical.get("payments", []):
            payments.setdefault(pay.get("externalId"), pay)
        warnings.extend(canonical.get("warnings", []))
        if canonical.get("version") == "v2":
            version = "v2"
        legacy += canonical.get("legacy_backfilled", 0)

    return {
        "tenants": tenants,
        "bills": list(bills.values()),
        "payments": list(payments.values()),
        "warnings": warnings,
        "version": version,
        "legacy_backfilled": legacy,
    }


# ---------------------------------------------------------------------------
# Conflict detection (v1 rules, canonical input)
# ---------------------------------------------------------------------------


def detect_conflicts(canonical: dict, landlord_id=None) -> dict:
    """Detect tenant and receipt conflicts between import data and existing
    system data. Returns ``{t_id_str: conflict_info}`` (keyed by file tenant id).

    Tenant identity is the numeric tenantId only; phone/email/meter are
    additional match signals surfaced to the user for resolution.
    """
    from app.services.billing_service import get_all_receipts
    from app.services.tenant_service import load_tenants

    sys_tenants = load_tenants(include_archived=True, landlord_id=landlord_id)
    sys_receipts = get_all_receipts(include_archived_tenants=True, landlord_id=landlord_id)

    sys_tenant_ids = {t.id for t in sys_tenants}
    sys_tenant_names = {t.name.lower(): t for t in sys_tenants}
    sys_tenant_phones = {t.phone.lower(): t for t in sys_tenants if t.phone}
    sys_tenant_emails = {t.email.lower(): t for t in sys_tenants if getattr(t, "email", "")}
    sys_tenant_meters = {t.meterId.lower(): t for t in sys_tenants if getattr(t, "meterId", "")}

    sys_receipt_bills = {r.get("Bill") for r in sys_receipts}
    sys_receipt_tenant_months = {
        f"{int(r.get('TenantId', 0) or 0)}_{r.get('Month', '').lower()}"
        for r in sys_receipts
        if int(r.get("TenantId", 0) or 0) > 0
    }

    conflicts = {}

    for t_id, t_data in _build_v1_parsed(canonical).items():
        p = t_data["profile"]
        t_name = p.get("tenantName", "").strip()
        t_phone = p.get("Phone", "").strip()
        t_email = p.get("Email", "").strip()
        t_meter = p.get("meterId", "").strip()

        numeric_id = _extract_numeric_tenant_id(t_id)

        conflict_info = {
            "importTenant": {"tenantId": t_id, "tenantName": t_name},
            "matches": [],
            "receiptConflicts": [],
        }

        # 1. Tenant ID match
        if numeric_id in sys_tenant_ids:
            existing = next((t for t in sys_tenants if t.id == numeric_id), None)
            if existing:
                conflict_info["matches"].append({
                    "type": "tenant_id",
                    "existingTenantId": existing.id,
                    "existingTenantName": existing.name,
                })

        # 2. Name match
        if t_name.lower() in sys_tenant_names:
            existing = sys_tenant_names[t_name.lower()]
            conflict_info["matches"].append({
                "type": "name",
                "existingTenantId": existing.id,
                "existingTenantName": existing.name,
            })

        # 3. Phone match
        if t_phone and t_phone.lower() in sys_tenant_phones:
            existing = sys_tenant_phones[t_phone.lower()]
            conflict_info["matches"].append({
                "type": "phone",
                "existingTenantId": existing.id,
                "existingTenantName": existing.name,
            })

        # 4. Email match
        if t_email and t_email.lower() in sys_tenant_emails:
            existing = sys_tenant_emails[t_email.lower()]
            conflict_info["matches"].append({
                "type": "email",
                "existingTenantId": existing.id,
                "existingTenantName": existing.name,
            })

        # 5. Meter ID match
        if t_meter and t_meter.lower() in sys_tenant_meters:
            existing = sys_tenant_meters[t_meter.lower()]
            conflict_info["matches"].append({
                "type": "meterId",
                "existingTenantId": existing.id,
                "existingTenantName": existing.name,
            })

        # Remove duplicate matches (same tenant matched multiple ways)
        unique_matches = []
        seen_match_keys = set()
        for m in conflict_info["matches"]:
            key = f"{m['type']}_{m['existingTenantId']}"
            if key not in seen_match_keys:
                seen_match_keys.add(key)
                unique_matches.append(m)
        conflict_info["matches"] = unique_matches

        # 6. Receipt matches
        for r in t_data.get("receipts", []):
            billNo = str(r.get("BillNo", "")).strip()
            month = _parse_month_date(str(r.get("Month", "")).strip())

            conflict_reason = None
            if billNo and billNo in sys_receipt_bills:
                conflict_reason = "billNo_exists"
            elif month:
                if f"{numeric_id}_{month.lower()}" in sys_receipt_tenant_months:
                    conflict_reason = "tenant_month_exists"

            if conflict_reason:
                conflict_info["receiptConflicts"].append({
                    "billNo": billNo,
                    "month": month,
                    "reason": conflict_reason,
                    "actionRequired": True,
                })

        if conflict_info["matches"] or conflict_info["receiptConflicts"]:
            conflicts[f"{t_id}"] = conflict_info

    return conflicts


def detect_encrypted_pins(canonical: dict) -> dict:
    """Detect encrypted PINs in the import data."""
    encrypted_pins = {}

    for t_id, t_data in _build_v1_parsed(canonical).items():
        p = t_data["profile"]
        pin_value = str(p.get("PIN") or "").strip()

        if pin_value and _is_encrypted_pin(pin_value):
            encrypted_pins[t_id] = {
                "tenantId": t_id,
                "tenantName": p.get("tenantName", ""),
                "pin_value": pin_value[:20] + "..." if len(pin_value) > 20 else pin_value,
                "pin_length": len(pin_value),
                "is_encrypted": True,
            }

    return encrypted_pins


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


class ConflictResolutionError(Exception):
    """Raised when the import still needs manual resolution (HTTP 409)."""

    def __init__(self, conflicts, encrypted_pins):
        super().__init__("Import requires manual resolution.")
        self.conflicts = conflicts or []
        self.encrypted_pins = encrypted_pins or []

    def to_payload(self) -> dict:
        return {
            "message": str(self),
            "conflicts": self.conflicts,
            "encrypted_pins": self.encrypted_pins,
        }


def _upsert_payment(conn, entry: dict, landlord_id, now: str, source: str) -> None:
    """Idempotent single-entry upsert (external_id ↔ ACTIVE row). Mirrors
    ``payment_service.import_payment_entries`` exactly, minus its own commit,
    so the caller keeps control of the surrounding transaction."""
    tenant_id = int(entry.get("tenantId") or 0)
    bill_no = entry.get("billNo")
    amount = float(entry.get("amount") or 0)
    if not bill_no or amount <= 0 or tenant_id <= 0:
        return

    payment_date = entry.get("paymentDate")
    if not payment_date:
        import datetime as _dt

        payment_date = _dt.date.today().isoformat()
    payment_method = S.normalize_payment_method(entry.get("paymentMethod") or "OTHER")
    reference = str(entry.get("reference") or "").strip() or None
    notes = str(entry.get("notes") or "").strip() or None
    external_id = str(entry.get("externalId") or "").strip() or None

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


def apply_import(
    canonical_files: dict,
    selected_list: list,
    id_resolutions: dict,
    status_overrides: dict,
    pin_handling_mode: str,
    pin_resolutions: dict,
    receipt_strategies: dict,
    landlord_id: int,
) -> dict:
    """Execute a V2 import inside a single transaction.

    ``canonical_files`` maps ``filename -> canonical model``. ``selected_list``
    is the list of ``"{filename}::{t_id}"`` target keys chosen by the client.
    Raises ConflictResolutionError (HTTP 409 contract) if unresolved conflicts or
    encrypted PINs remain. Returns the same summary shape as the v1 execute
    endpoint, plus payment counts.
    """
    from app.core.db import get_conn
    from app.services.billing_service import recompute_tenant_arrear_chain
    from app.services.payment_service import _apply_chain_and_pdfs, _recalculate_and_apply
    from app.services.tenant_service import load_tenants
    from app.authentication.common.utils import validate_tenantPin, hash_pin
    from app.authentication.common.pin_vault import encrypt_admin_view_pin

    # Existing system identity (scoped to landlord, global for ID allocation)
    sys_tenants = load_tenants(include_archived=True, landlord_id=landlord_id)
    sys_tenant_ids = {t.id for t in sys_tenants}
    sys_tenant_by_id = {t.id: t for t in sys_tenants}
    _global_tenant_ids = {t.id for t in load_tenants(include_archived=True)}

    # Validate resolutions (mirror v1 semantics exactly)
    unresolved_conflicts = []
    unresolved_pins = []

    for filename, canonical in canonical_files.items():
        conflicts = detect_conflicts(canonical, landlord_id=landlord_id)
        encrypted_pins = detect_encrypted_pins(canonical)

        for t_id, conflict_info in conflicts.items():
            target_key = f"{filename}::{t_id}"
            if target_key not in selected_list:
                continue

            has_tenant_conflict = len(conflict_info.get("matches", [])) > 0
            has_receipt_conflict = len(conflict_info.get("receiptConflicts", [])) > 0

            resolution_action = id_resolutions.get(target_key)
            if has_tenant_conflict and resolution_action not in (
                "CREATE_NEW", "UPDATE_EXISTING", "SKIP", "MERGE_RECEIPTS_ONLY"
            ):
                unresolved_conflicts.append({
                    "target": target_key,
                    "tenantName": conflict_info["importTenant"]["tenantName"],
                    "reason": "unresolved_tenant_conflict",
                    "matches": conflict_info.get("matches"),
                })
                continue

            receipt_action = receipt_strategies.get(target_key)
            if (
                has_receipt_conflict
                and receipt_action not in ("SKIP", "MERGE_RECEIPTS_ONLY", "REPLACE_RECEIPTS")
                and resolution_action != "SKIP"
            ):
                unresolved_conflicts.append({
                    "target": target_key,
                    "tenantName": conflict_info["importTenant"]["tenantName"],
                    "reason": "unresolved_receipt_conflict",
                    "receiptConflicts": conflict_info.get("receiptConflicts"),
                })

        if pin_handling_mode == "prompt":
            for t_id, pin_info in encrypted_pins.items():
                target_key = f"{filename}::{t_id}"
                if target_key not in selected_list:
                    continue
                if target_key not in pin_resolutions and id_resolutions.get(target_key) != "SKIP":
                    unresolved_pins.append({
                        "target": target_key,
                        "tenantName": pin_info["tenantName"],
                        "reason": "encrypted_pin_detected",
                    })

    if unresolved_conflicts or unresolved_pins:
        raise ConflictResolutionError(unresolved_conflicts, unresolved_pins)

    # Pre-compute target_key -> existing tenant id (ID match is authoritative).
    existing_tenant_id_map: dict = {}
    for filename, canonical in canonical_files.items():
        conflicts = detect_conflicts(canonical, landlord_id=landlord_id)
        for t_id, conflict_info in conflicts.items():
            matches = conflict_info.get("matches", [])
            if matches:
                existing_tenant_id_map[f"{filename}::{t_id}"] = matches[0]["existingTenantId"]

    imported_tenants = []
    imported_receipts = 0
    imported_payments = 0
    skipped_targets = set(selected_list)
    auto_assigned_pins = {}
    affected_tenant_ids = set()

    admin_username = "Admin"
    now_iso = datetime.datetime.utcnow().isoformat()

    try:
        with get_conn() as conn:
            conn.execute("BEGIN")

            job_row = conn.execute(
                "INSERT INTO \"importJobs\" (\"createdAt\", \"createdBy\", filename, status, \"previewJson\", \"resolutionJson\", \"resultJson\") "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (now_iso, admin_username, ", ".join(canonical_files.keys()), "IN_PROGRESS", "{}", "{}", "{}"),
            ).fetchone()
            job_id = job_row["id"]

            for filename, canonical in canonical_files.items():
                parsed = _build_v1_parsed(canonical)

                for t_id, t_data in parsed.items():
                    target_key = f"{filename}::{t_id}"
                    if target_key not in selected_list:
                        continue

                    skipped_targets.discard(target_key)
                    action = id_resolutions.get(target_key, "CREATE_NEW")

                    if action == "SKIP":
                        conn.execute(
                            "INSERT INTO \"importJobItems\" (\"importJobId\", \"targetKey\", \"importTenantId\", \"importTenantName\", action, result) "
                            "VALUES (%s, %s, %s, %s, %s, %s)",
                            (job_id, target_key, t_id, t_data["profile"].get("tenantName", ""), action, "SKIPPED"),
                        )
                        continue

                    p = t_data["profile"]
                    t_name = str(p.get("tenantName", "")).strip()
                    if not t_name:
                        continue

                    existing_tid = existing_tenant_id_map.get(target_key)
                    existing_t = sys_tenant_by_id.get(existing_tid) if existing_tid else None

                    tenantId = None
                    is_new = False

                    if action == "CREATE_NEW":
                        next_id = _get_next_available_tenant_id()
                        while next_id in _global_tenant_ids:
                            next_id += 1
                        tenantId = next_id

                        viewToken = str(uuid.uuid4())
                        conn.execute('''
                            INSERT INTO tenants (
                                id, name, company, phone, email, address, "roomNumber", occupation, notes, status,
                                "rentAmount", "waterCharge", "electricityRate", "previousMeter", "additionalPersonCharge", "securityDeposit",
                                "defaultTankWaterCharge", "meterId", "viewToken", "tenantPin", "failedAttempts", "landlordId"
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ''', (
                            tenantId, t_name, p.get("Company", ""), p.get("Phone", ""), p.get("Email", ""),
                            p.get("Address", ""), p.get("Room", ""), "", "", S.normalize_tenant_status(status_overrides.get(target_key), p.get("Status", "Active")),
                            float(p.get("Rent", 0) or 0), float(p.get("Water", 0) or 0), float(p.get("electricityRate", 0) or 0),
                            0, float(p.get("additionalPersonRate", 0) or 0), 0, float(p.get("tankWater", 0) or 0),
                            p.get("meterId", ""), viewToken, "", 0, landlord_id
                        ))
                        _global_tenant_ids.add(tenantId)
                        sys_tenant_ids.add(tenantId)
                        is_new = True

                    elif action == "UPDATE_EXISTING" and existing_t:
                        tenantId = existing_t.id
                        conn.execute('''
                            UPDATE tenants SET
                                company=COALESCE(%s, company), phone=COALESCE(%s, phone), email=COALESCE(%s, email),
                                address=COALESCE(%s, address), "roomNumber"=COALESCE(%s, "roomNumber"), "meterId"=COALESCE(%s, "meterId"),
                                "rentAmount"=COALESCE(%s, "rentAmount"), "waterCharge"=COALESCE(%s, "waterCharge"), "electricityRate"=COALESCE(%s, "electricityRate"),
                                "additionalPersonCharge"=COALESCE(%s, "additionalPersonCharge"), "defaultTankWaterCharge"=COALESCE(%s, "defaultTankWaterCharge"),
                                status=COALESCE(%s, status)
                            WHERE id=%s
                        ''', (
                            p.get("Company"), p.get("Phone"), p.get("Email"), p.get("Address"), p.get("Room"), p.get("meterId"),
                            float(p.get("Rent", 0) or 0) if p.get("Rent") else None,
                            float(p.get("Water", 0) or 0) if p.get("Water") else None,
                            float(p.get("electricityRate", 0) or 0) if p.get("electricityRate") else None,
                            float(p.get("additionalPersonRate", 0) or 0) if p.get("additionalPersonRate") else None,
                            float(p.get("tankWater", 0) or 0) if p.get("tankWater") else None,
                            S.normalize_tenant_status(status_overrides.get(target_key), p.get("Status", "Active")),
                            tenantId,
                        ))

                    elif action == "MERGE_RECEIPTS_ONLY" and existing_t:
                        tenantId = existing_t.id

                    if not tenantId:
                        continue

                    _lrow = conn.execute(
                        "SELECT \"landlordId\" FROM tenants WHERE id = %s", (tenantId,)
                    ).fetchone()
                    tenant_landlord_id = _lrow["landlordId"] if _lrow else None

                    # ── PIN HANDLING ──
                    if action in ("CREATE_NEW", "UPDATE_EXISTING"):
                        raw_pin = str(p.get("PIN") or "").strip()
                        plain_pin = None
                        pin_changed = False
                        hashed_pin = None
                        encrypted_pin = None

                        if raw_pin:
                            if _is_encrypted_pin(raw_pin):
                                if pin_handling_mode == "assign_random":
                                    plain_pin = _generate_random_pin()
                                    auto_assigned_pins[target_key] = plain_pin
                                    pin_changed = True
                                elif pin_handling_mode == "prompt":
                                    plain_pin = pin_resolutions.get(target_key)
                                    if plain_pin:
                                        pin_changed = True
                            else:
                                plain_pin = raw_pin
                                pin_changed = True

                        if pin_changed and plain_pin:
                            try:
                                validate_tenantPin(plain_pin)
                                hashed_pin = hash_pin(plain_pin)
                                encrypted_pin = encrypt_admin_view_pin(plain_pin)

                                conn.execute("UPDATE tenants SET \"tenantPin\" = %s WHERE id = %s", (hashed_pin, tenantId))
                                conn.execute(
                                    'INSERT INTO \"tenantPinHistory\" ("tenantId", \"pinHash\", \"changedAt\") VALUES (%s, %s, %s)',
                                    (tenantId, hashed_pin, now_iso),
                                )
                                conn.execute(
                                    'INSERT INTO \"tenantPinAdminStore\" ("tenantId", \"encryptedPin\", \"updatedAt\") VALUES (%s, %s, %s) '
                                    'ON CONFLICT ("tenantId") DO UPDATE SET \"encryptedPin\" = excluded.\"encryptedPin\", \"updatedAt\" = excluded.\"updatedAt\"',
                                    (tenantId, encrypted_pin, now_iso),
                                )
                                if not is_new:
                                    conn.execute('DELETE FROM \"tenantSessions\" WHERE "tenantId" = %s', (tenantId,))
                            except HTTPException:
                                pass  # Invalid pin format

                    # ── RECEIPTS + PAYMENTS ──
                    rec_strategy = receipt_strategies.get(target_key, "MERGE_RECEIPTS_ONLY")
                    if rec_strategy == "REPLACE_RECEIPTS":
                        conn.execute('DELETE FROM receipts WHERE "tenantId" = %s', (tenantId,))
                        # Remove payment history for the replaced receipts so the
                        # derived amountReceived / paymentStatus never goes stale.
                        conn.execute(
                            """DELETE FROM \"paymentEntries\" WHERE "tenantId" = %s AND status = 'ACTIVE'""",
                            (tenantId,),
                        )

                    if rec_strategy in ("MERGE_RECEIPTS_ONLY", "REPLACE_RECEIPTS"):
                        for r in t_data.get("receipts", []):
                            original_billNo = str(r.get("billNo", "")).strip()
                            if not original_billNo:
                                continue

                            if action == "CREATE_NEW":
                                billNo = _remap_bill_no(original_billNo, t_id, tenantId)
                            else:
                                billNo = original_billNo

                            r_date = _parse_excel_date(r.get("Date", ""))
                            r_month = _parse_month_date(r.get("Month", ""))

                            exists = conn.execute(
                                'SELECT 1 FROM receipts WHERE "billNo" = %s AND "tenantId" = %s',
                                (billNo, tenantId),
                            ).fetchone()

                            if exists:
                                if rec_strategy == "MERGE_RECEIPTS_ONLY":
                                    conn.execute('''
                                        UPDATE receipts SET
                                            "billDate"=%s, "billMonth"=%s, "tenantId"=%s, "tenantName"=%s, "previousMeter"=%s, "currentMeter"=%s, units=%s, "rentAmount"=%s,
                                            "additionalAmount"=%s, "waterAmount"=%s, "tankWaterAmount"=%s, "electricityAmount"=%s, "billTotal"=%s, pdf=%s,
                                            "electricityRate"=%s, status=%s, "additionalPersonRate"=%s,
                                            "paymentStatus"=%s, "maintenanceCharge"=%s, "maintenanceDesc"=%s, "previousArrears"=%s, "amountReceived"=%s
                                        WHERE "billNo"=%s AND "tenantId"=%s
                                    ''', (
                                        r_date, r_month, tenantId, t_name, float(r.get("Previous", 0) or 0), float(r.get("Current", 0) or 0),
                                        float(r.get("Units", 0) or 0), float(r.get("Rent", 0) or 0), float(r.get("Additional", 0) or 0),
                                        float(r.get("Water", 0) or 0), float(r.get("tankWater", 0) or 0), float(r.get("Electricity", 0) or 0),
                                        float(r.get("Total", 0) or 0), "", float(r.get("Rate", 0) or 0), r.get("receiptStatus", "ACTIVE"),
                                        float(r.get("additionalPersonRate", 0) or 0), "PENDING",
                                        float(r.get("Maintenance", 0) or 0), r.get("MaintenanceDesc", ""), float(r.get("Arrears", 0) or 0),
                                        0.0, billNo, tenantId,
                                    ))
                                    imported_receipts += 1
                            else:
                                conn.execute('''
                                    INSERT INTO receipts (
                                        "billNo", "billDate", "billMonth", "tenantId", "tenantName", "previousMeter", "currentMeter", units, "rentAmount",
                                        "additionalAmount", "waterAmount", "tankWaterAmount", "electricityAmount", "billTotal", pdf,
                                        "tenantPhone", "tenantCompany", "tenantAddress", "electricityRate", status,
                                        "additionalPersons", "additionalPersonRate", "receiptVersion", "generatedBy", "paymentStatus",
                                        "maintenanceCharge", "maintenanceDesc", "previousArrears", "amountReceived", "landlordId"
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ''', (
                                    billNo, r_date, r_month, tenantId, t_name, float(r.get("Previous", 0) or 0), float(r.get("Current", 0) or 0),
                                    float(r.get("Units", 0) or 0), float(r.get("Rent", 0) or 0), float(r.get("Additional", 0) or 0),
                                    float(r.get("Water", 0) or 0), float(r.get("tankWater", 0) or 0), float(r.get("Electricity", 0) or 0),
                                    float(r.get("Total", 0) or 0), "", "", "", "", float(r.get("Rate", 0) or 0), r.get("receiptStatus", "ACTIVE"),
                                    0, float(r.get("additionalPersonRate", 0) or 0), 8, "Import", "PENDING",
                                    float(r.get("Maintenance", 0) or 0), r.get("MaintenanceDesc", ""), float(r.get("Arrears", 0) or 0), 0.0,
                                    tenant_landlord_id,
                                ))
                                imported_receipts += 1

                        # ── PAYMENTS (v2) ──
                        # Apply payments for this file tenant. On CREATE_NEW both
                        # the bill numbers and the payments are remapped together.
                        file_tenant_id = _extract_numeric_tenant_id(t_id)
                        affected_bills = []  # (resolved tenant id, remapped bill no)
                        for pay in canonical.get("payments", []):
                            if pay.get("tenantId") != file_tenant_id:
                                continue
                            if action == "CREATE_NEW":
                                pay_bill_no = _remap_bill_no(pay.get("billNo"), t_id, tenantId)
                            else:
                                pay_bill_no = pay.get("billNo")
                            _upsert_payment(conn, {
                                "tenantId": tenantId,
                                "billNo": pay_bill_no,
                                "paymentDate": pay.get("paymentDate"),
                                "amount": pay.get("amount"),
                                "paymentMethod": pay.get("paymentMethod") or "OTHER",
                                "reference": pay.get("reference"),
                                "notes": pay.get("notes"),
                                "externalId": pay.get("externalId"),
                            }, landlord_id, now_iso, source=pay.get("source") or "IMPORT")
                            affected_bills.append((tenantId, pay_bill_no))
                            imported_payments += 1

                        for rid, rbno in affected_bills:
                            _recalculate_and_apply(conn, rid, rbno)
                            _apply_chain_and_pdfs(conn, rid, rbno)

                    affected_tenant_ids.add(tenantId)

                    conn.execute(
                        "INSERT INTO \"importJobItems\" (\"importJobId\", \"targetKey\", \"importTenantId\", \"importTenantName\", action, \"existingTenantId\", result) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (job_id, target_key, t_id, t_name, action, existing_t.id if existing_t else None, "SUCCESS"),
                    )

                    imported_tenants.append({
                        "target": target_key,
                        "tenantId": tenantId,
                        "tenantName": t_name,
                        "action": action,
                    })

            conn.execute(
                "UPDATE \"importJobs\" SET status = %s, \"resultJson\" = %s WHERE id = %s",
                ("COMPLETED", json.dumps({
                    "tenants": len(imported_tenants),
                    "receipts": imported_receipts,
                    "payments": imported_payments,
                }), job_id),
            )

            # Normalize every affected tenant's arrears chain before commit.
            for tid in affected_tenant_ids:
                recompute_tenant_arrear_chain(conn, tid)

            conn.commit()
    except Exception:
        raise

    msg_parts = ["Import completed successfully."]
    msg_parts.append(f"Tenants: {len(imported_tenants)} processed.")
    msg_parts.append(f"Receipts: {imported_receipts} imported/updated.")
    msg_parts.append(f"Payments: {imported_payments} imported/updated.")

    if auto_assigned_pins and pin_handling_mode == "assign_random":
        msg_parts.append(f"Auto-assigned PINs for {len(auto_assigned_pins)} tenant(s).")
    if skipped_targets:
        msg_parts.append(f"Warning: {len(skipped_targets)} selected target(s) not found in files.")

    response_data = {
        "status": "success",
        "message": " ".join(msg_parts),
        "tenants": len(imported_tenants),
        "receipts": imported_receipts,
        "payments": imported_payments,
        "imported_tenants": imported_tenants,
        "unmatched_targets": list(skipped_targets) if skipped_targets else [],
    }
    if auto_assigned_pins:
        response_data["auto_assigned_pins"] = [
            {"target": k, "pin": v} for k, v in auto_assigned_pins.items()
        ]
    return response_data