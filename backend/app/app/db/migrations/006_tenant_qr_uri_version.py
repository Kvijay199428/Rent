"""
Migration 006: Add tenants.qrUriVersion for the QR-login URL scheme bump (PROPAURA, PostgreSQL).

The tenant QR portal URL scheme changed from /{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}
to /tenant/{landlordUuid}/QR/{propertyId}/{tenantId}/{viewToken}. Printed/stored QRs under the old
scheme are stale: their deep link no longer resolves to the tenant portal.

qrUriVersion tracks which URL-scheme generation a tenant's QR has been re-issued under:
  - 1 = legacy scheme (all pre-existing rows) -> landlord must regenerate QR
  - 2 = current scheme (set when the QR endpoint next serves that tenant's QR)

Backend constant CURRENT_QR_URI_VERSION = 2; the landlord notification surface reports a
"regenerate QR" notice while any of a landlord's tenants is below it.
"""

CURRENT_QR_URI_VERSION = 2


def up(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'tenants' AND column_name = 'qrUriVersion'"
    )
    if cur.fetchone() is None:
        cur.execute(
            'ALTER TABLE "tenants" ADD COLUMN "qrUriVersion" SMALLINT NOT NULL DEFAULT 1'
        )


def down(conn):
    """Best-effort reverse: drop the column (existing no-op guard included)."""
    cur = conn.cursor()
    cur.execute('ALTER TABLE "tenants" DROP COLUMN IF EXISTS "qrUriVersion"')