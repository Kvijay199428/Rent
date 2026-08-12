import os
import json
import shutil
import hashlib
from datetime import datetime
import platform

from app.core.config_service import config
from app.core.paths import BACKUPS_DIR as BACKUP_DIR, DB_DIR, CONFIG_DIR, RECEIPTS_DIR, UPLOADS_DIR

# Map new storage directories to their legacy names for zip structure compatibility
DIR_MAPPING = {
    DB_DIR: "database",
    CONFIG_DIR: "config",
    RECEIPTS_DIR: "receipts",
    UPLOADS_DIR: "static/uploads/signatures"
}

REGISTRY_FILE = os.path.join(BACKUP_DIR, "registry.json")
LOG_FILE = os.path.join(BACKUP_DIR, "backup.jsonl")

# Ensure subdirectories
for sub in ["automatic/daily", "automatic/weekly", "automatic/monthly", "manual", "restore_points", "emergency"]:
    os.makedirs(os.path.join(BACKUP_DIR, sub), exist_ok=True)

def _log(operation, type_, status, duration_ms, details=None):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        "type": type_,
        "status": status,
        "duration_ms": duration_ms
    }
    if details:
        log_entry["details"] = details
        
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except:
        pass

def load_registry():
    if not os.path.exists(REGISTRY_FILE):
        return {"version": 1, "backups": []}
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"version": 1, "backups": []}

def save_registry(registry):
    try:
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=4)
    except Exception as e:
        print(f"Error saving registry: {e}")

def hash_file(filepath):
    h = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
    except Exception:
        return ""
    return h.hexdigest()

def hash_directory(dirpath):
    h = hashlib.sha256()
    if not os.path.exists(dirpath):
        return h.hexdigest()
        
    for root, dirs, files in os.walk(dirpath):
        for names in sorted(files):
            filepath = os.path.join(root, names)
            try:
                with open(filepath, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        h.update(chunk)
            except Exception:
                pass
    return h.hexdigest()

def create_manifest(backupId, backup_type, timestamp_str):
    schema_conf = config.get("schema", {})
    return {
        "application": "PROPAURA",
        "version": "3.0.0",
        "schema": schema_conf.get("receipt_schema", 4),
        "created": timestamp_str,
        "platform": platform.system(),
        "backup_type": backup_type,
        "backupId": backupId
    }

def get_db_stats():
    # Count receipts, tenants, PDFs
    from app.core.db import get_conn
    
    receipt_count = 0
    archived_count = 0
    tenant_count = 0
    inactive_tenant_count = 0
    pdf_count = 0
    
    try:
        with get_conn() as conn:
            receipt_count = conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
            archived_count = conn.execute("SELECT COUNT(*) FROM receipts WHERE status = 'ARCHIVED'").fetchone()[0]
            tenant_count = conn.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]
            inactive_tenant_count = conn.execute("SELECT COUNT(*) FROM tenants WHERE status = 'Inactive'").fetchone()[0]
    except Exception as e:
        pass
            
    for root, dirs, files in os.walk(RECEIPTS_DIR):
        for f in files:
            if f.endswith(".pdf"):
                pdf_count += 1
                
    return receipt_count, archived_count, tenant_count, inactive_tenant_count, pdf_count

def create_metadata(backupId, backup_type, timestamp_str):
    schema_conf = config.get("schema", {})
    ui_conf = config.get("ui", {})
    r_count, arc_count, t_count, it_count, p_count = get_db_stats()

    # Get tenant snapshot for restore point identification
    tenant_snapshot = []
    try:
        from app.services.tenant_service import load_tenants
        all_tenants = load_tenants(include_archived=True)
        tenant_snapshot = [
            {
                "id": t.id,
                "name": t.name,
                "status": t.status,
                "phone": t.phone,
                "roomNumber": t.roomNumber
            }
            for t in all_tenants
        ]
    except Exception:
        pass

    metadata = {
        "id": backupId,
        "type": backup_type,
        "date": timestamp_str,
        "application_version": "3.0.0",
        "schema_version": schema_conf.get("receipt_schema", 4),
        "created_by": "System",
        "machine_name": platform.node(),
        "os": platform.system(),
        "receipt_count": r_count,
        "archived_receipt_count": arc_count,
        "tenant_count": t_count,
        "inactive_tenant_count": it_count,
        "pdf_count": p_count,
        "tenant_snapshot": tenant_snapshot,
        "theme": ui_conf.get("theme", "system"),
        "checksums": {
            "database": hash_directory(DB_DIR),
            "config": hash_directory(CONFIG_DIR),
            "receipts": hash_directory(RECEIPTS_DIR)
        },
        "verified": True,
        "compressed": True,
        "password_protected": False
    }
    return metadata

def _stage_landlord_export(landlord_id: int, temp_dir: str):
    """Stage a per-landlord export (NO global DB, NO other landlords, NO
    PIN/password vaults). Writes data/tenants.json, data/receipts.json,
    data/occupants.json, config/landlord_config.json, receipts/*.pdf and
    signature/*.png."""
    import shutil as _shutil

    from app.core.db import get_conn
    from app.services.landlord_config_service import get_effective_landlord_config

    data_dir = os.path.join(temp_dir, "data")
    config_dir = os.path.join(temp_dir, "config")
    receipts_zip_dir = os.path.join(temp_dir, "receipts")
    signature_dir = os.path.join(temp_dir, "signature")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(receipts_zip_dir, exist_ok=True)
    os.makedirs(signature_dir, exist_ok=True)

    with get_conn() as conn:
        tenants = [dict(r) for r in conn.execute(
            "SELECT * FROM tenants WHERE landlord_id = ?", (landlord_id,)
        ).fetchall()]
        receipts = [dict(r) for r in conn.execute(
            "SELECT * FROM receipts WHERE landlord_id = ?", (landlord_id,)
        ).fetchall()]
        occupants = [dict(r) for r in conn.execute(
            "SELECT * FROM occupants WHERE landlord_id = ?", (landlord_id,)
        ).fetchall()]

    with open(os.path.join(data_dir, "tenants.json"), "w", encoding="utf-8") as f:
        json.dump(tenants, f, indent=4, default=str)
    with open(os.path.join(data_dir, "receipts.json"), "w", encoding="utf-8") as f:
        json.dump(receipts, f, indent=4, default=str)
    with open(os.path.join(data_dir, "occupants.json"), "w", encoding="utf-8") as f:
        json.dump(occupants, f, indent=4, default=str)

    try:
        landlord_conf = get_effective_landlord_config(landlord_id)
        with open(os.path.join(config_dir, "landlord_config.json"), "w", encoding="utf-8") as f:
            json.dump(landlord_conf, f, indent=4, default=str)
    except Exception:
        pass

    pdf_names = set()
    for r in receipts:
        pdf = (r.get("pdf") or "").strip()
        if pdf:
            pdf_names.add(os.path.basename(pdf))
    for pdf in sorted(pdf_names):
        src = os.path.join(RECEIPTS_DIR, pdf)
        if os.path.exists(src):
            _shutil.copy2(src, os.path.join(receipts_zip_dir, pdf))

    signature_file = os.path.join(UPLOADS_DIR, f"{landlord_id}_signature_flattened.png")
    if os.path.exists(signature_file):
        _shutil.copy2(signature_file, os.path.join(signature_dir, "signature_flattened.png"))

    return {
        "tenant_count": len(tenants),
        "receipt_count": len(receipts),
        "occupant_count": len(occupants),
        "pdf_count": len(pdf_names),
    }


def create_backup(type_="Manual", subtype="manual", tag="", landlord_id=None):
    """
    type_: 'Manual', 'Automatic', 'Restore Point', 'Emergency'
    subtype: 'manual', 'daily', 'weekly', 'monthly', 'before_edit', etc.
    landlord_id: when set, produces a per-landlord export (no global DB, no
    PIN/password vaults, no other landlords). When None, produces the full
    system backup (platform-admin scope).
    """
    start_time = datetime.now()
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    timestamp_iso = start_time.isoformat()
    backupId = f"BKP-{start_time.strftime('%Y%m%d-%H%M%S')}"
    
    if type_ == "Restore Point":
        dest_folder = "restore_points"
        filename = f"{subtype}_{timestamp}.zip"
    elif type_ == "Automatic":
        dest_folder = f"automatic/{subtype}"
        filename = f"{subtype}_{timestamp}.zip"
    elif type_ == "Emergency":
        dest_folder = "emergency"
        filename = f"emergency_{timestamp}.zip"
    else:
        dest_folder = "manual"
        filename = f"manual_{timestamp}.zip"
        
    rel_path = f"{dest_folder}/{filename}"
    abs_path = os.path.join(BACKUP_DIR, dest_folder, filename)
    
    temp_dir = os.path.join(BACKUP_DIR, "temp_backup_staging")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        if landlord_id is not None:
            counts = _stage_landlord_export(landlord_id, temp_dir)
        else:
            # Full system backup — includes the complete DB (platform-admin scope)
            for real_path, legacy_name in DIR_MAPPING.items():
                if os.path.exists(real_path):
                    shutil.copytree(real_path, os.path.join(temp_dir, legacy_name))
            counts = None
                
        # Generate manifest & metadata
        manifest = create_manifest(backupId, type_, timestamp_iso)
        with open(os.path.join(temp_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=4)
            
        metadata = create_metadata(backupId, type_, timestamp_iso)
        metadata["scope"] = "landlord" if landlord_id is not None else "system"
        if landlord_id is not None:
            metadata["landlord_id"] = landlord_id
            metadata["created_by"] = f"Landlord {landlord_id}"
            metadata["tenant_count"] = counts["tenant_count"]
            metadata["receipt_count"] = counts["receipt_count"]
            metadata["inactive_tenant_count"] = 0
            metadata["archived_receipt_count"] = 0
            metadata["pdf_count"] = counts["pdf_count"]
            metadata["tenant_snapshot"] = [
                {
                    "id": t.get("id"),
                    "name": t.get("name"),
                    "status": t.get("status"),
                    "phone": t.get("phone"),
                    "roomNumber": t.get("roomnumber") or t.get("roomNumber"),
                }
                for t in _landlord_tenants(landlord_id)
            ]
        if tag:
            metadata["notes"] = tag
            
        with open(os.path.join(temp_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=4)
            
        # Zip
        zip_base = abs_path.replace(".zip", "")
        shutil.make_archive(zip_base, 'zip', temp_dir)
        
        # Calculate size and zip checksum
        size_bytes = os.path.getsize(abs_path)
        size_mb = f"{size_bytes / (1024 * 1024):.1f} MB"
        metadata["size"] = size_mb
        metadata["filename"] = filename
        metadata["path"] = rel_path
        metadata["zip_sha256"] = hash_file(abs_path)
        
        # Update registry
        registry = load_registry()
        registry["backups"].insert(0, metadata) # Add at top
        save_registry(registry)
        
        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        _log("Backup", type_, "Success", duration, {"backupId": backupId, "path": rel_path})
        
        # Cleanup old backups depending on type (implement later in 14B)
        
        return metadata
    except Exception as e:
        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        _log("Backup", type_, "Failed", duration, {"error": str(e)})
        raise e
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def _landlord_tenants(landlord_id: int) -> list:
    from app.core.db import get_conn
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id, name, status, phone, roomnumber FROM tenants WHERE landlord_id = ?",
            (landlord_id,),
        ).fetchall()]


def create_full_backup(tag="auto", landlord_id=None):
    if tag == "auto" or not tag:
        return create_backup(type_="Automatic", subtype="daily", landlord_id=landlord_id)
    elif tag.startswith("settings_change"):
        return create_backup(type_="Restore Point", subtype="before_settings", tag="Settings Change", landlord_id=landlord_id)
    elif tag.startswith("restore_bill"):
        return create_backup(type_="Restore Point", subtype="before_restore", tag="Receipt Restore", landlord_id=landlord_id)
    elif tag.startswith("add_tenant") or tag.startswith("update_tenant") or tag.startswith("delete_tenant"):
        return None
    else:
        return None

def get_all_backups():
    return load_registry()

def get_backup_by_id(backupId):
    registry = load_registry()
    return next((b for b in registry["backups"] if b["id"] == backupId), None)

def get_backups_for_landlord(landlord_id):
    """Only backups scoped to this landlord (global/system backups are
    platform-admin-only and never visible to a landlord)."""
    registry = load_registry()
    return {
        "version": registry.get("version", 1),
        "backups": [b for b in registry["backups"] if b.get("landlord_id") == landlord_id],
    }

def backup_owned_by(backupId, landlord_id) -> bool:
    meta = get_backup_by_id(backupId)
    return bool(meta and meta.get("scope") == "landlord" and meta.get("landlord_id") == landlord_id)

def verify_backup_integrity(backupId):
    registry = load_registry()
    backup_meta = next((b for b in registry["backups"] if b["id"] == backupId), None)
    if not backup_meta:
        raise Exception("Backup not found in registry")
        
    abs_path = os.path.join(BACKUP_DIR, backup_meta["path"])
    if not os.path.exists(abs_path):
        raise Exception("Backup ZIP file is missing")
        
    current_hash = hash_file(abs_path)
    if current_hash != backup_meta.get("zip_sha256"):
        raise Exception("Backup ZIP checksum mismatch (corrupted)")
        
    return True

def delete_backup(backupId):
    registry = load_registry()
    for i, b in enumerate(registry["backups"]):
        if b["id"] == backupId:
            abs_path = os.path.join(BACKUP_DIR, b["path"])
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except:
                    pass
            registry["backups"].pop(i)
            save_registry(registry)
            return True
    return False

def restore_backup(backupId):
    start_time = datetime.now()
    try:
        verify_backup_integrity(backupId)
        
        registry = load_registry()
        backup_meta = next((b for b in registry["backups"] if b["id"] == backupId))
        abs_path = os.path.join(BACKUP_DIR, backup_meta["path"])
        
        # 1. Create Temporary Backup (Rollback Point)
        temp_backup = create_backup(type_="Emergency", subtype="before_restore", tag=f"Before restoring {backupId}")
        temp_abs_path = os.path.join(BACKUP_DIR, temp_backup["path"])
        
        # 2. Extract Backup to staging
        staging_dir = os.path.join(BACKUP_DIR, "restore_staging")
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir, ignore_errors=True)
        os.makedirs(staging_dir, exist_ok=True)
        
        shutil.unpack_archive(abs_path, staging_dir, 'zip')
        
        # 3. Validation
        if not os.path.exists(os.path.join(staging_dir, "database")) or not os.path.exists(os.path.join(staging_dir, "config")):
            raise Exception("Invalid backup archive structure")
            
        # 4. Replacement
        for real_path, legacy_name in DIR_MAPPING.items():
            src = os.path.join(staging_dir, legacy_name)
            dst = real_path
            if os.path.exists(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst)
                
        # 5. Cleanup Staging
        shutil.rmtree(staging_dir, ignore_errors=True)
        
        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        _log("Restore", "Full", "Success", duration, {"backupId": backupId})
        return True
        
    except Exception as e:
        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        _log("Restore", "Full", "Failed", duration, {"error": str(e), "backupId": backupId})
        raise e

