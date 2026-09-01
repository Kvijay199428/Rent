# Audit Bucket-List (files in scope)

## Backend (atomic billing changes)
- `backend/app/app/core/db.py` — `receipts.property_id` migration + index + FK-defensive backfill + `receipt_property_id_backfill_v1` marker
- `backend/app/app/database/final_schema.py` — receipts CREATE with `property_id`
- `backend/app/app/models/receipt.py` — `BillRequest` (UTF-8 BOM)
- `backend/app/app/models/tenant.py` — `propertyId` field
- `backend/app/app/services/billing_service.py` — `update_bill` (atomic), `calculate_charges`
- `backend/app/app/api/billing.py` — `api_update_bill`
- `backend/app/app/services/pdf_service.py` — Property row
- `backend/app/app/database/property_repository.py` — `get_property`

## Frontend (Edit Bill modal)
- `frontend/landlord-app/src/components/shared/EditBillModal.tsx` — rewritten (436 lines)
- `frontend/landlord-app/src/services/api.ts` — `updateBill`, `getProperties`, `getTenant`, `getReceipt`, `getBillingMonths`
- `frontend/landlord-app/src/types/index.ts` — `BillRequest`, `Receipt`, `Property`
- `frontend/landlord-app/src/pages/History.tsx`, `Dashboard.tsx`, `Archive.tsx` — callers (props unchanged)
- `frontend/landlord-app/src/pages/Billing.tsx` — reference layout

## Runtime / scratch
- `storage/database/rent.db` — REAL DB (must stay untouched; verified unchanged)
- `C:\Users\vjsin\AppData\Local\Temp\opencode\scratch_runtime_test.py` — temporary test harness (cleaned up)
- scratch dir `...\opencode\scratch\database\rent.db` — copied DB used for runtime test (cleaned up)

## Audit docs (this folder)
- `audit/task.md`, `audit/plan.md`, `audit/log.md`, `audit/bucket-list.md`

## Outstanding (awaiting user approval before any edit)
1. ~~`EditBillModal.tsx:20` — remove unused `Tenant` import~~ **DONE (approved).**
2. ~~`EditBillModal.tsx:102-110` — meterError `set-state-in-effect`~~ **DONE (approved; now derived const).**
   (Item at `:58` `setLoading(true)` in load effect is a pre-existing pattern, not a regression — left unchanged.)
