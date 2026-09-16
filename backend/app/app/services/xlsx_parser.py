"""Parse XLSX uploads/archives into normalized (headers, rows) per sheet.

Sheet order and required sheets are validated by the caller/engine; this module
only knows how to read a workbook into ``{sheet_name: (headers, rows)}`` where
cells are normalized to stripped strings (datetimes render as ISO). The
40-column flat CSV variant is read back as a single 'Sheet1' style parse by the
same code path (a flat XLSX is treated as one sheet).
"""

from __future__ import annotations

import datetime as _datetime
import io
import zipfile

import openpyxl

from . import data_schema as S


def _cell_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (_datetime.datetime, _datetime.date)):
        return value.isoformat()
    return str(value).strip()


def _sheet_rows(ws) -> tuple[list[str], list[dict]]:
    headers = [
        "" if cell.value is None else str(cell.value).strip()
        for cell in ws[1]
    ]
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if all(c is None or _cell_str(c) == "" for c in r):
            continue
        row = [_cell_str(c) for c in r]
        if len(row) < len(headers):
            row += [""] * (len(headers) - len(row))
        elif len(row) > len(headers):
            row = row[: len(headers)]
        rows.append({headers[i]: row[i] for i in range(len(headers))})
    return headers, rows


def parse_workbook(data) -> dict[str, tuple[list[str], list[dict]]]:
    raw = bytes(data)
    wb = openpyxl.load_workbook(filename=io.BytesIO(raw), data_only=True)
    out: dict[str, tuple[list[str], list[dict]]] = {}
    for name in wb.sheetnames:
        out[name] = _sheet_rows(wb[name])
    return out


def parse_xlsx_bytes(data) -> dict[str, tuple[list[str], list[dict]]]:
    return parse_workbook(data)


def extract_zip_xlsx(zip_data, member_name: str | None = None) -> dict[str, tuple[list[str], list[dict]]]:
    """Read the workbook contained inside a full-export .zip (first .xlsx)."""
    raw = bytes(zip_data)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = zf.namelist()
        if member_name and member_name in names:
            target = member_name
        else:
            target = next((n for n in names if n.lower().endswith(".xlsx")), None)
        if target is None:
            raise ValueError("Archive contains no Excel workbook")
        return parse_workbook(zf.read(target))


def is_zip(data) -> bool:
    try:
        return zipfile.is_zipfile(io.BytesIO(bytes(data)))
    except Exception:
        return False


def sheet_headers(out: dict) -> dict[str, list[str]]:
    """Map sheet name -> header list for quick version detection."""
    return {name: h for name, (h, _rows) in out.items()}