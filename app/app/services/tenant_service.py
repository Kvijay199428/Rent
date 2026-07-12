import os
from typing import List, Optional
import uuid

from app.models.tenant import Tenant
from app.core.db import get_conn

def load_tenants() -> List[Tenant]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM tenants ORDER BY id").fetchall()
    tenants = []
    for row in rows:
        t = Tenant(
            id=int(row["id"]),
            name=row["name"],
            company=row["company"],
            phone=row["phone"],
            email=row["email"],
            address=row["address"],
            room_number=row["roomnumber"],
            occupation=row["occupation"],
            notes=row["notes"],
            status=row["status"],
            rent=float(row["rent"]),
            water=float(row["water"]),
            default_tank_water_charge=float(row["defaulttankwatercharge"]),
            electricity_rate=float(row["electricityrate"]),
            previous_meter=float(row["previousmeter"]),
            additional_person_charge=float(row["additionalpersoncharge"]),
            security_deposit=float(row["securitydeposit"]),
            meter_id=row["meterid"],
            view_token=row["view_token"],
            tenant_pin=row["tenantpin"]
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
        room_number=row["roomnumber"],
        occupation=row["occupation"],
        notes=row["notes"],
        status=row["status"],
        rent=float(row["rent"]),
        water=float(row["water"]),
        default_tank_water_charge=float(row["defaulttankwatercharge"]),
        electricity_rate=float(row["electricityrate"]),
        previous_meter=float(row["previousmeter"]),
        additional_person_charge=float(row["additionalpersoncharge"]),
        security_deposit=float(row["securitydeposit"]),
        meter_id=row["meterid"],
        view_token=row["view_token"],
        tenant_pin=row["tenantpin"]
    )

def save_all_tenants(tenants_list: List[Tenant]):
    for t in tenants_list:
        update_tenant(t)

def add_tenant(t: Tenant):
    # Retrieve tenantpin and view_token from dict logic if present, else defaults
    # Since Pydantic model might not have them natively in current snapshot, we default if missing
    t_dict = t.dict()
    view_token = t_dict.get("view_token")
    if not view_token:
        import uuid
        view_token = str(uuid.uuid4())
    tenantpin = t_dict.get("tenant_pin") or ""
    
    with get_conn() as conn:
        conn.execute('''
            INSERT INTO tenants (
                id, name, company, phone, email, address, roomnumber, occupation,
                notes, status, rent, water, electricityrate, previousmeter,
                additionalpersoncharge, securitydeposit, defaulttankwatercharge,
                meterid, view_token, tenantpin
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            t.id, t.name, t.company, t.phone, t.email, t.address, t.room_number,
            t.occupation, t.notes, t.status, t.rent, t.water, t.electricity_rate,
            t.previous_meter, t.additional_person_charge, t.security_deposit,
            t.default_tank_water_charge, t.meter_id, view_token, tenantpin
        ))
        if t.id is None:
            t.id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
    return t.id

def update_tenant(t: Tenant):
    t_dict = t.dict()
    view_token = t_dict.get("view_token") or ""
    tenantpin = t_dict.get("tenant_pin") or ""
    
    with get_conn() as conn:
        conn.execute('''
            UPDATE tenants SET
                name=?, company=?, phone=?, email=?, address=?, roomnumber=?, occupation=?,
                notes=?, status=?, rent=?, water=?, electricityrate=?, previousmeter=?,
                additionalpersoncharge=?, securitydeposit=?, defaulttankwatercharge=?,
                meterid=?, view_token=?, tenantpin=?
            WHERE id=?
        ''', (
            t.name, t.company, t.phone, t.email, t.address, t.room_number,
            t.occupation, t.notes, t.status, t.rent, t.water, t.electricity_rate,
            t.previous_meter, t.additional_person_charge, t.security_deposit,
            t.default_tank_water_charge, t.meter_id, view_token, tenantpin,
            t.id
        ))
        conn.commit()

def delete_tenant(tenant_id: int, action: str = "archive"):
    action = (action or "archive").strip().lower()

    with get_conn() as conn:
        tenant_row = conn.execute(
            "SELECT id, name FROM tenants WHERE id = ?",
            (tenant_id,)
        ).fetchone()

        if not tenant_row:
            raise ValueError("Tenant not found.")

        tenant_name = tenant_row["name"]

        if action in {"hard", "delete"}:
            conn.execute("DELETE FROM occupants WHERE tenant_id = ?", (tenant_id,))
            conn.execute(
                """
                DELETE FROM receipts
                WHERE tenant_id = ?
                   OR lower(trim(tenant)) = lower(trim(?))
                """,
                (tenant_id, tenant_name)
            )
            conn.execute("DELETE FROM tenants WHERE id = ?", (tenant_id,))
            conn.commit()
            return {"tenant_id": tenant_id, "deleted": True}

        if action == "archive":
            conn.execute(
                "UPDATE tenants SET status = ? WHERE id = ?",
                ("Archived", tenant_id)
            )
            receipt_result = conn.execute(
                """
                UPDATE receipts
                SET status = ?,
                    tenant_id = COALESCE(tenant_id, ?)
                WHERE (tenant_id = ? OR lower(trim(tenant)) = lower(trim(?)))
                  AND status != ?
                """,
                ("ARCHIVED", tenant_id, tenant_id, tenant_name, "ARCHIVED")
            )
            conn.commit()
            return {
                "tenant_id": tenant_id,
                "archived": True,
                "receipts_updated": receipt_result.rowcount,
            }

        if action == "inactive":
            conn.execute(
                "UPDATE tenants SET status = ? WHERE id = ?",
                ("Inactive", tenant_id)
            )
            conn.commit()
            return {"tenant_id": tenant_id, "inactive": True}

        raise ValueError(f"Unsupported action: {action}")

def get_occupants(tenant_id: int) -> List[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM occupants WHERE tenant_id = ?", (tenant_id,)).fetchall()
    return [dict(r) for r in rows]

def save_occupant(tenant_id: int, occ_data: dict):
    uuid_val = occ_data.get("occupant_uuid") or occ_data.get("uuid")
    if not uuid_val:
        uuid_val = str(uuid.uuid4())
        
    with get_conn() as conn:
        # Try updating first
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE occupants SET
                name = ?, mobile = ?, status = ?, aadhaar_front = ?, aadhaar_back = ?,
                aadhaar_combined = ?, emp_front = ?, emp_back = ?, uploaddate = ?, uploadmonth = ?
            WHERE occupant_uuid = ?
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
                INSERT INTO occupants (tenant_id, occupant_uuid, name, mobile, status, aadhaar_front, aadhaar_back, aadhaar_combined, emp_front, emp_back, uploaddate, uploadmonth)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                tenant_id, uuid_val, occ_data.get("name", ""), occ_data.get("mobile", ""), occ_data.get("status", "Active"),
                occ_data.get("aadhaar_front", ""), occ_data.get("aadhaar_back", ""), occ_data.get("aadhaar_combined", ""),
                occ_data.get("emp_front", ""), occ_data.get("emp_back", ""), occ_data.get("uploaddate", ""), occ_data.get("uploadmonth", "")
            ))
        conn.commit()

def update_occupant_status(occupant_uuid: str, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE occupants SET status = ? WHERE occupant_uuid = ?", (status, occupant_uuid))
        conn.commit()

def delete_occupant(occupant_uuid: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM occupants WHERE occupant_uuid = ?", (occupant_uuid,))
        conn.commit()

