"""
app/database/property_repository.py

Pure SQL helpers for landlord_properties, landlord_profiles, and the
landlord setup-wizard flags. No business logic here — callers validate.
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.db import get_conn


# ──────────────────────────────────────────────────────────────────────────────
# Properties
# ──────────────────────────────────────────────────────────────────────────────

def list_properties(landlord_id: int) -> List[dict]:
    """Return all properties for a landlord, ordered by sort_order then id."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM \"landlordProperties\" WHERE \"landlordId\" = %s ORDER BY \"sortOrder\", id",
            (landlord_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def count_properties(landlord_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM \"landlordProperties\" WHERE \"landlordId\" = %s",
            (landlord_id,),
        ).fetchone()
    return int(row["c"] or 0)


def get_property(landlord_id: int, property_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM \"landlordProperties\" WHERE id = %s AND \"landlordId\" = %s",
            (property_id, landlord_id),
        ).fetchone()
    return dict(row) if row else None


def next_property_sort_order(landlord_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(\"sortOrder\"), -1) AS m FROM \"landlordProperties\" WHERE \"landlordId\" = %s",
            (landlord_id,),
        ).fetchone()
    return int(row["m"] if row["m"] is not None else -1) + 1


def create_property(landlord_id: int, property_name: str, address: str = "") -> dict:
    now = datetime.utcnow().isoformat()
    sort_order = next_property_sort_order(landlord_id)
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO \"landlordProperties\" (\"landlordId\", \"propertyName\", address, \"sortOrder\", \"createdAt\", \"updatedAt\") "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "RETURNING *",
            (landlord_id, property_name, address, sort_order, now, now),
        ).fetchone()
        conn.commit()
    return dict(row)


def update_property(landlord_id: int, property_id: int, property_name: Optional[str] = None, address: Optional[str] = None) -> Optional[dict]:
    existing = get_property(landlord_id, property_id)
    if not existing:
        return None
    now = datetime.utcnow().isoformat()
    new_name = property_name if property_name is not None else existing["propertyName"]
    new_address = address if address is not None else existing["address"]
    with get_conn() as conn:
        conn.execute(
            "UPDATE \"landlordProperties\" SET \"propertyName\" = %s, address = %s, \"updatedAt\" = %s WHERE id = %s AND \"landlordId\" = %s",
            (new_name, new_address, now, property_id, landlord_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM \"landlordProperties\" WHERE id = %s",
            (property_id,),
        ).fetchone()
    return dict(row)


def delete_property(landlord_id: int, property_id: int) -> bool:
    """Delete a property; its tenants are unassigned (property_id -> NULL)."""
    existing = get_property(landlord_id, property_id)
    if not existing:
        return False
    with get_conn() as conn:
        conn.execute(
            "UPDATE tenants SET \"propertyId\" = NULL WHERE \"landlordId\" = %s AND \"propertyId\" = %s",
            (landlord_id, property_id),
        )
        conn.execute(
            "DELETE FROM \"landlordProperties\" WHERE id = %s AND \"landlordId\" = %s",
            (property_id, landlord_id),
        )
        conn.commit()
    return True


def tenants_for_property(landlord_id: int, property_id: int) -> List[dict]:
    """Return non-archived tenants belonging to a property."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tenants WHERE \"landlordId\" = %s AND \"propertyId\" = %s AND status != 'Archived' ORDER BY name",
            (landlord_id, property_id),
        ).fetchall()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────────────────────
# Setup wizard flags
# ──────────────────────────────────────────────────────────────────────────────

def get_setup_flags(landlord_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT \"setupCompleted\", \"setupSkipped\" FROM \"landlordAccounts\" WHERE id = %s",
            (landlord_id,),
        ).fetchone()
    return {
        "setupCompleted": bool(row and row["setupCompleted"]),
        "setupSkipped": bool(row and row["setupSkipped"]),
    }


def mark_setup_complete(landlord_id: int) -> None:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE \"landlordAccounts\" SET \"setupCompleted\" = 1, \"setupSkipped\" = 0, \"updatedAt\" = %s WHERE id = %s",
            (now, landlord_id),
        )
        conn.commit()


def mark_setup_skipped(landlord_id: int) -> None:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE \"landlordAccounts\" SET \"setupCompleted\" = 0, \"setupSkipped\" = 1, \"updatedAt\" = %s WHERE id = %s",
            (now, landlord_id),
        )
        conn.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Per-landlord "landlord" config section (Settings + PDF source)
# ──────────────────────────────────────────────────────────────────────────────

def get_landlord_profile(landlord_id: int) -> Dict[str, Any]:
    """Return the per-landlord profile dict (stored JSON), or {} if none."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT \"configJson\" FROM \"landlordProfiles\" WHERE \"landlordId\" = %s",
            (landlord_id,),
        ).fetchone()
    if not row or not row["configJson"]:
        return {}
    try:
        return json.loads(row["configJson"])
    except json.JSONDecodeError:
        return {}


def save_landlord_profile(landlord_id: int, section: Dict[str, Any]) -> None:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO "landlordProfiles" ("landlordId", "configJson", "updatedAt")
               VALUES (%s, %s, %s)
               ON CONFLICT("landlordId") DO UPDATE SET "configJson" = %s, "updatedAt" = %s""",
            (landlord_id, json.dumps(section, ensure_ascii=False), now, json.dumps(section, ensure_ascii=False), now),
        )
        conn.commit()
