"""Normalize parsed imports (flat CSV rows or XLSX sheets) into the canonical
in-memory model consumed by the import engine.

Rules (locked design):
- tenants are deduplicated by numeric tenantId (first row wins)
- bills are deduplicated by (tenantId, BillNo) (first row wins)
- payments are keyed by paymentId (=> external_id); each id maps to at most one
  entry; blank ids are auto-generated as PAY-{tenantId}-{BillNo}-{seq}
- amountReceived / paymentStatus are DERIVED (never trusted from the file) from
  the sum of the bill's payment entries
- v2 files: the Payment_Entries sheet / payment block is authoritative; no
  amountReceived backfill is performed
- v1 (2-sheet, no payment sheet) files: bills whose file amountReceived > 0 and
  that have no payment entries get exactly one LEGACY_IMPORT payment

Return shape (dict JSON-safe):
    {
        "tenants": {int: profile-dict},
        "bills": [canonical-bill, ...],
        "payments": [canonical-payment, ...],
        "warnings": [str, ...],
        "version": "v2" | "v1",
        "legacy_backfilled": int,
    }
"""

from __future__ import annotations

from . import data_schema as S


EXPECTED_PAYMENT_HEADERS = {
    "paymentid", "billno", "tenantid", "paymentdate", "paymentamount", "paymentmethod",
}


# ---------------------------------------------------------------------------
# Canonical builders
# ---------------------------------------------------------------------------


def _canonical_tenant(raw: dict) -> tuple[int, dict]:
    num_id = S.parse_tenant_id(raw.get("tenantId") or raw.get("Tenant"))
    if num_id <= 0:
        return 0, {}
    profile = {h: S.clean(raw.get(h, "")) for h in S.PROFILE_HEADERS}
    profile["tenantId"] = S.format_tenant_id(num_id)
    profile["Status"] = S.normalize_tenant_status(raw.get("Status") or "Active")
    for field in ("Rent", "Water", "electricityRate", "additionalPersonRate", "tankWater"):
        profile[field] = S.to_float(profile[field], None) if profile[field] != "" else ""
    return num_id, profile


def _canonical_bill(num_id: int, raw: dict) -> dict:
    has_total = "Total" in raw and S.clean(raw.get("Total")) != ""
    total = S.to_float(raw.get("Total"))
    bill = {
        "tenantId": num_id,
        "billNo": S.clean(raw.get("BillNo")),
        "Month": S.format_receipt_month(raw.get("Month")),
        "Date": S.format_receipt_date(raw.get("Date")),
        "Previous": S.to_float(raw.get("Previous")),
        "Current": S.to_float(raw.get("Current")),
        "Units": S.to_float(raw.get("Units")),
        "Rent": S.to_float(raw.get("Rent")),
        "Water": S.to_float(raw.get("Water")),
        "Electricity": S.to_float(raw.get("Electricity")),
        "Additional": S.to_float(raw.get("Additional")),
        "tankWater": S.to_float(raw.get("tankWater")),
        "Maintenance": S.to_float(raw.get("Maintenance")),
        "MaintenanceDesc": S.clean(raw.get("MaintenanceDesc")),
        "Arrears": S.to_float(raw.get("Arrears")),
        "amountReceived": S.to_float(raw.get("amountReceived")),
        "paymentStatus": S.clean(raw.get("paymentStatus")),
        "receiptStatus": S.clean(raw.get("receiptStatus") or "ACTIVE").upper(),
        "Total": total,
        "_has_total": has_total,
    }
    return bill


def _bill_total(bill: dict) -> float:
    if bill["_has_total"]:
        return S.to_float(bill["Total"])
    return round(
        S.to_float(bill["Rent"])
        + S.to_float(bill["Water"])
        + S.to_float(bill["Electricity"])
        + S.to_float(bill["Additional"])
        + S.to_float(bill["tankWater"])
        + S.to_float(bill["Maintenance"])
        + S.to_float(bill["Arrears"]),
        2,
    )


def _canonical_payment(row: dict, bill: dict | None, seq: int, explicit_id: bool) -> dict:
    tenant_id = bill["tenantId"] if bill else S.parse_tenant_id(row.get("tenantId"))
    bill_no = (bill or {}).get("billNo") or S.clean(row.get("billNo") or row.get("BillNo"))
    payment_id = S.clean(row.get("paymentId"))
    amount = S.to_float(row.get("paymentAmount"))
    payment = {
        "tenantId": tenant_id,
        "billNo": bill_no,
        "paymentDate": S.normalize_payment_date(row.get("paymentDate")),
        "amount": amount,
        "paymentMethod": S.normalize_payment_method(row.get("paymentMethod")),
        "reference": S.clean(row.get("paymentReference") or None),
        "notes": S.clean(row.get("paymentNotes") or None),
        "externalId": payment_id if explicit_id else None,
        "source": S.clean(row.get("paymentSource") or "IMPORT"),
    }
    if not payment["externalId"]:
        payment["externalId"] = S.make_payment_id(tenant_id, bill_no or "?", seq)
    if not payment["paymentDate"]:
        payment["paymentDate"] = payment_date_fallback(bill)
    return payment


def payment_date_fallback(bill: dict | None) -> str:
    if bill is not None:
        d = S.normalize_payment_date(bill.get("Date"))
        if d:
            return d
    from datetime import date as _date

    return _date.today().isoformat()


def _recompute(result: dict) -> None:
    for bill in result["bills"]:
        bill["Total"] = _bill_total(bill)
        payments = [
            p for p in result["payments"]
            if p["tenantId"] == bill["tenantId"] and p["billNo"] == bill["billNo"]
        ]
        bill.setdefault("_has_total", True)
        S.recompute_bill_derived(bill, payments)


# ---------------------------------------------------------------------------
# Flat CSV
# ---------------------------------------------------------------------------


def canonicalize_flat(headers: list[str], rows: list[dict]) -> dict:
    warnings: list[str] = []
    tenants: dict[int, dict] = {}
    bills: dict[tuple[int, str], dict] = {}
    payments: list[dict] = {}
    seen_payments: set[str] = set()

    version, _missing = S.detect_flat_headers(headers)
    if version == "v1":
        warnings.append("Flat file missing some of the 40 canonical columns; values are best-effort.")

    for i, row in enumerate(rows, start=2):
        num_id, profile = _canonical_tenant(row)
        if num_id > 0:
            tenants.setdefault(num_id, profile)
        bill_no = S.clean(row.get("BillNo"))
        has_bill = bill_no != "" and (S.clean(row.get("Month")) or S.clean(row.get("Date")) or num_id > 0)
        if has_bill and num_id > 0:
            bills.setdefault((num_id, bill_no), _canonical_bill(num_id, row))
        elif has_bill:
            warnings.append(f"Row {i}: bill row has no resolvable tenantId; skipped.")

        pay_amount = S.to_float(row.get("paymentAmount"))
        pay_id = S.clean(row.get("paymentId"))
        has_payment = bool(pay_id or pay_amount > 0 or S.clean(row.get("paymentDate")))
        if has_payment and num_id > 0 and bill_no:
            bill = bills.get((num_id, bill_no))
            seq = 1 + len([p for p in payments.values() if p["tenantId"] == num_id and p["billNo"] == bill_no])
            pay = _canonical_payment(row, bill, seq, explicit_id=bool(pay_id))
            key = pay["externalId"]
            if key in seen_payments:
                warnings.append(f"Row {i}: duplicate paymentId '{key}'; first occurrence kept.")
                continue
            if pay["amount"] <= 0:
                warnings.append(f"Row {i}: payment '{key}' has no positive amount; skipped.")
                continue
            seen_payments.add(key)
            payments[key] = pay
        elif has_payment:
            warnings.append(f"Row {i}: payment row without both tenantId and billNo; skipped.")

    result = {
        "tenants": tenants,
        "bills": list(bills.values()),
        "payments": list(payments.values()),
        "warnings": warnings,
        "version": version,
        "legacy_backfilled": 0,
    }
    _recompute(result)
    return result


# ---------------------------------------------------------------------------
# XLSX
# ---------------------------------------------------------------------------


def _has_payment_sheet(sheets: dict) -> bool:
    for name in (S.SHEET_PAYMENTS, "PaymentEntries"):
        if name in sheets:
            headers = {h.lower() for h in sheets[name][0]}
            if EXPECTED_PAYMENT_HEADERS.issubset(headers):
                return True
    return False


def canonicalize_xlsx(sheets: dict) -> dict:
    warnings: list[str] = []
    missing = [s for s in (S.SHEET_PROFILE, S.SHEET_RECEIPTS) if s not in sheets]
    if missing:
        raise ValueError(f"Workbook is missing required sheet(s): {', '.join(missing)}")

    tenants: dict[int, dict] = {}
    bills: dict[tuple[int, str], dict] = {}
    payments: dict[str, dict] = {}
    seen_payments: set[str] = set()
    legacy_count = 0
    v2 = _has_payment_sheet(sheets)

    for (num_id, profile) in (_canonical_tenant(r) for r in sheets[S.SHEET_PROFILE][1]):
        if num_id > 0:
            tenants.setdefault(num_id, profile)

    for row in sheets[S.SHEET_RECEIPTS][1]:
        num_id = S.parse_tenant_id(row.get("tenantId"))
        bill_no = S.clean(row.get("BillNo"))
        if num_id <= 0 or not bill_no:
            continue
        bills.setdefault((num_id, bill_no), _canonical_bill(num_id, row))

    if v2:
        headers = {h.lower(): h for h in sheets[S.SHEET_PAYMENTS][0]}
        for row in sheets[S.SHEET_PAYMENTS][1]:
            row = {headers.get(k.lower(), k): v for k, v in row.items()}
            num_id = S.parse_tenant_id(row.get("tenantId"))
            bill_no = S.clean(row.get("billNo"))
            bill = bills.get((num_id, bill_no))
            pay_amount = S.to_float(row.get("paymentAmount"))
            pay_id = S.clean(row.get("paymentId"))
            has_pay = bool(pay_id or pay_amount > 0)
            if not (has_pay and bill):
                warnings.append("Payment_Entries: row without matching tenant/bill or amount skipped.")
                continue
            seq = 1 + len([p for p in payments.values() if p["tenantId"] == num_id and p["billNo"] == bill_no])
            pay = _canonical_payment(row, bill, seq, explicit_id=bool(pay_id))
            key = pay["externalId"]
            if key in seen_payments or pay["amount"] <= 0:
                warnings.append(f"Payment_Entries: duplicate/empty payment '{key}' skipped.")
                continue
            seen_payments.add(key)
            payments[key] = pay
    else:
        # v1 (2-sheet) legacy backfill: one LEGACY_IMPORT payment per bill whose
        # file amountReceived > 0 and that has no payment entries at all.
        for (num_id, bill_no), bill in bills.items():
            amount_received = S.to_float(bill["amountReceived"])
            if amount_received <= 0:
                continue
            key = f"LEGACY-{num_id}-{bill_no}"
            payments[key] = _canonical_payment(
                {
                    "tenantId": S.format_tenant_id(num_id),
                    "billNo": bill_no,
                    "paymentDate": bill["Date"],
                    "paymentAmount": amount_received,
                    "paymentMethod": "OTHER",
                    "paymentReference": "",
                    "paymentNotes": "Legacy v1 receipt amount",
                    "paymentSource": "LEGACY_IMPORT",
                },
                bill,
                0,
                explicit_id=False,
            )
            legacy_count += 1

    result = {
        "tenants": tenants,
        "bills": list(bills.values()),
        "payments": list(payments.values()),
        "warnings": warnings,
        "version": "v2" if v2 else "v1",
        "legacy_backfilled": legacy_count,
    }
    # recompute derived fields after any backfill
    _recompute(result)
    return result