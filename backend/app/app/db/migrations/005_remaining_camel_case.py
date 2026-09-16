"""
Migration 005: Complete the camelCase normalization (PROPAURA, PostgreSQL).

004 renamed every identifier listed in its maps but left a deterministic set of
residual folded columns: columns that 001 defined as *unquoted mixed-case*
identifiers (folded to lowercase by PostgreSQL) and that 004's COLUMN_MAPS did
not include.

Before 005            (physical post-004)   After 005  (physical, quoted camel)
    tenants.viewtoken                        "viewToken"
    tenantPasswordHistory.tenantid           "tenantId"
    tenantPasswordResetEvents.tenantid       "tenantId"
    tenantPinHistory.tenantid                "tenantId"
    tenantPinAdminStore.tenantid             "tenantId"
    tenantSessions.tenantid                  "tenantId"
    tenantAuditLogs.tenantid                 "tenantId"
    receipts.billno / tenantid               "billNo" / "tenantId"
    paymentEntries.billno / tenantid         "billNo" / "tenantId"
    occupants.tenantid / occupantuuid /
              residentsince                  "tenantId" / "occupantUuid" /
                                             "residentSince"

Rules:
  - Column renames only; NO table renames (tables are already camel post-004).
  - Dual guard per rename: the folded old column must exist AND the camel new
    column must NOT already exist (idempotent, safe to re-run).
  - PostgreSQL natively re-points dependent indexes / FKs / constraint
    expressions when a column is renamed; 005 additionally re-normalizes
    constraint names that embedded the pre-rename folded attname (e.g.
    `fk_tenantSessions_tenantid` -> `fk_tenantSessions_tenantId`,
    `receipts_pkey` -> `pk_receipts_billNo`) using the same introspection
    helper convention 004 established.

This migration is the closing boundary of the Phase-2 normalization contract:
runtime SQL must quote these camelCase identifiers and access row keys exactly
as written here (see docs/database-column-mapping-v3.md).
"""

RESIDUAL_COLUMN_RENAMES = {
    # folded physical -> quoted camel target
    "tenants": {
        "viewtoken": "viewToken",
    },
    "tenantPasswordHistory": {
        "tenantid": "tenantId",
    },
    "tenantPasswordResetEvents": {
        "tenantid": "tenantId",
    },
    "tenantPinHistory": {
        "tenantid": "tenantId",
    },
    "tenantPinAdminStore": {
        "tenantid": "tenantId",
    },
    "tenantSessions": {
        "tenantid": "tenantId",
    },
    "tenantAuditLogs": {
        "tenantid": "tenantId",
    },
    "receipts": {
        "billno": "billNo",
        "tenantid": "tenantId",
    },
    "paymentEntries": {
        "billno": "billNo",
        "tenantid": "tenantId",
    },
    "occupants": {
        "tenantid": "tenantId",
        "occupantuuid": "occupantUuid",
        "residentsince": "residentSince",
    },
}


# ══ Guarded helpers ═════════════════════════════════════════════════════════

def _q(name):
    """Quote an identifier if it is not a bare lowercase word."""
    if name.islower() and all(c.isalnum() or c == "_" for c in name):
        return name
    return '"%s"' % name


def _table_exists(cur, table):
    cur.execute("SELECT to_regclass(%s)", ("public." + _q(table),))
    return cur.fetchone()["to_regclass"] is not None


def _column_exists(cur, table, column):
    cur.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s AND column_name = %s",
        (table, column),
    )
    return cur.fetchone() is not None


def _constraint_exists(cur, table, conname):
    cur.execute(
        "SELECT 1 FROM pg_constraint c "
        "JOIN pg_class cls ON cls.oid = c.conrelid "
        "JOIN pg_namespace n ON n.oid = cls.relnamespace "
        "WHERE n.nspname = 'public' AND cls.relname = %s AND c.conname = %s",
        (table, conname),
    )
    return cur.fetchone() is not None


# ══ Column renames (dual-guarded) ═══════════════════════════════════════════

def _rename_remaining_columns(cur):
    renamed = 0
    for table, colmap in RESIDUAL_COLUMN_RENAMES.items():
        if not _table_exists(cur, table):
            continue
        for old, new in colmap.items():
            if not _column_exists(cur, table, old):
                continue
            if _column_exists(cur, table, new):
                continue
            cur.execute(
                "ALTER TABLE %s RENAME COLUMN %s TO %s"
                % (_q(table), _q(old), _q(new))
            )
            renamed += 1
    return renamed


# ══ Constraint-name normalization (post-rename attnames) ════════════════════

def _pk_target(table_camel):
    return "pk_" + table_camel


def _uk_target(table_camel, col):
    return "uk_%s_%s" % (table_camel, col)


def _fk_target(table_camel, col):
    return "fk_%s_%s" % (table_camel, col)


def _rename_residual_constraints(cur):
    """Re-derive PK / UNIQUE / FK names from the now-camel attnames.

    Mirrors 004's introspection helper: only single-column constraints exist
    in this schema, and constraint names that already match the convention are
    skipped (no-op for every constraint 004 already normalized).
    """
    cur.execute(
        "SELECT DISTINCT ON (c.conname) c.conname, c.contype, a.attname, cls.relname "
        "FROM pg_constraint c "
        "JOIN pg_class cls ON cls.oid = c.conrelid "
        "JOIN pg_namespace n ON n.oid = cls.relnamespace "
        "JOIN pg_attribute a ON a.attrelid = c.conrelid "
        "    AND a.attnum = ANY(c.conkey) "
        "WHERE n.nspname = 'public' AND c.contype IN ('p', 'u', 'f') "
        "ORDER BY c.conname, a.attnum"
    )
    for row in cur.fetchall():
        conname = row["conname"]
        contype = row["contype"]
        attname = row["attname"]
        relname = row["relname"]
        if contype == "p":
            target = _pk_target(relname)
        elif contype == "u":
            target = _uk_target(relname, attname)
        else:
            target = _fk_target(relname, attname)
        if target == conname:
            continue
        if _constraint_exists(cur, relname, target):
            continue
        cur.execute(
            "ALTER TABLE %s RENAME CONSTRAINT %s TO %s"
            % (_q(relname), _q(conname), _q(target))
        )


# ══ up / down ═══════════════════════════════════════════════════════════════

def up(conn):
    cur = conn.cursor()

    # Step 1: dual-guarded residual column renames (folded -> quoted camel).
    _rename_remaining_columns(cur)

    # Step 2: normalize constraint names that embedded the folded attname.
    _rename_residual_constraints(cur)


def down(conn):
    """Best-effort reverse: restore the folded column names. Constraint names
    keep their camel form (consistent with 004's down(), which is best-effort
    and does not revert constraint renames)."""
    cur = conn.cursor()

    for table, colmap in reversed(list(RESIDUAL_COLUMN_RENAMES.items())):
        for old, new in reversed(list(colmap.items())):
            if _column_exists(cur, table, new) and not _column_exists(cur, table, old):
                cur.execute(
                    "ALTER TABLE %s RENAME COLUMN %s TO %s"
                    % (_q(table), _q(new), _q(old))
                )