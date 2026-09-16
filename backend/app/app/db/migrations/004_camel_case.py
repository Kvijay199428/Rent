"""
Migration 004: camelCase normalization for PROPAURA (PostgreSQL).

Applies the Phase 2 frozen contract (docs/database-column-mapping-v3.md):
every identifier becomes camelCase, stored *quoted* in PostgreSQL (mixed-case
identifiers require quoting). Finalizes the duplicate runtime DDL by
reconciling `tenant_recovery_snapshots.landlord_id` (present in service DDL,
absent from 001) inside a single versioned migration.

Steps (all guarded / non-destructive):
    1. Reconcile `tenant_recovery_snapshots.landlord_id INTEGER` (parity w/ service DDL).
    2. Column renames across all tables (folded source -> quoted camelCase target).
    3. Table renames (folded source -> quoted camelCase target).
    4. Constraint renames via `pg_constraint` introspection (pk_/uk_/fk_ prefixes).
    5. Explicit `idx_*` index renames via `ALTER INDEX ... RENAME TO`.
    6. Create `idx_tenantRecoverySnapshots_landlordId` if missing.

Guarding philosophy: every statement is preceded by an existence/wrong-guess
check (information_schema.columns, pg_constraint, to_regclass, pg_indexes) so
that a missing object or a mismatched auto-generated name skips harmlessly.
This makes the migration idempotent-ish and safe on both fresh (001+002+003
only) and existing (service-DDL-patched) databases.

NOTE: No conn.commit() inside up()/down() — the migrator owns the transaction.

Deployment: this MUST ship in the same release as the Phase 9/10 backend SQL
rewrite, because a snake_case column list stops resolving after renames and
the dict_row row factory resolves keys exactly (no case folding), so snake
lookups against renamed columns raise KeyError.
"""

# ── Column rename maps: {table: {folded_source: camel_target}} ──────────────
# `old` is the name as PostgreSQL folds it (lowercase) on creation.
# `new` is the stored camel word; mixed-case targets are quoted.

COLUMN_MAPS = {
    "admins": {
        "password_hash": "passwordHash",
        "totp_secret": "totpSecret",
        "is_platform_admin": "isPlatformAdmin",
        "telegram_chat_id": "telegramChatId",
        "failed_attempts": "failedAttempts",
        "locked_until": "lockedUntil",
        "created_at": "createdAt",
        "updated_at": "updatedAt",
    },
    "admin_login_otps": {
        "admin_id": "adminId",
        "otp_hash": "otpHash",
        "expires_at": "expiresAt",
        "created_at": "createdAt",
    },
    "admin_sessions": {
        "session_id": "sessionId",
        "admin_id": "adminId",
        "refresh_token_hash": "refreshTokenHash",
        "device_name": "deviceName",
        "ip_address": "ipAddress",
        "created_at": "createdAt",
        "last_activity": "lastActivity",
        "expires_at": "expiresAt",
        "revoked_at": "revokedAt",
        "remember_me": "rememberMe",
    },
    "tenant_sessions": {
        "session_id": "sessionId",
        "refresh_token_hash": "refreshTokenHash",
        "device_name": "deviceName",
        "ip_address": "ipAddress",
        "created_at": "createdAt",
        "last_activity": "lastActivity",
        "expires_at": "expiresAt",
        "revoked_at": "revokedAt",
        "remember_me": "rememberMe",
    },
    "landlord_sessions": {
        "session_id": "sessionId",
        "landlord_id": "landlordId",
        "refresh_token_hash": "refreshTokenHash",
        "device_name": "deviceName",
        "ip_address": "ipAddress",
        "created_at": "createdAt",
        "last_activity": "lastActivity",
        "expires_at": "expiresAt",
        "revoked_at": "revokedAt",
        "remember_me": "rememberMe",
    },
    "tenants": {
        "roomnumber": "roomNumber",
        "electricityrate": "electricityRate",
        "previousmeter": "previousMeter",
        "additionalpersoncharge": "additionalPersonCharge",
        "securitydeposit": "securityDeposit",
        "defaulttankwatercharge": "defaultTankWaterCharge",
        "meterid": "meterId",
        "tenantpin": "tenantPin",
        "failed_attempts": "failedAttempts",
        "locked_until": "lockedUntil",
        "status_changed_at": "statusChangedAt",
        "qr_key": "qrKey",
        "tenant_username": "tenantUsername",
        "password_hash": "passwordHash",
        "password_failed_attempts": "passwordFailedAttempts",
        "password_locked_until": "passwordLockedUntil",
        "password_reset_token_hash": "passwordResetTokenHash",
        "password_reset_expires_at": "passwordResetExpiresAt",
        "password_reset_requested_at": "passwordResetRequestedAt",
        "password_reset_required": "passwordResetRequired",
        "last_password_change_at": "lastPasswordChangeAt",
        "landlord_id": "landlordId",
        "property_id": "propertyId",
        "rent": "rentAmount",
        "water": "waterCharge",
    },
    "tenant_password_history": {
        "password_hash": "passwordHash",
        "changed_at": "changedAt",
        "changed_by": "changedBy",
    },
    "tenant_password_reset_events": {
        "token_hash": "tokenHash",
        "created_at": "createdAt",
        "expires_at": "expiresAt",
        "used_at": "usedAt",
        "requested_ip": "requestedIp",
    },
    "tenantpin_history": {
        "pin_hash": "pinHash",
        "changed_at": "changedAt",
    },
    "tenantpin_admin_store": {
        "encrypted_pin": "encryptedPin",
        "updated_at": "updatedAt",
    },
    "tenant_audit_logs": {
        "ip_address": "ipAddress",
        "created_at": "createdAt",
        "meta_json": "metaJson",
    },
    "receipts": {
        "date": "billDate",
        "month": "billMonth",
        "tenant": "tenantName",
        "property_id": "propertyId",
        "previous": "previousMeter",
        "current": "currentMeter",
        "rent": "rentAmount",
        "additional": "additionalAmount",
        "water": "waterAmount",
        "tankwater": "tankWaterAmount",
        "electricity": "electricityAmount",
        "total": "billTotal",
        "tenantphone": "tenantPhone",
        "tenantcompany": "tenantCompany",
        "tenantaddress": "tenantAddress",
        "rate": "electricityRate",
        "archiveddate": "archivedDate",
        "archivedby": "archivedBy",
        "deleteddate": "deletedDate",
        "additionalpersons": "additionalPersons",
        "additionalpersonrate": "additionalPersonRate",
        "receiptversion": "receiptVersion",
        "generatedby": "generatedBy",
        "paymentstatus": "paymentStatus",
        "maintenancecharge": "maintenanceCharge",
        "maintenancedesc": "maintenanceDesc",
        "previousarrears": "previousArrears",
        "amountreceived": "amountReceived",
        "landlord_id": "landlordId",
        "settled_by_bill_no": "settledByBillNo",
        "settlement_type": "settlementType",
        "settled_at": "settledAt",
        "settlement_amount": "settlementAmount",
    },
    "payment_entries": {
        "landlord_id": "landlordId",
        "payment_date": "paymentDate",
        "amount": "paymentAmount",
        "created_at": "createdAt",
        "updated_at": "updatedAt",
        "created_by": "createdBy",
        "updated_by": "updatedBy",
        "payment_type": "paymentType",
        "payment_method": "paymentMethod",
        "external_id": "externalId",
    },
    "payment_allocations": {
        "payment_entry_id": "paymentEntryId",
        "tenant_id": "tenantId",
        "bill_no": "billNo",
        "allocated_amount": "allocatedAmount",
        "allocation_type": "allocationType",
        "created_at": "createdAt",
    },
    "occupants": {
        "aadhaar_front": "aadhaarFront",
        "aadhaar_back": "aadhaarBack",
        "aadhaar_combined": "aadhaarCombined",
        "emp_front": "empFront",
        "emp_back": "empBack",
        "uploaddate": "uploadDate",
        "uploadmonth": "uploadMonth",
        "landlord_id": "landlordId",
    },
    "tenant_qr_feedback": {
        "tenant_id": "tenantId",
        "landlord_id": "landlordId",
        "property_id": "propertyId",
        "tenant_name": "tenantName",
        "view_token": "viewToken",
        "qr_key": "qrKey",
        "diagnostics_json": "diagnosticsJson",
        "failed_attempts": "failedAttempts",
        "admin_reply": "adminReply",
        "resolved_at": "resolvedAt",
        "resolved_by": "resolvedBy",
        "created_at": "createdAt",
        "ip_address": "ipAddress",
    },
    "import_jobs": {
        "created_at": "createdAt",
        "created_by": "createdBy",
        "preview_json": "previewJson",
        "resolution_json": "resolutionJson",
        "result_json": "resultJson",
    },
    "import_job_items": {
        "import_job_id": "importJobId",
        "target_key": "targetKey",
        "import_tenant_id": "importTenantId",
        "import_tenant_name": "importTenantName",
        "existing_tenant_id": "existingTenantId",
    },
    "tenant_recovery_snapshots": {
        "tenant_id": "tenantId",
        "tenant_name": "tenantName",
        "created_at": "createdAt",
        "expires_at": "expiresAt",
        "deleted_by": "deletedBy",
        "landlord_id": "landlordId",
        "archive_path": "archivePath",
        "metadata_json": "metadataJson",
        "restored_at": "restoredAt",
        "purged_at": "purgedAt",
    },
    "landlord_accounts": {
        "landlord_uuid": "landlordUuid",
        "full_name": "fullName",
        "password_hash": "passwordHash",
        "created_at": "createdAt",
        "updated_at": "updatedAt",
        "totp_secret": "totpSecret",
        "totp_enabled": "totpEnabled",
        "privacy_consented": "privacyConsented",
        "privacy_version": "privacyVersion",
        "privacy_accepted_at": "privacyAcceptedAt",
        "privacy_accepted_ip": "privacyAcceptedIp",
        "privacy_accepted_user_agent": "privacyAcceptedUserAgent",
        "requires_password_change": "requiresPasswordChange",
        "temp_password_created_at": "tempPasswordCreatedAt",
        "temp_password_consumed": "tempPasswordConsumed",
        "failed_attempts": "failedAttempts",
        "locked_until": "lockedUntil",
        "google_sub": "googleSub",
        "auth_provider": "authProvider",
        "avatar_url": "avatarUrl",
        "terms_consented": "termsConsented",
        "terms_version": "termsVersion",
        "terms_accepted_at": "termsAcceptedAt",
        "terms_accepted_ip": "termsAcceptedIp",
        "terms_accepted_user_agent": "termsAcceptedUserAgent",
        "setup_completed": "setupCompleted",
        "setup_skipped": "setupSkipped",
    },
    "landlord_audit_logs": {
        "landlord_id": "landlordId",
        "ip_address": "ipAddress",
        "created_at": "createdAt",
        "meta_json": "metaJson",
    },
    "landlord_ui_config": {
        "landlorduuid": "landlordUuid",
        "updated_at": "updatedAt",
    },
    "landlords": {
        "admin_id": "adminId",
    },
    "landlord_properties": {
        "landlord_id": "landlordId",
        "property_name": "propertyName",
        "sort_order": "sortOrder",
        "created_at": "createdAt",
        "updated_at": "updatedAt",
    },
    "landlord_profiles": {
        "landlord_id": "landlordId",
        "config_json": "configJson",
        "updated_at": "updatedAt",
    },
    "landlord_privacy_consents": {
        "landlord_id": "landlordId",
        "privacy_version": "privacyVersion",
        "accepted_at": "acceptedAt",
        "accepted_ip": "acceptedIp",
        "accepted_user_agent": "acceptedUserAgent",
    },
    "landlord_terms_consents": {
        "landlord_id": "landlordId",
        "terms_version": "termsVersion",
        "accepted_at": "acceptedAt",
        "accepted_ip": "acceptedIp",
        "accepted_user_agent": "acceptedUserAgent",
    },
    "landlord_password_admin_store": {
        "landlord_id": "landlordId",
        "encrypted_password": "encryptedPassword",
        "updated_at": "updatedAt",
    },
    "platform_admin_audit_logs": {
        "admin_id": "adminId",
        "target_type": "targetType",
        "target_id": "targetId",
        "ip_address": "ipAddress",
        "meta_json": "metaJson",
        "created_at": "createdAt",
    },
}

# ── Table rename map: {folded_source: camel_target} ─────────────────────────
TABLE_RENAMES = {
    "app_metadata": "appMetadata",
    "admin_login_otps": "adminLoginOtps",
    "admin_sessions": "adminSessions",
    "tenant_password_history": "tenantPasswordHistory",
    "tenant_password_reset_events": "tenantPasswordResetEvents",
    "tenantpin_history": "tenantPinHistory",
    "tenantpin_admin_store": "tenantPinAdminStore",
    "tenant_sessions": "tenantSessions",
    "tenant_audit_logs": "tenantAuditLogs",
    "payment_entries": "paymentEntries",
    "payment_allocations": "paymentAllocations",
    "tenant_qr_feedback": "tenantQrFeedback",
    "import_jobs": "importJobs",
    "import_job_items": "importJobItems",
    "tenant_recovery_snapshots": "tenantRecoverySnapshots",
    "landlord_accounts": "landlordAccounts",
    "landlord_sessions": "landlordSessions",
    "landlord_audit_logs": "landlordAuditLogs",
    "landlord_ui_config": "landlordUiConfig",
    "landlords": "landlordLegacyMappings",
    "landlord_properties": "landlordProperties",
    "landlord_profiles": "landlordProfiles",
    "landlord_privacy_consents": "landlordPrivacyConsents",
    "landlord_terms_consents": "landlordTermsConsents",
    "landlord_password_admin_store": "landlordPasswordAdminStore",
    "platform_admin_audit_logs": "platformAdminAuditLogs",
}

# ── Explicit index renames: {old_index: new_index} ──────────────────────────
INDEX_RENAMES = {
    "idx_tenants_qr_key": "idx_tenants_qrKey",
    "idx_tenants_landlord_id": "idx_tenants_landlordId",
    "idx_tenants_property_id": "idx_tenants_propertyId",
    "idx_tenants_tenant_username": "idx_tenants_tenantUsername",
    "idx_admin_login_otps_admin": "idx_adminLoginOtps_adminId",
    "idx_tenant_password_history_tenantid": "idx_tenantPasswordHistory_tenantId",
    "idx_tenant_password_reset_tenantid": "idx_tenantPasswordResetEvents_tenantId",
    "idx_tenantpin_history_tenantid": "idx_tenantPinHistory_tenantId",
    "idx_payment_entries_bill": "idx_paymentEntries_billNo",
    "idx_payment_entries_tenant": "idx_paymentEntries_tenantId",
    "idx_payment_entries_date": "idx_paymentEntries_paymentDate",
    "idx_payment_entries_landlord": "idx_paymentEntries_landlordId",
    "idx_payment_entries_status": "idx_paymentEntries_status",
    "idx_payment_entries_method": "idx_paymentEntries_paymentMethod",
    "idx_payment_entries_external_id": "idx_paymentEntries_externalId",
    "idx_payment_allocations_tenant": "idx_paymentAllocations_tenantId",
    "idx_payment_allocations_bill": "idx_paymentAllocations_billNo",
    "idx_payment_allocations_payment": "idx_paymentAllocations_paymentEntryId",
    "idx_tenant_qr_feedback_status": "idx_tenantQrFeedback_status",
    "idx_tenant_qr_feedback_landlord": "idx_tenantQrFeedback_landlordId",
    "idx_tenant_recovery_expiry": "idx_tenantRecoverySnapshots_expiry",
    "idx_tenant_recovery_landlord": "idx_tenantRecoverySnapshots_landlordId",
    "idx_landlord_accounts_username": "idx_landlordAccounts_username",
    "idx_landlord_accounts_google_sub": "idx_landlordAccounts_googleSub",
    "idx_landlord_sessions_landlord_id": "idx_landlordSessions_landlordId",
    "idx_landlord_sessions_status": "idx_landlordSessions_status",
    "idx_landlord_audit_logs_landlord_id": "idx_landlordAuditLogs_landlordId",
    "idx_landlord_audit_logs_action": "idx_landlordAuditLogs_action",
    "idx_landlords_uuid": "idx_landlordLegacyMappings_landlordUuid",
    "idx_landlord_properties_landlord": "idx_landlordProperties_landlordId",
    "idx_landlord_privacy_consents_landlord": "idx_landlordPrivacyConsents_landlordId",
    "idx_landlord_terms_consents_landlord": "idx_landlordTermsConsents_landlordId",
    "idx_platform_audit_admin": "idx_platformAdminAuditLogs_adminId",
    "idx_platform_audit_action": "idx_platformAdminAuditLogs_action",
    "idx_receipts_tenant": "idx_receipts_tenantName",
    "idx_receipts_paymentstatus": "idx_receipts_paymentStatus",
    "idx_receipts_landlord_id": "idx_receipts_landlordId",
    "idx_occupants_landlord_id": "idx_occupants_landlordId",
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


def _index_exists(cur, index):
    cur.execute("SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = %s", (index,))
    return cur.fetchone() is not None


# ══ Column / table renames ══════════════════════════════════════════════════

def _rename_columns(cur, table, colmap):
    if _table_exists(cur, table):
        for old, new in colmap.items():
            if _column_exists(cur, table, old):
                cur.execute(
                    "ALTER TABLE %s RENAME COLUMN %s TO %s"
                    % (_q(table), _q(old), _q(new))
                )


def _rename_tables(cur, tablemap):
    for old, new in tablemap.items():
        if _table_exists(cur, old) and not _table_exists(cur, new):
            cur.execute("ALTER TABLE %s RENAME TO %s" % (_q(old), _q(new)))


# ══ Constraint renames (introspection-based) ════════════════════════════════

def _pk_target(table_camel):
    return "pk_" + table_camel


def _uk_target(table_camel, col):
    return "uk_%s_%s" % (table_camel, col)


def _fk_target(table_camel, col):
    return "fk_%s_%s" % (table_camel, col)


def _rename_constraints(cur):
    """Rename PK / UNIQUE / FK constraints per convention.

    Runs after table/column renames, so constraint names are derived directly
    from *current* camelCase relname + attname (no folded lookup needed), and
    renaming the backing implicit index is avoided entirely — PostgreSQL
    auto-reparents the index that backs a renamed constraint.

    Multi-column constraints are matched on their first (lowest attnum) column,
    which is deterministic because 001/003 only ever created single-column
    UNIQUE/FK/PK constraints in this schema.
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


def _constraint_exists(cur, table, conname):
    cur.execute(
        "SELECT 1 FROM pg_constraint c "
        "JOIN pg_class cls ON cls.oid = c.conrelid "
        "JOIN pg_namespace n ON n.oid = cls.relnamespace "
        "WHERE n.nspname = 'public' AND cls.relname = %s AND c.conname = %s",
        (table, conname),
    )
    return cur.fetchone() is not None


# ══ Index renames ═══════════════════════════════════════════════════════════

def _rename_indexes(cur, idxmap):
    for old, new in idxmap.items():
        if _index_exists(cur, old) and not _index_exists(cur, new):
            cur.execute("ALTER INDEX %s RENAME TO %s" % (_q(old), _q(new)))


# ══ tenantRecoverySnapshots landlord index (Phase 8 parity) ═════════════════

_SNAPS_LANDLORD_IDX = "idx_tenantRecoverySnapshots_landlordId"
_SNAPS_TABLE = "tenantRecoverySnapshots"


def _ensure_snaps_landlord_index(cur):
    if _table_exists(cur, _SNAPS_TABLE) and not _index_exists(cur, _SNAPS_LANDLORD_IDX):
        cur.execute(
            "CREATE INDEX IF NOT EXISTS %s "
            "ON %s (\"landlordId\", status)"
            % (_q(_SNAPS_LANDLORD_IDX), _q(_SNAPS_TABLE))
        )


# ══ Step 1: landlord_id reconcile ═══════════════════════════════════════════

def _reconcile_snapshots_landlord_id(cur, table):
    """ADDs landlord_id to tenant_recovery_snapshots (service-DDL parity).

    The service runtime DDL historically created the table with landlord_id
    and an index; migration 001 did not. After 004 the service no longer owns
    runtime DDL, so 001-created databases need this column before the later
    column rename (landlord_id -> landlordId) can fire.
    """
    if _table_exists(cur, table) and not _column_exists(cur, table, "landlord_id"):
        cur.execute("ALTER TABLE %s ADD COLUMN landlord_id INTEGER" % _q(table))


# ══ up / down ═══════════════════════════════════════════════════════════════

def up(conn):
    cur = conn.cursor()

    # Step 1: reconcile snapsets.landlord_id before renaming.
    _reconcile_snapshots_landlord_id(cur, "tenant_recovery_snapshots")

    # Step 2: rename columns (folded -> camel). Tables still at old names here.
    for table, colmap in COLUMN_MAPS.items():
        _rename_columns(cur, table, colmap)

    # Step 3: rename tables (folded -> camel).
    _rename_tables(cur, TABLE_RENAMES)

    # Step 4: rename constraints (post-rename column attnames + camel table).
    _rename_constraints(cur)

    # Step 5: rename explicit indexes.
    _rename_indexes(cur, INDEX_RENAMES)

    # Step 6: ensure the tenantRecoverySnapshots landlord index exists.
    _ensure_snaps_landlord_index(cur)


def down(conn):
    """Best-effort reverse of up(). Primary path is up(); see docs."""
    cur = conn.cursor()

    # Reverse index renames: camel -> folded. This also restores the
    # service-provisioned `idx_tenant_recovery_landlord` (INDEX_RENAMES maps it
    # to the camel landlord index), which is the name that existed pre-004.
    for old, new in reversed(list(INDEX_RENAMES.items())):
        if _index_exists(cur, new) and not _index_exists(cur, old):
            cur.execute("ALTER INDEX %s RENAME TO %s" % (_q(new), _q(old)))

    # reverse table renames: camel -> folded
    folded_by_camel = {v: k for k, v in TABLE_RENAMES.items()}
    for camel, folded in folded_by_camel.items():
        if _table_exists(cur, camel) and not _table_exists(cur, folded):
            cur.execute("ALTER TABLE %s RENAME TO %s" % (_q(camel), _q(folded)))

    # reverse column renames: camel -> folded (tables now at folded names)
    for table, colmap in reversed(list(COLUMN_MAPS.items())):
        for old, new in reversed(list(colmap.items())):
            if _column_exists(cur, table, new) and not _column_exists(cur, table, old):
                cur.execute(
                    "ALTER TABLE %s RENAME COLUMN %s TO %s"
                    % (_q(table), _q(new), _q(old))
                )
