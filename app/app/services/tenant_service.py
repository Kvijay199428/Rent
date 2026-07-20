# //File: app\app\services\tenant_service.py
# POLICY: tenantId is the only identity key for tenant-related data.
# tenantName is display-only and must never be used for joins, ownership, lookup, or mutation.
from typing import List, Optional
from datetime import datetime
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

def get_tenant(tenantId: int) -> Optional[Tenant]:
    """Get a single tenant by ID. Returns None if not found."""
    if tenantId is None:
        return None
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tenants WHERE id = ?", (tenantId,)
        ).fetchone()
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
        # Cascade identity/contact fields to all receipt rows for this tenant.
        # Only updates display-snapshot fields; historical billing values (rent, water,
        # electricity, rate, total, month, date) are intentionally left unchanged.
        conn.execute(
            """
            UPDATE receipts
            SET tenant = ?,
                tenantphone = ?,
                tenantcompany = ?,
                tenantaddress = ?
            WHERE tenantId = ?
            """,
            (
                t.name,
                t.phone or "",
                getattr(t, "company", "") or "",
                getattr(t, "address", "") or "",
                t.id,
            ),
        )
        conn.commit()

def _tenant_row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"] or "",
        "company": row["company"] or "",
        "phone": row["phone"] or "",
        "email": row["email"] or "",
        "address": row["address"] or "",
        "roomNumber": row["roomnumber"] or "",
        "occupation": row["occupation"] or "",
        "notes": row["notes"] or "",
        "status": row["status"] or "Active",
        "rent": float(row["rent"] or 0),
        "water": float(row["water"] or 0),
        "defaulttankWaterCharge": float(row["defaulttankwatercharge"] or 0),
        "electricityRate": float(row["electricityrate"] or 0),
        "previousMeter": float(row["previousmeter"] or 0),
        "additionalPersonCharge": float(row["additionalpersoncharge"] or 0),
        "securityDeposit": float(row["securitydeposit"] or 0),
        "meterId": row["meterid"] or "",
        "viewToken": row["viewToken"] or "",
        "arrears": 0,
    }


def _receipt_row_to_dict(row) -> dict:
    return {
        "Bill": row["billNo"] or "",
        "Date": row["date"] or "",
        "Month": row["month"] or "",
        "Tenant": row["tenant"] or "",
        "TenantId": int(row["tenantId"] or 0),
        "Previous": float(row["previous"] or 0),
        "Current": float(row["current"] or 0),
        "Units": float(row["units"] or 0),
        "Rent": float(row["rent"] or 0),
        "Additional": float(row["additional"] or 0),
        "Water": float(row["water"] or 0),
        "tankWater": float(row["tankWater"] or 0),
        "Electricity": float(row["electricity"] or 0),
        "Total": float(row["total"] or 0),
        "PDF": row["pdf"] or "",
        "Tenant_Phone": row["tenantphone"] or "",
        "Tenant_Company": row["tenantcompany"] or "",
        "Tenant_Address": row["tenantaddress"] or "",
        "Rate": float(row["rate"] or 0),
        "Status": row["status"] or "ACTIVE",
        "Archived_Date": row["archiveddate"] or "",
        "Archived_By": row["archivedby"] or "",
        "Deleted_Date": row["deleteddate"] or "",
        "Additional_Persons": int(row["additionalpersons"] or 0),
        "additionalPersonRate": float(row["additionalpersonrate"] or 0),
        "Receipt_Version": int(row["receiptversion"] or 0),
        "Generated_By": row["generatedby"] or "",
        "paymentStatus": row["paymentstatus"] or "PENDING",
        "MaintenanceCharge": float(row["maintenancecharge"] or 0),
        "MaintenanceDesc": row["maintenancedesc"] or "",
        "previousArrears": float(row["previousarrears"] or 0),
        "amountReceived": float(row["amountreceived"] or 0),
    }


def delete_tenant(tenantId: int, action: str = "archive"):
    action = (action or "archive").strip().lower()

    with get_conn() as conn:
        tenant_row = conn.execute(
            "SELECT * FROM tenants WHERE id = ?",
            (tenantId,)
        ).fetchone()

        if not tenant_row:
            raise ValueError("Tenant not found.")

        if action in {"hard", "delete"}:
            conn.execute("DELETE FROM occupants WHERE tenantId = ?", (tenantId,))
            conn.execute("DELETE FROM receipts WHERE tenantId = ?", (tenantId,))
            conn.execute("DELETE FROM tenants WHERE id = ?", (tenantId,))
            conn.commit()
            return {"tenantId": tenantId, "deleted": True, "archived": False, "restored": False}

        if action == "archive":
            archived_at = datetime.utcnow().strftime("%d %B %Y")

            conn.execute(
                "UPDATE tenants SET status = ? WHERE id = ?",
                ("Archived", tenantId),
            )
            receipt_result = conn.execute(
                """
                UPDATE receipts
                   SET status = 'ARCHIVED',
                       archiveddate = CASE
                           WHEN archiveddate IS NULL OR archiveddate = '' THEN ?
                           ELSE archiveddate
                       END
                 WHERE tenantId = ?
                """,
                (archived_at, tenantId),
            )
            conn.commit()

            tenant_after = conn.execute(
                "SELECT * FROM tenants WHERE id = ?", (tenantId,)
            ).fetchone()
            receipt_rows = conn.execute(
                "SELECT * FROM receipts WHERE tenantId = ? ORDER BY date DESC, billNo DESC",
                (tenantId,),
            ).fetchall()

            return {
                "tenantId": tenantId,
                "archived": True,
                "restored": False,
                "receipts_updated": receipt_result.rowcount,
                "tenant": _tenant_row_to_dict(tenant_after),
                "receipts": [_receipt_row_to_dict(r) for r in receipt_rows],
            }

        if action == "restore":
            updated_tenant = conn.execute(
                "UPDATE tenants SET status = ? WHERE id = ?",
                ("Active", tenantId),
            )
            if updated_tenant.rowcount == 0:
                raise ValueError("Tenant not found.")

            receipt_result = conn.execute(
                """
                UPDATE receipts
                   SET status = 'ACTIVE',
                       archiveddate = '',
                       archivedby = ''
                 WHERE tenantId = ?
                   AND UPPER(COALESCE(status, '')) = 'ARCHIVED'
                """,
                (tenantId,),
            )
            conn.commit()

            tenant_after = conn.execute(
                "SELECT * FROM tenants WHERE id = ?", (tenantId,)
            ).fetchone()
            receipt_rows = conn.execute(
                "SELECT * FROM receipts WHERE tenantId = ? ORDER BY date DESC, billNo DESC",
                (tenantId,),
            ).fetchall()

            return {
                "tenantId": tenantId,
                "archived": False,
                "restored": True,
                "receipts_updated": receipt_result.rowcount,
                "tenant": _tenant_row_to_dict(tenant_after),
                "receipts": [_receipt_row_to_dict(r) for r in receipt_rows],
            }

        if action == "inactive":
            conn.execute(
                "UPDATE tenants SET status = ? WHERE id = ?",
                ("Inactive", tenantId)
            )
            conn.commit()
            return {"tenantId": tenantId, "inactive": True, "archived": False, "restored": False}

        raise ValueError(f"Unsupported action: {action}")

def get_occupants(tenantId: int) -> List[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM occupants WHERE tenantId = ?", (tenantId,)).fetchall()

    result = []
    for r in rows:
        row = dict(r)
        # Remap snake_case DB columns to camelCase/joined field names the frontend expects
        row["aadhaarfront"] = row.pop("aadhaar_front", "") or ""
        row["aadhaarback"] = row.pop("aadhaar_back", "") or ""
        row["aadhaarcombined"] = row.pop("aadhaar_combined", "") or ""
        row["empfront"] = row.pop("emp_front", "") or ""
        row["empback"] = row.pop("emp_back", "") or ""
        # Keep "Occupant UUID" alias for admin-app backwards compatibility
        row["Occupant UUID"] = row.get("occupantUuid", "")
        result.append(row)
    return result

def save_occupant(tenantId: int, occ_data: dict):
    uuid_val = occ_data.get("occupantUuid") or occ_data.get("uuid")
    if not uuid_val:
        uuid_val = str(uuid.uuid4())
        
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE occupants SET
                name = ?, mobile = ?, address = ?, residentSince = ?,
                status = ?, aadhaar_front = ?, aadhaar_back = ?,
                aadhaar_combined = ?, emp_front = ?, emp_back = ?,
                uploaddate = ?, uploadmonth = ?
            WHERE occupantUuid = ?
        ''', (
            occ_data.get("name", ""),
            occ_data.get("mobile", ""),
            occ_data.get("address", ""),
            occ_data.get("residentSince", ""),
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
                INSERT INTO occupants (
                    tenantId, occupantUuid, name, mobile, address, residentSince,
                    status, aadhaar_front, aadhaar_back, aadhaar_combined,
                    emp_front, emp_back, uploaddate, uploadmonth
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                tenantId, uuid_val,
                occ_data.get("name", ""), occ_data.get("mobile", ""),
                occ_data.get("address", ""), occ_data.get("residentSince", ""),
                occ_data.get("status", "Active"),
                occ_data.get("aadhaar_front", ""), occ_data.get("aadhaar_back", ""),
                occ_data.get("aadhaar_combined", ""),
                occ_data.get("emp_front", ""), occ_data.get("emp_back", ""),
                occ_data.get("uploaddate", ""), occ_data.get("uploadmonth", "")
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

