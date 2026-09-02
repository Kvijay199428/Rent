"""
Schema migration runner for PROPAURA (PostgreSQL).

Migrations are plain-Python modules under app/db/migrations, each exposing:
    up(conn)      - apply the migration
    down(conn)    - revert the migration (best effort)

Version tracking lives in a dedicated table `schema_migrations` so the
application schema (app_metadata) is not polluted by infra bookkeeping.

Usage (command line, inside the backend container):
    python -m app.db.migrations.migrator up
    python -m app.db.migrations.migrator up --target 003
    python -m app.db.migrations.migrator down --target 001
    python -m app.db.migrations.migrator status
"""

import importlib
import os
import pkgutil
import sys

from app.db.connection import init_pool, close_pool, get_conn


MIGRATIONS_PKG = "app.db.migrations"
TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT now()::text
)
"""


def _discover() -> list:
    mods = []
    for m in pkgutil.iter_modules(importlib.import_module(MIGRATIONS_PKG).__path__):
        if m.name == "__init__" or m.name.startswith("_"):
            continue
        try:
            seq = int(m.name.split("_", 1)[0])
        except ValueError:
            continue
        mods.append((seq, m.name))
    mods.sort()
    return mods


def _applied(conn) -> dict:
    conn.execute(TABLE_SQL)
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {r["version"] for r in rows}


def _record(conn, version, name):
    conn.execute(
        "INSERT INTO schema_migrations (version, name) VALUES (%s, %s) "
        "ON CONFLICT (version) DO NOTHING",
        (version, name),
    )


def _forget(conn, version):
    conn.execute("DELETE FROM schema_migrations WHERE version = %s", (version,))


def _load(name):
    mod = importlib.import_module(f"{MIGRATIONS_PKG}.{name}")
    if not hasattr(mod, "up"):
        raise RuntimeError(f"migration {name} has no up()")
    return mod


def _applied_versions() -> set:
    with get_conn() as conn:
        return _applied(conn)


def _apply_one(name):
    mod = _load(name)
    with get_conn() as tx:
        mod.up(tx)
        _record(tx, name.split("_", 1)[0], name)
    print(f"[migrate] applied {name}")


def _revert_one(name):
    mod = _load(name)
    if not hasattr(mod, "down"):
        raise RuntimeError(f"migration {name} has no down()")
    with get_conn() as tx:
        mod.down(tx)
        _forget(tx, name.split("_", 1)[0])
    print(f"[migrate] reverted {name}")


def up(target=None):
    init_pool()
    try:
        applied = _applied_versions()
        for seq, name in _discover():
            if str(seq) in applied:
                continue
            if target and seq > int(target):
                break
            _apply_one(name)
            applied.add(str(seq))
        print("[migrate] up to date")
    finally:
        close_pool()


def down(target=None):
    init_pool()
    try:
        applied = _applied_versions()
        for seq, name in reversed(_discover()):
            if str(seq) not in applied:
                continue
            if target and seq <= int(target):
                continue
            _revert_one(name)
    finally:
        close_pool()


def status():
    init_pool()
    try:
        applied = _applied_versions()
        print(f"{'SEQ':<6} {'NAME':<40} STATE")
        for seq, name in _discover():
            state = "applied" if str(seq) in applied else "pending"
            print(f"{seq:<6} {name:<40} {state}")
    finally:
        close_pool()


if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    target = None
    for i, a in enumerate(args):
        if a == "--target" and i + 1 < len(args):
            target = args[i + 1]
    if cmd == "up":
        up(target)
    elif cmd == "down":
        down(target)
    elif cmd == "status":
        status()
    else:
        print(__doc__)
        sys.exit(2)
