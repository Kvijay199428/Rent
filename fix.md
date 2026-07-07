Yes — below are drop-in SQLite-only replacements that preserve the same service function names your routes, pages, Excel import flow, PDF generation, and public KYC flow already call today, so you can remove CSV persistence without changing the API layer. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/d7d36b18-5c83-42dc-b22e-039ec70c1def/rent.md?AWSAccessKeyId=ASIA2F3EMEYEX7HX7LAZ&Signature=ni6z4cZLJEPH%2BK8KHpvJ2NdzC88%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEHEaCXVzLWVhc3QtMSJIMEYCIQCo6d6XxibEtzY7vMur7KCspKFzKx%2Bv0kRewrvhtCycDAIhAMM4IrERa0pbjUIWsOZE3hbLCRKTp0fKiP91WXuHs9BfKvMECDkQARoMNjk5NzUzMzA5NzA1Igzbik0H7zOEajhn4r8q0AR3ZHS1TYhgldSyKCATI4zU6YILU4ylmMy%2Fx8Ibs%2BmYJV%2BwGrxlgGyr%2BHJdGR2uYSVBH53bxe%2BSoCPBBR3RV71kRYbVYP3JraC1Dvp0YtBRiqemZaxxg5%2FodS212f8Vup%2B7SLBEPAc%2BvdsRjJEUV1Ojullm%2FjOhPqzJfUGiIAZJ2zHvCYgZiao2rI2y4PY5Z9K5ZAhnkNdtu0BVKTlhu6UGT6fqY09tIgwjKTutxUQIn5I6r6L8tc6gW7HrsbcTZF2udLBxwFBeNYHSiScscyEjPl84QnNKZpBoKiRVIBibtfk%2Fmpw%2FwDS2HLZtJlAVU8raXvAqKj7NQ2TeCmkfsK9IfRB%2BjKUGu%2B5gjlNuJ%2BEW5mDL1Pyke3YjSD5uDd8CmbFT%2BXaBfUk9GjP8zQWTVhFthxJyFf9IklGx%2BDEgYTP38iyGWc8WSFd3ksQKnh3pYeNm%2BEwJirExdWw6EzxT1gq%2FHaDIeb1ch4ipivHVuQkB9OSErUw%2BT8hGT8hAkPcqK1SGZ0uDVwM9N3LX7unArfzT%2FCXx5tPfnazaaVwmAekdvp5LUh6HqavCAj%2FLWZAB5S7Veg8s4327cOETxmBSExpnDJGjcbN%2BT9oGeKpeua74RPmW3PA9%2B7rsiznushmP5fSv4WN3ai4BRYvgb3%2F%2BHj7sPkateS2XwMaccvc7TKHj1qj11g4YB%2F3QGRfb%2B3c4K%2FB%2Fk00GSHKcr87Rx8YtfImywLuOQVxBbKtjQ0oDmsg9Y9WkS6%2B11Qmtc04ml81dTWumT%2FOtl7QV%2BChCxrUcvNULMKGiqNIGOpcB3fCoG9FyciJCqz0Ry7MtzDMBOtlOCvAyNmQMojuek7tgTK11YMMdqdsLWlg7WWXxw0InJz6P6WKrhLKzLig2s8LS6T5Zy7s0s7UW%2BQmAT017pUEf7vPvgENwaxneBi93flUeIQjnS1uiyEnpgbXiBjM1FbRP5mFxfHukqI6%2BpYRb7QqUzYdtFOwrDX%2Fn0W7vtTTt1dEYaA%3D%3D&Expires=1783242484)
I’m also including the `getdbstats()` SQL version, because your current backup flow still assumes `receipts.csv` and `tenants.csv` for database stats even though the rest of the app should move to `rent.db`. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/d7d36b18-5c83-42dc-b22e-039ec70c1def/rent.md?AWSAccessKeyId=ASIA2F3EMEYEX7HX7LAZ&Signature=ni6z4cZLJEPH%2BK8KHpvJ2NdzC88%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEHEaCXVzLWVhc3QtMSJIMEYCIQCo6d6XxibEtzY7vMur7KCspKFzKx%2Bv0kRewrvhtCycDAIhAMM4IrERa0pbjUIWsOZE3hbLCRKTp0fKiP91WXuHs9BfKvMECDkQARoMNjk5NzUzMzA5NzA1Igzbik0H7zOEajhn4r8q0AR3ZHS1TYhgldSyKCATI4zU6YILU4ylmMy%2Fx8Ibs%2BmYJV%2BwGrxlgGyr%2BHJdGR2uYSVBH53bxe%2BSoCPBBR3RV71kRYbVYP3JraC1Dvp0YtBRiqemZaxxg5%2FodS212f8Vup%2B7SLBEPAc%2BvdsRjJEUV1Ojullm%2FjOhPqzJfUGiIAZJ2zHvCYgZiao2rI2y4PY5Z9K5ZAhnkNdtu0BVKTlhu6UGT6fqY09tIgwjKTutxUQIn5I6r6L8tc6gW7HrsbcTZF2udLBxwFBeNYHSiScscyEjPl84QnNKZpBoKiRVIBibtfk%2Fmpw%2FwDS2HLZtJlAVU8raXvAqKj7NQ2TeCmkfsK9IfRB%2BjKUGu%2B5gjlNuJ%2BEW5mDL1Pyke3YjSD5uDd8CmbFT%2BXaBfUk9GjP8zQWTVhFthxJyFf9IklGx%2BDEgYTP38iyGWc8WSFd3ksQKnh3pYeNm%2BEwJirExdWw6EzxT1gq%2FHaDIeb1ch4ipivHVuQkB9OSErUw%2BT8hGT8hAkPcqK1SGZ0uDVwM9N3LX7unArfzT%2FCXx5tPfnazaaVwmAekdvp5LUh6HqavCAj%2FLWZAB5S7Veg8s4327cOETxmBSExpnDJGjcbN%2BT9oGeKpeua74RPmW3PA9%2B7rsiznushmP5fSv4WN3ai4BRYvgb3%2F%2BHj7sPkateS2XwMaccvc7TKHj1qj11g4YB%2F3QGRfb%2B3c4K%2FB%2Fk00GSHKcr87Rx8YtfImywLuOQVxBbKtjQ0oDmsg9Y9WkS6%2B11Qmtc04ml81dTWumT%2FOtl7QV%2BChCxrUcvNULMKGiqNIGOpcB3fCoG9FyciJCqz0Ry7MtzDMBOtlOCvAyNmQMojuek7tgTK11YMMdqdsLWlg7WWXxw0InJz6P6WKrhLKzLig2s8LS6T5Zy7s0s7UW%2BQmAT017pUEf7vPvgENwaxneBi93flUeIQjnS1uiyEnpgbXiBjM1FbRP5mFxfHukqI6%2BpYRb7QqUzYdtFOwrDX%2Fn0W7vtTTt1dEYaA%3D%3D&Expires=1783242484)

## Service replacements

Replace `app/services/tenantservice.py` with this SQLite-only version, because the app currently depends on `loadtenants()`, `addtenant()`, `updatetenant()`, `deletetenant()`, `getoccupants()`, `saveoccupant()`, `updateoccupantstatus()`, and `deleteoccupant()` throughout tenant pages and public KYC endpoints. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/d7d36b18-5c83-42dc-b22e-039ec70c1def/rent.md?AWSAccessKeyId=ASIA2F3EMEYEX7HX7LAZ&Signature=ni6z4cZLJEPH%2BK8KHpvJ2NdzC88%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEHEaCXVzLWVhc3QtMSJIMEYCIQCo6d6XxibEtzY7vMur7KCspKFzKx%2Bv0kRewrvhtCycDAIhAMM4IrERa0pbjUIWsOZE3hbLCRKTp0fKiP91WXuHs9BfKvMECDkQARoMNjk5NzUzMzA5NzA1Igzbik0H7zOEajhn4r8q0AR3ZHS1TYhgldSyKCATI4zU6YILU4ylmMy%2Fx8Ibs%2BmYJV%2BwGrxlgGyr%2BHJdGR2uYSVBH53bxe%2BSoCPBBR3RV71kRYbVYP3JraC1Dvp0YtBRiqemZaxxg5%2FodS212f8Vup%2B7SLBEPAc%2BvdsRjJEUV1Ojullm%2FjOhPqzJfUGiIAZJ2zHvCYgZiao2rI2y4PY5Z9K5ZAhnkNdtu0BVKTlhu6UGT6fqY09tIgwjKTutxUQIn5I6r6L8tc6gW7HrsbcTZF2udLBxwFBeNYHSiScscyEjPl84QnNKZpBoKiRVIBibtfk%2Fmpw%2FwDS2HLZtJlAVU8raXvAqKj7NQ2TeCmkfsK9IfRB%2BjKUGu%2B5gjlNuJ%2BEW5mDL1Pyke3YjSD5uDd8CmbFT%2BXaBfUk9GjP8zQWTVhFthxJyFf9IklGx%2BDEgYTP38iyGWc8WSFd3ksQKnh3pYeNm%2BEwJirExdWw6EzxT1gq%2FHaDIeb1ch4ipivHVuQkB9OSErUw%2BT8hGT8hAkPcqK1SGZ0uDVwM9N3LX7unArfzT%2FCXx5tPfnazaaVwmAekdvp5LUh6HqavCAj%2FLWZAB5S7Veg8s4327cOETxmBSExpnDJGjcbN%2BT9oGeKpeua74RPmW3PA9%2B7rsiznushmP5fSv4WN3ai4BRYvgb3%2F%2BHj7sPkateS2XwMaccvc7TKHj1qj11g4YB%2F3QGRfb%2B3c4K%2FB%2Fk00GSHKcr87Rx8YtfImywLuOQVxBbKtjQ0oDmsg9Y9WkS6%2B11Qmtc04ml81dTWumT%2FOtl7QV%2BChCxrUcvNULMKGiqNIGOpcB3fCoG9FyciJCqz0Ry7MtzDMBOtlOCvAyNmQMojuek7tgTK11YMMdqdsLWlg7WWXxw0InJz6P6WKrhLKzLig2s8LS6T5Zy7s0s7UW%2BQmAT017pUEf7vPvgENwaxneBi93flUeIQjnS1uiyEnpgbXiBjM1FbRP5mFxfHukqI6%2BpYRb7QqUzYdtFOwrDX%2Fn0W7vtTTt1dEYaA%3D%3D&Expires=1783242484)

```python
# app/services/tenantservice.py
from __future__ import annotations

from typing import List, Dict, Any
from app.core.db import get_conn
from app.models.tenant import Tenant


def _safe_float(val, default=0.0) -> float:
    try:
        return float(str(val).strip() or default)
    except Exception:
        return default


def _safe_int(val, default=0) -> int:
    try:
        return int(float(str(val).strip() or default))
    except Exception:
        return default


def _row_to_tenant(row) -> Tenant:
    return Tenant(
        id=row["id"],
        name=row["name"] or "",
        company=row["company"] or "",
        phone=row["phone"] or "",
        email=row["email"] or "",
        address=row["address"] or "",
        roomnumber=row["roomnumber"] or "",
        occupation=row["occupation"] or "",
        notes=row["notes"] or "",
        status=row["status"] or "Active",
        rent=_safe_float(row["rent"]),
        water=_safe_float(row["water"]),
        defaulttankwatercharge=_safe_float(row["defaulttankwatercharge"]),
        electricityrate=_safe_float(row["electricityrate"]),
        previousmeter=_safe_float(row["previousmeter"]),
        additionalpersoncharge=_safe_float(row["additionalpersoncharge"]),
        securitydeposit=_safe_float(row["securitydeposit"]),
        meterid=row["meterid"] or "",
        viewtoken=row["viewtoken"] or "",
        tenantpin=row["tenantpin"] or "1234",
    )


def _tenant_params(t: Tenant):
    return (
        t.id,
        t.name,
        t.company or "",
        t.phone or "",
        t.email or "",
        t.address or "",
        t.roomnumber or "",
        t.occupation or "",
        t.notes or "",
        t.status or "Active",
        float(t.rent or 0),
        float(t.water or 0),
        float(t.electricityrate or 0),
        float(t.previousmeter or 0),
        float(t.additionalpersoncharge or 0),
        float(t.securitydeposit or 0),
        float(t.defaulttankwatercharge or 0),
        t.meterid or "",
        getattr(t, "viewtoken", "") or "",
        getattr(t, "tenantpin", "1234") or "1234",
    )


def loadtenants() -> List[Tenant]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM tenants ORDER BY id ASC").fetchall()
    return [_row_to_tenant(r) for r in rows]


def savealltenants(tenantslist: List[Tenant]) -> List[Tenant]:
    with get_conn() as conn:
        conn.execute("DELETE FROM tenants")
        for t in tenantslist:
            conn.execute(
                """
                INSERT INTO tenants (
                    id, name, company, phone, email, address, roomnumber,
                    occupation, notes, status, rent, water, electricityrate,
                    previousmeter, additionalpersoncharge, securitydeposit,
                    defaulttankwatercharge, meterid, viewtoken, tenantpin
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _tenant_params(t),
            )
        conn.commit()
    return tenantslist


def addtenant(t: Tenant) -> Tenant:
    with get_conn() as conn:
        nextid = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM tenants").fetchone()[0]
        t.id = int(nextid)
        if not t.meterid:
            t.meterid = f"MTR-F-{str(t.id).zfill(2)}"

        conn.execute(
            """
            INSERT INTO tenants (
                id, name, company, phone, email, address, roomnumber,
                occupation, notes, status, rent, water, electricityrate,
                previousmeter, additionalpersoncharge, securitydeposit,
                defaulttankwatercharge, meterid, viewtoken, tenantpin
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _tenant_params(t),
        )
        conn.commit()
    return t


def updatetenant(t: Tenant) -> Tenant:
    if t.id is None:
        raise ValueError("Tenant id is required for update.")

    if not t.meterid:
        t.meterid = f"MTR-F-{str(t.id).zfill(2)}"

    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM tenants WHERE id = ?", (t.id,)).fetchone()
        if exists:
            conn.execute(
                """
                UPDATE tenants SET
                    name = ?, company = ?, phone = ?, email = ?, address = ?,
                    roomnumber = ?, occupation = ?, notes = ?, status = ?,
                    rent = ?, water = ?, electricityrate = ?, previousmeter = ?,
                    additionalpersoncharge = ?, securitydeposit = ?,
                    defaulttankwatercharge = ?, meterid = ?, viewtoken = ?, tenantpin = ?
                WHERE id = ?
                """,
                (
                    t.name,
                    t.company or "",
                    t.phone or "",
                    t.email or "",
                    t.address or "",
                    t.roomnumber or "",
                    t.occupation or "",
                    t.notes or "",
                    t.status or "Active",
                    float(t.rent or 0),
                    float(t.water or 0),
                    float(t.electricityrate or 0),
                    float(t.previousmeter or 0),
                    float(t.additionalpersoncharge or 0),
                    float(t.securitydeposit or 0),
                    float(t.defaulttankwatercharge or 0),
                    t.meterid or "",
                    getattr(t, "viewtoken", "") or "",
                    getattr(t, "tenantpin", "1234") or "1234",
                    t.id,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO tenants (
                    id, name, company, phone, email, address, roomnumber,
                    occupation, notes, status, rent, water, electricityrate,
                    previousmeter, additionalpersoncharge, securitydeposit,
                    defaulttankwatercharge, meterid, viewtoken, tenantpin
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _tenant_params(t),
            )
        conn.commit()
    return t


def getoccupants(tenantid: int) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT tenant_id, occupant_uuid, name, mobile, status,
                   aadhaar_front, aadhaar_back, aadhaar_combined,
                   emp_front, emp_back, uploaddate, uploadmonth
            FROM occupants
            WHERE tenant_id = ?
            ORDER BY rowid DESC
            """,
            (tenantid,),
        ).fetchall()

    results = []
    for r in rows:
        results.append(
            {
                "Tenant ID": r["tenant_id"],
                "Occupant UUID": r["occupant_uuid"],
                "Name": r["name"] or "",
                "Mobile": r["mobile"] or "",
                "Status": r["status"] or "Active",
                "Aadhaar Front": r["aadhaar_front"] or "",
                "Aadhaar Back": r["aadhaar_back"] or "",
                "Aadhaar Combined": r["aadhaar_combined"] or "",
                "Emp Front": r["emp_front"] or "",
                "Emp Back": r["emp_back"] or "",
                "UploadDate": r["uploaddate"] or "",
                "UploadMonth": r["uploadmonth"] or "Legacy Uploads",
            }
        )
    return results


def saveoccupant(tenantid: int, occdata: Dict[str, Any]):
    occupantuuid = occdata.get("Occupant UUID") or occdata.get("uuid")
    if not occupantuuid:
        raise ValueError("Occupant UUID is required.")

    payload = {
        "tenant_id": tenantid,
        "occupant_uuid": occupantuuid,
        "name": occdata.get("Name", "") or "",
        "mobile": occdata.get("Mobile", "") or "",
        "status": occdata.get("Status", "Active") or "Active",
        "aadhaar_front": occdata.get("Aadhaar Front", "") or "",
        "aadhaar_back": occdata.get("Aadhaar Back", "") or "",
        "aadhaar_combined": occdata.get("Aadhaar Combined", "") or "",
        "emp_front": occdata.get("Emp Front", "") or "",
        "emp_back": occdata.get("Emp Back", "") or "",
        "uploaddate": occdata.get("UploadDate", "") or "",
        "uploadmonth": occdata.get("UploadMonth", "Legacy Uploads") or "Legacy Uploads",
    }

    with get_conn() as conn:
        exists = conn.execute(
            "SELECT 1 FROM occupants WHERE occupant_uuid = ?",
            (occupantuuid,),
        ).fetchone()

        if exists:
            conn.execute(
                """
                UPDATE occupants SET
                    tenant_id = ?, name = ?, mobile = ?, status = ?,
                    aadhaar_front = ?, aadhaar_back = ?, aadhaar_combined = ?,
                    emp_front = ?, emp_back = ?, uploaddate = ?, uploadmonth = ?
                WHERE occupant_uuid = ?
                """,
                (
                    payload["tenant_id"],
                    payload["name"],
                    payload["mobile"],
                    payload["status"],
                    payload["aadhaar_front"],
                    payload["aadhaar_back"],
                    payload["aadhaar_combined"],
                    payload["emp_front"],
                    payload["emp_back"],
                    payload["uploaddate"],
                    payload["uploadmonth"],
                    payload["occupant_uuid"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO occupants (
                    tenant_id, occupant_uuid, name, mobile, status,
                    aadhaar_front, aadhaar_back, aadhaar_combined,
                    emp_front, emp_back, uploaddate, uploadmonth
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["tenant_id"],
                    payload["occupant_uuid"],
                    payload["name"],
                    payload["mobile"],
                    payload["status"],
                    payload["aadhaar_front"],
                    payload["aadhaar_back"],
                    payload["aadhaar_combined"],
                    payload["emp_front"],
                    payload["emp_back"],
                    payload["uploaddate"],
                    payload["uploadmonth"],
                ),
            )
        conn.commit()


def updateoccupantstatus(occupantuuid: str, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE occupants SET status = ? WHERE occupant_uuid = ?",
            (status, occupantuuid),
        )
        conn.commit()


def deleteoccupant(occupantuuid: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM occupants WHERE occupant_uuid = ?", (occupantuuid,))
        conn.commit()


def deletetenant(tenantid: int, action: str = "archive"):
    tenants = loadtenants()
    targettenant = next((t for t in tenants if t.id == tenantid), None)
    if not targettenant:
        return

    from app.services.billingservice import getallreceipts, archivebill, deletebill

    tenantreceipts = [r for r in getallreceipts() if r.get("Tenant") == targettenant.name]

    if action == "archive":
        targettenant.status = "Inactive"
        updatetenant(targettenant)
        for r in tenantreceipts:
            if r.get("Status") != "ARCHIVED":
                try:
                    archivebill(r["Bill"])
                except Exception:
                    pass
        return

    if action != "delete":
        raise ValueError("Invalid delete action.")

    for r in tenantreceipts:
        if r.get("Status") != "ARCHIVED":
            try:
                archivebill(r["Bill"])
            except Exception:
                pass
        try:
            deletebill(r["Bill"])
        except Exception:
            pass

    with get_conn() as conn:
        conn.execute("DELETE FROM occupants WHERE tenant_id = ?", (tenantid,))
        conn.execute("DELETE FROM tenants WHERE id = ?", (tenantid,))
        conn.commit()
```

Replace `app/services/billingservice.py` with this SQLite-only version, because billing pages, payment updates, archive/restore flows, dashboard stats, PDF generation, WhatsApp links, and Excel import/export all rely on these same billing service functions and their current receipt-dict shape. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/d7d36b18-5c83-42dc-b22e-039ec70c1def/rent.md?AWSAccessKeyId=ASIA2F3EMEYEX7HX7LAZ&Signature=ni6z4cZLJEPH%2BK8KHpvJ2NdzC88%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEHEaCXVzLWVhc3QtMSJIMEYCIQCo6d6XxibEtzY7vMur7KCspKFzKx%2Bv0kRewrvhtCycDAIhAMM4IrERa0pbjUIWsOZE3hbLCRKTp0fKiP91WXuHs9BfKvMECDkQARoMNjk5NzUzMzA5NzA1Igzbik0H7zOEajhn4r8q0AR3ZHS1TYhgldSyKCATI4zU6YILU4ylmMy%2Fx8Ibs%2BmYJV%2BwGrxlgGyr%2BHJdGR2uYSVBH53bxe%2BSoCPBBR3RV71kRYbVYP3JraC1Dvp0YtBRiqemZaxxg5%2FodS212f8Vup%2B7SLBEPAc%2BvdsRjJEUV1Ojullm%2FjOhPqzJfUGiIAZJ2zHvCYgZiao2rI2y4PY5Z9K5ZAhnkNdtu0BVKTlhu6UGT6fqY09tIgwjKTutxUQIn5I6r6L8tc6gW7HrsbcTZF2udLBxwFBeNYHSiScscyEjPl84QnNKZpBoKiRVIBibtfk%2Fmpw%2FwDS2HLZtJlAVU8raXvAqKj7NQ2TeCmkfsK9IfRB%2BjKUGu%2B5gjlNuJ%2BEW5mDL1Pyke3YjSD5uDd8CmbFT%2BXaBfUk9GjP8zQWTVhFthxJyFf9IklGx%2BDEgYTP38iyGWc8WSFd3ksQKnh3pYeNm%2BEwJirExdWw6EzxT1gq%2FHaDIeb1ch4ipivHVuQkB9OSErUw%2BT8hGT8hAkPcqK1SGZ0uDVwM9N3LX7unArfzT%2FCXx5tPfnazaaVwmAekdvp5LUh6HqavCAj%2FLWZAB5S7Veg8s4327cOETxmBSExpnDJGjcbN%2BT9oGeKpeua74RPmW3PA9%2B7rsiznushmP5fSv4WN3ai4BRYvgb3%2F%2BHj7sPkateS2XwMaccvc7TKHj1qj11g4YB%2F3QGRfb%2B3c4K%2FB%2Fk00GSHKcr87Rx8YtfImywLuOQVxBbKtjQ0oDmsg9Y9WkS6%2B11Qmtc04ml81dTWumT%2FOtl7QV%2BChCxrUcvNULMKGiqNIGOpcB3fCoG9FyciJCqz0Ry7MtzDMBOtlOCvAyNmQMojuek7tgTK11YMMdqdsLWlg7WWXxw0InJz6P6WKrhLKzLig2s8LS6T5Zy7s0s7UW%2BQmAT017pUEf7vPvgENwaxneBi93flUeIQjnS1uiyEnpgbXiBjM1FbRP5mFxfHukqI6%2BpYRb7QqUzYdtFOwrDX%2Fn0W7vtTTt1dEYaA%3D%3D&Expires=1783242484)
This version also keeps `saveallreceipts()` because your Excel import flow currently builds an in-memory receipt list and then calls that function to persist the final result. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/d7d36b18-5c83-42dc-b22e-039ec70c1def/rent.md?AWSAccessKeyId=ASIA2F3EMEYEX7HX7LAZ&Signature=ni6z4cZLJEPH%2BK8KHpvJ2NdzC88%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEHEaCXVzLWVhc3QtMSJIMEYCIQCo6d6XxibEtzY7vMur7KCspKFzKx%2Bv0kRewrvhtCycDAIhAMM4IrERa0pbjUIWsOZE3hbLCRKTp0fKiP91WXuHs9BfKvMECDkQARoMNjk5NzUzMzA5NzA1Igzbik0H7zOEajhn4r8q0AR3ZHS1TYhgldSyKCATI4zU6YILU4ylmMy%2Fx8Ibs%2BmYJV%2BwGrxlgGyr%2BHJdGR2uYSVBH53bxe%2BSoCPBBR3RV71kRYbVYP3JraC1Dvp0YtBRiqemZaxxg5%2FodS212f8Vup%2B7SLBEPAc%2BvdsRjJEUV1Ojullm%2FjOhPqzJfUGiIAZJ2zHvCYgZiao2rI2y4PY5Z9K5ZAhnkNdtu0BVKTlhu6UGT6fqY09tIgwjKTutxUQIn5I6r6L8tc6gW7HrsbcTZF2udLBxwFBeNYHSiScscyEjPl84QnNKZpBoKiRVIBibtfk%2Fmpw%2FwDS2HLZtJlAVU8raXvAqKj7NQ2TeCmkfsK9IfRB%2BjKUGu%2B5gjlNuJ%2BEW5mDL1Pyke3YjSD5uDd8CmbFT%2BXaBfUk9GjP8zQWTVhFthxJyFf9IklGx%2BDEgYTP38iyGWc8WSFd3ksQKnh3pYeNm%2BEwJirExdWw6EzxT1gq%2FHaDIeb1ch4ipivHVuQkB9OSErUw%2BT8hGT8hAkPcqK1SGZ0uDVwM9N3LX7unArfzT%2FCXx5tPfnazaaVwmAekdvp5LUh6HqavCAj%2FLWZAB5S7Veg8s4327cOETxmBSExpnDJGjcbN%2BT9oGeKpeua74RPmW3PA9%2B7rsiznushmP5fSv4WN3ai4BRYvgb3%2F%2BHj7sPkateS2XwMaccvc7TKHj1qj11g4YB%2F3QGRfb%2B3c4K%2FB%2Fk00GSHKcr87Rx8YtfImywLuOQVxBbKtjQ0oDmsg9Y9WkS6%2B11Qmtc04ml81dTWumT%2FOtl7QV%2BChCxrUcvNULMKGiqNIGOpcB3fCoG9FyciJCqz0Ry7MtzDMBOtlOCvAyNmQMojuek7tgTK11YMMdqdsLWlg7WWXxw0InJz6P6WKrhLKzLig2s8LS6T5Zy7s0s7UW%2BQmAT017pUEf7vPvgENwaxneBi93flUeIQjnS1uiyEnpgbXiBjM1FbRP5mFxfHukqI6%2BpYRb7QqUzYdtFOwrDX%2Fn0W7vtTTt1dEYaA%3D%3D&Expires=1783242484)

```python
# app/services/billingservice.py
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Any

from app.core.configservice import config
from app.core.db import get_conn
from app.models.tenant import Tenant
from app.services.tenantservice import loadtenants, updatetenant


MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def _safe_float(val, default=0.0) -> float:
    try:
        return float(str(val).strip() or default)
    except Exception:
        return default


def _safe_int(val, default=0) -> int:
    try:
        return int(float(str(val).strip() or default))
    except Exception:
        return default


def _save_billing_config(data: dict):
    if hasattr(config, "savebilling"):
        config.savebilling(data)
    else:
        config.save("billing", data)


def _receipt_row_to_dict(row) -> Dict[str, Any]:
    return {
        "Bill": row["billno"],
        "Date": row["date"],
        "Month": row["month"],
        "Tenant": row["tenant"],
        "Previous": row["previous"],
        "Current": row["current"],
        "Units": row["units"],
        "Rent": row["rent"],
        "Additional": row["additional"],
        "Water": row["water"],
        "TankWater": row["tankwater"],
        "Electricity": row["electricity"],
        "Total": row["total"],
        "PDF": row["pdf"] or "",
        "TenantPhone": row["tenantphone"] or "",
        "TenantCompany": row["tenantcompany"] or "",
        "TenantAddress": row["tenantaddress"] or "",
        "Rate": row["rate"],
        "Status": row["status"] or "ACTIVE",
        "ArchivedDate": row["archiveddate"] or "",
        "ArchivedBy": row["archivedby"] or "",
        "DeletedDate": row["deleteddate"] or "",
        "AdditionalPersons": row["additionalpersons"],
        "AdditionalPersonRate": row["additionalpersonrate"],
        "ReceiptVersion": row["receiptversion"],
        "GeneratedBy": row["generatedby"] or "Admin",
        "PaymentStatus": row["paymentstatus"] or "PENDING",
        "MaintenanceCharge": row["maintenancecharge"],
        "MaintenanceDesc": row["maintenancedesc"] or "",
        "PreviousArrears": row["previousarrears"],
        "AmountReceived": row["amountreceived"],
    }


def _receipt_insert_params(data: Dict[str, Any]):
    return (
        data.get("Bill", ""),
        data.get("Date", ""),
        data.get("Month", ""),
        data.get("Tenant", ""),
        _safe_float(data.get("Previous")),
        _safe_float(data.get("Current")),
        _safe_float(data.get("Units")),
        _safe_float(data.get("Rent")),
        _safe_float(data.get("Additional")),
        _safe_float(data.get("Water")),
        _safe_float(data.get("TankWater")),
        _safe_float(data.get("Electricity")),
        _safe_float(data.get("Total")),
        data.get("PDF", ""),
        data.get("TenantPhone", ""),
        data.get("TenantCompany", ""),
        data.get("TenantAddress", ""),
        _safe_float(data.get("Rate")),
        data.get("Status", "ACTIVE"),
        data.get("ArchivedDate", ""),
        data.get("ArchivedBy", ""),
        data.get("DeletedDate", ""),
        _safe_int(data.get("AdditionalPersons")),
        _safe_float(data.get("AdditionalPersonRate")),
        _safe_int(data.get("ReceiptVersion"), 8),
        data.get("GeneratedBy", "Admin"),
        data.get("PaymentStatus", "PENDING"),
        _safe_float(data.get("MaintenanceCharge")),
        data.get("MaintenanceDesc", ""),
        _safe_float(data.get("PreviousArrears")),
        _safe_float(data.get("AmountReceived")),
    )


def getallreceipts() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM receipts ORDER BY rowid ASC").fetchall()
    return [_receipt_row_to_dict(r) for r in rows]


def saveallreceipts(receiptslist: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        conn.execute("DELETE FROM receipts")
        for r in receiptslist:
            conn.execute(
                """
                INSERT INTO receipts (
                    billno, date, month, tenant, previous, current, units,
                    rent, additional, water, tankwater, electricity, total,
                    pdf, tenantphone, tenantcompany, tenantaddress, rate,
                    status, archiveddate, archivedby, deleteddate,
                    additionalpersons, additionalpersonrate, receiptversion,
                    generatedby, paymentstatus, maintenancecharge,
                    maintenancedesc, previousarrears, amountreceived
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _receipt_insert_params(r),
            )
        conn.commit()
    return receiptslist


def getreceipt(billno: str) -> Dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE billno = ?", (billno,)).fetchone()
    return _receipt_row_to_dict(row) if row else None


def getbilldetails(billno: str) -> Dict[str, Any] | None:
    return getreceipt(billno)


def getbillingmonths() -> List[str]:
    months = {r.get("Month", "") for r in getallreceipts() if r.get("Month")}
    def sort_key(label: str):
        try:
            dt = datetime.strptime(label, "%B %Y")
            return (dt.year, dt.month)
        except Exception:
            return (0, 0)
    return sorted(months, key=sort_key, reverse=True)


def calculatecharges(
    currentreading: float,
    additionalpersons: int,
    prevreading: float | None = None,
    rent: float | None = None,
    water: float | None = None,
    tankwater: float = 0.0,
    maintenancecharge: float = 0.0,
    rate: float | None = None,
    addpersoncharge: float | None = None,
) -> Dict[str, Any]:
    billingconf = config.get("billing") or {}

    prev = _safe_float(
        billingconf.get("previousmeterreading", 0.0) if prevreading is None else prevreading
    )
    rent_amt = _safe_float(billingconf.get("rent", 0.0) if rent is None else rent)
    water_amt = _safe_float(billingconf.get("water", 0.0) if water is None else water)
    rate_amt = _safe_float(
        billingconf.get("electricityrate", 0.0) if rate is None else rate
    )
    add_rate = _safe_float(
        billingconf.get("additionalpersoncharge", 0.0)
        if addpersoncharge is None else addpersoncharge
    )

    curr = _safe_float(currentreading)
    add_count = _safe_int(additionalpersons)
    tank = _safe_float(tankwater)
    maintenance = _safe_float(maintenancecharge)

    units = max(curr - prev, 0.0)
    electricity = units * rate_amt
    additional = add_count * add_rate
    total = rent_amt + water_amt + electricity + additional + tank + maintenance

    return {
        "previous": round(prev, 2),
        "current": round(curr, 2),
        "units": round(units, 2),
        "rent": round(rent_amt, 2),
        "additional": round(additional, 2),
        "water": round(water_amt, 2),
        "tankwater": round(tank, 2),
        "maintenancecharge": round(maintenance, 2),
        "electricity": round(electricity, 2),
        "total": round(total, 2),
        "rate": round(rate_amt, 2),
    }


def resolvepaymentstate(
    currenttotal: float,
    previousarrears: float = 0.0,
    amountreceived: float | None = None,
    paymentstatus: str = "PENDING",
) -> Dict[str, Any]:
    grandtotal = round(_safe_float(currenttotal) + _safe_float(previousarrears), 2)
    received = round(_safe_float(amountreceived, 0.0), 2)

    if received <= 0:
        return {"paymentstatus": "PENDING", "amountreceived": 0.0}

    if abs(received - grandtotal) < 0.01:
        return {"paymentstatus": "PAID", "amountreceived": grandtotal}

    if received > grandtotal:
        return {"paymentstatus": "ADVANCE", "amountreceived": received}

    return {"paymentstatus": "PARTIAL", "amountreceived": received}


def createbill(
    tenantname,
    month,
    currentreading,
    additionalpersons,
    tankwater,
    maintenancecharge,
    maintenancedesc,
    previousarrears=0.0,
    amountreceived=None,
    paymentstatus="PENDING",
):
    receipts = getallreceipts()
    for r in receipts:
        if r.get("Tenant") == tenantname and r.get("Month") == month and r.get("Status", "ACTIVE") == "ACTIVE":
            raise ValueError(
                f"A receipt for {tenantname} for {month} already exists (Bill {r['Bill']}). "
                "Please edit the existing bill instead."
            )

    tenants = loadtenants()
    tenantdetails = next((t for t in tenants if t.name == tenantname), None)
    if not tenantdetails:
        raise ValueError("Tenant not found.")

    charges = calculatecharges(
        currentreading=currentreading,
        additionalpersons=additionalpersons,
        prevreading=tenantdetails.previousmeter,
        rent=tenantdetails.rent,
        water=tenantdetails.water,
        tankwater=tankwater,
        maintenancecharge=maintenancecharge,
        rate=tenantdetails.electricityrate,
        addpersoncharge=tenantdetails.additionalpersoncharge,
    )

    tenantreceipts = [r for r in receipts if r.get("Tenant") == tenantname]
    maxseq = 0
    for r in tenantreceipts:
        try:
            billstr = r.get("Bill", "")
            seq = int(billstr.split("-")[-1]) if "-" in billstr else int(billstr)
            maxseq = max(maxseq, seq)
        except Exception:
            pass

    billno = f"T{tenantdetails.id}-{str(maxseq + 1).zfill(3)}"
    datestr = datetime.now().strftime("%d %b %Y")
    pdffilename = f"{billno}.pdf"

    grandtotal = round(charges["total"] + _safe_float(previousarrears), 2)
    if amountreceived is None:
        amountreceived = grandtotal if str(paymentstatus).upper() == "PAID" else 0.0

    resolved = resolvepaymentstate(
        currenttotal=charges["total"],
        previousarrears=previousarrears,
        amountreceived=amountreceived,
        paymentstatus=paymentstatus,
    )

    datadict = {
        "Bill": billno,
        "Date": datestr,
        "Month": month,
        "Tenant": tenantname,
        "Previous": charges["previous"],
        "Current": _safe_float(currentreading),
        "Units": charges["units"],
        "Rent": charges["rent"],
        "Additional": charges["additional"],
        "Water": charges["water"],
        "TankWater": charges["tankwater"],
        "Electricity": charges["electricity"],
        "Total": charges["total"],
        "PDF": pdffilename,
        "TenantPhone": tenantdetails.phone or "",
        "TenantCompany": tenantdetails.company or "",
        "TenantAddress": tenantdetails.address or "",
        "Rate": charges["rate"],
        "Status": "ACTIVE",
        "ArchivedDate": "",
        "ArchivedBy": "",
        "DeletedDate": "",
        "AdditionalPersons": _safe_int(additionalpersons),
        "AdditionalPersonRate": _safe_float(tenantdetails.additionalpersoncharge),
        "ReceiptVersion": 8,
        "GeneratedBy": "Admin",
        "PaymentStatus": resolved["paymentstatus"],
        "MaintenanceCharge": _safe_float(maintenancecharge),
        "MaintenanceDesc": maintenancedesc or "",
        "PreviousArrears": _safe_float(previousarrears),
        "AmountReceived": resolved["amountreceived"],
    }

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO receipts (
                billno, date, month, tenant, previous, current, units,
                rent, additional, water, tankwater, electricity, total,
                pdf, tenantphone, tenantcompany, tenantaddress, rate,
                status, archiveddate, archivedby, deleteddate,
                additionalpersons, additionalpersonrate, receiptversion,
                generatedby, paymentstatus, maintenancecharge,
                maintenancedesc, previousarrears, amountreceived
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _receipt_insert_params(datadict),
        )
        conn.commit()

    tenantdetails.previousmeter = _safe_float(currentreading)
    updatetenant(tenantdetails)

    billingconf = config.get("billing") or {}
    nextbill = _safe_int(billingconf.get("nextbillnumber", 1), 1) + 1
    _save_billing_config({
        "previousmeterreading": _safe_float(currentreading),
        "nextbillnumber": nextbill,
    })

    return datadict


def updatebill(
    billno,
    tenantname,
    month,
    currentreading,
    additionalpersons,
    tankwater,
    maintenancecharge,
    maintenancedesc,
    previousarrears=0.0,
    amountreceived=None,
    paymentstatus="PENDING",
):
    receipt = getreceipt(billno)
    if not receipt:
        raise ValueError("Receipt not found.")

    tenants = loadtenants()
    tenantdetails = next((t for t in tenants if t.name == tenantname), None)

    prevreading = _safe_float(receipt.get("Previous"))
    snaprent = _safe_float(receipt.get("Rent"))
    snapwater = _safe_float(receipt.get("Water"))
    snaprate = _safe_float(receipt.get("Rate"))
    snapaddrate = _safe_float(receipt.get("AdditionalPersonRate"))
    if snapaddrate == 0.0 and tenantdetails:
        snapaddrate = _safe_float(tenantdetails.additionalpersoncharge)

    charges = calculatecharges(
        currentreading=currentreading,
        additionalpersons=additionalpersons,
        prevreading=prevreading,
        rent=snaprent,
        water=snapwater,
        tankwater=tankwater,
        maintenancecharge=maintenancecharge,
        rate=snaprate,
        addpersoncharge=snapaddrate,
    )

    grandtotal = round(charges["total"] + _safe_float(previousarrears), 2)
    if amountreceived is None:
        existing_recv = _safe_float(receipt.get("AmountReceived"))
        amountreceived = existing_recv
        if str(paymentstatus).upper() == "PAID" and existing_recv <= 0:
            amountreceived = grandtotal

    resolved = resolvepaymentstate(
        currenttotal=charges["total"],
        previousarrears=previousarrears,
        amountreceived=amountreceived,
        paymentstatus=paymentstatus,
    )

    updateddict = {
        "Bill": billno,
        "Date": receipt.get("Date", datetime.now().strftime("%d %b %Y")),
        "Month": month,
        "Tenant": tenantname,
        "Previous": prevreading,
        "Current": _safe_float(currentreading),
        "Units": charges["units"],
        "Rent": charges["rent"],
        "Additional": charges["additional"],
        "Water": charges["water"],
        "TankWater": charges["tankwater"],
        "Electricity": charges["electricity"],
        "Total": charges["total"],
        "PDF": receipt.get("PDF", f"{billno}.pdf"),
        "TenantPhone": receipt.get("TenantPhone", ""),
        "TenantCompany": receipt.get("TenantCompany", ""),
        "TenantAddress": receipt.get("TenantAddress", ""),
        "Rate": charges["rate"],
        "Status": receipt.get("Status", "ACTIVE"),
        "ArchivedDate": receipt.get("ArchivedDate", ""),
        "ArchivedBy": receipt.get("ArchivedBy", ""),
        "DeletedDate": receipt.get("DeletedDate", ""),
        "AdditionalPersons": _safe_int(additionalpersons),
        "AdditionalPersonRate": snapaddrate,
        "ReceiptVersion": _safe_int(receipt.get("ReceiptVersion"), 8),
        "GeneratedBy": receipt.get("GeneratedBy", "Admin"),
        "PaymentStatus": resolved["paymentstatus"],
        "MaintenanceCharge": _safe_float(maintenancecharge),
        "MaintenanceDesc": maintenancedesc or "",
        "PreviousArrears": _safe_float(previousarrears),
        "AmountReceived": resolved["amountreceived"],
    }

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE receipts SET
                date = ?, month = ?, tenant = ?, previous = ?, current = ?, units = ?,
                rent = ?, additional = ?, water = ?, tankwater = ?, electricity = ?, total = ?,
                pdf = ?, tenantphone = ?, tenantcompany = ?, tenantaddress = ?, rate = ?,
                status = ?, archiveddate = ?, archivedby = ?, deleteddate = ?,
                additionalpersons = ?, additionalpersonrate = ?, receiptversion = ?,
                generatedby = ?, paymentstatus = ?, maintenancecharge = ?,
                maintenancedesc = ?, previousarrears = ?, amountreceived = ?
            WHERE billno = ?
            """,
            (
                updateddict["Date"],
                updateddict["Month"],
                updateddict["Tenant"],
                updateddict["Previous"],
                updateddict["Current"],
                updateddict["Units"],
                updateddict["Rent"],
                updateddict["Additional"],
                updateddict["Water"],
                updateddict["TankWater"],
                updateddict["Electricity"],
                updateddict["Total"],
                updateddict["PDF"],
                updateddict["TenantPhone"],
                updateddict["TenantCompany"],
                updateddict["TenantAddress"],
                updateddict["Rate"],
                updateddict["Status"],
                updateddict["ArchivedDate"],
                updateddict["ArchivedBy"],
                updateddict["DeletedDate"],
                updateddict["AdditionalPersons"],
                updateddict["AdditionalPersonRate"],
                updateddict["ReceiptVersion"],
                updateddict["GeneratedBy"],
                updateddict["PaymentStatus"],
                updateddict["MaintenanceCharge"],
                updateddict["MaintenanceDesc"],
                updateddict["PreviousArrears"],
                updateddict["AmountReceived"],
                billno,
            ),
        )
        conn.commit()

    return updateddict


def updatepaymentstatus(billno: str, paymentstatus: str, amountreceived=None):
    receipt = getreceipt(billno)
    if not receipt:
        raise ValueError("Receipt not found.")

    resolved = resolvepaymentstate(
        currenttotal=_safe_float(receipt.get("Total")),
        previousarrears=_safe_float(receipt.get("PreviousArrears")),
        amountreceived=amountreceived,
        paymentstatus=paymentstatus,
    )

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE receipts
            SET paymentstatus = ?, amountreceived = ?
            WHERE billno = ?
            """,
            (resolved["paymentstatus"], resolved["amountreceived"], billno),
        )
        conn.commit()


def archivebill(billno: str):
    receipt = getreceipt(billno)
    if not receipt:
        raise ValueError("Receipt not found.")
    if receipt.get("Status") == "ARCHIVED":
        return receipt

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE receipts
            SET status = 'ARCHIVED', archiveddate = ?, archivedby = 'Admin'
            WHERE billno = ?
            """,
            (datetime.now().strftime("%Y-%m-%d"), billno),
        )
        conn.commit()

    return getreceipt(billno)


def restorebill(billno: str):
    receipt = getreceipt(billno)
    if not receipt:
        raise ValueError("Receipt not found.")
    if receipt.get("Status") == "ACTIVE":
        return receipt

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE receipts
            SET status = 'ACTIVE', archiveddate = '', archivedby = ''
            WHERE billno = ?
            """,
            (billno,),
        )
        conn.commit()

    return getreceipt(billno)


def deletebill(billno: str):
    receipt = getreceipt(billno)
    if not receipt:
        raise ValueError("Receipt not found.")
    if receipt.get("Status") != "ARCHIVED":
        raise ValueError("Only archived receipts can be permanently deleted.")

    with get_conn() as conn:
        conn.execute("DELETE FROM receipts WHERE billno = ?", (billno,))
        conn.commit()


def getdashboardstats():
    billingconf = config.get("billing") or {}
    receipts = getallreceipts()
    tenants = loadtenants()

    nextbill = str(billingconf.get("nextbillnumber", 1)).zfill(3)

    now = datetime.now()
    currentyear = now.year
    currentmonthidx = now.month
    currentmonthstr = f"{MONTHS[currentmonthidx - 1]} {currentyear}"

    if currentmonthidx == 1:
        prevmonthidx = 12
        prevyear = currentyear - 1
    else:
        prevmonthidx = currentmonthidx - 1
        prevyear = currentyear
    prevmonthstr = f"{MONTHS[prevmonthidx - 1]} {prevyear}"

    activetenants = len([t for t in tenants if t.status == "Active"])
    inactivetenants = len([t for t in tenants if t.status == "Inactive"])
    totaltenants = len(tenants)

    activereceipts = [r for r in receipts if r.get("Status", "ACTIVE") == "ACTIVE"]
    archivedreceipts = [r for r in receipts if r.get("Status") == "ARCHIVED"]
    totalactivereceipts = len(activereceipts)
    totalarchivedreceipts = len(archivedreceipts)
    totalreceiptsall = totalactivereceipts + totalarchivedreceipts

    monthlyrevenue = 0.0
    prevmonthlyrevenue = 0.0
    pendingpaymentscount = 0
    pendingamount = 0.0
    amountcollected = 0.0
    electricityconsumedthismonth = 0.0
    highestmeterreading = 0.0
    paidbillscount = 0

    for r in activereceipts:
        try:
            currentreading = _safe_float(r.get("Current"))
            highestmeterreading = max(highestmeterreading, currentreading)
        except Exception:
            pass

        status = r.get("PaymentStatus", "PENDING")
        grossamount = _safe_float(r.get("Total")) + _safe_float(r.get("PreviousArrears"))
        rawrecv = r.get("AmountReceived")
        received = (
            _safe_float(rawrecv)
            if rawrecv not in ("", None)
            else (grossamount if status == "PAID" else 0.0)
        )
        outstanding = max(grossamount - received, 0.0)

        ispaid = status == "PAID"
        isdue = status in ("PENDING", "PARTIAL")

        amountcollected += received

        if r.get("Month") == currentmonthstr:
            monthlyrevenue += received
            electricityconsumedthismonth += _safe_float(r.get("Units"))

        if r.get("Month") == prevmonthstr:
            prevmonthlyrevenue += received

        if isdue:
            pendingpaymentscount += 1
            if outstanding > 0:
                pendingamount += outstanding

        if ispaid:
            paidbillscount += 1

    if prevmonthlyrevenue == 0.0:
        revenuechangestr = "New Month"
    else:
        diff = monthlyrevenue - prevmonthlyrevenue
        pct = (diff / prevmonthlyrevenue) * 100
        sign = "+" if diff >= 0 else ""
        revenuechangestr = f"{sign}{pct:.2f}%"

    collectionrate = 0.0 if totalactivereceipts == 0 else (paidbillscount / totalactivereceipts) * 100

    recentbills = []
    for r in reversed(activereceipts[-5:]):
        recentbills.append(
            {
                "billno": r["Bill"],
                "tenantname": r["Tenant"],
                "total": _safe_float(r.get("Total")) + _safe_float(r.get("PreviousArrears")),
                "amountreceived": _safe_float(r.get("AmountReceived")),
                "month": r["Month"],
                "paymentstatus": r.get("PaymentStatus", "PENDING"),
            }
        )

    revenuechartdata = {m: 0.0 for m in MONTHS}
    electricitychartdata = {m: 0.0 for m in MONTHS}

    for r in activereceipts:
        try:
            rmonth, ryear = r["Month"].split()
            if ryear == str(currentyear) and rmonth in revenuechartdata:
                revenuechartdata[rmonth] += _safe_float(r.get("AmountReceived"), _safe_float(r.get("Total")))
                electricitychartdata[rmonth] += _safe_float(r.get("Units"))
        except Exception:
            pass

    chartmonths = [m for m in MONTHS if revenuechartdata[m] != 0 or electricitychartdata[m] != 0]
    if not chartmonths:
        chartmonths = MONTHS[:currentmonthidx]

    revenuelist = [revenuechartdata[m] for m in chartmonths]
    electricitylist = [electricitychartdata[m] for m in chartmonths]

    return {
        "nextbill": nextbill,
        "currentmonth": currentmonthstr,
        "monthlyrevenue": monthlyrevenue,
        "prevmonthlyrevenue": prevmonthlyrevenue,
        "revenuechangestr": revenuechangestr,
        "totalactivereceipts": totalactivereceipts,
        "totalarchivedreceipts": totalarchivedreceipts,
        "totalreceiptsall": totalreceiptsall,
        "activetenants": activetenants,
        "inactivetenants": inactivetenants,
        "totaltenants": totaltenants,
        "highestmeterreading": highestmeterreading,
        "electricityconsumed": electricityconsumedthismonth,
        "pendingpaymentscount": pendingpaymentscount,
        "pendingamount": pendingamount,
        "amountcollected": amountcollected,
        "collectionrate": collectionrate,
        "recentbills": recentbills,
        "chartlabels": chartmonths,
        "chartrevenue": revenuelist,
        "chartelectricity": electricitylist,
    }
```

Replace only the `getdbstats()` part of `app/services/backupservice.py` with this SQL-backed version, because your current backup metadata still derives table counts from CSV files while backups themselves already operate around storage directories. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/d7d36b18-5c83-42dc-b22e-039ec70c1def/rent.md?AWSAccessKeyId=ASIA2F3EMEYEX7HX7LAZ&Signature=ni6z4cZLJEPH%2BK8KHpvJ2NdzC88%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEHEaCXVzLWVhc3QtMSJIMEYCIQCo6d6XxibEtzY7vMur7KCspKFzKx%2Bv0kRewrvhtCycDAIhAMM4IrERa0pbjUIWsOZE3hbLCRKTp0fKiP91WXuHs9BfKvMECDkQARoMNjk5NzUzMzA5NzA1Igzbik0H7zOEajhn4r8q0AR3ZHS1TYhgldSyKCATI4zU6YILU4ylmMy%2Fx8Ibs%2BmYJV%2BwGrxlgGyr%2BHJdGR2uYSVBH53bxe%2BSoCPBBR3RV71kRYbVYP3JraC1Dvp0YtBRiqemZaxxg5%2FodS212f8Vup%2B7SLBEPAc%2BvdsRjJEUV1Ojullm%2FjOhPqzJfUGiIAZJ2zHvCYgZiao2rI2y4PY5Z9K5ZAhnkNdtu0BVKTlhu6UGT6fqY09tIgwjKTutxUQIn5I6r6L8tc6gW7HrsbcTZF2udLBxwFBeNYHSiScscyEjPl84QnNKZpBoKiRVIBibtfk%2Fmpw%2FwDS2HLZtJlAVU8raXvAqKj7NQ2TeCmkfsK9IfRB%2BjKUGu%2B5gjlNuJ%2BEW5mDL1Pyke3YjSD5uDd8CmbFT%2BXaBfUk9GjP8zQWTVhFthxJyFf9IklGx%2BDEgYTP38iyGWc8WSFd3ksQKnh3pYeNm%2BEwJirExdWw6EzxT1gq%2FHaDIeb1ch4ipivHVuQkB9OSErUw%2BT8hGT8hAkPcqK1SGZ0uDVwM9N3LX7unArfzT%2FCXx5tPfnazaaVwmAekdvp5LUh6HqavCAj%2FLWZAB5S7Veg8s4327cOETxmBSExpnDJGjcbN%2BT9oGeKpeua74RPmW3PA9%2B7rsiznushmP5fSv4WN3ai4BRYvgb3%2F%2BHj7sPkateS2XwMaccvc7TKHj1qj11g4YB%2F3QGRfb%2B3c4K%2FB%2Fk00GSHKcr87Rx8YtfImywLuOQVxBbKtjQ0oDmsg9Y9WkS6%2B11Qmtc04ml81dTWumT%2FOtl7QV%2BChCxrUcvNULMKGiqNIGOpcB3fCoG9FyciJCqz0Ry7MtzDMBOtlOCvAyNmQMojuek7tgTK11YMMdqdsLWlg7WWXxw0InJz6P6WKrhLKzLig2s8LS6T5Zy7s0s7UW%2BQmAT017pUEf7vPvgENwaxneBi93flUeIQjnS1uiyEnpgbXiBjM1FbRP5mFxfHukqI6%2BpYRb7QqUzYdtFOwrDX%2Fn0W7vtTTt1dEYaA%3D%3D&Expires=1783242484)

```python
# app/services/backupservice.py
import os
from app.core.db import get_conn
from app.core.paths import RECEIPTSDIR

def getdbstats():
    with get_conn() as conn:
        totaltenants = conn.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]
        activetenants = conn.execute(
            "SELECT COUNT(*) FROM tenants WHERE status = 'Active'"
        ).fetchone()[0]
        inactivetenants = conn.execute(
            "SELECT COUNT(*) FROM tenants WHERE status = 'Inactive'"
        ).fetchone()[0]

        totalreceipts = conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
        activereceipts = conn.execute(
            "SELECT COUNT(*) FROM receipts WHERE status = 'ACTIVE'"
        ).fetchone()[0]
        archivedreceipts = conn.execute(
            "SELECT COUNT(*) FROM receipts WHERE status = 'ARCHIVED'"
        ).fetchone()[0]
        pendingreceipts = conn.execute(
            "SELECT COUNT(*) FROM receipts WHERE status != 'ARCHIVED' AND paymentstatus IN ('PENDING', 'PARTIAL')"
        ).fetchone()[0]

        occupants = conn.execute("SELECT COUNT(*) FROM occupants").fetchone()[0]

    pdffiles = 0
    if os.path.isdir(RECEIPTSDIR):
        for name in os.listdir(RECEIPTSDIR):
            if name.lower().endswith(".pdf"):
                pdffiles += 1

    return {
        "total_tenants": totaltenants,
        "active_tenants": activetenants,
        "inactive_tenants": inactivetenants,
        "total_receipts": totalreceipts,
        "active_receipts": activereceipts,
        "archived_receipts": archivedreceipts,
        "pending_receipts": pendingreceipts,
        "total_occupants": occupants,
        "pdf_files": pdffiles,
    }
```

## Required patch

You also need `init_db()` called during startup, because your current updated source already has `app/core/db.py` with `get_conn()`, but startup still initializes storage, config, and static files rather than the SQLite schema itself. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/d7d36b18-5c83-42dc-b22e-039ec70c1def/rent.md?AWSAccessKeyId=ASIA2F3EMEYEX7HX7LAZ&Signature=ni6z4cZLJEPH%2BK8KHpvJ2NdzC88%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEHEaCXVzLWVhc3QtMSJIMEYCIQCo6d6XxibEtzY7vMur7KCspKFzKx%2Bv0kRewrvhtCycDAIhAMM4IrERa0pbjUIWsOZE3hbLCRKTp0fKiP91WXuHs9BfKvMECDkQARoMNjk5NzUzMzA5NzA1Igzbik0H7zOEajhn4r8q0AR3ZHS1TYhgldSyKCATI4zU6YILU4ylmMy%2Fx8Ibs%2BmYJV%2BwGrxlgGyr%2BHJdGR2uYSVBH53bxe%2BSoCPBBR3RV71kRYbVYP3JraC1Dvp0YtBRiqemZaxxg5%2FodS212f8Vup%2B7SLBEPAc%2BvdsRjJEUV1Ojullm%2FjOhPqzJfUGiIAZJ2zHvCYgZiao2rI2y4PY5Z9K5ZAhnkNdtu0BVKTlhu6UGT6fqY09tIgwjKTutxUQIn5I6r6L8tc6gW7HrsbcTZF2udLBxwFBeNYHSiScscyEjPl84QnNKZpBoKiRVIBibtfk%2Fmpw%2FwDS2HLZtJlAVU8raXvAqKj7NQ2TeCmkfsK9IfRB%2BjKUGu%2B5gjlNuJ%2BEW5mDL1Pyke3YjSD5uDd8CmbFT%2BXaBfUk9GjP8zQWTVhFthxJyFf9IklGx%2BDEgYTP38iyGWc8WSFd3ksQKnh3pYeNm%2BEwJirExdWw6EzxT1gq%2FHaDIeb1ch4ipivHVuQkB9OSErUw%2BT8hGT8hAkPcqK1SGZ0uDVwM9N3LX7unArfzT%2FCXx5tPfnazaaVwmAekdvp5LUh6HqavCAj%2FLWZAB5S7Veg8s4327cOETxmBSExpnDJGjcbN%2BT9oGeKpeua74RPmW3PA9%2B7rsiznushmP5fSv4WN3ai4BRYvgb3%2F%2BHj7sPkateS2XwMaccvc7TKHj1qj11g4YB%2F3QGRfb%2B3c4K%2FB%2Fk00GSHKcr87Rx8YtfImywLuOQVxBbKtjQ0oDmsg9Y9WkS6%2B11Qmtc04ml81dTWumT%2FOtl7QV%2BChCxrUcvNULMKGiqNIGOpcB3fCoG9FyciJCqz0Ry7MtzDMBOtlOCvAyNmQMojuek7tgTK11YMMdqdsLWlg7WWXxw0InJz6P6WKrhLKzLig2s8LS6T5Zy7s0s7UW%2BQmAT017pUEf7vPvgENwaxneBi93flUeIQjnS1uiyEnpgbXiBjM1FbRP5mFxfHukqI6%2BpYRb7QqUzYdtFOwrDX%2Fn0W7vtTTt1dEYaA%3D%3D&Expires=1783242484)
Add this one-line patch in startup after config initialization so `rent.db` is always ready before any service function runs. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/d7d36b18-5c83-42dc-b22e-039ec70c1def/rent.md?AWSAccessKeyId=ASIA2F3EMEYEX7HX7LAZ&Signature=ni6z4cZLJEPH%2BK8KHpvJ2NdzC88%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEHEaCXVzLWVhc3QtMSJIMEYCIQCo6d6XxibEtzY7vMur7KCspKFzKx%2Bv0kRewrvhtCycDAIhAMM4IrERa0pbjUIWsOZE3hbLCRKTp0fKiP91WXuHs9BfKvMECDkQARoMNjk5NzUzMzA5NzA1Igzbik0H7zOEajhn4r8q0AR3ZHS1TYhgldSyKCATI4zU6YILU4ylmMy%2Fx8Ibs%2BmYJV%2BwGrxlgGyr%2BHJdGR2uYSVBH53bxe%2BSoCPBBR3RV71kRYbVYP3JraC1Dvp0YtBRiqemZaxxg5%2FodS212f8Vup%2B7SLBEPAc%2BvdsRjJEUV1Ojullm%2FjOhPqzJfUGiIAZJ2zHvCYgZiao2rI2y4PY5Z9K5ZAhnkNdtu0BVKTlhu6UGT6fqY09tIgwjKTutxUQIn5I6r6L8tc6gW7HrsbcTZF2udLBxwFBeNYHSiScscyEjPl84QnNKZpBoKiRVIBibtfk%2Fmpw%2FwDS2HLZtJlAVU8raXvAqKj7NQ2TeCmkfsK9IfRB%2BjKUGu%2B5gjlNuJ%2BEW5mDL1Pyke3YjSD5uDd8CmbFT%2BXaBfUk9GjP8zQWTVhFthxJyFf9IklGx%2BDEgYTP38iyGWc8WSFd3ksQKnh3pYeNm%2BEwJirExdWw6EzxT1gq%2FHaDIeb1ch4ipivHVuQkB9OSErUw%2BT8hGT8hAkPcqK1SGZ0uDVwM9N3LX7unArfzT%2FCXx5tPfnazaaVwmAekdvp5LUh6HqavCAj%2FLWZAB5S7Veg8s4327cOETxmBSExpnDJGjcbN%2BT9oGeKpeua74RPmW3PA9%2B7rsiznushmP5fSv4WN3ai4BRYvgb3%2F%2BHj7sPkateS2XwMaccvc7TKHj1qj11g4YB%2F3QGRfb%2B3c4K%2FB%2Fk00GSHKcr87Rx8YtfImywLuOQVxBbKtjQ0oDmsg9Y9WkS6%2B11Qmtc04ml81dTWumT%2FOtl7QV%2BChCxrUcvNULMKGiqNIGOpcB3fCoG9FyciJCqz0Ry7MtzDMBOtlOCvAyNmQMojuek7tgTK11YMMdqdsLWlg7WWXxw0InJz6P6WKrhLKzLig2s8LS6T5Zy7s0s7UW%2BQmAT017pUEf7vPvgENwaxneBi93flUeIQjnS1uiyEnpgbXiBjM1FbRP5mFxfHukqI6%2BpYRb7QqUzYdtFOwrDX%2Fn0W7vtTTt1dEYaA%3D%3D&Expires=1783242484)

```python
# app/core/startup.py
from app.core.db import init_db

class StartupManager:
    @staticmethod
    def initialize(app):
        StartupManager.initialize_storage()
        StartupManager.initialize_config()
        init_db()
        StartupManager.mount_static(app)
        StartupManager.register_middlewares(app)
        StartupManager.register_events(app)
```

## Apply order

Use this sequence, because your import/export and tenant/billing routes already depend on the existing service signatures, and the replacements above are designed to preserve those signatures while swapping only the storage engine. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/d7d36b18-5c83-42dc-b22e-039ec70c1def/rent.md?AWSAccessKeyId=ASIA2F3EMEYEX7HX7LAZ&Signature=ni6z4cZLJEPH%2BK8KHpvJ2NdzC88%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEHEaCXVzLWVhc3QtMSJIMEYCIQCo6d6XxibEtzY7vMur7KCspKFzKx%2Bv0kRewrvhtCycDAIhAMM4IrERa0pbjUIWsOZE3hbLCRKTp0fKiP91WXuHs9BfKvMECDkQARoMNjk5NzUzMzA5NzA1Igzbik0H7zOEajhn4r8q0AR3ZHS1TYhgldSyKCATI4zU6YILU4ylmMy%2Fx8Ibs%2BmYJV%2BwGrxlgGyr%2BHJdGR2uYSVBH53bxe%2BSoCPBBR3RV71kRYbVYP3JraC1Dvp0YtBRiqemZaxxg5%2FodS212f8Vup%2B7SLBEPAc%2BvdsRjJEUV1Ojullm%2FjOhPqzJfUGiIAZJ2zHvCYgZiao2rI2y4PY5Z9K5ZAhnkNdtu0BVKTlhu6UGT6fqY09tIgwjKTutxUQIn5I6r6L8tc6gW7HrsbcTZF2udLBxwFBeNYHSiScscyEjPl84QnNKZpBoKiRVIBibtfk%2Fmpw%2FwDS2HLZtJlAVU8raXvAqKj7NQ2TeCmkfsK9IfRB%2BjKUGu%2B5gjlNuJ%2BEW5mDL1Pyke3YjSD5uDd8CmbFT%2BXaBfUk9GjP8zQWTVhFthxJyFf9IklGx%2BDEgYTP38iyGWc8WSFd3ksQKnh3pYeNm%2BEwJirExdWw6EzxT1gq%2FHaDIeb1ch4ipivHVuQkB9OSErUw%2BT8hGT8hAkPcqK1SGZ0uDVwM9N3LX7unArfzT%2FCXx5tPfnazaaVwmAekdvp5LUh6HqavCAj%2FLWZAB5S7Veg8s4327cOETxmBSExpnDJGjcbN%2BT9oGeKpeua74RPmW3PA9%2B7rsiznushmP5fSv4WN3ai4BRYvgb3%2F%2BHj7sPkateS2XwMaccvc7TKHj1qj11g4YB%2F3QGRfb%2B3c4K%2FB%2Fk00GSHKcr87Rx8YtfImywLuOQVxBbKtjQ0oDmsg9Y9WkS6%2B11Qmtc04ml81dTWumT%2FOtl7QV%2BChCxrUcvNULMKGiqNIGOpcB3fCoG9FyciJCqz0Ry7MtzDMBOtlOCvAyNmQMojuek7tgTK11YMMdqdsLWlg7WWXxw0InJz6P6WKrhLKzLig2s8LS6T5Zy7s0s7UW%2BQmAT017pUEf7vPvgENwaxneBi93flUeIQjnS1uiyEnpgbXiBjM1FbRP5mFxfHukqI6%2BpYRb7QqUzYdtFOwrDX%2Fn0W7vtTTt1dEYaA%3D%3D&Expires=1783242484)

1. Add `init_db()` to `app/core/db.py` and patch startup to call it. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/d7d36b18-5c83-42dc-b22e-039ec70c1def/rent.md?AWSAccessKeyId=ASIA2F3EMEYEX7HX7LAZ&Signature=ni6z4cZLJEPH%2BK8KHpvJ2NdzC88%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEHEaCXVzLWVhc3QtMSJIMEYCIQCo6d6XxibEtzY7vMur7KCspKFzKx%2Bv0kRewrvhtCycDAIhAMM4IrERa0pbjUIWsOZE3hbLCRKTp0fKiP91WXuHs9BfKvMECDkQARoMNjk5NzUzMzA5NzA1Igzbik0H7zOEajhn4r8q0AR3ZHS1TYhgldSyKCATI4zU6YILU4ylmMy%2Fx8Ibs%2BmYJV%2BwGrxlgGyr%2BHJdGR2uYSVBH53bxe%2BSoCPBBR3RV71kRYbVYP3JraC1Dvp0YtBRiqemZaxxg5%2FodS212f8Vup%2B7SLBEPAc%2BvdsRjJEUV1Ojullm%2FjOhPqzJfUGiIAZJ2zHvCYgZiao2rI2y4PY5Z9K5ZAhnkNdtu0BVKTlhu6UGT6fqY09tIgwjKTutxUQIn5I6r6L8tc6gW7HrsbcTZF2udLBxwFBeNYHSiScscyEjPl84QnNKZpBoKiRVIBibtfk%2Fmpw%2FwDS2HLZtJlAVU8raXvAqKj7NQ2TeCmkfsK9IfRB%2BjKUGu%2B5gjlNuJ%2BEW5mDL1Pyke3YjSD5uDd8CmbFT%2BXaBfUk9GjP8zQWTVhFthxJyFf9IklGx%2BDEgYTP38iyGWc8WSFd3ksQKnh3pYeNm%2BEwJirExdWw6EzxT1gq%2FHaDIeb1ch4ipivHVuQkB9OSErUw%2BT8hGT8hAkPcqK1SGZ0uDVwM9N3LX7unArfzT%2FCXx5tPfnazaaVwmAekdvp5LUh6HqavCAj%2FLWZAB5S7Veg8s4327cOETxmBSExpnDJGjcbN%2BT9oGeKpeua74RPmW3PA9%2B7rsiznushmP5fSv4WN3ai4BRYvgb3%2F%2BHj7sPkateS2XwMaccvc7TKHj1qj11g4YB%2F3QGRfb%2B3c4K%2FB%2Fk00GSHKcr87Rx8YtfImywLuOQVxBbKtjQ0oDmsg9Y9WkS6%2B11Qmtc04ml81dTWumT%2FOtl7QV%2BChCxrUcvNULMKGiqNIGOpcB3fCoG9FyciJCqz0Ry7MtzDMBOtlOCvAyNmQMojuek7tgTK11YMMdqdsLWlg7WWXxw0InJz6P6WKrhLKzLig2s8LS6T5Zy7s0s7UW%2BQmAT017pUEf7vPvgENwaxneBi93flUeIQjnS1uiyEnpgbXiBjM1FbRP5mFxfHukqI6%2BpYRb7QqUzYdtFOwrDX%2Fn0W7vtTTt1dEYaA%3D%3D&Expires=1783242484)
2. Replace `tenantservice.py` and `billingservice.py` with the SQLite versions above. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/d7d36b18-5c83-42dc-b22e-039ec70c1def/rent.md?AWSAccessKeyId=ASIA2F3EMEYEX7HX7LAZ&Signature=ni6z4cZLJEPH%2BK8KHpvJ2NdzC88%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEHEaCXVzLWVhc3QtMSJIMEYCIQCo6d6XxibEtzY7vMur7KCspKFzKx%2Bv0kRewrvhtCycDAIhAMM4IrERa0pbjUIWsOZE3hbLCRKTp0fKiP91WXuHs9BfKvMECDkQARoMNjk5NzUzMzA5NzA1Igzbik0H7zOEajhn4r8q0AR3ZHS1TYhgldSyKCATI4zU6YILU4ylmMy%2Fx8Ibs%2BmYJV%2BwGrxlgGyr%2BHJdGR2uYSVBH53bxe%2BSoCPBBR3RV71kRYbVYP3JraC1Dvp0YtBRiqemZaxxg5%2FodS212f8Vup%2B7SLBEPAc%2BvdsRjJEUV1Ojullm%2FjOhPqzJfUGiIAZJ2zHvCYgZiao2rI2y4PY5Z9K5ZAhnkNdtu0BVKTlhu6UGT6fqY09tIgwjKTutxUQIn5I6r6L8tc6gW7HrsbcTZF2udLBxwFBeNYHSiScscyEjPl84QnNKZpBoKiRVIBibtfk%2Fmpw%2FwDS2HLZtJlAVU8raXvAqKj7NQ2TeCmkfsK9IfRB%2BjKUGu%2B5gjlNuJ%2BEW5mDL1Pyke3YjSD5uDd8CmbFT%2BXaBfUk9GjP8zQWTVhFthxJyFf9IklGx%2BDEgYTP38iyGWc8WSFd3ksQKnh3pYeNm%2BEwJirExdWw6EzxT1gq%2FHaDIeb1ch4ipivHVuQkB9OSErUw%2BT8hGT8hAkPcqK1SGZ0uDVwM9N3LX7unArfzT%2FCXx5tPfnazaaVwmAekdvp5LUh6HqavCAj%2FLWZAB5S7Veg8s4327cOETxmBSExpnDJGjcbN%2BT9oGeKpeua74RPmW3PA9%2B7rsiznushmP5fSv4WN3ai4BRYvgb3%2F%2BHj7sPkateS2XwMaccvc7TKHj1qj11g4YB%2F3QGRfb%2B3c4K%2FB%2Fk00GSHKcr87Rx8YtfImywLuOQVxBbKtjQ0oDmsg9Y9WkS6%2B11Qmtc04ml81dTWumT%2FOtl7QV%2BChCxrUcvNULMKGiqNIGOpcB3fCoG9FyciJCqz0Ry7MtzDMBOtlOCvAyNmQMojuek7tgTK11YMMdqdsLWlg7WWXxw0InJz6P6WKrhLKzLig2s8LS6T5Zy7s0s7UW%2BQmAT017pUEf7vPvgENwaxneBi93flUeIQjnS1uiyEnpgbXiBjM1FbRP5mFxfHukqI6%2BpYRb7QqUzYdtFOwrDX%2Fn0W7vtTTt1dEYaA%3D%3D&Expires=1783242484)
3. Replace `backupservice.getdbstats()` with the SQL version above. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/d7d36b18-5c83-42dc-b22e-039ec70c1def/rent.md?AWSAccessKeyId=ASIA2F3EMEYEX7HX7LAZ&Signature=ni6z4cZLJEPH%2BK8KHpvJ2NdzC88%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEHEaCXVzLWVhc3QtMSJIMEYCIQCo6d6XxibEtzY7vMur7KCspKFzKx%2Bv0kRewrvhtCycDAIhAMM4IrERa0pbjUIWsOZE3hbLCRKTp0fKiP91WXuHs9BfKvMECDkQARoMNjk5NzUzMzA5NzA1Igzbik0H7zOEajhn4r8q0AR3ZHS1TYhgldSyKCATI4zU6YILU4ylmMy%2Fx8Ibs%2BmYJV%2BwGrxlgGyr%2BHJdGR2uYSVBH53bxe%2BSoCPBBR3RV71kRYbVYP3JraC1Dvp0YtBRiqemZaxxg5%2FodS212f8Vup%2B7SLBEPAc%2BvdsRjJEUV1Ojullm%2FjOhPqzJfUGiIAZJ2zHvCYgZiao2rI2y4PY5Z9K5ZAhnkNdtu0BVKTlhu6UGT6fqY09tIgwjKTutxUQIn5I6r6L8tc6gW7HrsbcTZF2udLBxwFBeNYHSiScscyEjPl84QnNKZpBoKiRVIBibtfk%2Fmpw%2FwDS2HLZtJlAVU8raXvAqKj7NQ2TeCmkfsK9IfRB%2BjKUGu%2B5gjlNuJ%2BEW5mDL1Pyke3YjSD5uDd8CmbFT%2BXaBfUk9GjP8zQWTVhFthxJyFf9IklGx%2BDEgYTP38iyGWc8WSFd3ksQKnh3pYeNm%2BEwJirExdWw6EzxT1gq%2FHaDIeb1ch4ipivHVuQkB9OSErUw%2BT8hGT8hAkPcqK1SGZ0uDVwM9N3LX7unArfzT%2FCXx5tPfnazaaVwmAekdvp5LUh6HqavCAj%2FLWZAB5S7Veg8s4327cOETxmBSExpnDJGjcbN%2BT9oGeKpeua74RPmW3PA9%2B7rsiznushmP5fSv4WN3ai4BRYvgb3%2F%2BHj7sPkateS2XwMaccvc7TKHj1qj11g4YB%2F3QGRfb%2B3c4K%2FB%2Fk00GSHKcr87Rx8YtfImywLuOQVxBbKtjQ0oDmsg9Y9WkS6%2B11Qmtc04ml81dTWumT%2FOtl7QV%2BChCxrUcvNULMKGiqNIGOpcB3fCoG9FyciJCqz0Ry7MtzDMBOtlOCvAyNmQMojuek7tgTK11YMMdqdsLWlg7WWXxw0InJz6P6WKrhLKzLig2s8LS6T5Zy7s0s7UW%2BQmAT017pUEf7vPvgENwaxneBi93flUeIQjnS1uiyEnpgbXiBjM1FbRP5mFxfHukqI6%2BpYRb7QqUzYdtFOwrDX%2Fn0W7vtTTt1dEYaA%3D%3D&Expires=1783242484)
4. Run your one-time CSV-to-SQLite migration script, then start the app and verify tenants, receipts, public tenant page, KYC uploads, PDF view, payment updates, archive/restore, and Excel import all work normally. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/d7d36b18-5c83-42dc-b22e-039ec70c1def/rent.md?AWSAccessKeyId=ASIA2F3EMEYEX7HX7LAZ&Signature=ni6z4cZLJEPH%2BK8KHpvJ2NdzC88%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEHEaCXVzLWVhc3QtMSJIMEYCIQCo6d6XxibEtzY7vMur7KCspKFzKx%2Bv0kRewrvhtCycDAIhAMM4IrERa0pbjUIWsOZE3hbLCRKTp0fKiP91WXuHs9BfKvMECDkQARoMNjk5NzUzMzA5NzA1Igzbik0H7zOEajhn4r8q0AR3ZHS1TYhgldSyKCATI4zU6YILU4ylmMy%2Fx8Ibs%2BmYJV%2BwGrxlgGyr%2BHJdGR2uYSVBH53bxe%2BSoCPBBR3RV71kRYbVYP3JraC1Dvp0YtBRiqemZaxxg5%2FodS212f8Vup%2B7SLBEPAc%2BvdsRjJEUV1Ojullm%2FjOhPqzJfUGiIAZJ2zHvCYgZiao2rI2y4PY5Z9K5ZAhnkNdtu0BVKTlhu6UGT6fqY09tIgwjKTutxUQIn5I6r6L8tc6gW7HrsbcTZF2udLBxwFBeNYHSiScscyEjPl84QnNKZpBoKiRVIBibtfk%2Fmpw%2FwDS2HLZtJlAVU8raXvAqKj7NQ2TeCmkfsK9IfRB%2BjKUGu%2B5gjlNuJ%2BEW5mDL1Pyke3YjSD5uDd8CmbFT%2BXaBfUk9GjP8zQWTVhFthxJyFf9IklGx%2BDEgYTP38iyGWc8WSFd3ksQKnh3pYeNm%2BEwJirExdWw6EzxT1gq%2FHaDIeb1ch4ipivHVuQkB9OSErUw%2BT8hGT8hAkPcqK1SGZ0uDVwM9N3LX7unArfzT%2FCXx5tPfnazaaVwmAekdvp5LUh6HqavCAj%2FLWZAB5S7Veg8s4327cOETxmBSExpnDJGjcbN%2BT9oGeKpeua74RPmW3PA9%2B7rsiznushmP5fSv4WN3ai4BRYvgb3%2F%2BHj7sPkateS2XwMaccvc7TKHj1qj11g4YB%2F3QGRfb%2B3c4K%2FB%2Fk00GSHKcr87Rx8YtfImywLuOQVxBbKtjQ0oDmsg9Y9WkS6%2B11Qmtc04ml81dTWumT%2FOtl7QV%2BChCxrUcvNULMKGiqNIGOpcB3fCoG9FyciJCqz0Ry7MtzDMBOtlOCvAyNmQMojuek7tgTK11YMMdqdsLWlg7WWXxw0InJz6P6WKrhLKzLig2s8LS6T5Zy7s0s7UW%2BQmAT017pUEf7vPvgENwaxneBi93flUeIQjnS1uiyEnpgbXiBjM1FbRP5mFxfHukqI6%2BpYRb7QqUzYdtFOwrDX%2Fn0W7vtTTt1dEYaA%3D%3D&Expires=1783242484)
5. After validation, delete `tenants.csv`, `receipts.csv`, and `occupants.csv`, because you explicitly want CSV persistence removed and unsupported going forward. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/d7d36b18-5c83-42dc-b22e-039ec70c1def/rent.md?AWSAccessKeyId=ASIA2F3EMEYEX7HX7LAZ&Signature=ni6z4cZLJEPH%2BK8KHpvJ2NdzC88%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEHEaCXVzLWVhc3QtMSJIMEYCIQCo6d6XxibEtzY7vMur7KCspKFzKx%2Bv0kRewrvhtCycDAIhAMM4IrERa0pbjUIWsOZE3hbLCRKTp0fKiP91WXuHs9BfKvMECDkQARoMNjk5NzUzMzA5NzA1Igzbik0H7zOEajhn4r8q0AR3ZHS1TYhgldSyKCATI4zU6YILU4ylmMy%2Fx8Ibs%2BmYJV%2BwGrxlgGyr%2BHJdGR2uYSVBH53bxe%2BSoCPBBR3RV71kRYbVYP3JraC1Dvp0YtBRiqemZaxxg5%2FodS212f8Vup%2B7SLBEPAc%2BvdsRjJEUV1Ojullm%2FjOhPqzJfUGiIAZJ2zHvCYgZiao2rI2y4PY5Z9K5ZAhnkNdtu0BVKTlhu6UGT6fqY09tIgwjKTutxUQIn5I6r6L8tc6gW7HrsbcTZF2udLBxwFBeNYHSiScscyEjPl84QnNKZpBoKiRVIBibtfk%2Fmpw%2FwDS2HLZtJlAVU8raXvAqKj7NQ2TeCmkfsK9IfRB%2BjKUGu%2B5gjlNuJ%2BEW5mDL1Pyke3YjSD5uDd8CmbFT%2BXaBfUk9GjP8zQWTVhFthxJyFf9IklGx%2BDEgYTP38iyGWc8WSFd3ksQKnh3pYeNm%2BEwJirExdWw6EzxT1gq%2FHaDIeb1ch4ipivHVuQkB9OSErUw%2BT8hGT8hAkPcqK1SGZ0uDVwM9N3LX7unArfzT%2FCXx5tPfnazaaVwmAekdvp5LUh6HqavCAj%2FLWZAB5S7Veg8s4327cOETxmBSExpnDJGjcbN%2BT9oGeKpeua74RPmW3PA9%2B7rsiznushmP5fSv4WN3ai4BRYvgb3%2F%2BHj7sPkateS2XwMaccvc7TKHj1qj11g4YB%2F3QGRfb%2B3c4K%2FB%2Fk00GSHKcr87Rx8YtfImywLuOQVxBbKtjQ0oDmsg9Y9WkS6%2B11Qmtc04ml81dTWumT%2FOtl7QV%2BChCxrUcvNULMKGiqNIGOpcB3fCoG9FyciJCqz0Ry7MtzDMBOtlOCvAyNmQMojuek7tgTK11YMMdqdsLWlg7WWXxw0InJz6P6WKrhLKzLig2s8LS6T5Zy7s0s7UW%2BQmAT017pUEf7vPvgENwaxneBi93flUeIQjnS1uiyEnpgbXiBjM1FbRP5mFxfHukqI6%2BpYRb7QqUzYdtFOwrDX%2Fn0W7vtTTt1dEYaA%3D%3D&Expires=1783242484)

One small cleanup remains outside the core migration: your health route still reports “Using flat files,” so change that text to “Using SQLite rent.db” after cutover to avoid misleading diagnostics. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/83904925/d7d36b18-5c83-42dc-b22e-039ec70c1def/rent.md?AWSAccessKeyId=ASIA2F3EMEYEX7HX7LAZ&Signature=ni6z4cZLJEPH%2BK8KHpvJ2NdzC88%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEHEaCXVzLWVhc3QtMSJIMEYCIQCo6d6XxibEtzY7vMur7KCspKFzKx%2Bv0kRewrvhtCycDAIhAMM4IrERa0pbjUIWsOZE3hbLCRKTp0fKiP91WXuHs9BfKvMECDkQARoMNjk5NzUzMzA5NzA1Igzbik0H7zOEajhn4r8q0AR3ZHS1TYhgldSyKCATI4zU6YILU4ylmMy%2Fx8Ibs%2BmYJV%2BwGrxlgGyr%2BHJdGR2uYSVBH53bxe%2BSoCPBBR3RV71kRYbVYP3JraC1Dvp0YtBRiqemZaxxg5%2FodS212f8Vup%2B7SLBEPAc%2BvdsRjJEUV1Ojullm%2FjOhPqzJfUGiIAZJ2zHvCYgZiao2rI2y4PY5Z9K5ZAhnkNdtu0BVKTlhu6UGT6fqY09tIgwjKTutxUQIn5I6r6L8tc6gW7HrsbcTZF2udLBxwFBeNYHSiScscyEjPl84QnNKZpBoKiRVIBibtfk%2Fmpw%2FwDS2HLZtJlAVU8raXvAqKj7NQ2TeCmkfsK9IfRB%2BjKUGu%2B5gjlNuJ%2BEW5mDL1Pyke3YjSD5uDd8CmbFT%2BXaBfUk9GjP8zQWTVhFthxJyFf9IklGx%2BDEgYTP38iyGWc8WSFd3ksQKnh3pYeNm%2BEwJirExdWw6EzxT1gq%2FHaDIeb1ch4ipivHVuQkB9OSErUw%2BT8hGT8hAkPcqK1SGZ0uDVwM9N3LX7unArfzT%2FCXx5tPfnazaaVwmAekdvp5LUh6HqavCAj%2FLWZAB5S7Veg8s4327cOETxmBSExpnDJGjcbN%2BT9oGeKpeua74RPmW3PA9%2B7rsiznushmP5fSv4WN3ai4BRYvgb3%2F%2BHj7sPkateS2XwMaccvc7TKHj1qj11g4YB%2F3QGRfb%2B3c4K%2FB%2Fk00GSHKcr87Rx8YtfImywLuOQVxBbKtjQ0oDmsg9Y9WkS6%2B11Qmtc04ml81dTWumT%2FOtl7QV%2BChCxrUcvNULMKGiqNIGOpcB3fCoG9FyciJCqz0Ry7MtzDMBOtlOCvAyNmQMojuek7tgTK11YMMdqdsLWlg7WWXxw0InJz6P6WKrhLKzLig2s8LS6T5Zy7s0s7UW%2BQmAT017pUEf7vPvgENwaxneBi93flUeIQjnS1uiyEnpgbXiBjM1FbRP5mFxfHukqI6%2BpYRb7QqUzYdtFOwrDX%2Fn0W7vtTTt1dEYaA%3D%3D&Expires=1783242484)
Next, I can give you the exact `app/core/db.py` file with `init_db()` included and a final one-time migration script matched to your current CSV headers.