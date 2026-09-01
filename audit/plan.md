# Audit Plan — Billing Edit: property_id Migration + Atomic Rate Updates

**Status:** COMPLETED

## Approach
- **Testing mode:** Manual + tooling smoke tests. No framework installed (repo has no vitest/jest/pytest). Tooling: `tsc --noEmit`, `eslint`, `npm run build`, `ast.parse`, Python `sqlite3` runtime harness.
- **DB verification:** Copied `storage/database/rent.db` to a scratch dir, set `RENT_STORAGE_DIR` to the copy, ran `init_db()` + `update_bill` against the copy. Real DB untouched.
- **Tenant App:** not modified.

## Steps
1. Frontend static: `tsc --noEmit`, `eslint src/components/shared/EditBillModal.tsx`, `npm run build`.
2. Caller verification: History/Dashboard/Archive pass unchanged props.
3. Backend syntax/import: `ast.parse` (utf-8-sig) on 6 edited files; import `billing_service`, `db`, `property_repository`.
4. Schema-score consistency: extract `UPDATE receipts/tenants ... SET` columns from `update_bill`; diff against live `receipts`/`tenants` schema.
5. Migration smoke (in-memory): simulate pre-migration schema; run guarded ALTER + index + backfill twice (idempotency); insert valid + orphan tenant to confirm orphan backfill safety.
6. Scratch-DB runtime (end-to-end): copy DB → `RENT_STORAGE_DIR` → `init_db()` (migration) → seed landlord_accounts/landlord_properties/tenant/receipt → `update_bill` with edited rates + property → assert 20 checks (migration, snapshot, profile, atomics, ownership, meter guard, PDF).
7. Report lint findings; ask approval before editing.
8. Write `/audit/*.md`.

## Outcome
- Steps 1–6 all green.
- Step 7: **2 new lint items** await approval (see log.md). 1 pre-existing lint pattern (set-state-in-effect at load) exists in the committed baseline too.
