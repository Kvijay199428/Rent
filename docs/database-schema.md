# PROPAURA — PostgreSQL Database Schema (Production)

## Overview

- **31 tables**: 30 application tables + 1 migration ledger (`schema_migrations`). _Verified against live dev DB: 31 tables total (30 app + ledger)._
- All application tables are created by **migration `001_initial.py`**. Migration `002_seed.py` seeds version metadata, backfills `tenants.qr_key`, and seeds the default platform admin. Migration `003_payment_method.py` extends `payment_entries` with payment-method fields.
- Schema source: `backend/app/app/db/migrations/`.
- Timestamps are stored as **ISO-8601 TEXT**, exactly as the application produces them.
- Booleans are stored as **INTEGER (0/1)**.
- Migration runner: `migrator.py` (tracks applied versions in `schema_migrations`).

| Migration | Scope |
|---|---|
| `001_initial.py` | Full consolidated PostgreSQL schema (31 tables + indexes + FKs) |
| `002_seed.py` | Version metadata rows, `qr_key` backfill, default `admin` platform admin |
| `003_payment_method.py` | `payment_entries`: `payment_method`, `external_id`, `reference`, `notes` (+ unique index on `external_id`) |

---

## Domain Groups

### 1. Core Rental Data

#### `tenants`
The central tenant record. Purpose: tenant identity, rent/utility billing params, PIN + password auth state, landlord/property assignment.

Columns: `id` (PK), `name`, `company`, `phone`, `email`, `address`, `roomnumber`, `occupation`, `notes`, `status`, `rent`, `water`, `electricityrate`, `previousmeter`, `additionalpersoncharge`, `securitydeposit`, `defaulttankWatercharge`, `meterid`, `viewToken`, `tenantpin`, `failed_attempts`, `locked_until`, `status_changed_at`, `qr_key`, `tenant_username`, `password_hash`, `password_failed_attempts`, `password_locked_until`, `password_reset_token_hash`, `password_reset_expires_at`, `password_reset_requested_at`, `password_reset_required`, `last_password_change_at`, `landlord_id`, `property_id`.

Indexes: `idx_tenants_qr_key`, `idx_tenants_landlord_id`, `idx_tenants_property_id`, unique partial `idx_tenants_tenant_username` (WHERE username NOT NULL and non-empty). FKs: `landlord_id → landlord_accounts`, `property_id → landlord_properties`.

Used by: `tenant_service`, `billing_service`, `tenant_recovery_service`, `import_engine`, `api/sync`, `backup_service`, `property_repository`, `routers/platform_admin`, `routers/landlordauth`, `routers/auth`, `api/public`, `api/tenants`.

#### `receipts`
Bills / receipts issued to tenants. Purpose: full bill record (meter reading, rent/utility breakdown, totals), status lifecycle, payment-status tracking, settlement fields.

Columns: `id` (UNIQUE, non-PK), `billNo` (**PK**), `date`, `month`, `tenantId`, `tenant`, `property_id`, `previous`, `current`, `units`, `rent`, `additional`, `water`, `tankWater`, `electricity`, `total`, `pdf`, `tenantphone`, `tenantcompany`, `tenantaddress`, `rate`, `status`, `archiveddate`, `archivedby`, `deleteddate`, `additionalpersons`, `additionalpersonrate`, `receiptversion`, `generatedby`, `paymentstatus`, `maintenancecharge`, `maintenancedesc`, `previousarrears`, `amountreceived`, `landlord_id`, `settled_by_bill_no`, `settlement_type`, `settled_at`, `settlement_amount`.

Indexes: `idx_receipts_tenant`, `idx_receipts_status`, `idx_receipts_paymentstatus`, `idx_receipts_tenantId`, `idx_receipts_landlord_id`. FKs: `property_id → landlord_properties`, `landlord_id → landlord_accounts`.

Used by: `billing_service`, `payment_service`, `tenant_service`, `tenant_recovery_service`, `import_engine`, `api/sync`, `backup_service`, `routers/platform_admin`, **`scripts/recalculate_payment_status.py`**.

#### `payment_entries`
Ledger of payment transactions against bills. Purpose: money-in ledger; the invariant `receipts.amountreceived == SUM(ACTIVE payment_entries)` underpins the V2 payment-status engine. Unique `external_id` makes imports idempotent.

Columns (`001`/`002` base): `id` (PK), `billNo`, `tenantId`, `landlord_id`, `payment_date`, `amount`, `created_at`, `updated_at`, `created_by`, `updated_by`, `status`, `payment_type`, `source`. **`003` additions**: `payment_method`, `external_id`, `reference`, `notes`.

Indexes: `idx_payment_entries_bill`, `idx_payment_entries_tenant`, `idx_payment_entries_date`, `idx_payment_entries_landlord`, `idx_payment_entries_status`, `idx_payment_entries_method`, unique partial `idx_payment_entries_external_id` (WHERE external_id NOT NULL). FK: `billNo → receipts(billNo)` ON DELETE CASCADE.

Used by: `payment_service`, `billing_service`, `import_engine`, `export_engine`, `scripts/recalculate_payment_status.py`.

#### `payment_allocations`
Per-bill split of each payment entry. Purpose: allocate a payment across current bill / arrears / advance buckets.

Columns: `id` (PK), `payment_entry_id`, `tenant_id`, `bill_no`, `allocated_amount`, `allocation_type`, `created_at`.

Indexes: `idx_payment_allocations_tenant`, `idx_payment_allocations_bill` (tenant_id, bill_no), `idx_payment_allocations_payment`. FK: `payment_entry_id → payment_entries(id)` ON DELETE CASCADE.

Used by: `payment_service` (only).

#### `occupants`
Occupant/KYC records attached to tenants. Purpose: occupant identity + uploaded KYC documents (Aadhaar, employment).

Columns: `id` (UNIQUE, non-PK), `tenantId`, `occupantUuid` (**PK**), `name`, `mobile`, `address`, `residentSince`, `status`, `aadhaar_front`, `aadhaar_back`, `aadhaar_combined`, `emp_front`, `emp_back`, `uploaddate`, `uploadmonth`, `landlord_id`.

Indexes: `idx_occupants_tenantId`, `idx_occupants_landlord_id`. FK: `tenantId → tenants`, `landlord_id → landlord_accounts`.

Used by: `tenant_service`, `tenant_recovery_service`, `backup_service`, `routers/platform_admin`, `api/public`, `api/tenants`.

#### `tenant_recovery_snapshots`
Recovery/backup snapshots for tenant restore. **Note: this table has duplicate DDL — created both in the migration and self-managed by the service.** See Duplicate Analysis.

Columns: `id` (PK, **TEXT** in live dev DB — service-created DDL, not migration's bigint; note in Duplicate Analysis), `tenant_id`, `tenant_name`, `landlord_id`, `created_at`, `expires_at`, `deleted_by`, `status`, `archive_path`, `sha256`, `metadata_json`, `restored_at`, `purged_at`.

Indexes: `idx_tenant_recovery_expiry`, `idx_tenant_recovery_landlord` (both present in live dev DB).

Used by: `tenant_recovery_service` (only).

---

### 2. Authentication & Sessions

#### `admins`
Platform admin accounts. Purpose: admin login, platform-admin flag, TOTP, Telegram 2FA chat link, lockout state.

Columns: `id` (PK), `username`, `password_hash`, `totp_secret`, `email`, `is_platform_admin`, `telegram_chat_id`, `failed_attempts`, `locked_until`, `created_at`, `updated_at`.

Used by: `routers/platform_admin`, `routers/admin_auth`, `database/auth_repository`, `services/telegram_otp_service`, `migrations/002_seed`.

#### `landlord_accounts`
Landlord auth accounts. Purpose: landlord login, TOTP, privacy/terms consent, temporary password + setup workflow, Google OAuth linking.

Columns: `id` (PK), `landlord_uuid`, `full_name`, `email`, `phone`, `username`, `password_hash`, `status`, `created_at`, `updated_at`, `totp_secret`, `totp_enabled`, `privacy_consented`, `privacy_version`, `privacy_accepted_at`, `privacy_accepted_ip`, `privacy_accepted_user_agent`, `requires_password_change`, `temp_password_created_at`, `temp_password_consumed`, `failed_attempts`, `locked_until`, `google_sub`, `auth_provider`, `avatar_url`, `terms_consented`, `terms_version`, `terms_accepted_at`, `terms_accepted_ip`, `terms_accepted_user_agent`, `setup_completed`, `setup_skipped`.

Indexes: `idx_landlord_accounts_username`, unique partial `idx_landlord_accounts_google_sub` (WHERE google_sub NOT NULL and non-empty).

Used by: `database/landlord_repository`, `routers/landlordauth`, `routers/platform_admin`, `services/google_oauth_service`, `database/property_repository`, `authentication/landlord/middleware`, `api/public`.

#### `admin_sessions` / `tenant_sessions` / `landlord_sessions`
Sessions per actor. **Identical schema shape used for three different actor types (duplicate shape — see Duplicate Analysis).**

Common columns: `session_id` (PK), `<actor>_id`, `refresh_token_hash`, `device_name`, `browser`, `os`, `ip_address`, `created_at`, `last_activity`, `expires_at`, `revoked_at`, `remember_me`, `status`.

- `admin_sessions` — FK `admin_id → admins`. Used by `platform_admin`, `auth_repository`, `authentication/admin/sessions`.
- `tenant_sessions` — FK `tenantId → tenants`. Used by `authentication/tenant/sessions`, `auth_repository`, `tenant_recovery_service`, `import_engine`, `api/sync`.
- `landlord_sessions` — FK `landlord_id → landlord_accounts`. Used by `authentication/landlord/sessions`.

#### `admin_login_otps`
One-time PINs for admin Telegram 2FA login.

Columns: `id` (PK), `admin_id`, `otp_hash`, `expires_at`, `attempts`, `used`, `created_at`. FK `admin_id → admins` ON DELETE CASCADE.

Used by: `services/telegram_otp_service`.

#### `tenant_password_history`
History of tenant password hashes (for reuse-check).

Columns: `id`, `tenantId`, `password_hash`, `changed_at`, `changed_by`. FK `tenantId → tenants`.

Used by: `api/public`, `api/tenants`.

#### `tenant_password_reset_events`
Self-service password-reset event tracking.

Columns: `id`, `tenantId`, `channel`, `token_hash`, `created_at`, `expires_at`, `used_at`, `requested_ip`. FK `tenantId → tenants`.

Used by: `api/public`.

#### `tenantPin_history`
History of tenant PIN hashes (last-5 reuse-check). **Same "history" shape as `tenant_password_history` but for the PIN.**

Columns: `id`, `tenantId`, `pin_hash`, `changed_at`. FK `tenantId → tenants`.

Used by: `api/tenants`, `import_engine`, `api/sync`, `tenant_recovery_service`.

#### `tenantPin_admin_store`
Admin-encrypted tenant PIN (Fernet). **Twin of `landlord_password_admin_store` (admin-store pattern) — see Duplicate Analysis.**

Columns: `tenantId` (PK), `encrypted_pin`, `updated_at`. FK `tenantId → tenants`.

Used by: `api/tenants`, `routers/platform_admin`, `api/whatsapp`, `api/sync`, `import_engine`, `export_engine`, `tenant_recovery_service`.

#### `landlord_password_admin_store`
Admin-set landlord password store (encrypted). Twin of `tenantPin_admin_store`.

Columns: `landlord_id` (PK), `encrypted_password`, `updated_at`. FK `landlord_id → landlord_accounts`.

Used by: `routers/landlordauth`, `routers/platform_admin`.

#### `landlords` (legacy proxy table)
Legacy read-only proxy mapping `admin_id` → `landlordUuid`. Purpose: backward-compatible legacy landlord PIN-login routing only. Distinct from `landlord_accounts` (see Duplicate Analysis).

Columns: `id` (PK), `admin_id`, `landlordUuid`, `active`. FK `admin_id → admins`.

Used by: `routers/landlord_routes` (read-only `SELECT`).

---

### 3. Privacy / Consent / Config

| Table | Purpose | Columns | Used by |
|---|---|---|---|
| `landlord_ui_config` | Per-landlord UI theme | `landlorduuid` (PK), `theme`, `updated_at` | `api/settings` |
| `landlord_profiles` | Landlord config blob | `landlord_id` (PK), `config_json`, `updated_at` | `property_repository`, `landlord_config_service` |
| `landlord_privacy_consents` | Privacy-version consents | `id`, `landlord_id`, `privacy_version`, `accepted`, `accepted_at`, `accepted_ip`, `accepted_user_agent` | `landlord_repository` |
| `landlord_terms_consents` | Terms-version consents | `id`, `landlord_id`, `terms_version`, `accepted`, `accepted_at`, `accepted_ip`, `accepted_user_agent` | `landlord_repository` |
| `landlord_properties` | Properties under a landlord | `id`, `landlord_id`, `property_name`, `address`, `sort_order`, `created_at`, `updated_at` | `property_repository`, `api/public` |

---

### 4. Audit Logs

| Table | Purpose | Columns | Used by |
|---|---|---|---|
| `tenant_audit_logs` | Tenant-action audit | `id`, `tenantId`, `action`, `ip_address`, `created_at`, `meta_json` | `auth_repository`, `platform_admin`, `landlordauth`, `api/public`, `core/audit`, `tenant_recovery_service` |
| `landlord_audit_logs` | Landlord-action audit | `id`, `landlord_id`, `action`, `ip_address`, `created_at`, `meta_json` | `landlord_repository`, `landlordauth`, `platform_admin`, `core/audit` |
| `platform_admin_audit_logs` | Platform-admin-action audit | `id`, `admin_id`, `action`, `target_type`, `target_id`, `ip_address`, `meta_json`, `created_at` | `core/audit`, `platform_admin` |
| `tenant_qr_feedback` | QR login-failure feedback / support | `id`, `tenant_id`, `landlord_id`, `property_id`, `tenant_name`, `view_token`, `qr_key`, `message`, `diagnostics_json`, `failed_attempts`, `status`, `admin_reply`, `resolved_at`, `resolved_by`, `created_at`, `ip_address` | `api/public`, `routers/platform_admin` |

The three audit tables share near-identical shape, differentiated by actor (see Duplicate Analysis).

---

### 5. Import / Sync / Ops

| Table | Purpose | Columns | Used by |
|---|---|---|---|
| `import_jobs` | Import job header | `id`, `created_at`, `created_by`, `filename`, `status`, `preview_json`, `resolution_json`, `result_json` | `import_engine`, `api/sync` |
| `import_job_items` | Per-row import result | `id`, `import_job_id`, `target_key`, `import_tenant_id`, `import_tenant_name`, `action`, `existing_tenant_id`, `result`, `message` | `import_engine`, `api/sync` |
| `app_metadata` | Key/value metadata | `key` (PK), `value` | migrations only — **no runtime app references** |
| `schema_migrations` | Migration ledger | `version` (PK), `name`, `applied_at` | `migrator.py` only |

---

## Duplicate Schema Analysis

### A. Genuine duplicate DDL (same table, two definitions — drift risk)
**`tenant_recovery_snapshots`** was previously created in **two places** with slightly different schemas:

- `migrations/001_initial.py:383` — defines the table **without** `landlord_id`.
- `services/tenant_recovery_service.py` — `_init_snapshots_table()` defined the table **with** `landlord_id`, plus an idempotent `ALTER TABLE ... ADD COLUMN landlord_id` reconciler.

Same table, same purpose; the service self-managed schema the migration already owns. Result: the migration version was missing `landlord_id` until the service reconciler ran. **This was the only true duplicated DDL in the schema.**

**Resolved in the camelCase migration (`004_camel_case.py`) + the service neutrality change:** 004 adds `landlord_id INTEGER` (skip if present) inside a versioned migration and creates `idx_tenantRecoverySnapshots_landlordId (landlordId, status)` via `CREATE INDEX IF NOT EXISTS`; `_init_snapshots_table()` no longer runs any DDL — it is a pure `information_schema` existence check that raises `RuntimeError` (run migrations) when the table is missing.

> **Live-verified (dev DB):** the running service reconciler has already applied — the live `tenant_recovery_snapshots` **has** `landlord_id` (INTEGER, nullable) and `id` is TEXT (matching the migration's `TEXT PRIMARY KEY`). So the live dev DB matches the **service** definition on the `landlord_id` column, but 001 lacked it; a fresh DB created purely from migrations would lack `landlord_id` until the service touches the table. `004_camel_case.py` now reconciles this column (and its index) in a versioned migration instead of runtime DDL.

### B. Duplicate schema shape — intentional, used for different actors
Identical (or near-identical) column shapes reused across distinct actor tables. These are intentional — not bugs.

- **Session tables (×3):** `admin_sessions`, `tenant_sessions`, `landlord_sessions` have byte-for-byte identical columns; each stores refresh-token sessions for a **different actor** (admin / tenant / landlord).
- **Audit log tables (×3):** `tenant_audit_logs`, `landlord_audit_logs`, `platform_admin_audit_logs` have near-identical columns (platform variant adds `target_type`/`target_id`); each logs a **different actor**.
- **Admin-secret store tables (×2):** `tenantPin_admin_store` and `landlord_password_admin_store` share the same "admin-encrypted secret" shape (`<actor>_id` PK, `encrypted_*`, `updated_at`) but store **different secret types**: tenant **PINs** vs landlord **passwords**, using different encryption (Fernet PIN vault vs password encryption).
- **Secret-history tables (×N):** `tenantPin_history`, `tenant_password_history`, `tenant_password_reset_events` share the "history/event per tenant" shape for different secret lifecycles (PIN vs password vs reset events).

### C. Similar-purpose but distinct tables
- **`landlords` (legacy proxy) vs `landlord_accounts` (real auth):** same domain, different eras. `landlords` is a read-only legacy routing proxy (`admin_id` → `landlordUuid`); `landlord_accounts` is the actual landlord auth store. They are **not duplicates** — only `landlords` is legacy.
- **`payment_entries` vs `payment_allocations`:** the transaction ledger vs the per-bill split of each payment. Related but distinct — not duplicates.

---

## Live DB Drift Notes

_Generated from a live query of the **dev** database on host `192.168.1.50` (SSH 22009), executed inside the `propaura_backend_dev` container via `app.db.connection`. Snapshot: tables + row counts, `information_schema.columns`, `pg_indexes`, `information_schema` FK join._

### Verified inventory (live dev DB)

- **31 tables** (30 app + `schema_migrations`), **328 columns**, **79 indexes**, **25 FK constraints**.
- Row counts (non-zero): `admin_sessions`=2, `admins`=1, `app_metadata`=4, `landlord_accounts`=2, `landlord_audit_logs`=17, `landlord_password_admin_store`=2, `landlord_privacy_consents`=2, `landlord_profiles`=1, `landlord_properties`=1, `landlord_sessions`=114, `landlord_terms_consents`=2, `landlord_ui_config`=1, `platform_admin_audit_logs`=12, `schema_migrations`=3. All billing/tenant/import tables are empty (`tenants`=0, `receipts`=0, `payment_entries`=0, `payment_allocations`=0, `occupants`=0, imports=0).
- `schema_migrations` = 3 applied (001, 002, 003) — ledger matches the three migration files.

### Notes and deviations vs migration source

1. **`tenant_recovery_snapshots` is the only table where the live DB differs from the migration DDL.** Live has `landlord_id` (INTEGER, nullable) and `id` is TEXT. This is the service reconciler (`services/tenant_recovery_service.py`) having already run — see Duplicate Analysis §A.

2. **PostgreSQL folds unquoted identifiers to lowercase.** Migration source uses camelCase column names (`billNo`, `tenantId`, `tenantpin`, `qr_key` → mixed), but PostgreSQL stores and reports them folded: `billno`, `tenantid`, `tenantpin`, `tenant_username`… Matching in SQL is case-insensitive for unquoted identifiers; the app's `_FlexRow` row factory (connection.py:32) case-folds `row["billNo"]` → `billno` to keep the SQLite-era call sites working.

3. **`tenant_recovery_snapshots.id` type** is `TEXT PRIMARY KEY` in **both** the migration source (`001_initial.py:384`) and the service DDL — there is **no type drift**. The only actual drift was the **missing `landlord_id INTEGER` column** (present in service DDL, absent in 001) plus its `idx_tenant_recovery_landlord` index. This was resolved in `004_camel_case.py` (adds the column + `idx_tenantRecoverySnapshots_landlordId` if missing) and by neutralizing `_init_snapshots_table` to a pure existence check (no runtime DDL).

4. **Index inventory is consistent with the documented set.** Verified live index names match the migration-declared indexes (tenants, receipts, payment_entries, payment_allocations, occupants, landlord_accounts, sessions, audit logs, qr feedback, recovery snapshots). Column-name case in index definitions is folded PostgreSQL-lowercase.

5. **Unique constraints present in live DB beyond the doc's main list** (documented/indexed or legacy-consistent): `admins.username`, `landlord_accounts.email`, `landlord_accounts.landlord_uuid`, `landlord_accounts.username` (+ a duplicate non-unique `idx_landlord_accounts_username`), `landlords.landlorduuid`, `occupants.id`, `receipts.id`. These are all UNIQUE indexes — consistent with the source DDL.

6. **`payment_entries.external_id`** is a **unique partial index** (`CREATE UNIQUE INDEX ... WHERE external_id IS NOT NULL`) — confirmed live, enables idempotent imports.

7. **No `export_*` / `import_*` drift:** `import_jobs` / `import_job_items` columns match migration; they are unused (0 rows) in the empty dev DB.

8. **`tenant_qr_feedback`** FK to `tenants` was NOT present as a formal FK constraint in the live FK join — the source defines the tenant linkage as a plain indexed column (`idx_tenant_qr_feedback_landlord`, `idx_tenant_qr_feedback_status`) alongside `tenant_id`, not as a FK. (No drift — matches source.)

### FK constraint summary (verified, 25 total)

`admin_login_otps.admin_id → admins.id`, `admin_sessions.admin_id → admins.id`, `tenant_password_history.tenantid → tenants.id`, `tenant_password_reset_events.tenantid → tenants.id`, `tenantpin_history.tenantid → tenants.id`, `tenantpin_admin_store.tenantid → tenants.id`, `tenant_sessions.tenantid → tenants.id`, `payment_entries.billno → receipts.billno`, `payment_allocations.payment_entry_id → payment_entries.id`, `occupants.tenantid → tenants.id` (+ `occupants.landlord_id → landlord_accounts.id`), `import_job_items.import_job_id → import_jobs.id`, `landlord_sessions.landlord_id → landlord_accounts.id`, `landlord_audit_logs.landlord_id → landlord_accounts.id`, `landlords.admin_id → admins.id`, `landlord_properties.landlord_id → landlord_accounts.id`, `landlord_profiles.landlord_id → landlord_accounts.id`, `landlord_privacy_consents.landlord_id → landlord_accounts.id`, `landlord_terms_consents.landlord_id → landlord_accounts.id`, `landlord_password_admin_store.landlord_id → landlord_accounts.id`, `platform_admin_audit_logs.admin_id → admins.id`, `tenants.landlord_id → landlord_accounts.id`, `tenants.property_id → landlord_properties.id`, `receipts.property_id → landlord_properties.id`, `receipts.landlord_id → landlord_accounts.id`.
