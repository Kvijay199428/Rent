# Audit Task — Billing Edit: `receipts.property_id` Migration + Atomic Tenant-Profile Rate Updates in `update_bill`

**Status:** COMPLETED (testing done, 2 minor lint items awaiting approval)
**Date:** 2026-08-31

## Objectives
1. Audit the reworked `EditBillModal.tsx` against the atomic backend billing changes.
2. Verify `receipts.property_id` migration + FK-defensive backfill (db.py).
3. Verify tenant-profile rate updates run atomically inside `update_bill` (single commit).
4. Produce `/audit/*.md` docs from real test results.

## Non-Goals / Locked Decisions
- Tenant App must NOT be modified.
- Property is editable per-receipt (NOT synced to tenant).
- Rates updated on tenant profile atomically in one `update_bill` transaction.
- Submit = single `api.updateBill` call.
- No test framework installed (repo has none — no vitest/jest/pytest).
- Runtime verification used a copied scratch DB via `RENT_STORAGE_DIR`; real DB untouched.

## Acceptance Criteria
- [x] `EditBillModal.tsx` compiles (`tsc --noEmit` clean).
- [x] Build passes (`npm run build`).
- [x] Backend edited files parse + import.
- [x] `update_bill` SQL columns all exist in live schema.
- [x] Migration (ALTER + index + marker) + backfill idempotent and orphan-FK safe.
- [x] `update_bill` atomically updates receipt snapshot + tenant profile; `tenants.property_id` unchanged.
- [x] Self-owned property wins; other-landlord property rejected.
- [x] Real DB `storage/database/rent.db` untouched.
- [ ] (awaiting approval) Fix 2 new lint items in `EditBillModal.tsx`.

## Files Under Audit (bucket-list)
see `bucket-list.md`
