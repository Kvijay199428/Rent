"""
PostgreSQL persistence facade (replaces the SQLite core/db.py).

Keeps the historical import/API contract so the rest of the application is
unchanged:
    from app.core.db import get_conn      # same name, same signature
    with get_conn() as conn:
        rows = conn.execute("SELECT ... %s", (args,)).fetchall()

The implementation delegates to app.db.connection (psycopg_pool bounded pool).
`init_db` now applies the versioned PostgreSQL migrations.
"""

from app.db.connection import get_conn, init_pool
from app.db.migrations import migrator


def init_db():
    """Initialize the database schema (PostgreSQL migrations).

    Idempotent: only pending migrations are applied. Opens the pool first.
    """
    init_pool()
    migrator.up()


def migrate(target=None):
    """Alias for the migration runner (exposes up/down/status programmatically)."""
    if target is None:
        migrator.up()
    else:
        migrator.up(target)
