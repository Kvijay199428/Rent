import os
from typing import List, Optional
import uuid

from app.models.tenant import Tenant
from app.core.db import get_conn

def load_tenants(include_archived: bool = False) -> List[Tenant]:
    with get_conn() as conn:
        if include_archived:
            rows = conn.execute("SELECT * FROM tenants ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tenants WHERE status != 'Archived' ORDER BY id"
            ).fetchall()
    tenants = []
    for row in rows:
        t = Tenant(
            id=int(row["id"]),
            name=row["name"],
            company=row["company"],
            phone=row["phone"],
            email=row["email"],
            address=row["address"],
            roomNumber=row["roomnumber"],
            occupation=row["occupation"],
            notes=row["notes"],
            status=row["status"],
            rent=float(row["rent"]),
            water=float(row["water"]),
            defaulttankWaterCharge=float(row["defaulttankWatercharge"]),
            electricityRate=float(row["electricityrate"]),
            previousMeter=float(row["previousmeter"]),
            additionalPersonCharge=float(row["additionalpersoncharge"]),
            securityDeposit=float(row["securitydeposit"]),
            meterId=row["meterid"],
            viewToken=row["viewToken"],
            tenantPin=row["tenantpin"]
        )
        tenants.append(t)
    return tenants

def get_tenant_by_name(name: str) -> Optional[Tenant]:
    if not name:
        return None
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tenants WHERE name COLLATE NOCASE = ?", (name,)).fetchone()
    if not row:
        return None
    return Tenant(
        id=int(row["id"]),
        name=row["name"],
        company=row["company"],
        phone=row["phone"],
        email=row["email"],
        address=row["address"],
        roomNumber=row["roomnumber"],
        occupation=row["occupation"],
        notes=row["notes"],
        status=row["status"],
        rent=float(row["rent"]),
        water=float(row["water"]),
        defaulttankWaterCharge=float(row["defaulttankWatercharge"]),
        electricityRate=float(row["electricityrate"]),
        previousMeter=float(row["previousmeter"]),
        additionalPersonCharge=float(row["additionalpersoncharge"]),
        securityDeposit=float(row["securitydeposit"]),
        meterId=row["meterid"],
        viewToken=row["viewToken"],
        tenantPin=row["tenantpin"]
    )

def save_all_tenants(tenants_list: List[Tenant]):
    for t in tenants_list:
        update_tenant(t)

def add_tenant(t: Tenant):
    # Retrieve tenantpin and viewToken from dict logic if present, else defaults
    # Since Pydantic model might not have them natively in current snapshot, we default if missing
    t_dict = t.dict()
    viewToken = t_dict.get("viewToken")
    if not viewToken:
        import uuid
        viewToken = str(uuid.uuid4())
    tenantpin = t_dict.get("tenantPin") or ""
    
    with get_conn() as conn:
        conn.execute('''
            INSERT INTO tenants (
                id, name, company, phone, email, address, roomnumber, occupation,
                notes, status, rent, water, electricityrate, previousmeter,
                additionalpersoncharge, securitydeposit, defaulttankWatercharge,
                meterid, viewToken, tenantpin
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            t.id, t.name, t.company, t.phone, t.email, t.address, t.roomNumber,
            t.occupation, t.notes, t.status, t.rent, t.water, t.electricityRate,
            t.previousMeter, t.additionalPersonCharge, t.securityDeposit,
            t.defaulttankWaterCharge, t.meterId, viewToken, tenantpin
        ))
        if t.id is None:
            t.id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
    return t.id

def update_tenant(t: Tenant):
    t_dict = t.dict()
    viewToken = t_dict.get("viewToken") or ""
    tenantpin = t_dict.get("tenantPin") or ""
    
    with get_conn() as conn:
        conn.execute('''
            UPDATE tenants SET
                name=?, company=?, phone=?, email=?, address=?, roomnumber=?, occupation=?,
                notes=?, status=?, rent=?, water=?, electricityrate=?, previousmeter=?,
                additionalpersoncharge=?, securitydeposit=?, defaulttankWatercharge=?,
                meterid=?, viewToken=?, tenantpin=?
            WHERE id=?
        ''', (
            t.name, t.company, t.phone, t.email, t.address, t.roomNumber,
            t.occupation, t.notes, t.status, t.rent, t.water, t.electricityRate,
            t.previousMeter, t.additionalPersonCharge, t.securityDeposit,
            t.defaulttankWaterCharge, t.meterId, viewToken, tenantpin,
            t.id
        ))
        conn.commit()

def delete_tenant(tenantId: int, action: str = "archive"):
    action = (action or "archive").strip().lower()

    with get_conn() as conn:
        tenant_row = conn.execute(
            "SELECT id, name FROM tenants WHERE id = ?",
            (tenantId,)
        ).fetchone()

        if not tenant_row:
            raise ValueError("Tenant not found.")

        tenantName = tenant_row["name"]

        if action in {"hard", "delete"}:
            conn.execute("DELETE FROM occupants WHERE tenantId = ?", (tenantId,))
            conn.execute(
                """
                DELETE FROM receipts
                WHERE tenantId = ?
                   OR lower(trim(tenant)) = lower(trim(?))
                """,
                (tenantId, tenantName)
            )
            conn.execute("DELETE FROM tenants WHERE id = ?", (tenantId,))
            conn.commit()
            return {"tenantId": tenantId, "deleted": True}

        if action == "archive":
            conn.execute(
                "UPDATE tenants SET status = ? WHERE id = ?",
                ("Archived", tenantId)
            )
            receipt_result = conn.execute(
                """
                UPDATE receipts
                SET status = ?,
                    tenantId = COALESCE(tenantId, ?)
                WHERE (tenantId = ? OR lower(trim(tenant)) = lower(trim(?)))
                  AND status != ?
                """,
                ("ARCHIVED", tenantId, tenantId, tenantName, "ARCHIVED")
            )
            conn.commit()
            return {
                "tenantId": tenantId,
                "archived": True,
                "receipts_updated": receipt_result.rowcount,
            }

        if action == "inactive":
            conn.execute(
                "UPDATE tenants SET status = ? WHERE id = ?",
                ("Inactive", tenantId)
            )
            conn.commit()
            return {"tenantId": tenantId, "inactive": True}

        raise ValueError(f"Unsupported action: {action}")

def get_occupants(tenantId: int) -> List[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM occupants WHERE tenantId = ?", (tenantId,)).fetchall()
    return [dict(r) for r in rows]

def save_occupant(tenantId: int, occ_data: dict):
    uuid_val = occ_data.get("occupantUuid") or occ_data.get("uuid")
    if not uuid_val:
        uuid_val = str(uuid.uuid4())
        
    with get_conn() as conn:
        # Try updating first
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE occupants SET
                name = ?, mobile = ?, status = ?, aadhaar_front = ?, aadhaar_back = ?,
                aadhaar_combined = ?, emp_front = ?, emp_back = ?, uploaddate = ?, uploadmonth = ?
            WHERE occupantUuid = ?
        ''', (
            occ_data.get("name", ""),
            occ_data.get("mobile", ""),
            occ_data.get("status", "Active"),
            occ_data.get("aadhaar_front", ""),
            occ_data.get("aadhaar_back", ""),
            occ_data.get("aadhaar_combined", ""),
            occ_data.get("emp_front", ""),
            occ_data.get("emp_back", ""),
            occ_data.get("uploaddate", ""),
            occ_data.get("uploadmonth", ""),
            uuid_val
        ))
        
        if cursor.rowcount == 0:
            cursor.execute('''
                INSERT INTO occupants (tenantId, occupantUuid, name, mobile, status, aadhaar_front, aadhaar_back, aadhaar_combined, emp_front, emp_back, uploaddate, uploadmonth)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                tenantId, uuid_val, occ_data.get("name", ""), occ_data.get("mobile", ""), occ_data.get("status", "Active"),
                occ_data.get("aadhaar_front", ""), occ_data.get("aadhaar_back", ""), occ_data.get("aadhaar_combined", ""),
                occ_data.get("emp_front", ""), occ_data.get("emp_back", ""), occ_data.get("uploaddate", ""), occ_data.get("uploadmonth", "")
            ))
        conn.commit()

def update_occupant_status(occupantUuid: str, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE occupants SET status = ? WHERE occupantUuid = ?", (status, occupantUuid))
        conn.commit()

def delete_occupant(occupantUuid: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM occupants WHERE occupantUuid = ?", (occupantUuid,))
        conn.commit()

