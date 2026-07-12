I'll generate a complete, production-ready final database schema that consolidates everything from all your migrations into a single, clean initialization script
Now let me also create the raw SQL version for direct execution, and a combined init script that replaces your existing `init_db()` entirely
Here are all the production-ready files:

## Download Links

| File | Purpose |
|------|---------|
| [final_schema.py](sandbox:///mnt/agents/output/final_schema.py) | Standalone Python script — run `python final_schema.py` to init a fresh DB |
| [final_schema.sql](sandbox:///mnt/agents/output/final_schema.sql) | Raw SQL — execute via `sqlite3 rent.db < final_schema.sql` |
| [init_db_replacement.py](sandbox:///mnt/agents/output/init_db_replacement.py) | Copy-paste replacement for `app/core/db.py` `init_db()` function |
| [m005_recovery_view_tokens.py](sandbox:///mnt/agents/output/m005_recovery_view_tokens.py) | Emergency fix for your current broken production DB |
| [m005_backfill_view_tokens_FIXED.py](sandbox:///mnt/agents/output/m005_backfill_view_tokens_FIXED.py) | Fixed migration that checks column existence instead of just version |

---

## Final Schema Overview (10 Tables, 6 Indexes)

| # | Table | Purpose |
|---|-------|---------|
| 1 | `app_metadata` | Schema version tracking |
| 2 | `admins` | Admin accounts with TOTP |
| 3 | `admin_sessions` | Admin session management (Auth V2) |
| 4 | `tenants` | Core tenant data + `view_token`, `tenantpin`, `failed_attempts`, `locked_until` |
| 5 | `tenant_pin_history` | PIN change audit trail |
| 6 | `tenant_pin_admin_store` | Encrypted PIN vault for admin reveal |
| 7 | `tenant_sessions` | Tenant session management (Auth V2) |
| 8 | `tenant_audit_logs` | Tenant action audit |
| 9 | `receipts` | Billing records with `tenant_id`, `paymentstatus`, `maintenancecharge`, `previousarrears`, `amountreceived` |
| 10 | `occupants` | KYC/occupant data |

**Schema Versions:** `auth=1`, `receipt=1`, `tenant=2`

---

## To Fix Your Current Production DB Right Now

```bash
# Option A: One-liner inside Docker
docker exec -it rent-app-20081 python -c "
import sqlite3, uuid
DB = '/code/storage/database/rent.db'
conn = sqlite3.connect(DB)
cols = [r[1] for r in conn.execute('PRAGMA table_info(tenants)')]
if 'view_token' not in cols:
    conn.execute('ALTER TABLE tenants ADD COLUMN view_token TEXT')
    for tid, name in conn.execute('SELECT id, name FROM tenants'):
        conn.execute('UPDATE tenants SET view_token=? WHERE id=?', (str(uuid.uuid4()), tid))
    conn.execute(\"INSERT OR REPLACE INTO app_metadata VALUES ('tenant_schema_version','2')\")
    conn.commit()
    print('Fixed!')
else:
    print('Already OK')
conn.close()
"
docker restart rent-app-20081
```

```bash
# Option B: Copy and run the recovery script
docker cp /mnt/agents/output/m005_recovery_view_tokens.py rent-app-20081:/code/
docker exec rent-app-20081 python /code/m005_recovery_view_tokens.py
docker restart rent-app-20081
```