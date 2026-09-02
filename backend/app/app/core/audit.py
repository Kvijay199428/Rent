"""
Platform admin audit logging — dual-writes to SQLite + JSONL.

SQLite table: platform_admin_audit_logs  (fast queries for UI)
JSONL file:   STORAGE_DIR/audit/audit.jsonl  (export / archival)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

from app.core.db import get_conn
from app.core.paths import STORAGE_DIR

AUDIT_DIR = os.path.join(STORAGE_DIR, "audit")
AUDIT_JSONL = os.path.join(AUDIT_DIR, "audit.jsonl")

# Ensure directory exists
os.makedirs(AUDIT_DIR, exist_ok=True)


def create_platform_admin_audit_log(
    admin_id: int,
    action: str,
    *,
    admin_username: str = "",
    target_type: str | None = None,
    target_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    meta: dict | None = None,
) -> None:
    """Write an audit entry to both SQLite and JSONL."""
    now = datetime.utcnow().isoformat()

    # --- SQLite ---
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO platform_admin_audit_logs
                    (admin_id, action, target_type, target_id, ip_address, meta_json, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    admin_id,
                    action,
                    target_type,
                    target_id,
                    ip_address,
                    json.dumps(meta) if meta else None,
                    now,
                ),
            )
            conn.commit()
    except Exception:
        pass  # don't let audit write failures break the request

    # --- JSONL ---
    entry = {
        "timestamp": now,
        "admin_id": admin_id,
        "admin_username": admin_username,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "meta": meta or {},
    }
    try:
        with open(AUDIT_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def cleanup_old_audit_logs(days: int) -> int:
    """Delete audit entries older than *days* from all 3 tables. Returns total count removed."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    removed = 0

    # --- SQLite: clean all 3 audit tables ---
    for table in ("platform_admin_audit_logs", "landlord_audit_logs", "tenant_audit_logs"):
        try:
            with get_conn() as conn:
                result = conn.execute(
                    f"DELETE FROM {table} WHERE created_at < %s", (cutoff,)
                )
                removed += result.rowcount or 0
                conn.commit()
        except Exception:
            pass

    # --- JSONL rewrite (drop old lines) ---
    if os.path.exists(AUDIT_JSONL):
        try:
            kept: list[str] = []
            with open(AUDIT_JSONL, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("timestamp", "") >= cutoff:
                            kept.append(line)
                    except json.JSONDecodeError:
                        kept.append(line)  # keep unparseable lines
            with open(AUDIT_JSONL, "w", encoding="utf-8") as f:
                for line in kept:
                    f.write(line + "\n")
        except Exception:
            pass

    return removed


def get_audit_log_path() -> str:
    return AUDIT_JSONL
