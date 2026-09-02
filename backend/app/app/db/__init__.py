"""PostgreSQL persistence package for PROPAURA.

Provides:
    connection  - psycopg_pool bounded pool + get_conn() context manager
    migrations  - versioned schema migrations (see migration command)

Import the app-facing handle from here for convenience:
    from app.db import get_conn
"""

from app.db.connection import (
    get_conn,
    init_pool,
    close_pool,
    build_dsn,
)

__all__ = [
    "get_conn",
    "init_pool",
    "close_pool",
    "build_dsn",
]
