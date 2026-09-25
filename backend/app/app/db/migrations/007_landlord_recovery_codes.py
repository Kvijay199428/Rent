"""
Migration 007: landlordRecoveryCodes table for TOTP backup codes (PROPAURA, PostgreSQL).

Landlords with TOTP enabled can generate a batch of single-use recovery
(backup) codes. Only the SHA-256 hash of each normalized code is stored; the
plaintext codes are shown to the landlord exactly once at generation time.
At login, a code that fails TOTP validation may be traded for a valid
unused recovery code.

Columns (camelCase per schema standard):
  - id          BIGSERIAL PK
  - landlordId  owning landlordAccounts.id (cascade delete)
  - codeHash    SHA-256 hex of the normalized plaintext code
  - used        0 = available, 1 = consumed
  - usedAt      ISO timestamp when consumed
  - createdAt   issuance timestamp
"""

RECOVERY_CODES_TABLE = "landlordRecoveryCodes"


def up(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = %s",
        (RECOVERY_CODES_TABLE,),
    )
    if cur.fetchone() is not None:
        return
    cur.execute(
        '''
        CREATE TABLE "landlordRecoveryCodes" (
            id           BIGSERIAL PRIMARY KEY,
            "landlordId" INTEGER NOT NULL REFERENCES "landlordAccounts"(id) ON DELETE CASCADE,
            "codeHash"   TEXT NOT NULL,
            "used"       SMALLINT NOT NULL DEFAULT 0,
            "usedAt"     TEXT,
            "createdAt"  TEXT NOT NULL
        )
        '''
    )
    cur.execute(
        'CREATE INDEX "idx_landlordRecoveryCodes_landlordId_used" '
        'ON "landlordRecoveryCodes"("landlordId", "used")'
    )


def down(conn):
    """Best-effort reverse: drop the table."""
    cur = conn.cursor()
    cur.execute('DROP TABLE IF EXISTS "landlordRecoveryCodes"')