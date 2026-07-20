# app/app/services/tenant_recovery_service.py
#
# Tenant Recovery Snapshot Service
# ---------------------------------
# Implements synchronous snapshot-before-delete, permanent deletion, conflict-aware
# restore, and automatic expiry purge for permanently deleted tenants.
#
# POLICY (from fix.md):
#   - Snapshot MUST be created and verified BEFORE any live data is deleted.
#   - Do NOT use BackgroundTasks for this operation.
#   - tenantId is the canonical ownership key — never tenant name.
#   - After expires_at, archives are permanently wiped; restoration becomes impossible.

import os
import json
import shutil
import hashlib
import uuid
import zipfile
from datetime import datetime, timedelta
from typing import Optional

from app.core.db import get_conn
from app.core.config_service import config
from app.core.paths import BACKUPS_DIR, KYC_DIR, RECEIPTS_DIR

# ── Storage ───────────────────────────────────────────────────────────────────

SNAPSHOTS_DIR = os.path.join(BACKUPS_DIR, "tenant_recovery")
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

# ── Retention helpers ─────────────────────────────────────────────────────────

def _get_retention_config():
    """Return (value, unit) from backup.tenantRecoveryRetention config."""
    retention = config.get("backup", {}).get("tenantRecoveryRetention", {})
    value = int(retention.get("value", 30))
    unit = str(retention.get("unit", "days")).lower()
    if value < 1:
        value = 1
    if unit not in ("days", "months", "years"):
        unit = "days"
    return value, unit


def calculate_expiry(value: int, unit: str, now: datetime) -> datetime:
    """Calendar-aware expiry calculation using relativedelta for months/years."""
    if value < 1:
        raise ValueError("Retention value must be at least 1")
    if unit == "days":
        return now + timedelta(days=value)
    if unit == "months":
        try:
            from dateutil.relativedelta import relativedelta
            return now + relativedelta(months=value)
        except ImportError:
            # Fallback: approximate months as 30 days each
            return now + timedelta(days=value * 30)
    if unit == "years":
        try:
            from dateutil.relativedelta import relativedelta
            return now + relativedelta(years=value)
        except ImportError:
            return now + timedelta(days=value * 365)
    raise ValueError(f"Invalid retention unit: {unit}")


# ── Checksum helpers ──────────────────────────────────────────────────────────

def _hash_file(filepath: str) -> str:
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except Exception:
        return ""
    return h.hexdigest()


# ── DB helpers ────────────────────────────────────────────────────────────────

def _init_snapshots_table():
    """Ensure the tenant_recovery_snapshots table exists (idempotent)."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tenant_recovery_snapshots (
                id TEXT PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                tenant_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                deleted_by INTEGER,
                status TEXT NOT NULL DEFAULT 'AVAILABLE',
                archive_path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                restored_at TEXT,
                purged_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tenant_recovery_expiry
                ON tenant_recovery_snapshots(expires_at, status);
        """)
        conn.commit()


# ── Snapshot creation ─────────────────────────────────────────────────────────

def create_tenant_recovery_snapshot(tenant_id: int, admin_id: Optional[int] = None) -> dict:
    """
    Synchronously create a recovery snapshot for an archived tenant BEFORE deletion.

    Steps:
    1. Load all tenant data from the DB (profile, receipts, occupants, PIN store).
    2. Copy KYC files and receipt PDFs into a staging dir.
    3. Zip the staging dir.
    4. Compute and verify SHA-256 checksum.
    5. Register in tenant_recovery_snapshots table.

    Returns the snapshot registry dict on success.
    Raises on any failure — caller must NOT delete live data if this raises.
    """
    _init_snapshots_table()

    snapshot_id = f"TRS-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.utcnow()
    ret_value, ret_unit = _get_retention_config()
    expires_at = calculate_expiry(ret_value, ret_unit, now)

    # ── Gather all data from DB ──────────────────────────────────────────────
    with get_conn() as conn:
        tenant_row = conn.execute(
            "SELECT * FROM tenants WHERE id = ?", (tenant_id,)
        ).fetchone()
        if not tenant_row:
            raise ValueError(f"Tenant {tenant_id} not found in database.")

        receipt_rows = conn.execute(
            "SELECT * FROM receipts WHERE tenantId = ?", (tenant_id,)
        ).fetchall()

        occupant_rows = conn.execute(
            "SELECT * FROM occupants WHERE tenantId = ?", (tenant_id,)
        ).fetchall()

        pin_history_rows = conn.execute(
            "SELECT * FROM tenantPin_history WHERE tenantId = ?", (tenant_id,)
        ).fetchall()

        pin_store_row = conn.execute(
            "SELECT * FROM tenantPin_admin_store WHERE tenantId = ?", (tenant_id,)
        ).fetchone()

        audit_rows = conn.execute(
            "SELECT * FROM tenant_audit_logs WHERE tenantId = ?", (tenant_id,)
        ).fetchall()

    tenant_dict = dict(tenant_row)
    receipts_list = [dict(r) for r in receipt_rows]
    occupants_list = [dict(o) for o in occupant_rows]
    pin_history_list = [dict(p) for p in pin_history_rows]
    pin_store = dict(pin_store_row) if pin_store_row else None
    audit_list = [dict(a) for a in audit_rows]

    # ── Build staging directory ───────────────────────────────────────────────
    staging_dir = os.path.join(SNAPSHOTS_DIR, f"_staging_{snapshot_id}")
    os.makedirs(staging_dir, exist_ok=True)

    try:
        # 1. Profile + all DB data as JSON
        db_export = {
            "snapshot_id": snapshot_id,
            "tenant_id": tenant_id,
            "exported_at": now.isoformat(),
            "tenant": tenant_dict,
            "receipts": receipts_list,
            "occupants": occupants_list,
            "pin_history": pin_history_list,
            "pin_store": pin_store,
            "audit_logs": audit_list,
        }
        with open(os.path.join(staging_dir, "tenant_data.json"), "w", encoding="utf-8") as f:
            json.dump(db_export, f, indent=2, default=str)

        # 2. Copy KYC files for all occupants
        kyc_staging = os.path.join(staging_dir, "kyc")
        os.makedirs(kyc_staging, exist_ok=True)
        kyc_fields = ["aadhaar_front", "aadhaar_back", "aadhaar_combined", "emp_front", "emp_back"]
        for occ in occupants_list:
            for field in kyc_fields:
                filename = occ.get(field) or ""
                if filename:
                    src = os.path.join(KYC_DIR, os.path.basename(filename))
                    if os.path.exists(src):
                        shutil.copy2(src, os.path.join(kyc_staging, os.path.basename(filename)))

        # 3. Copy receipt PDFs
        pdfs_staging = os.path.join(staging_dir, "receipts")
        os.makedirs(pdfs_staging, exist_ok=True)
        for receipt in receipts_list:
            pdf_filename = receipt.get("pdf") or ""
            if pdf_filename:
                src = os.path.join(RECEIPTS_DIR, os.path.basename(pdf_filename))
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(pdfs_staging, os.path.basename(pdf_filename)))

        # 4. Write snapshot manifest
        tenant_name = tenant_dict.get("name", f"Tenant-{tenant_id}")
        manifest = {
            "snapshot_id": snapshot_id,
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "deleted_by_admin_id": admin_id,
            "receipt_count": len(receipts_list),
            "occupant_count": len(occupants_list),
            "retention": {"value": ret_value, "unit": ret_unit},
            "format_version": 1,
        }
        with open(os.path.join(staging_dir, "snapshot_manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # 5. Create ZIP archive
        zip_name = f"{snapshot_id}.zip"
        zip_path = os.path.join(SNAPSHOTS_DIR, zip_name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(staging_dir):
                for file in files:
                    abs_file = os.path.join(root, file)
                    arcname = os.path.relpath(abs_file, staging_dir)
                    zf.write(abs_file, arcname)

        # 6. Compute SHA-256 of ZIP and verify it's readable
        sha256 = _hash_file(zip_path)
        if not sha256:
            raise RuntimeError("Failed to compute checksum of snapshot archive.")

        # Verify ZIP can be read back (basic integrity check)
        with zipfile.ZipFile(zip_path, "r") as zf:
            bad = zf.testzip()
            if bad is not None:
                raise RuntimeError(f"Snapshot ZIP is corrupted: first bad file = {bad}")

        # 7. Register in DB
        metadata_json = json.dumps(manifest, default=str)
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO tenant_recovery_snapshots
                    (id, tenant_id, tenant_name, created_at, expires_at, deleted_by,
                     status, archive_path, sha256, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, 'AVAILABLE', ?, ?, ?)
                """,
                (
                    snapshot_id,
                    tenant_id,
                    tenant_name,
                    now.isoformat(),
                    expires_at.isoformat(),
                    admin_id,
                    zip_path,
                    sha256,
                    metadata_json,
                ),
            )
            conn.commit()

        return {
            "id": snapshot_id,
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "sha256": sha256,
            "archive_path": zip_path,
            "status": "AVAILABLE",
        }

    except Exception:
        # Cleanup staging on any failure
        shutil.rmtree(staging_dir, ignore_errors=True)
        # If ZIP was partially created, remove it
        zip_path_candidate = os.path.join(SNAPSHOTS_DIR, f"{snapshot_id}.zip")
        if os.path.exists(zip_path_candidate):
            try:
                os.remove(zip_path_candidate)
            except Exception:
                pass
        raise
    finally:
        # Always cleanup staging dir
        shutil.rmtree(staging_dir, ignore_errors=True)


# ── Permanent deletion ────────────────────────────────────────────────────────

def permanently_delete_tenant_data(tenant_id: int) -> dict:
    """
    Permanently remove ALL live data for a tenant from the database and filesystem.

    Deletes:
    - tenants row
    - receipts rows (and their PDF files from disk)
    - occupants rows (and their KYC files from disk)
    - tenant_sessions rows
    - tenantPin_history rows
    - tenantPin_admin_store row
    - tenant_audit_logs rows

    This function must only be called AFTER create_tenant_recovery_snapshot() succeeds.
    """
    with get_conn() as conn:
        # Collect KYC filenames before deleting occupants
        occ_rows = conn.execute(
            "SELECT aadhaar_front, aadhaar_back, aadhaar_combined, emp_front, emp_back "
            "FROM occupants WHERE tenantId = ?",
            (tenant_id,),
        ).fetchall()

        # Collect PDF filenames before deleting receipts
        pdf_rows = conn.execute(
            "SELECT pdf FROM receipts WHERE tenantId = ?", (tenant_id,)
        ).fetchall()

        # Delete all DB rows (FK cascades handle sessions/pin history/pin store/occupants)
        conn.execute("DELETE FROM tenant_audit_logs WHERE tenantId = ?", (tenant_id,))
        conn.execute("DELETE FROM tenant_sessions WHERE tenantId = ?", (tenant_id,))
        conn.execute("DELETE FROM tenantPin_history WHERE tenantId = ?", (tenant_id,))
        conn.execute("DELETE FROM tenantPin_admin_store WHERE tenantId = ?", (tenant_id,))
        conn.execute("DELETE FROM occupants WHERE tenantId = ?", (tenant_id,))
        conn.execute("DELETE FROM receipts WHERE tenantId = ?", (tenant_id,))
        conn.execute("DELETE FROM tenants WHERE id = ?", (tenant_id,))
        conn.commit()

    # Delete KYC files from disk
    kyc_fields = ["aadhaar_front", "aadhaar_back", "aadhaar_combined", "emp_front", "emp_back"]
    deleted_kyc = 0
    for occ_row in occ_rows:
        for i, field in enumerate(kyc_fields):
            fname = occ_row[i] or ""
            if fname:
                fpath = os.path.join(KYC_DIR, os.path.basename(fname))
                if os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                        deleted_kyc += 1
                    except Exception:
                        pass

    # Delete receipt PDFs from disk
    deleted_pdfs = 0
    for pdf_row in pdf_rows:
        fname = pdf_row[0] or ""
        if fname:
            fpath = os.path.join(RECEIPTS_DIR, os.path.basename(fname))
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                    deleted_pdfs += 1
                except Exception:
                    pass

    return {
        "tenant_id": tenant_id,
        "deleted": True,
        "deleted_kyc_files": deleted_kyc,
        "deleted_pdf_files": deleted_pdfs,
    }


# ── Snapshot listing ──────────────────────────────────────────────────────────

def get_tenant_recovery_snapshots() -> list:
    """
    Return all tenant recovery snapshots, running expiry purge first.
    """
    _init_snapshots_table()
    purge_expired_tenant_recovery_snapshots()  # Always purge before listing

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, tenant_id, tenant_name, created_at, expires_at,
                   deleted_by, status, archive_path, sha256, metadata_json,
                   restored_at, purged_at
            FROM tenant_recovery_snapshots
            ORDER BY created_at DESC
            """
        ).fetchall()

    snapshots = []
    now_iso = datetime.utcnow().isoformat()
    for row in rows:
        snap = dict(row)
        # Compute time-remaining for AVAILABLE snapshots
        if snap["status"] == "AVAILABLE":
            try:
                expires_dt = datetime.fromisoformat(snap["expires_at"])
                remaining = expires_dt - datetime.utcnow()
                snap["days_remaining"] = max(0, remaining.days)
                snap["expired"] = remaining.total_seconds() <= 0
            except Exception:
                snap["days_remaining"] = 0
                snap["expired"] = True
        else:
            snap["days_remaining"] = 0
            snap["expired"] = True

        # Parse metadata for display
        try:
            snap["metadata"] = json.loads(snap["metadata_json"])
        except Exception:
            snap["metadata"] = {}

        # Verify archive file exists for AVAILABLE status
        if snap["status"] == "AVAILABLE":
            snap["archive_exists"] = os.path.exists(snap.get("archive_path", ""))
        else:
            snap["archive_exists"] = False

        snapshots.append(snap)

    return snapshots


# ── Restore preview (conflict detection) ─────────────────────────────────────

def get_snapshot_restore_preview(snapshot_id: str) -> dict:
    """
    Inspect a snapshot and return a conflict report before allowing restore.

    Returns:
    {
      "canRestore": bool,
      "conflicts": { tenantId?, roomNumber?, phone?, email?, billNumbers? },
      "options": ["cancel"] or ["cancel", "restore-with-new-tenant-id"],
      "snapshot": { id, tenant_id, tenant_name, ... }
    }
    """
    _init_snapshots_table()

    with get_conn() as conn:
        snap_row = conn.execute(
            "SELECT * FROM tenant_recovery_snapshots WHERE id = ?", (snapshot_id,)
        ).fetchone()

    if not snap_row:
        raise ValueError(f"Snapshot {snapshot_id} not found.")

    snap = dict(snap_row)

    if snap["status"] != "AVAILABLE":
        return {
            "canRestore": False,
            "reason": f"Snapshot is {snap['status']} and cannot be restored.",
            "conflicts": {},
            "options": ["cancel"],
            "snapshot": snap,
        }

    # Check archive file exists and is valid
    archive_path = snap.get("archive_path", "")
    if not os.path.exists(archive_path):
        return {
            "canRestore": False,
            "reason": "Snapshot archive file is missing.",
            "conflicts": {},
            "options": ["cancel"],
            "snapshot": snap,
        }

    # Verify checksum
    current_sha = _hash_file(archive_path)
    if current_sha != snap["sha256"]:
        return {
            "canRestore": False,
            "reason": "Snapshot archive checksum mismatch — archive may be corrupted.",
            "conflicts": {},
            "options": ["cancel"],
            "snapshot": snap,
        }

    # Extract snapshot data for conflict checking
    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            with zf.open("tenant_data.json") as f:
                tenant_data = json.load(f)
    except Exception as e:
        return {
            "canRestore": False,
            "reason": f"Failed to read snapshot data: {e}",
            "conflicts": {},
            "options": ["cancel"],
            "snapshot": snap,
        }

    tenant_profile = tenant_data.get("tenant", {})
    receipts = tenant_data.get("receipts", [])
    orig_id = snap["tenant_id"]

    conflicts = {}
    options = ["cancel"]

    with get_conn() as conn:
        # 1. Check if original tenant ID already exists in live DB
        existing_tenant = conn.execute(
            "SELECT id, name, status FROM tenants WHERE id = ?", (orig_id,)
        ).fetchone()
        if existing_tenant:
            conflicts["tenantId"] = orig_id
            conflicts["existingTenantName"] = existing_tenant["name"]
            # Can offer restore-with-new-id only if no bill number conflicts
            # (we check that below)

        # 2. Check room number occupancy
        room = tenant_profile.get("roomnumber") or ""
        if room:
            occupied = conn.execute(
                "SELECT id, name FROM tenants WHERE LOWER(roomnumber) = LOWER(?) AND status NOT IN ('Archived', 'Inactive')",
                (room,),
            ).fetchone()
            if occupied:
                conflicts["roomNumber"] = room
                conflicts["roomOccupiedBy"] = occupied["name"]

        # 3. Check phone/email belonging to another active tenant
        phone = tenant_profile.get("phone") or ""
        email = tenant_profile.get("email") or ""
        if phone:
            phone_conflict = conn.execute(
                "SELECT id, name FROM tenants WHERE phone = ? AND id != ?", (phone, orig_id)
            ).fetchone()
            if phone_conflict:
                conflicts["phone"] = phone
                conflicts["phoneConflictTenant"] = phone_conflict["name"]

        if email:
            email_conflict = conn.execute(
                "SELECT id, name FROM tenants WHERE email = ? AND id != ?", (email, orig_id)
            ).fetchone()
            if email_conflict:
                conflicts["email"] = email
                conflicts["emailConflictTenant"] = email_conflict["name"]

        # 4. Check receipt bill number collisions (HARD BLOCK)
        bill_conflicts = []
        for r in receipts:
            bill_no = r.get("billNo") or ""
            if bill_no:
                exists = conn.execute(
                    "SELECT 1 FROM receipts WHERE billNo = ?", (bill_no,)
                ).fetchone()
                if exists:
                    bill_conflicts.append(bill_no)
        if bill_conflicts:
            conflicts["billNumbers"] = bill_conflicts

    # Determine if restore is possible and what options exist
    has_bill_conflict = bool(conflicts.get("billNumbers"))
    has_id_conflict = "tenantId" in conflicts

    if has_bill_conflict:
        # Bill number conflicts are HARD BLOCKs — cannot restore
        can_restore = False
        reason = "Bill number conflicts exist. Cannot restore without overwriting live receipts."
    elif has_id_conflict and not has_bill_conflict:
        # Can still restore with a new tenant ID
        can_restore = True
        options.append("restore-with-new-tenant-id")
        reason = "Tenant ID conflict exists but no bill conflicts. Can restore with a new tenant ID."
    elif conflicts:
        # Other conflicts (room, phone, email) — warn but allow
        can_restore = True
        reason = "Some conflicts detected. Review before restoring."
    else:
        can_restore = True
        reason = "No conflicts detected. Safe to restore."
        options.append("restore-original")

    if can_restore and "restore-original" not in options and "restore-with-new-tenant-id" not in options:
        options.append("restore-original")

    return {
        "canRestore": can_restore,
        "reason": reason,
        "conflicts": conflicts,
        "options": options,
        "snapshot": snap,
        "tenantProfile": tenant_profile,
        "receiptCount": len(receipts),
    }


# ── Restore execution ─────────────────────────────────────────────────────────

def restore_tenant_from_snapshot(snapshot_id: str, force_new_id: bool = False) -> dict:
    """
    Restore a tenant from a recovery snapshot.

    - If force_new_id=False: use original tenant ID (fails if ID already exists).
    - If force_new_id=True: assign a new auto-incremented ID (rewrites receipts.tenantId,
      occupants.tenantId, sessions, pin tables, audit logs accordingly).

    After successful restore, marks snapshot status as RESTORED.
    """
    _init_snapshots_table()

    with get_conn() as conn:
        snap_row = conn.execute(
            "SELECT * FROM tenant_recovery_snapshots WHERE id = ?", (snapshot_id,)
        ).fetchone()

    if not snap_row:
        raise ValueError(f"Snapshot {snapshot_id} not found.")

    snap = dict(snap_row)

    if snap["status"] != "AVAILABLE":
        raise ValueError(f"Snapshot is {snap['status']} and cannot be restored.")

    # Check expiry
    try:
        expires_dt = datetime.fromisoformat(snap["expires_at"])
        if datetime.utcnow() > expires_dt:
            raise ValueError("Snapshot has expired and can no longer be restored.")
    except ValueError:
        raise

    archive_path = snap["archive_path"]
    if not os.path.exists(archive_path):
        raise ValueError("Snapshot archive file is missing.")

    # Verify checksum
    current_sha = _hash_file(archive_path)
    if current_sha != snap["sha256"]:
        raise ValueError("Snapshot archive checksum mismatch — archive may be corrupted.")

    # Extract data
    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            with zf.open("tenant_data.json") as f:
                tenant_data = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to read snapshot data: {e}")

    tenant_profile = tenant_data.get("tenant", {})
    receipts = tenant_data.get("receipts", [])
    occupants = tenant_data.get("occupants", [])
    pin_history = tenant_data.get("pin_history", [])
    pin_store = tenant_data.get("pin_store")
    audit_logs = tenant_data.get("audit_logs", [])

    orig_id = snap["tenant_id"]
    now_iso = datetime.utcnow().isoformat()

    with get_conn() as conn:
        # Check if original ID is free or if we need a new one
        id_taken = conn.execute(
            "SELECT 1 FROM tenants WHERE id = ?", (orig_id,)
        ).fetchone()

        if id_taken and not force_new_id:
            raise ValueError(
                f"Tenant ID {orig_id} already exists in the live database. "
                "Use force_new_id=True to restore with a new tenant ID."
            )

        # Determine actual ID to use
        if id_taken and force_new_id:
            # Use next available auto-increment
            max_id = conn.execute("SELECT MAX(id) FROM tenants").fetchone()[0] or 0
            new_tenant_id = max_id + 1
        else:
            new_tenant_id = orig_id

        # Restore tenant row
        t = tenant_profile
        conn.execute(
            """
            INSERT INTO tenants (
                id, name, company, phone, email, address, roomnumber, occupation,
                notes, status, rent, water, electricityrate, previousmeter,
                additionalpersoncharge, securitydeposit, defaulttankwatercharge,
                meterid, viewToken, tenantpin, failed_attempts, locked_until
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_tenant_id,
                t.get("name", ""),
                t.get("company", ""),
                t.get("phone", ""),
                t.get("email", ""),
                t.get("address", ""),
                t.get("roomnumber", ""),
                t.get("occupation", ""),
                t.get("notes", ""),
                "Active",   # Always restore as Active
                float(t.get("rent", 0)),
                float(t.get("water", 0)),
                float(t.get("electricityrate", 0)),
                float(t.get("previousmeter", 0)),
                float(t.get("additionalpersoncharge", 0)),
                float(t.get("securitydeposit", 0)),
                float(t.get("defaulttankwatercharge", 0)),
                t.get("meterid", ""),
                t.get("viewToken", ""),
                t.get("tenantpin", ""),
                0,
                None,
            ),
        )

        # Restore receipts — check each bill number for conflicts before inserting
        restored_receipts = 0
        skipped_receipts = 0
        for r in receipts:
            bill_no = r.get("billNo", "")
            if not bill_no:
                continue
            existing_bill = conn.execute(
                "SELECT 1 FROM receipts WHERE billNo = ?", (bill_no,)
            ).fetchone()
            if existing_bill:
                skipped_receipts += 1
                continue  # Never overwrite live receipts

            conn.execute(
                """
                INSERT INTO receipts (
                    billNo, date, month, tenantId, tenant, previous, current, units,
                    rent, additional, water, tankWater, electricity, total, pdf,
                    tenantphone, tenantcompany, tenantaddress, rate, status,
                    archiveddate, archivedby, deleteddate, additionalpersons,
                    additionalpersonrate, receiptversion, generatedby,
                    paymentstatus, maintenancecharge, maintenancedesc,
                    previousarrears, amountreceived
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    bill_no,
                    r.get("date", ""),
                    r.get("month", ""),
                    new_tenant_id,  # Rewrite to new ID if changed
                    r.get("tenant", ""),
                    float(r.get("previous", 0)),
                    float(r.get("current", 0)),
                    float(r.get("units", 0)),
                    float(r.get("rent", 0)),
                    float(r.get("additional", 0)),
                    float(r.get("water", 0)),
                    float(r.get("tankWater", 0)),
                    float(r.get("electricity", 0)),
                    float(r.get("total", 0)),
                    r.get("pdf", ""),
                    r.get("tenantphone", ""),
                    r.get("tenantcompany", ""),
                    r.get("tenantaddress", ""),
                    float(r.get("rate", 0)),
                    "ACTIVE",  # Restore as ACTIVE
                    "",        # Clear archiveddate
                    "",        # Clear archivedby
                    "",        # Clear deleteddate
                    int(r.get("additionalpersons", 0)),
                    float(r.get("additionalpersonrate", 0)),
                    int(r.get("receiptversion", 8)),
                    r.get("generatedby", "Admin"),
                    r.get("paymentstatus", "PENDING"),
                    float(r.get("maintenancecharge", 0)),
                    r.get("maintenancedesc", ""),
                    float(r.get("previousarrears", 0)),
                    float(r.get("amountreceived", 0)),
                ),
            )
            restored_receipts += 1

        # Restore occupants
        for occ in occupants:
            occ_uuid = occ.get("occupantUuid", "")
            if not occ_uuid:
                continue
            existing_occ = conn.execute(
                "SELECT 1 FROM occupants WHERE occupantUuid = ?", (occ_uuid,)
            ).fetchone()
            if not existing_occ:
                conn.execute(
                    """
                    INSERT INTO occupants (
                        tenantId, occupantUuid, name, mobile, status,
                        aadhaar_front, aadhaar_back, aadhaar_combined,
                        emp_front, emp_back, uploaddate, uploadmonth
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_tenant_id,
                        occ_uuid,
                        occ.get("name", ""),
                        occ.get("mobile", ""),
                        "Active",
                        occ.get("aadhaar_front", ""),
                        occ.get("aadhaar_back", ""),
                        occ.get("aadhaar_combined", ""),
                        occ.get("emp_front", ""),
                        occ.get("emp_back", ""),
                        occ.get("uploaddate", ""),
                        occ.get("uploadmonth", ""),
                    ),
                )

        # Restore PIN history (only if tenant IDs match — skip if force_new_id to avoid pollution)
        if not force_new_id:
            for ph in pin_history:
                conn.execute(
                    "INSERT OR IGNORE INTO tenantPin_history (tenantId, pin_hash, changed_at) VALUES (?, ?, ?)",
                    (new_tenant_id, ph.get("pin_hash", ""), ph.get("changed_at", now_iso)),
                )
            if pin_store:
                conn.execute(
                    "INSERT OR REPLACE INTO tenantPin_admin_store (tenantId, encrypted_pin, updated_at) VALUES (?, ?, ?)",
                    (new_tenant_id, pin_store.get("encrypted_pin", ""), pin_store.get("updated_at", now_iso)),
                )

        # Mark snapshot as RESTORED
        conn.execute(
            "UPDATE tenant_recovery_snapshots SET status = 'RESTORED', restored_at = ? WHERE id = ?",
            (now_iso, snapshot_id),
        )
        conn.commit()

    # Restore KYC files and PDFs from ZIP back to filesystem
    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            kyc_names = [n for n in zf.namelist() if n.startswith("kyc/")]
            for name in kyc_names:
                fname = os.path.basename(name)
                if fname:
                    dest = os.path.join(KYC_DIR, fname)
                    if not os.path.exists(dest):
                        with zf.open(name) as src_f, open(dest, "wb") as dst_f:
                            shutil.copyfileobj(src_f, dst_f)

            pdf_names = [n for n in zf.namelist() if n.startswith("receipts/")]
            for name in pdf_names:
                fname = os.path.basename(name)
                if fname:
                    dest = os.path.join(RECEIPTS_DIR, fname)
                    if not os.path.exists(dest):
                        with zf.open(name) as src_f, open(dest, "wb") as dst_f:
                            shutil.copyfileobj(src_f, dst_f)
    except Exception as e:
        print(f"[TenantRecovery] Warning: Failed to restore some files from snapshot: {e}")

    return {
        "status": "success",
        "original_tenant_id": orig_id,
        "restored_tenant_id": new_tenant_id,
        "id_changed": new_tenant_id != orig_id,
        "receipts_restored": restored_receipts,
        "receipts_skipped": skipped_receipts,
    }


# ── Expiry purge ──────────────────────────────────────────────────────────────

def purge_expired_tenant_recovery_snapshots() -> int:
    """
    Find all AVAILABLE snapshots that have passed their expires_at deadline,
    securely remove their archive files, and mark them as PURGED.

    Returns the number of snapshots purged.
    """
    _init_snapshots_table()

    now_iso = datetime.utcnow().isoformat()
    with get_conn() as conn:
        expired_rows = conn.execute(
            """
            SELECT id, archive_path FROM tenant_recovery_snapshots
            WHERE status = 'AVAILABLE' AND expires_at <= ?
            """,
            (now_iso,),
        ).fetchall()

    purged_count = 0
    for row in expired_rows:
        snap_id = row["id"]
        archive_path = row["archive_path"] or ""

        # Securely remove archive file
        if archive_path and os.path.exists(archive_path):
            try:
                os.remove(archive_path)
            except Exception as e:
                print(f"[TenantRecovery] Failed to delete snapshot archive {archive_path}: {e}")

        # Mark as PURGED in DB
        with get_conn() as conn:
            conn.execute(
                "UPDATE tenant_recovery_snapshots SET status = 'PURGED', purged_at = ? WHERE id = ?",
                (now_iso, snap_id),
            )
            conn.commit()

        purged_count += 1
        print(f"[TenantRecovery] Purged expired snapshot: {snap_id}")

    return purged_count
