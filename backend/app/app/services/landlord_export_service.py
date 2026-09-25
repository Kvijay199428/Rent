"""
app/services/landlord_export_service.py

Build a JSON-safe snapshot of a single landlord's data for the Settings -> Data
export endpoint (feature-gated by system.features.data_export).

Everything is read-only and scoped to the landlord. Credential-bearing columns
(password hashes, TOTP secrets, tenant auth tokens) are stripped from the
payload; regenerable artifacts (receipt PDFs) are excluded.
"""

from datetime import datetime

from app.core.config_service import config
from app.core.db import get_conn
from app.services.landlord_config_service import get_effective_landlord_config

# landlordAccounts columns that must never leave the server.
_SENSITIVE_LANDLORD_FIELDS = {"passwordHash", "tempPasswordCreatedAt", "tempPasswordConsumed", "totpSecret"}

# tenants columns that identify the tenant or grant access to their account.
_SENSITIVE_TENANT_FIELDS = {"passwordHash", "pinHash", "passwordResetTokenHash", "viewToken", "qrKey"}

# receipts columns that are large, regenerable artifacts.
_DROP_RECEIPT_FIELDS = {"pdf"}


def _rows(conn, sql: str, params: tuple = ()) -> list:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _strip(row: dict, drop: set) -> dict:
    return {k: v for k, v in row.items() if k not in drop}


def export_landlord_data(landlord_id: int) -> dict:
    """Return the landlord's scoped data as one JSON-serializable payload."""
    with get_conn() as conn:
        landlord_row = conn.execute(
            'SELECT * FROM "landlordAccounts" WHERE id = %s', (landlord_id,)
        ).fetchone()

        tenants = [
            _strip(row, _SENSITIVE_TENANT_FIELDS)
            for row in _rows(conn, 'SELECT * FROM tenants WHERE "landlordId" = %s ORDER BY id', (landlord_id,))
        ]

        receipts = [
            _strip(row, _DROP_RECEIPT_FIELDS)
            for row in _rows(conn, 'SELECT * FROM receipts WHERE "landlordId" = %s ORDER BY id', (landlord_id,))
        ]

        payment_entries = _rows(
            conn,
            'SELECT * FROM "paymentEntries" WHERE "landlordId" = %s ORDER BY id',
            (landlord_id,),
        )

        payment_allocations = _rows(
            conn,
            'SELECT * FROM "paymentAllocations" '
            'WHERE "paymentEntryId" IN '
            '(SELECT id FROM "paymentEntries" WHERE "landlordId" = %s) '
            'ORDER BY id',
            (landlord_id,),
        )

        occupants = _rows(
            conn,
            'SELECT * FROM occupants WHERE "landlordId" = %s ORDER BY "tenantId", id',
            (landlord_id,),
        )

        audit_logs = _rows(
            conn,
            'SELECT * FROM "landlordAuditLogs" WHERE "landlordId" = %s ORDER BY id',
            (landlord_id,),
        )

    landlord = _strip(dict(landlord_row), _SENSITIVE_LANDLORD_FIELDS) if landlord_row else {}

    return {
        "exportedAt": datetime.utcnow().isoformat() + "Z",
        "landlord": landlord,
        "config": {
            "landlord": get_effective_landlord_config(landlord_id),
            "ui": config.get("ui", default={}),
            "billing": config.get("billing", default={}),
            "notifications": config.get("notifications", default={}),
            "backup": config.get("backup", default={}),
            "whatsapp": config.get("whatsapp", default={}),
        },
        "tenants": tenants,
        "receipts": receipts,
        "paymentEntries": payment_entries,
        "paymentAllocations": payment_allocations,
        "occupants": occupants,
        "auditLogs": audit_logs,
    }