"""
Migration 002: Initial seed / idempotent backfills (PostgreSQL).

Ports the pure-SQL backfills from the SQLite core/db.py init that do not
depend on application Python code:

  * ensure `app_metadata` version rows exist
  * backfill tenants.qr_key with a random hex key (md5(random()::text))
  * seed the default platform admin (admin/<pin>) so first login works

Backfills that require application logic (payment_entries legacy migration,
payment_allocations recompute) are executed post-cutover in Phase O, where the
source SQLite data and the app services are both available.
"""

from app.authentication.common.utils import hash_pin


def up(conn):
    cur = conn.cursor()

    # Ensure app_metadata version rows exist
    for key, value in (
        ("auth_schema_version", "2"),
        ("receipt_schema_version", "1"),
        ("tenant_schema_version", "3"),
        ("landlord_schema_version", "1"),
    ):
        cur.execute(
            "INSERT INTO app_metadata (key, value) VALUES (%s, %s) "
            "ON CONFLICT (key) DO NOTHING",
            (key, value),
        )

    # Backfill qr_key (idempotent) - random 32-hex key matching SQLite
    # randomblob(16) lowercased hex.
    cur.execute(
        """
        UPDATE tenants
        SET qr_key = md5(random()::text || clock_timestamp()::text)
        WHERE qr_key IS NULL OR qr_key = ''
        """
    )

    # Seed default platform admin (admin/<pin>) if none exists.
    has_admin = cur.execute(
        "SELECT 1 FROM admins WHERE is_platform_admin = 1 LIMIT 1"
    ).fetchone()
    if not has_admin:
        cur.execute(
            """
            INSERT INTO admins (username, password_hash, is_platform_admin, created_at)
            SELECT 'admin', %s, 1, now()::text
            WHERE NOT EXISTS (SELECT 1 FROM admins WHERE username = 'admin')
            """,
            (hash_pin("admin"),),
        )

    conn.commit()


def down(conn):
    # Seed is logically a no-op to revert: qr_key stays, admin stays, metadata
    # stays. Leaving data intact is the correct downgrade behavior.
    pass
