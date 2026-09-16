"""Parse flat CSV uploads (v2 flat file and legacy raw receipts CSV).

This module only turns bytes into normalized ``(headers, rows)`` where each
row is a dict keyed by the (stripped) header cell. Format detection / the 40
column contract live in ``data_schema``; semantic grouping lives in
``canonicalizer``.
"""

from __future__ import annotations

import csv
import io


def decode_csv_bytes(data) -> str:
    raw = bytes(data)
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _blank(cell) -> bool:
    return cell is None or not str(cell).strip()


def _norm_row(row, headers) -> dict:
    row = ["" if _blank(c) else str(c).strip() for c in row]
    if len(row) < len(headers):
        row += [""] * (len(headers) - len(row))
    elif len(row) > len(headers):
        row = row[: len(headers)]
    return {headers[i]: row[i] for i in range(len(headers))}


def parse_csv_bytes(data) -> tuple[list[str], list[dict]]:
    """Return ``(headers, rows)`` for a CSV byte payload."""
    text = decode_csv_bytes(data)
    reader = csv.reader(io.StringIO(text))
    table = [[c for c in r] for r in reader]
    table = [r for r in table if any(not _blank(c) for c in r)]
    if not table:
        return [], []
    headers = ["" if _blank(c) else str(c).strip() for c in table[0]]
    rows = [_norm_row(r, headers) for r in table[1:]]
    return headers, rows


def sheet_rows_to_csv(headers: list[str], rows) -> bytes:
    """Serialize a (headers, rows) pair as UTF-8 CSV bytes (for export)."""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({h: r.get(h, "") for h in headers})
    return out.getvalue().encode("utf-8-sig")