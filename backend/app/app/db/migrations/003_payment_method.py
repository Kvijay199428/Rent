"""
Migration 003: Payment transaction extensibility for PROPAURA (PostgreSQL).

Schema V2 (Import/Export) additions to `payment_entries`:

    payment_method  TEXT  CASH | UPI | BANK_TRANSFER | CHEQUE | CARD | ONLINE | OTHER
    external_id     TEXT  portable payment identity (PAY-<tenantId>-<billNo>-<seq>)
    reference       TEXT  operator reference (e.g. UPI transaction id / cheque no.)
    notes           TEXT  free-text note

The partial unique index on external_id enforces the import/export invariant
that a payment transaction is imported/upserted exactly once (idempotent
re-import), keeping internal BIGSERIAL `id` values separate from the portable
`external_id` identity.
"""


def up(conn):
    cur = conn.cursor()

    cur.execute(
        "ALTER TABLE payment_entries "
        "ADD COLUMN IF NOT EXISTS payment_method TEXT NOT NULL DEFAULT 'OTHER'"
    )
    cur.execute("ALTER TABLE payment_entries ADD COLUMN IF NOT EXISTS external_id TEXT")
    cur.execute("ALTER TABLE payment_entries ADD COLUMN IF NOT EXISTS reference TEXT")
    cur.execute("ALTER TABLE payment_entries ADD COLUMN IF NOT EXISTS notes TEXT")

    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_payment_entries_method "
        "ON payment_entries(payment_method)"
    )
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_entries_external_id "
        "ON payment_entries(external_id) WHERE external_id IS NOT NULL"
    )

    conn.commit()


def down(conn):
    cur = conn.cursor()

    cur.execute("DROP INDEX IF EXISTS idx_payment_entries_external_id")
    cur.execute("DROP INDEX IF EXISTS idx_payment_entries_method")
    cur.execute("ALTER TABLE payment_entries DROP COLUMN IF EXISTS notes")
    cur.execute("ALTER TABLE payment_entries DROP COLUMN IF EXISTS reference")
    cur.execute("ALTER TABLE payment_entries DROP COLUMN IF EXISTS external_id")
    cur.execute("ALTER TABLE payment_entries DROP COLUMN IF EXISTS payment_method")

    conn.commit()