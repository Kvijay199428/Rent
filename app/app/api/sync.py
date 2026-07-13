# File: app/app/api/sync.py
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks

from app.core.routes_manifest import Names, Routes

from fastapi.responses import StreamingResponse, FileResponse
from app.core.dependencies import config
from app.models.tenant import Tenant
import os
import io
import json
import datetime
import zipfile
import csv
from typing import List
import uvicorn
import socket

from app.services.tenant_service import load_tenants, add_tenant, update_tenant
from app.services.billing_service import get_all_receipts
from app.services.backup_service import create_full_backup
from app.core.paths import BACKUPS_DIR

from app.authentication.common.utils import validate_tenantPin, hash_pin
from app.authentication.common.pin_vault import encrypt_admin_view_pin
from app.authentication.tenant.sessions import revoke_all_tenant_sessions
from app.core.db import get_conn

import openpyxl
from openpyxl.styles import Font, PatternFill
router = APIRouter()


# ==========================================
# EXCEL IMPORT & EXPORT ENGINE (RELATIONAL)
# ==========================================

PROFILE_HEADERS = [
    "tenantId", "tenantName", "Phone", "Email", "Company", "Address", "Room",
    "meterId", "PIN", "Rent", "Water", "electricityRate", "additionalPersonRate",
    "tankWater", "Status"
]

RECEIPT_HEADERS = [
    "BillNo", "tenantId", "Month", "Date", "Previous", "Current", "Units", "Rent",
    "Water", "Electricity", "Additional", "tankWater", "Maintenance", "Arrears",
    "amountReceived", "Total", "paymentStatus", "receiptStatus"
]

def _build_excel_workbook(tenants_list, receipts_list):
    """Shared helper: builds and returns an openpyxl workbook in memory."""
    wb = openpyxl.Workbook()
    ws_profile = wb.active
    ws_profile.title = "Tenant_Profile"
    ws_profile.append(PROFILE_HEADERS)

    ws_receipts = wb.create_sheet("Rent_Receipts")
    ws_receipts.append(RECEIPT_HEADERS)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    for ws in [ws_profile, ws_receipts]:
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill

    tenantId_map = {}
    for t in tenants_list:
        t_id_str = f"T{str(t.id).zfill(3)}"
        tenantId_map[t.name] = t_id_str
        ws_profile.append([
            t_id_str, t.name, str(t.phone), getattr(t, 'email', ''), getattr(t, 'company', ''),
            getattr(t, 'address', ''), getattr(t, 'roomNumber', ''), getattr(t, 'meterId', ''),
            getattr(t, 'tenantPin', ''), float(t.rent), float(t.water), float(t.electricityRate),
            float(t.additionalPersonCharge), float(getattr(t, 'defaulttankWaterCharge', 0.0)), t.status
        ])

    for r in receipts_list:
        t_name = r.get("Tenant", "")
        t_id_str = tenantId_map.get(t_name, "UNKNOWN")
        ws_receipts.append([
            r.get("Bill", ""), t_id_str, r.get("Month", ""), r.get("Date", ""),
            float(r.get("Previous", 0)), float(r.get("Current", 0)), float(r.get("Units", 0)),
            float(r.get("Rent", 0)), float(r.get("Water", 0)), float(r.get("Electricity", 0)),
            float(r.get("Additional", 0)), float(r.get("tankWater", 0)),
            float(r.get("MaintenanceCharge", 0)), float(r.get("previousArrears", 0)),
            float(r.get("amountReceived", 0)), float(r.get("Total", 0)),
            r.get("paymentStatus", "PENDING"), r.get("Status", "ACTIVE")
        ])

    return wb


@router.get(Routes.ADMINAPISYNCEXPORTCSV, name=Names.EXPORTRECEIPTSCSV)
async def export_receipts_csv(tenants_list: str = "all"):
    tenants = load_tenants()
    receipts = get_all_receipts()

    if tenants_list != "all":
        selected_ids = [int(x) for x in tenants_list.split(",") if x.isdigit()]
        selected_names = [t.name for t in tenants if t.id in selected_ids]
        receipts = [r for r in receipts if r.get("Tenant") in selected_names]

    stream = io.StringIO()
    if receipts:
        writer = csv.DictWriter(stream, fieldnames=receipts[0].keys())
        writer.writeheader()
        writer.writerows(receipts)
    else:
        stream.write("No data found for selected tenants.")

    date_str = datetime.datetime.now().strftime('%Y%m%d')
    filename = f"receipts_export_{date_str}.csv"

    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

@router.get(Routes.ADMINAPISYNCEXPORTZIP, name=Names.EXPORTFULLZIP)
async def export_full_zip(tenants_list: str = "all"):
    tenants = load_tenants()
    receipts = get_all_receipts()

    if tenants_list != "all":
        selected_ids = [int(x) for x in tenants_list.split(",") if x.isdigit()]
        selected_names = [t.name for t in tenants if t.id in selected_ids]
        receipts = [r for r in receipts if r.get("Tenant") in selected_names]

    date_str = datetime.datetime.now().strftime('%Y%m%d')
    zip_filename = f"tenant_data_{date_str}.zip"
    zip_path = os.path.join(BACKUPS_DIR, zip_filename)
    os.makedirs(BACKUPS_DIR, exist_ok=True)

    from app.services.pdf_service import generate_professional_pdf
    from app.core.config_service import config
    landlord_conf = config.get("landlord", {})

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        stream = io.StringIO()
        if receipts:
            writer = csv.DictWriter(stream, fieldnames=receipts[0].keys())
            writer.writeheader()
            writer.writerows(receipts)
        zipf.writestr("receipts_data.csv", stream.getvalue())

        for r in receipts:
            tenantName = r.get("Tenant", "Unknown").replace(" ", "_")
            try:
                formatted_date = datetime.datetime.strptime(
                                r.get("Date", ""), "%d %B %Y"
                            ).strftime("%Y%m%d")
            except Exception:
                formatted_date = r.get("Date", "").replace(" ", "")

            custom_filename = f"{tenantName}_{formatted_date}_{r['Bill']}.pdf"
            status = r.get("Status", "ACTIVE")
            folder = "archive" if status == "ARCHIVED" else "active"

            try:
                pdf_stream = generate_professional_pdf(r, landlord_conf)
                zipf.writestr(f"PDFs/{folder}/{custom_filename}", pdf_stream.getvalue())
            except Exception as e:
                print(f"Failed to generate PDF for {r['Bill']}: {e}")

    response = FileResponse(zip_path, media_type="application/zip", filename=zip_filename)
    response.headers["Content-Disposition"] = f'attachment; filename="{zip_filename}"'
    return response

@router.get(Routes.ADMINAPISYNCTEMPLATE, name=Names.DOWNLOADEXCELTEMPLATE)
async def download_excel_template():
    wb = openpyxl.Workbook()
    ws_profile = wb.active
    ws_profile.title = "Tenant_Profile"
    ws_profile.append(PROFILE_HEADERS)
    ws_receipts = wb.create_sheet("Rent_Receipts")
    ws_receipts.append(RECEIPT_HEADERS)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    for ws in [ws_profile, ws_receipts]:
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill

    # Sample data rows
    ws_profile.append(["T001", "John Doe", "9876543210", "john@gmail.com", "ABC Pvt Ltd", "Delhi", "A101", "MTR001", "", 15000, 500, 8.5, 1000, 300, "Active"])
    ws_profile.append(["T002", "Alice Smith", "9988776655", "alice@gmail.com", "XYZ Ltd", "Noida", "B202", "MTR002", "", 18000, 600, 9.0, 1200, 400, "Active"])
    ws_receipts.append(["T1-001", "T001", "January 2026", "01 Jan 2026", 120, 150, 30, 15000, 500, 255, 1000, 300, 0, 0, 17055, 17055, "PAID", "ACTIVE"])
    ws_receipts.append(["T2-001", "T002", "January 2026", "01 Jan 2026", 80, 110, 30, 18000, 600, 270, 0, 400, 0, 0, 19270, 19270, "PAID", "ACTIVE"])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    response = StreamingResponse(iter([stream.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Content-Disposition"] = 'attachment; filename="Rent_Data_Template.xlsx"'
    return response

# @router.get(Routes.ADMINAPISYNCEXPORTEXCEL, name=Names.EXPORTEXCELDATA)
# async def export_excel_data(format: str):
#     tenants = load_tenants()
#     receipts = get_all_receipts()

#     # Build workbook entirely in RAM
#     wb = _build_excel_workbook(tenants, receipts)
#     excel_stream = io.BytesIO()
#     wb.save(excel_stream)
#     excel_stream.seek(0)

#     date_str = datetime.datetime.now().strftime('%Y%m%d')

#     if format == "xlsx":
#         filename = f"Rent_Data_Export_{date_str}.xlsx"
#         response = StreamingResponse(
#             iter([excel_stream.getvalue()]),
#             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#         )
#         response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
#         return response

#     elif format == "zip":
#         zip_stream = io.BytesIO()
#         with zipfile.ZipFile(zip_stream, 'w', zipfile.ZIP_DEFLATED) as zipf:
#             zipf.writestr(f"Rent_Data_Export_{date_str}.xlsx", excel_stream.getvalue())
#         zip_stream.seek(0)
#         zip_filename = f"Rent_Data_Archive_{date_str}.zip"
#         response = StreamingResponse(
#             iter([zip_stream.getvalue()]),
#             media_type="application/zip"
#         )
#         response.headers["Content-Disposition"] = f'attachment; filename="{zip_filename}"'
#         return response

#     raise HTTPException(status_code=400, detail="Unsupported format. Use 'xlsx' or 'zip'.")
@router.get(Routes.ADMINAPISYNCEXPORTEXCEL, name=Names.EXPORTEXCELDATA)
async def export_excel_data(format: str):
    tenants = load_tenants()
    receipts = get_all_receipts()

    # Build workbook entirely in RAM
    wb = _build_excel_workbook(tenants, receipts)
    excel_stream = io.BytesIO()
    wb.save(excel_stream)
    excel_stream.seek(0)

    date_str = datetime.datetime.now().strftime('%Y%m%d')

    if format == "xlsx":
        filename = f"Rent_Data_Export_{date_str}.xlsx"
        response = StreamingResponse(
            iter([excel_stream.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    elif format == "zip":
        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr(f"Rent_Data_Export_{date_str}.xlsx", excel_stream.getvalue())
        zip_stream.seek(0)
        zip_filename = f"Rent_Data_Archive_{date_str}.zip"
        response = StreamingResponse(
            iter([zip_stream.getvalue()]),
            media_type="application/zip"
        )
        response.headers["Content-Disposition"] = f'attachment; filename="{zip_filename}"'
        return response

    elif format == "csv":
        # Convert receipts to CSV
        stream = io.StringIO()
        if receipts:
            writer = csv.DictWriter(stream, fieldnames=receipts[0].keys())
            writer.writeheader()
            writer.writerows(receipts)
        else:
            stream.write("No data found.")
        
        csv_filename = f"receipts_export_{date_str}.csv"
        response = StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv"
        )
        response.headers["Content-Disposition"] = f'attachment; filename="{csv_filename}"'
        return response

    raise HTTPException(status_code=400, detail="Unsupported format. Use 'xlsx', 'zip', or 'csv'.")

def parse_excel_bytes(file_bytes, filename):
    wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), data_only=True)
    if "Tenant_Profile" not in wb.sheetnames or "Rent_Receipts" not in wb.sheetnames:
        raise ValueError(f"File '{filename}' is missing required sheets 'Tenant_Profile' and/or 'Rent_Receipts'.")

    ws_profile = wb["Tenant_Profile"]
    ws_receipts = wb["Rent_Receipts"]

    p_headers = [str(cell.value).strip() if cell.value else f"Col{i}" for i, cell in enumerate(ws_profile[1])]
    r_headers = [str(cell.value).strip() if cell.value else f"Col{i}" for i, cell in enumerate(ws_receipts[1])]

    tenants_dict = {}
    for row in ws_profile.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        row_dict = {p_headers[i]: (str(val).strip() if val is not None else "") for i, val in enumerate(row)}
        t_id = row_dict.get("tenantId", "")
        if t_id:
            tenants_dict[t_id] = {"profile": row_dict, "receipts": []}

    for row in ws_receipts.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue
        row_dict = {r_headers[i]: (str(val).strip() if val is not None else "") for i, val in enumerate(row)}
        t_id = row_dict.get("tenantId", "")
        if t_id in tenants_dict:
            tenants_dict[t_id]["receipts"].append(row_dict)

    return tenants_dict

@router.post(Routes.ADMINAPISYNCIMPORTPREVIEW, name=Names.IMPORTPREVIEWDATA)
async def import_preview_data(files: List[UploadFile] = File(...)):
    preview_data = {}
    try:
        for file in files:
            content = await file.read()
            if file.filename.endswith('.zip'):
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    for zip_info in z.infolist():
                        if zip_info.filename.endswith('.xlsx'):
                            with z.open(zip_info) as f:
                                preview_data[zip_info.filename] = parse_excel_bytes(f.read(), zip_info.filename)
            elif file.filename.endswith('.xlsx'):
                preview_data[file.filename] = parse_excel_bytes(content, file.filename)
            else:
                raise HTTPException(status_code=400, detail="Only .xlsx or .zip files are supported.")
        return {"status": "success", "files": preview_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _parse_excel_date(val: str) -> str:
    """Parse Excel date strings/serials and format as 'dd MMMM yyyy'."""
    if not val or not str(val).strip():
        return ""
    val_str = str(val).strip()

    # Try ISO format: 2026-06-01 00:00:00 or 2026-06-01T00:00:00
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(val_str, fmt)
            return dt.strftime("%d %B %Y")  # e.g., "01 June 2026"
        except ValueError:
            continue

    # Try Excel serial number
    try:
        serial = float(val_str)
        # Excel epoch is 1899-12-30 (with the infamous 1900 leap year bug)
        excel_epoch = datetime.datetime(1899, 12, 30)
        dt = excel_epoch + datetime.timedelta(days=serial)
        return dt.strftime("%d %B %Y")
    except (ValueError, OverflowError):
        pass

    # Return original if we can't parse
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

    # Try Excel serial
    try:
        serial = float(val_str)
        excel_epoch = datetime.datetime(1899, 12, 30)
        dt = excel_epoch + datetime.timedelta(days=serial)
        return dt.strftime("%B %Y")
    except (ValueError, OverflowError):
        pass

    return val_str

@router.post(Routes.ADMINAPISYNCIMPORTEXECUTE, name=Names.IMPORTEXECUTEDATA)
async def import_execute_data(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    selectedtargets: Optional[str] = Form(None),
    selectedTargets: Optional[str] = Form(None),
):
    # Accept either casing
    targets = selectedtargets or selectedTargets or ""
    if not targets:
        raise HTTPException(status_code=400, detail="selectedtargets is required")
    
    try:
        selected_list = json.loads(targets)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in selectedtargets")

    if not isinstance(selected_list, list):
        raise HTTPException(status_code=400, detail="selectedtargets must be a JSON array")

    if not selected_list:
        raise HTTPException(status_code=400, detail="No tenants selected for import.")

    sys_tenants = load_tenants()
    sys_receipts = get_all_receipts()

    # Schedule backup BEFORE processing (non-blocking)
    background_tasks.add_task(create_full_backup, tag="pre_import_excel")

    # Track results for reporting
    imported_tenants = []
    imported_receipts = 0
    skipped_targets = set(selected_list)  # Will remove matched ones

    def execute_import_for_file(file_bytes, filename):
        nonlocal imported_receipts
        parsed_data = parse_excel_bytes(file_bytes, filename)

        for t_id, t_data in parsed_data.items():
            target_key = f"{filename}::{t_id}"
            if target_key not in selected_list:
                continue

            skipped_targets.discard(target_key)  # Mark as processed

            p = t_data["profile"]
            t_name = p.get("tenantName", "").strip()
            if not t_name:
                continue

            t = next((x for x in sys_tenants if x.name.lower() == t_name.lower()), None)
            is_new = False
            if not t:
                t = Tenant(name=t_name, phone=p.get("Phone", ""), rent=0.0, water=0.0, electricityRate=0.0)
                is_new = True

            t.phone = p.get("Phone", t.phone)
            t.email = p.get("Email", getattr(t, 'email', ''))
            t.company = p.get("Company", getattr(t, 'company', ''))
            t.address = p.get("Address", getattr(t, 'address', ''))
            t.roomNumber = p.get("Room", getattr(t, 'roomNumber', ''))
            t.meterId = p.get("meterId", getattr(t, "meterId", ""))

            if not getattr(t, "viewToken", ""):
                import uuid
                t.viewToken = str(uuid.uuid4())

            plain_pin = str(p.get("PIN") or "").strip()

            pin_changed = False
            hashed_pin = None
            encrypted_pin = None

            if plain_pin:
                validate_tenantPin(plain_pin)
                hashed_pin = hash_pin(plain_pin)
                encrypted_pin = encrypt_admin_view_pin(plain_pin)
                t.tenantPin = hashed_pin
                pin_changed = True

            t.rent = float(p.get("Rent", t.rent) or 0.0)
            t.water = float(p.get("Water", t.water) or 0.0)
            t.electricityRate = float(p.get("electricityRate", t.electricityRate) or 0.0)
            t.additionalPersonCharge = float(p.get("additionalPersonRate", getattr(t, 'additionalPersonCharge', 0.0)) or 0.0)
            t.defaulttankWaterCharge = float(p.get("tankWater", getattr(t, 'defaulttankWaterCharge', 0.0)) or 0.0)
            t.status = p.get("Status", getattr(t, 'status', 'Active'))

            if is_new:
                tenantId = add_tenant(t)
                t.id = tenantId
                sys_tenants.append(t)

                if pin_changed:
                    now = datetime.datetime.utcnow().isoformat()
                    with get_conn() as conn:
                        conn.execute(
                            """
                            INSERT INTO tenantPin_history
                            (tenantId, pin_hash, changed_at)
                            VALUES (?, ?, ?)
                            """,
                            (tenantId, hashed_pin, now)
                        )
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO tenantPin_admin_store
                            (tenantId, encrypted_pin, updated_at)
                            VALUES (?, ?, ?)
                            """,
                            (tenantId, encrypted_pin, now)
                        )
                        conn.commit()
            else:
                update_tenant(t)

                if pin_changed:
                    now = datetime.datetime.utcnow().isoformat()
                    with get_conn() as conn:
                        conn.execute(
                            """
                            INSERT INTO tenantPin_history
                            (tenantId, pin_hash, changed_at)
                            VALUES (?, ?, ?)
                            """,
                            (t.id, hashed_pin, now)
                        )
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO tenantPin_admin_store
                            (tenantId, encrypted_pin, updated_at)
                            VALUES (?, ?, ?)
                            """,
                            (t.id, encrypted_pin, now)
                        )
                        conn.commit()
                    revoke_all_tenant_sessions(t.id)

            imported_tenants.append(t_name)

            for r in t_data["receipts"]:
                billNo = r.get("BillNo", "").strip()
                if not billNo:
                    continue
                sys_r = next((x for x in sys_receipts if x.get("Bill") == billNo), None)

                # FIX #4, #5: Parse Excel dates to proper format
                raw_date = r.get("Date", "")
                raw_month = r.get("Month", "")

                data = {
                    "Bill": billNo,
                    "Date": _parse_excel_date(raw_date),
                    "Month": _parse_month_date(raw_month),
                    "Tenant": t_name,
                    "Previous": float(r.get("Previous", 0) or 0),
                    "Current": float(r.get("Current", 0) or 0),
                    "Units": float(r.get("Units", 0) or 0),
                    "Rent": float(r.get("Rent", 0) or 0),
                    "Additional": float(r.get("Additional", 0) or 0),
                    "Water": float(r.get("Water", 0) or 0),
                    "tankWater": float(r.get("tankWater", 0) or 0),
                    "Electricity": float(r.get("Electricity", 0) or 0),
                    "MaintenanceCharge": float(r.get("Maintenance", 0) or 0),
                    "MaintenanceDesc": r.get("MaintenanceDesc", ""),
                    "previousArrears": float(r.get("Arrears", 0) or 0),
                    # FIX #7: Ensure amountReceived is float
                    "amountReceived": float(r.get("amountReceived", 0) or 0),
                    "Total": float(r.get("Total", 0) or 0),
                    "paymentStatus": r.get("paymentStatus", "PENDING"),
                    "Status": r.get("receiptStatus", "ACTIVE"),
                    "Receipt_Version": 8,
                    "Generated_By": "Import"
                }
                if sys_r:
                    sys_r.update(data)
                else:
                    sys_receipts.append(data)
                    imported_receipts += 1

    # ── Process uploaded files ──
    temp_files_to_cleanup = []

    try:
        for file in files:
            content = await file.read()

            # Collect for cleanup
            temp_files_to_cleanup.append(file)

            if file.filename.endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    for zip_info in z.infolist():
                        if zip_info.filename.endswith(".xlsx"):
                            with z.open(zip_info) as f:
                                execute_import_for_file(f.read(), zip_info.filename)

            elif file.filename.endswith(".xlsx"):
                execute_import_for_file(content, file.filename)

        from app.services.billing_service import save_all_receipts
        save_all_receipts(sys_receipts)

        # Build response message
        msg_parts = [f"Import completed successfully."]
        msg_parts.append(f"Tenants: {len(imported_tenants)} processed.")
        msg_parts.append(f"Receipts: {imported_receipts} imported/updated.")

        if skipped_targets:
            msg_parts.append(f"Warning: {len(skipped_targets)} selected target(s) not found in files.")

        return {
            "status": "success",
            "message": " ".join(msg_parts),
            "tenants": len(imported_tenants),
            "receipts": imported_receipts,
            "unmatched_targets": list(skipped_targets) if skipped_targets else []
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")

    finally:
        # FIX #2: Cleanup all collected files, not just last loop variable
        for tf in temp_files_to_cleanup:
            try:
                await tf.close()
            except Exception:
                pass

            try:
                temp_path = getattr(tf.file, "name", None)
                if isinstance(temp_path, str) and os.path.isfile(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass


if __name__ == "__main__":
    sys_conf = config.get("system", {})
    server_host = sys_conf["server"]["host"]
    server_port = sys_conf["server"]["port"]
    is_debug = sys_conf["server"]["debug"]

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()

    print(f"\n{'='*50}")
    print(f" {sys_conf['app']['title']} is starting...")
    print(f"{'='*50}")
    print(f" [Local]:   http://127.0.0.1:{server_port}")
    print(f" [Network]: http://{local_ip}:{server_port}")
    print(f" [Note]:    Do NOT click the {server_host} link below")
    print(f"{'='*50}\n")

    uvicorn.run(
        "app:app",
        host=server_host,
        port=server_port,
        reload=is_debug,
        proxy_headers=True,
        forwarded_allow_ips="*",
        access_log=True
    )