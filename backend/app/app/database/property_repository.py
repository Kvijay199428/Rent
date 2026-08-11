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
            "SELECT * FROM landlord_properties WHERE landlord_id = ? ORDER BY sort_order, id",
            (landlord_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def count_properties(landlord_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM landlord_properties WHERE landlord_id = ?",
            (landlord_id,),
        ).fetchone()
    return int(row["c"] or 0)


def get_property(landlord_id: int, property_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM landlord_properties WHERE id = ? AND landlord_id = ?",
            (property_id, landlord_id),
        ).fetchone()
    return dict(row) if row else None


def next_property_sort_order(landlord_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) AS m FROM landlord_properties WHERE landlord_id = ?",
            (landlord_id,),
        ).fetchone()
    return int(row["m"] if row["m"] is not None else -1) + 1


def create_property(landlord_id: int, property_name: str, address: str = "") -> dict:
    now = datetime.utcnow().isoformat()
    sort_order = next_property_sort_order(landlord_id)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO landlord_properties (landlord_id, property_name, address, sort_order, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (landlord_id, property_name, address, sort_order, now, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM landlord_properties WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
    return dict(row)


def update_property(landlord_id: int, property_id: int, property_name: Optional[str] = None, address: Optional[str] = None) -> Optional[dict]:
    existing = get_property(landlord_id, property_id)
    if not existing:
        return None
    now = datetime.utcnow().isoformat()
    new_name = property_name if property_name is not None else existing["property_name"]
    new_address = address if address is not None else existing["address"]
    with get_conn() as conn:
        conn.execute(
            "UPDATE landlord_properties SET property_name = ?, address = ?, updated_at = ? WHERE id = ? AND landlord_id = ?",
            (new_name, new_address, now, property_id, landlord_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM landlord_properties WHERE id = ?",
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
            "UPDATE tenants SET property_id = NULL WHERE landlord_id = ? AND property_id = ?",
            (landlord_id, property_id),
        )
        conn.execute(
            "DELETE FROM landlord_properties WHERE id = ? AND landlord_id = ?",
            (property_id, landlord_id),
        )
        conn.commit()
    return True


def tenants_for_property(landlord_id: int, property_id: int) -> List[dict]:
    """Return non-archived tenants belonging to a property."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tenants WHERE landlord_id = ? AND property_id = ? AND status != 'Archived' ORDER BY name",
            (landlord_id, property_id),
        ).fetchall()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────────────────────
# Setup wizard flags
# ──────────────────────────────────────────────────────────────────────────────

def get_setup_flags(landlord_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT setup_completed, setup_skipped FROM landlord_accounts WHERE id = ?",
            (landlord_id,),
        ).fetchone()
    return {
        "setupCompleted": bool(row and row["setup_completed"]),
        "setupSkipped": bool(row and row["setup_skipped"]),
    }


def mark_setup_complete(landlord_id: int) -> None:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE landlord_accounts SET setup_completed = 1, setup_skipped = 0, updated_at = ? WHERE id = ?",
            (now, landlord_id),
        )
        conn.commit()


def mark_setup_skipped(landlord_id: int) -> None:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE landlord_accounts SET setup_completed = 0, setup_skipped = 1, updated_at = ? WHERE id = ?",
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
            "SELECT config_json FROM landlord_profiles WHERE landlord_id = ?",
            (landlord_id,),
        ).fetchone()
    if not row or not row["config_json"]:
        return {}
    try:
        return json.loads(row["config_json"])
    except json.JSONDecodeError:
        return {}


def save_landlord_profile(landlord_id: int, section: Dict[str, Any]) -> None:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO landlord_profiles (landlord_id, config_json, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(landlord_id) DO UPDATE SET config_json = ?, updated_at = ?""",
            (landlord_id, json.dumps(section, ensure_ascii=False), now, json.dumps(section, ensure_ascii=False), now),
        )
        conn.commit()
