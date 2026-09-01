# Audit Log — Real Test Results

**Date:** 2026-08-31

## Frontend

### `tsc --noEmit` (landlord-app)
```
exit 0, clean
```
### `npm run build` (vite 8.1.5)
```
✓ built in 867ms
exit 0
```
### `eslint src/components/shared/EditBillModal.tsx`
- `20:15` `@typescript-eslint/no-unused-vars` — `'Tenant' is defined but never used`  ← **NEW — FIXED** (removed unused import; user-approved)
- `58:7` `react-hooks/set-state-in-effect` — `setLoading(true)` in load effect  ← **PRE-EXISTING** (baseline also called setLoading in an effect; not a regression) — **left as-is per report**
- `102/110` `react-hooks/set-state-in-effect` — `setMeterError(...)` in new meterError effect  ← **NEW — FIXED** (replaced state+effect with a derived `const meterError`; user-approved)
- Whole-app `npm run lint`: 131 pre-existing problems (repo lint red before this work; unrelated).

**Post-fix state:** `eslint` on `EditBillModal.tsx` reports only the 1 pre-existing `setLoading(true)` item. `tsc --noEmit` clean. `npm run build` exit 0.

### Callers (props unchanged — compile fine)
- `History.tsx:158` `<EditBillModal billNo ... tenantId ... onClose ... onSaved ... />`
- `Dashboard.tsx:515` same props
- `Archive.tsx:218` same props

## Backend — Syntax & Imports
`ast.parse` (utf-8-sig) OK on: `billing.py, db.py, final_schema.py, receipt.py, billing_service.py, pdf_service.py`.
Imports OK: `app.services.billing_service`, `app.core.db`, `app.database.property_repository`; `get_property` wired.

## Backend — Schema-Score Consistency
`update_bill` SET columns all present in live schema. Only "missing" = `receipts.property_id` (the intentionally-added column created by migration). WHERE handles `tenantId`, `billNo`, `landlord_id` — all present. ✅

## Backend — Migration + Backfill Smoke Test (in-memory)
- Fresh: VALID tenant receipt → `property_id` backfilled (1); ORPHAN tenant receipt → stays `NULL` (no FK crash). ✅
- Idempotent re-run: guard skips ALTER, no error. ✅

## Backend — Scratch-DB Runtime Test (end-to-end, real `update_bill`)
Copied `storage/database/rent.db` → scratch; `RENT_STORAGE_DIR` pointed at copy; ran `init_db()` + seeded + `update_bill`.
| Check | Result |
|---|---|
| A. receipts.property_id column added | PASS |
| B. landlord_properties table exists | PASS |
| C. idx_receipts_property_id index created | PASS |
| D. backfill marker written | PASS |
| E. backfill on empty DB (0 filled) | PASS |
| F. seeded receipt present | PASS |
| G. update_bill returned (current=150, rent=1200) | PASS |
| H. receipt.rent snapshot = 1200 | PASS |
| I. receipt.rate snapshot = 9 | PASS |
| J. receipt.additionalpersons = 3 | PASS |
| K. receipt.additionalpersonrate = 60 | PASS |
| L. receipt.property_id = Prop Beta (edited) | PASS |
| M. tenant.profile rent = 1200 | PASS |
| N. tenant.profile water = 250 | PASS |
| O. tenant.profile electricityrate = 9 | PASS |
| P. tenant.profile additionalpersoncharge = 60 | PASS |
| Q. tenants.property_id UNCHANGED (stays Prop Alpha) | PASS |
| R. other-landlord property rejected | PASS |
| S. meter-guard (current<prev) rejected | PASS |
| T. PDF regenerated on scratch | PASS |

**20/20 PASS.** Atomicity confirmed by inspection + runtime: receipt UPDATE and tenant-profile UPDATE run in the same `with get_conn()` block, single `conn.commit()`.

## Real DB Safety
`storage/database/rent.db` verified untouched: no `property_id`, no `landlord_properties`, 0 receipts, 0 tenants. Scratch cleaned up after test.

## Notes / Test-Harness Corrections (not code defects)
- Runtime seed required supplying NOT NULL cols (`landlord_accounts`, `created_at`/`updated_at`, receipt `date`, explicit `billno`) — all test-harness details, not app bugs.
- `S` meter guard requires `previous > 0`; initial seed had `previous=0` (guard correctly skipped). Fixed seed → PASS.
