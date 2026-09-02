"""
PostgreSQL connection layer for PROPAURA (replaces SQLite core/db.py).

Uses psycopg 3 + psycopg_pool with a bounded connection pool.

DSN is built from environment variables. The database host/port match the
production container topology:
    dev  : propaura_database_dev   (:28004 internal)
    prod : propaura_database_prod  (:28013 internal)

Environment:
    RENT_PGHOST     (default: propaura_database_dev)
    RENT_PGPORT     (default: 28004)
    RENT_PGDATABASE (default: rent)
    RENT_PGUSER     (default: rent)
    RENT_PGPASSWORD (required at runtime; sourced from .env host secrets)
"""

import os
import logging

from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

DEFAULT_HOST = "propaura_database_dev"
DEFAULT_PORT = "28004"
DEFAULT_DB = "rent"
DEFAULT_USER = "rent"


def build_dsn() -> str:
    """Build a libpq connection string from environment variables."""
    host = os.environ.get("RENT_PGHOST", DEFAULT_HOST)
    port = os.environ.get("RENT_PGPORT", DEFAULT_PORT)
    dbname = os.environ.get("RENT_PGDATABASE", DEFAULT_DB)
    user = os.environ.get("RENT_PGUSER", DEFAULT_USER)
    password = os.environ.get("RENT_PGPASSWORD", "")
    import urllib.parse
    return (
        f"host={host} port={port} dbname={dbname} "
        f"user={urllib.parse.quote(user)} password={urllib.parse.quote(password)}"
    )


MIN_SIZE = int(os.environ.get("RENT_PGPOOL_MIN", "2"))
MAX_SIZE = int(os.environ.get("RENT_PGPOOL_MAX", "10"))
ACQUIRE_TIMEOUT = float(os.environ.get("RENT_PGPOOL_TIMEOUT", "5"))

_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=build_dsn(),
            min_size=MIN_SIZE,
            max_size=MAX_SIZE,
            open=False,           # lazy open; started explicitly
            kwargs={"row_factory": dict_row},
            check=ConnectionPool.check_connection,
            name="propaura-pg",
        )
    return _pool


def init_pool():
    """Open the connection pool. Called once at application startup."""
    pool = _get_pool()
    if not pool.closed:
        return
    pool.open(wait=True, timeout=30)
    logger.info("PostgreSQL connection pool opened (%s..%s connections)", MIN_SIZE, MAX_SIZE)


def close_pool():
    """Close the connection pool (shutdown path)."""
    global _pool
    if _pool is not None and not _pool.closed:
        _pool.close()
        logger.info("PostgreSQL connection pool closed")


class _Transaction:
    """Context manager returned by get_conn().

    Wraps ``ConnectionPool.connection()`` (the canonical acquire/return API)
    so the app-facing contract is unchanged from the SQLite era:

        with get_conn() as conn:
            rows = conn.execute("SELECT ...").fetchall()

    On __exit__ success -> commit and return the connection to the pool.
    On exception        -> rollback and return the connection to the pool.
    psycopg_pool also transparently replaces connections that fail the check.
    """

    def __init__(self, pool: ConnectionPool, timeout: float | None = None):
        self._pool = pool
        self._timeout = timeout
        self._cm = None
        self.conn = None

    def __enter__(self):
        self._cm = self._pool.connection(timeout=self._timeout)
        self.conn = self._cm.__enter__()
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._cm is not None:
                return self._cm.__exit__(exc_type, exc, tb)
        finally:
            self._cm = None
            self.conn = None
        return False


def get_conn(timeout: float | None = None):
    """App-facing database handle (see _Transaction docstring).

    Each `with` block is a transaction: it is committed on success and rolled
    back on exception. The underlying PostgreSQL connection is returned to the
    shared bounded pool afterwards. `timeout` bounds how long to wait for a
    free connection (defaults to RENT_PGPOOL_TIMEOUT / 5s).
    """
    if timeout is None:
        timeout = ACQUIRE_TIMEOUT
    return _Transaction(_get_pool(), timeout=timeout)


def check_database() -> tuple:
    """Best-effort health probe. Returns (ok, database_name_or_error). Never raises."""
    try:
        with get_conn(timeout=2.0) as conn:
            rows = conn.execute("SELECT current_database() AS db").fetchall()
            name = rows[0]["db"] if rows else "unknown"
        return True, name
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
