# //File: app\app\services\tenant_service.py
# POLICY: tenantId is the only identity key for tenant-related data.
# tenantName is display-only and must never be used for joins, ownership, lookup, or mutation.
from typing import List, Optional
from datetime import datetime
import uuid

from app.models.tenant import Tenant
from app.core.db import get_conn

def load_tenants(include_archived: bool = False, landlord_id: Optional[int] = None) -> List[Tenant]:
    clauses = []
    params: list = []
    if not include_archived:
        clauses.append("status != 'Archived'")
    if landlord_id is not None:
        clauses.append("\"landlordId\" = %s")
        params.append(landlord_id)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with get_conn() as conn:
        rows = conn.execute(f"SELECT * FROM tenants{where} ORDER BY id", params).fetchall()
    tenants = []
    for row in rows:
        t = Tenant(
            id=int(row["id"]),
            name=row["name"],
            company=row["company"],
            phone=row["phone"],
            email=row["email"],
            address=row["address"],
            roomNumber=row["roomNumber"],
            occupation=row["occupation"],
            notes=row["notes"],
            status=row["status"],
            rent=float(row["rentAmount"]),
            water=float(row["waterCharge"]),
            defaulttankWaterCharge=float(row["defaultTankWaterCharge"]),
            electricityRate=float(row["electricityRate"]),
            previousMeter=float(row["previousMeter"]),
            additionalPersonCharge=float(row["additionalPersonCharge"]),
            securityDeposit=float(row["securityDeposit"]),
            meterId=row["meterId"],
            viewToken=row["viewToken"],
            tenantPin=row["tenantPin"],
            qr_key=row["qrKey"] or "",
            tenantUsername=row["tenantUsername"] or "",
            statusChangedAt=row["statusChangedAt"] or None,
            landlord_id=row["landlordId"],
            property_id=row["propertyId"],
        )
        tenants.append(t)
    return tenants

def get_tenant(tenantId: int, landlord_id: Optional[int] = None) -> Optional[Tenant]:
    """Get a single tenant by ID. Optionally scoped to a landlord. Returns None if not found."""
    if tenantId is None:
        return None
    clauses = ["id = %s"]
    params: list = [tenantId]
    if landlord_id is not None:
        clauses.append("\"landlordId\" = %s")
        params.append(landlord_id)
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT * FROM tenants WHERE {' AND '.join(clauses)}", tuple(params)
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
        roomNumber=row["roomNumber"],
        occupation=row["occupation"],
        notes=row["notes"],
        status=row["status"],
        rent=float(row["rentAmount"]),
        water=float(row["waterCharge"]),
        defaulttankWaterCharge=float(row["defaultTankWaterCharge"]),
        electricityRate=float(row["electricityRate"]),
        previousMeter=float(row["previousMeter"]),
        additionalPersonCharge=float(row["additionalPersonCharge"]),
        securityDeposit=float(row["securityDeposit"]),
        meterId=row["meterId"],
        viewToken=row["viewToken"],
        tenantPin=row["tenantPin"],
        statusChangedAt=row["statusChangedAt"] or None,
        landlord_id=row["landlordId"],
        property_id=row["propertyId"],
    )

def tenant_belongs_to_landlord(tenantId: int, landlord_id: Optional[int]) -> bool:
    """True if the tenant exists and is owned by the given landlord."""
    if tenantId is None or landlord_id is None:
        return False
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM tenants WHERE id = %s AND \"landlordId\" = %s",
            (tenantId, landlord_id),
        ).fetchone()
    return row is not None


def get_tenant_by_name(name: str) -> Optional[Tenant]:
    if not name:
        return None
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tenants WHERE LOWER(name) = LOWER(%s)", (name,)).fetchone()
    if not row:
        return None
    return Tenant(
        id=int(row["id"]),
        name=row["name"],
        company=row["company"],
        phone=row["phone"],
        email=row["email"],
        address=row["address"],
        roomNumber=row["roomNumber"],
        occupation=row["occupation"],
        notes=row["notes"],
        status=row["status"],
        rent=float(row["rentAmount"]),
        water=float(row["waterCharge"]),
        defaulttankWaterCharge=float(row["defaultTankWaterCharge"]),
        electricityRate=float(row["electricityRate"]),
        previousMeter=float(row["previousMeter"]),
        additionalPersonCharge=float(row["additionalPersonCharge"]),
        securityDeposit=float(row["securityDeposit"]),
        meterId=row["meterId"],
        viewToken=row["viewToken"],
        tenantPin=row["tenantPin"],
        statusChangedAt=row["statusChangedAt"] or None,
        landlord_id=row["landlordId"],
        property_id=row["propertyId"],
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
    qr_key = (t_dict.get("qr_key") or "").strip()
    if not qr_key:
        # Single 128-bit key; a longer key would bloat the QR payload into a
        # larger matrix and hurt scannability.
        qr_key = uuid.uuid4().hex
    
    with get_conn() as conn:
        if t.id is None:
            row = conn.execute('''
                INSERT INTO tenants (
                    name, company, phone, email, address, "roomNumber", occupation,
                    notes, status, "rentAmount", "waterCharge", "electricityRate", "previousMeter",
                    "additionalPersonCharge", "securityDeposit", "defaultTankWaterCharge",
                    "meterId", "viewToken", "tenantPin", "landlordId", "qrKey", "propertyId"
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                t.name, t.company, t.phone, t.email, t.address, t.roomNumber,
                t.occupation, t.notes, t.status, t.rent, t.water, t.electricityRate,
                t.previousMeter, t.additionalPersonCharge, t.securityDeposit,
                t.defaulttankWaterCharge, t.meterId, viewToken, tenantpin, t.landlord_id,
                qr_key, t.propertyId
            )).fetchone()
            t.id = row["id"]
        else:
            conn.execute('''
                INSERT INTO tenants (
                    id, name, company, phone, email, address, "roomNumber", occupation,
                    notes, status, "rentAmount", "waterCharge", "electricityRate", "previousMeter",
                    "additionalPersonCharge", "securityDeposit", "defaultTankWaterCharge",
                    "meterId", "viewToken", "tenantPin", "landlordId", "qrKey", "propertyId"
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                t.id, t.name, t.company, t.phone, t.email, t.address, t.roomNumber,
                t.occupation, t.notes, t.status, t.rent, t.water, t.electricityRate,
                t.previousMeter, t.additionalPersonCharge, t.securityDeposit,
                t.defaulttankWaterCharge, t.meterId, viewToken, tenantpin, t.landlord_id,
                qr_key, t.propertyId
            ))
        conn.commit()
    return t.id

def update_tenant(t: Tenant):
    t_dict = t.dict()
    viewToken = t_dict.get("viewToken") or ""
    tenantpin = t_dict.get("tenantPin") or ""
    qr_key = (t_dict.get("qr_key") or "").strip()
    
    with get_conn() as conn:
        # Detect status change and record timestamp
        if t.id is not None:
            existing = conn.execute("SELECT status, \"qrKey\" FROM tenants WHERE id = %s", (t.id,)).fetchone()
            if existing and (existing["status"] or "").strip().lower() != (t.status or "").strip().lower():
                t.statusChangedAt = datetime.utcnow().isoformat()
            # Preserve the existing qr_key when the model doesn't carry one
            if not qr_key and existing and (existing["qrKey"] or ""):
                qr_key = existing["qrKey"]

        conn.execute('''
            UPDATE tenants SET
                name=%s, company=%s, phone=%s, email=%s, address=%s, "roomNumber"=%s, occupation=%s,
                notes=%s, status=%s, "rentAmount"=%s, "waterCharge"=%s, "electricityRate"=%s, "previousMeter"=%s,
                "additionalPersonCharge"=%s, "securityDeposit"=%s, "defaultTankWaterCharge"=%s,
                "meterId"=%s, "viewToken"=%s, "tenantPin"=%s, "qrKey"=%s, "statusChangedAt"=%s, "propertyId"=%s
            WHERE id=%s
        ''', (
            t.name, t.company, t.phone, t.email, t.address, t.roomNumber,
            t.occupation, t.notes, t.status, t.rent, t.water, t.electricityRate,
            t.previousMeter, t.additionalPersonCharge, t.securityDeposit,
            t.defaulttankWaterCharge, t.meterId, viewToken, tenantpin, qr_key,
            t.statusChangedAt, t.propertyId, t.id
        ))
        # Cascade identity/contact fields to all receipt rows for this tenant.
        # Only updates display-snapshot fields; historical billing values (rent, water,
        # electricity, rate, total, month, date) are intentionally left unchanged.
        conn.execute(
            '''
            UPDATE receipts
            SET "tenantName" = %s,
                "tenantPhone" = %s,
                "tenantCompany" = %s,
                "tenantAddress" = %s
            WHERE "tenantId" = %s
            ''',
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
        "roomNumber": row["roomNumber"] or "",
        "occupation": row["occupation"] or "",
        "notes": row["notes"] or "",
        "status": row["status"] or "Active",
        "rent": float(row["rentAmount"] or 0),
        "water": float(row["waterCharge"] or 0),
        "defaulttankWaterCharge": float(row["defaultTankWaterCharge"] or 0),
        "electricityRate": float(row["electricityRate"] or 0),
        "previousMeter": float(row["previousMeter"] or 0),
        "additionalPersonCharge": float(row["additionalPersonCharge"] or 0),
        "securityDeposit": float(row["securityDeposit"] or 0),
        "meterId": row["meterId"] or "",
        "viewToken": row["viewToken"] or "",
        "arrears": 0,
        "statusChangedAt": row["statusChangedAt"] or None,
        "propertyId": row["propertyId"] or None,
    }


def _receipt_row_to_dict(row) -> dict:
    return {
        "Bill": row["billNo"] or "",
        "Date": row["billDate"] or "",
        "Month": row["billMonth"] or "",
        "Tenant": row["tenantName"] or "",
        "TenantId": int(row["tenantId"] or 0),
        "Previous": float(row["previousMeter"] or 0),
        "Current": float(row["currentMeter"] or 0),
        "Units": float(row["units"] or 0),
        "Rent": float(row["rentAmount"] or 0),
        "Additional": float(row["additionalAmount"] or 0),
        "Water": float(row["waterAmount"] or 0),
        "tankWater": float(row["tankWaterAmount"] or 0),
        "Electricity": float(row["electricityAmount"] or 0),
        "Total": float(row["billTotal"] or 0),
        "PDF": row["pdf"] or "",
        "Tenant_Phone": row["tenantPhone"] or "",
        "Tenant_Company": row["tenantCompany"] or "",
        "Tenant_Address": row["tenantAddress"] or "",
        "Rate": float(row["electricityRate"] or 0),
        "Status": row["status"] or "ACTIVE",
        "Archived_Date": row["archivedDate"] or "",
        "Archived_By": row["archivedBy"] or "",
        "Deleted_Date": row["deletedDate"] or "",
        "Additional_Persons": int(row["additionalPersons"] or 0),
        "additionalPersonRate": float(row["additionalPersonRate"] or 0),
        "Receipt_Version": int(row["receiptVersion"] or 0),
        "Generated_By": row["generatedBy"] or "",
        "paymentStatus": row["paymentStatus"] or "PENDING",
        "MaintenanceCharge": float(row["maintenanceCharge"] or 0),
        "MaintenanceDesc": row["maintenanceDesc"] or "",
        "previousArrears": float(row["previousArrears"] or 0),
        "amountReceived": float(row["amountReceived"] or 0),
    }


def delete_tenant(tenantId: int, action: str = "archive", landlord_id: Optional[int] = None):
    action = (action or "archive").strip().lower()

    with get_conn() as conn:
        tenant_row = conn.execute(
            "SELECT * FROM tenants WHERE id = %s",
            (tenantId,)
        ).fetchone()

        if not tenant_row:
            raise ValueError("Tenant not found.")

        if landlord_id is not None and int(tenant_row["landlordId"] or 0) != int(landlord_id):
            raise ValueError("Tenant not found.")

        if action in {"hard", "delete"}:
            conn.execute('DELETE FROM occupants WHERE "tenantId" = %s', (tenantId,))
            conn.execute('DELETE FROM receipts WHERE "tenantId" = %s', (tenantId,))
            conn.execute("DELETE FROM tenants WHERE id = %s", (tenantId,))
            conn.commit()
            return {"tenantId": tenantId, "deleted": True, "archived": False, "restored": False}

        if action == "archive":
            archived_at = datetime.utcnow().strftime("%d %B %Y")
            now_iso = datetime.utcnow().isoformat()

            conn.execute(
                "UPDATE tenants SET status = %s, \"statusChangedAt\" = %s WHERE id = %s",
                ("Archived", now_iso, tenantId),
            )
            receipt_result = conn.execute(
                '''
                UPDATE receipts
                   SET status = 'ARCHIVED',
                       "archivedDate" = CASE
                           WHEN "archivedDate" IS NULL OR "archivedDate" = '' THEN %s
                           ELSE "archivedDate"
                       END
                 WHERE "tenantId" = %s
                ''',
                (archived_at, tenantId),
            )
            conn.commit()

            tenant_after = conn.execute(
                "SELECT * FROM tenants WHERE id = %s", (tenantId,)
            ).fetchone()
            receipt_rows = conn.execute(
                'SELECT * FROM receipts WHERE "tenantId" = %s ORDER BY \"billDate\" DESC, "billNo" DESC',
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
            now_iso = datetime.utcnow().isoformat()
            updated_tenant = conn.execute(
                "UPDATE tenants SET status = %s, \"statusChangedAt\" = %s WHERE id = %s",
                ("Active", now_iso, tenantId),
            )
            if updated_tenant.rowcount == 0:
                raise ValueError("Tenant not found.")

            receipt_result = conn.execute(
                '''
                UPDATE receipts
                   SET status = 'ACTIVE',
                       "archivedDate" = '',
                       "archivedBy" = ''
                 WHERE "tenantId" = %s
                   AND UPPER(COALESCE(status, '')) = 'ARCHIVED'
                ''',
                (tenantId,),
            )
            conn.commit()

            tenant_after = conn.execute(
                "SELECT * FROM tenants WHERE id = %s", (tenantId,)
            ).fetchone()
            receipt_rows = conn.execute(
                'SELECT * FROM receipts WHERE "tenantId" = %s ORDER BY \"billDate\" DESC, "billNo" DESC',
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
            now_iso = datetime.utcnow().isoformat()
            conn.execute(
                "UPDATE tenants SET status = %s, \"statusChangedAt\" = %s WHERE id = %s",
                ("Inactive", now_iso, tenantId)
            )
            conn.commit()
            return {"tenantId": tenantId, "inactive": True, "archived": False, "restored": False}

        raise ValueError(f"Unsupported action: {action}")

def get_occupants(tenantId: int) -> List[dict]:
    with get_conn() as conn:
        rows = conn.execute('SELECT * FROM occupants WHERE "tenantId" = %s', (tenantId,)).fetchall()

    result = []
    for r in rows:
        row = dict(r)
        # Remap camelCase DB columns to lowercase/joined field names the frontend expects
        row["aadhaarfront"] = row.pop("aadhaarFront", "") or ""
        row["aadhaarback"] = row.pop("aadhaarBack", "") or ""
        row["aadhaarcombined"] = row.pop("aadhaarCombined", "") or ""
        row["empfront"] = row.pop("empFront", "") or ""
        row["empback"] = row.pop("empBack", "") or ""
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
                name = %s, mobile = %s, address = %s, "residentSince" = %s,
                status = %s, "aadhaarFront" = %s, "aadhaarBack" = %s,
                "aadhaarCombined" = %s, "empFront" = %s, "empBack" = %s,
                "uploadDate" = %s, "uploadMonth" = %s
            WHERE "occupantUuid" = %s
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
                    "tenantId", "occupantUuid", name, mobile, address, "residentSince",
                    status, "aadhaarFront", "aadhaarBack", "aadhaarCombined",
                    "empFront", "empBack", "uploadDate", "uploadMonth"
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        conn.execute('UPDATE occupants SET status = %s WHERE "occupantUuid" = %s', (status, occupantUuid))
        conn.commit()

def delete_occupant(occupantUuid: str):
    with get_conn() as conn:
        conn.execute('DELETE FROM occupants WHERE "occupantUuid" = %s', (occupantUuid,))
        conn.commit()

