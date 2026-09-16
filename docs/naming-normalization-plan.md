# Naming Normalization Plan (Phase 1: Freeze + Baseline + Execution Plan)

Status: **FROZEN** — approved. This document anchors the 18-phase campaign to normalize all
Propaura database identifiers to **camelCase** (quoted PostgreSQL identifiers), eliminate
naming collisions / semantic ambiguity, remove the duplicated `tenant_recovery_snapshots`
runtime DDL, and keep the payment matrix green.

---

## 0. Baseline (verified 2026-09)

| Item | Value |
| --- | --- |
| Git HEAD | `2337e85` |
| Working tree | clean (only unrelated `.agents/skills/testing-audit-debugging-protocol/...` modifications; untouched by this campaign) |
| Live schema snapshot | `docs/database-schema.md` (verified against live dev DB — 31 tables / 328 columns / 79 indexes / 25 FK) |
| Migrations | `001_initial.py`, `002_seed.py`, `003_payment_method.py`, `migrator.py` |
| Migration runner | `python -m app.db.migrations.migrator up | down | status` (tracks `schema_migrations`) |
| DB access | live dev DB reachable only via container on `192.168.1.50`; **no local psycopg** |

### Corrected drift note (O-3): `tenant_recovery_snapshots.id`

Direct read of `001_initial.py` (line 384) confirms **`id TEXT PRIMARY KEY`** in the migration
*source* — NOT `BIGINT identity`. The service-side DDL (`tenant_recovery_service.py`:
`_init_snapshots_table`) also declares `id TEXT PRIMARY KEY`. **There is NO id-type drift.**
The claim in `docs/database-schema.md` for O-3 is inaccurate for the migration source and is
being corrected there.

The only real drift on this table: migration `001` does **not** create `landlord_id`, while the
service DDL does (plus `idx_tenant_recovery_landlord`). Migration `004` reconciles this (Phase 3/8).

---

## 1. Freeze (approved rules — frozen 2026-09)

1. **Canonical convention:** every user-facing identifier is **camelCase** and stored **quoted**.
   Single-word identifiers that already fold identically (`admins`, `tenants`, `receipts`,
   `occupants`, `id`, `billNo`, `units`, `status`) are unchanged.
2. **Case-insensitive lookups are forbidden going forward.** Raw-SQL `_FlexRow` casefold
   compatibility is a *transitional* mechanism only; it is removed in Phase 10.
3. **Semantic disambiguation**
   - Rates end in `*Rate` (`electricityRate`, `additionalPersonRate`); amounts in
     `*Amount` (`rentAmount`, `waterAmount`, `additionalAmount`, `paymentAmount`,
     `allocatedAmount`).
   - Bill-level status is `paymentStatus` (receipts side); payment-record status stays `status`.
   - Payment identity: `externalId` is the business key; `id` is the internal PK.
   - `amountReceived` / `paymentStatus` are **derived** fields — never re-normalized downstream.
4. **Multi-word table names are renamed camelCase**, including `landlords` → `landlordLegacyMappings`
   (legacy landlord → admin mapping; NOT merged into `landlordAccounts`).
5. **Dedicated migration `004_camel_case.py`** owns all DDL added by this campaign. The runtime
   reconciler `_init_snapshots_table` is **neutralized** to a presence check (migrations own DDL).
6. **Constraint normalization:** prefixes `pk_`, `fk_`, `uk_`; format
   `{pk|uk|fk}_{tableCamel}_{columnCamel}`.
7. **Index naming convention:** `idx_{tableCamel}_{columnCamel(s)}`. Constraint-backed implicit
   indexes (e.g. `admins_username_key`, `landlords_landlorduuid_key`, `receipts_id_key`) cannot be
   renamed directly — they are re-parented via their constraint `RENAME CONSTRAINT`.
8. **Non-destructive renames only.** Every rename is guarded (checks `information_schema.columns`,
   `pg_constraint`, `to_regclass`, `pg_indexes`) so missing objects or wrong auto-name guesses
   **skip harmlessly**. Wrong guesses must never error.
9. **No data rewriting.** No column type changes, no value transforms, no backfills.
10. **`schema_migrations` is excluded** (infrastructure ledger owned by `migrator.py`).
11. **Kept quirks** (documented, accepted):
    `payment_entries.landlord_id` is `TEXT` (001) vs `INTEGER` elsewhere; the 3 session tables and
    3 audit tables stay separate; `payment_entries`/`payment_allocations` stay separate;
    `landlords`→`landlordLegacyMappings` is not merged.

---

## 2. Deployment sequencing (critical)

- The DB rename (`004`) and the **backend SQL→camelCase rewrite (Phase 9-10) MUST ship in the
  SAME release.** After 004 live:
  - Explicit snake-column `INSERT/UPDATE` statements fail (column no longer exists).
  - `_FlexRow` casefold still matches renamed camel keys for reads (`row["billNo"]`), but any old
    `row["total"]`-style lookup that no longer maps to a camel key breaks.
- Downstream exports/imports (CSV/XLSX) must reference canonical camelCase headers.

---

## 3. The 18-phase execution plan

| # | Phase | Input | Output | Done |
| --- | --- | --- | --- | --- |
| 1 | Freeze + baseline | this doc | approved naming rules | ✅ (this doc) |
| 2 | camelCase contract | naming rules | `docs/database-column-mapping-v3.md` | next |
| 3 | Fix `tenant_recovery_snapshots` DDL duplication | live drift | reconcile in 004 + neutralize `_init_snapshots_table` | next |
| 4 | Migration `004_camel_case.py` | mapping v3 | guarded non-destructive renames | next |
| 5 | PG schema rename | 004 | all tables/columns→camelCase quoted | 004 |
| 6 | PK/FK normalization | 004 | `pk_/fk_/uk_` naming | 004 |
| 7 | Index naming | 004 | `idx_{table}_{col}` | 004 |
| 8 | `idx_tenantRecoverySnapshots_landlordId` ensure | 001+service | CREATE IF NOT EXISTS in 004 | 004 |
| 9 | Backend SQL → camelCase | 004 applied | `app/db/repos`, `app/services`, `app/routers`, `app/database` use camelCase quoted | after |
| 10 | Remove `_FlexRow` | Phase 9 | strict keyed access / real typed rows | after |
| 11 | CSV V3 | data_schema | zero collision headers, camelCase | after |
| 12 | XLSX V3 | same | same | after |
| 13 | Legacy import compat | V2→V3 | importer maps old → new | after |
| 14 | Export parity | V3 writers | exports use canonical headers | after |
| 15 | Schema validator | V3 contract | rejects snake_case | after |
| 16 | Payment matrix regression | 004 + backend | 43/43 green | after |
| 17 | Fresh DB test | 004 from 001+002+003 | clean apply | after |
| 18 | Existing DB upgrade test | 004 on live-ish DB | guarded idempotent apply | after |

---

## 4. Migration 004 design (agreed)

Data-driven dicts + guarded helpers. Execution order inside `up()`:

1. Ensure `landlord_id INTEGER` exists on `tenant_recovery_snapshots` (service parity; skip if present).
2. Column renames (snake→camel), guarded.
3. Table renames (snake→camel), guarded.
4. Constraint renames via `ALTER TABLE ... RENAME CONSTRAINT` → `pk_/fk_/uk_` prefixes
   (renames constraint-backed implicit indexes via the constraint).
5. Explicit `idx_*` index renames via `ALTER INDEX ... RENAME TO` (convention `idx_{table}_{cols}`).
6. Create `idx_tenantRecoverySnapshots_landlordId` if missing.

- No `commit()` inside `up()`: `migrator.py` wraps in `with get_conn() as tx:` (mirrors 001/003).
- `down()` reverses the same renames in reverse order, same guards (best-effort; documented).

Verification: `python -m py_compile` only (no local psycopg). Execution happens on the dev DB
via container during Phase 17/18.