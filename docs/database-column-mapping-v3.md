# Database Column Mapping V3 — camelCase contract (Phase 2)

Status: **FROZEN**. Source of truth for migration `004_camel_case.py`, the backend SQL
rewrite (Phase 9-10), and the CSV/XLSX V3 writers (Phase 11-14).

## 0. Contract rules

- Every identifier is **camelCase**; multi-record identifiers are stored **quoted**
  (`"landlordId"`, `"tenantRecoverySnapshots"`). Single-word identifiers stay as-is.
- Rates: `*Rate`. Amounts: `*Amount`. Derived fields: `amountReceived`, `paymentStatus`.
- Payment identity: `id` = internal PK, `externalId` = business key.
- `schema_migrations` excluded. `admins`, `tenants`, `receipts`, `occupants` names unchanged.
- Direction: `old -> new`. `old` is the name as PostgreSQL folds it (lowercase); `new` is the
  stored camel word (quoted where mixed case).

## 1. Table renames (28 of 31; admins/tenants/receipts/occupants unchanged)

| Old (folded) | New |
| --- | --- |
| app_metadata | appMetadata |
| admin_login_otps | adminLoginOtps |
| admin_sessions | adminSessions |
| admin_login_otps | adminLoginOtps |
| tenant_password_history | tenantPasswordHistory |
| tenant_password_reset_events | tenantPasswordResetEvents |
| tenantPin_history | tenantPinHistory |
| tenantPin_admin_store | tenantPinAdminStore |
| tenant_sessions | tenantSessions |
| tenant_audit_logs | tenantAuditLogs |
| payment_entries | paymentEntries |
| payment_allocations | paymentAllocations |
| tenant_qr_feedback | tenantQrFeedback |
| import_jobs | importJobs |
| import_job_items | importJobItems |
| tenant_recovery_snapshots | tenantRecoverySnapshots |
| landlord_accounts | landlordAccounts |
| landlord_sessions | landlordSessions |
| landlord_audit_logs | landlordAuditLogs |
| landlord_ui_config | landlordUiConfig |
| landlords | landlordLegacyMappings |
| landlord_properties | landlordProperties |
| landlord_profiles | landlordProfiles |
| landlord_privacy_consents | landlordPrivacyConsents |
| landlord_terms_consents | landlordTermsConsents |
| landlord_password_admin_store | landlordPasswordAdminStore |
| platform_admin_audit_logs | platformAdminAuditLogs |

*(duplicate admin_login_otps row folded in as a second occurrence in the editor; source map is the
unique set — see 004.)*

## 2. Column maps by table

### admins (table unchanged)
password_hash→passwordHash, totp_secret→totpSecret, is_platform_admin→isPlatformAdmin,
telegram_chat_id→telegramChatId, failed_attempts→failedAttempts, locked_until→lockedUntil,
created_at→createdAt, updated_at→updatedAt. (id, username, email unchanged)

### admin_login_otps
admin_id→adminId, otp_hash→otpHash, expires_at→expiresAt, created_at→createdAt.
(id, attempts, used unchanged)

### admin_sessions / tenant_sessions / landlord_sessions
session_id→sessionId; admin_id→adminId / landlord_id→landlordId (session tables);
refresh_token_hash→refreshTokenHash, device_name→deviceName, ip_address→ipAddress,
created_at→createdAt, last_activity→lastActivity, expires_at→expiresAt, revoked_at→revokedAt,
remember_me→rememberMe. (browser, os, status unchanged; tenantSessions.tenantId unchanged)

### admin_sessions / tenant_sessions / landlord_sessions
(as above)

### tenants
roomnumber→roomNumber, electricityrate→electricityRate, previousmeter→previousMeter,
additionalpersoncharge→additionalPersonCharge, securitydeposit→securityDeposit,
defaulttankWatercharge→defaultTankWaterCharge, meterid→meterId, tenantpin→tenantPin,
failed_attempts→failedAttempts, locked_until→lockedUntil, status_changed_at→statusChangedAt,
qr_key→qrKey, tenant_username→tenantUsername, password_hash→passwordHash,
password_failed_attempts→passwordFailedAttempts, password_locked_until→passwordLockedUntil,
password_reset_token_hash→passwordResetTokenHash, password_reset_expires_at→passwordResetExpiresAt,
password_reset_requested_at→passwordResetRequestedAt, password_reset_required→passwordResetRequired,
last_password_change_at→lastPasswordChangeAt, landlord_id→landlordId, property_id→propertyId,
rent→rentAmount, water→waterCharge.
(id, name, company, phone, email, address, occupation, notes, status, viewToken unchanged)

### tenant_password_history
password_hash→passwordHash, changed_at→changedAt, changed_by→changedBy.
(id, tenantId unchanged)

### tenant_password_reset_events
token_hash→tokenHash, created_at→createdAt, expires_at→expiresAt, used_at→usedAt,
requested_ip→requestedIp. (id, tenantId, channel unchanged)

### tenantPin_history
pin_hash→pinHash, changed_at→changedAt. (id, tenantId unchanged)

### tenantPin_admin_store
encrypted_pin→encryptedPin, updated_at→updatedAt.

### tenant_audit_logs
ip_address→ipAddress, created_at→createdAt, meta_json→metaJson.
(id, tenantId, action unchanged)

### receipts (table unchanged)
date→billDate, month→billMonth, tenant→tenantName, property_id→propertyId, previous→previousMeter,
current→currentMeter, rent→rentAmount, additional→additionalAmount, water→waterAmount,
tankWater→tankWaterAmount, electricity→electricityAmount, total→billTotal,
tenantphone→tenantPhone, tenantcompany→tenantCompany, tenantaddress→tenantAddress, rate→electricityRate,
archiveddate→archivedDate, archivedby→archivedBy, deleteddate→deletedDate,
additionalpersons→additionalPersons, additionalpersonrate→additionalPersonRate,
receiptversion→receiptVersion, generatedby→generatedBy, paymentstatus→paymentStatus,
maintenancecharge→maintenanceCharge, maintenancedesc→maintenanceDesc, previousarrears→previousArrears,
amountreceived→amountReceived, landlord_id→landlordId, settled_by_bill_no→settledByBillNo,
settlement_type→settlementType, settled_at→settledAt, settlement_amount→settlementAmount.
(id, billNo, tenantId, units, pdf, status unchanged)

### payment_entries
landlord_id→landlordId, payment_date→paymentDate, amount→paymentAmount, created_at→createdAt,
updated_at→updatedAt, created_by→createdBy, updated_by→updatedBy, payment_type→paymentType,
payment_method→paymentMethod, external_id→externalId.
(id, billNo, tenantId, status, source, reference, notes unchanged)

### payment_allocations
payment_entry_id→paymentEntryId, tenant_id→tenantId, bill_no→billNo, allocated_amount→allocatedAmount,
allocation_type→allocationType, created_at→createdAt. (id unchanged)

### occupants (table unchanged)
aadhaar_front→aadhaarFront, aadhaar_back→aadhaarBack, aadhaar_combined→aadhaarCombined,
emp_front→empFront, emp_back→empBack, uploaddate→uploadDate, uploadmonth→uploadMonth,
landlord_id→landlordId. (id, tenantId, occupantUuid, name, mobile, address, residentSince, status unchanged)

### tenant_qr_feedback
tenant_id→tenantId, landlord_id→landlordId, property_id→propertyId, tenant_name→tenantName,
view_token→viewToken, qr_key→qrKey, diagnostics_json→diagnosticsJson, failed_attempts→failedAttempts,
admin_reply→adminReply, resolved_at→resolvedAt, resolved_by→resolvedBy, created_at→createdAt,
ip_address→ipAddress. (id, message, status unchanged)

### import_jobs
created_at→createdAt, created_by→createdBy, preview_json→previewJson, resolution_json→resolutionJson,
result_json→resultJson. (id, filename, status unchanged)

### import_job_items
import_job_id→importJobId, target_key→targetKey, import_tenant_id→importTenantId,
import_tenant_name→importTenantName, existing_tenant_id→existingTenantId.
(id, action, result, message unchanged)

### tenant_recovery_snapshots
tenant_id→tenantId, tenant_name→tenantName, created_at→createdAt, expires_at→expiresAt,
deleted_by→deletedBy, archive_path→archivePath, metadata_json→metadataJson,
restored_at→restoredAt, purged_at→purgedAt. (id, status, sha256 unchanged)
**Note:** `landlord_id` is NOT renamed here — it does not exist in migration 001. 004 ADDs
`landlord_id INTEGER` (service parity), then this map's `landlord_id→landlordId` applies.

### landlord_accounts
landlord_uuid→landlordUuid, full_name→fullName, password_hash→passwordHash, created_at→createdAt,
updated_at→updatedAt, totp_secret→totpSecret, totp_enabled→totpEnabled,
privacy_consented→privacyConsented, privacy_version→privacyVersion,
privacy_accepted_at→privacyAcceptedAt, privacy_accepted_ip→privacyAcceptedIp,
privacy_accepted_user_agent→privacyAcceptedUserAgent, requires_password_change→requiresPasswordChange,
temp_password_created_at→tempPasswordCreatedAt, temp_password_consumed→tempPasswordConsumed,
failed_attempts→failedAttempts, locked_until→lockedUntil, google_sub→googleSub,
auth_provider→authProvider, avatar_url→avatarUrl, terms_consented→termsConsented,
terms_version→termsVersion, terms_accepted_at→termsAcceptedAt, terms_accepted_ip→termsAcceptedIp,
terms_accepted_user_agent→termsAcceptedUserAgent, setup_completed→setupCompleted,
setup_skipped→setupSkipped. (id, email, phone, username, status unchanged)

### landlord_audit_logs
landlord_id→landlordId, ip_address→ipAddress, created_at→createdAt, meta_json→metaJson.
(id, action unchanged)

### landlord_ui_config
landlorduuid→landlordUuid, updated_at→updatedAt. (theme unchanged)

### landlords → landlordLegacyMappings
admin_id→adminId. (id, landlordUuid, active unchanged)

### landlord_properties
landlord_id→landlordId, property_name→propertyName, sort_order→sortOrder, created_at→createdAt,
updated_at→updatedAt. (id, address unchanged)

### landlord_profiles
landlord_id→landlordId, config_json→configJson, updated_at→updatedAt.

### landlord_privacy_consents / landlord_terms_consents
landlord_id→landlordId, privacy_version→privacyVersion / terms_version→termsVersion,
accepted_at→acceptedAt, accepted_ip→acceptedIp, accepted_user_agent→acceptedUserAgent.
(id, accepted unchanged)

### landlord_password_admin_store
landlord_id→landlordId, encrypted_password→encryptedPassword, updated_at→updatedAt.

### platform_admin_audit_logs
admin_id→adminId, target_type→targetType, target_id→targetId, ip_address→ipAddress,
meta_json→metaJson, created_at→createdAt. (id, action unchanged)

### app_metadata (table unchanged)
(key, value unchanged — no renames)

## 3. Constraint renames (Phase 7)

Format: `{pk|uk|fk}_{tableCamel}_{columnCamel}`.

- PK: `{oldTable}_pkey` → `pk_{tableCamel}`
- Unique: `{oldTable}_{col}_key` → `uk_{tableCamel}_{colCamel}`
  (e.g. admins_username_key→uk_admins_username, landlord_accounts_landlord_uuid_key→
  uk_landlordAccounts_landlordUuid, landlord_accounts_email_key→uk_landlordAccounts_email,
  landlord_accounts_username_key→uk_landlordAccounts_username,
  landlords_landlorduuid_key→uk_landlordLegacyMappings_landlorduuid, receipts_id_key→
  uk_receipts_id, occupants_id_key→uk_occupants_id)
- FK auto-names `{table}_{col}_fkey` → `fk_{tableCamel}_{colCamel}` (e.g.
  tenant_password_history_tenantid_fkey→fk_tenantPasswordHistory_tenantId,
  payment_entries_billno_fkey→fk_paymentEntries_billNo,
  payment_allocations_payment_entry_id_fkey→fk_paymentAllocations_paymentEntryId,
  import_job_items_import_job_id_fkey→fk_importJobItems_importJobId, all
  landlord_*_landlord_id_fkey→fk_{camel}_landlordId, admin_*_admin_id_fkey→fk_{camel}_adminId,
  tenantPin_*_tenantid_fkey→fk_{camel}_tenantId, tenant_sessions_tenantid_fkey→
  fk_tenantSessions_tenantId, occupants_tenantid_fkey→fk_occupants_tenantId)
- Explicit FKs: fk_tenants_landlord→fk_tenants_landlordId, fk_tenants_property→fk_tenants_propertyId,
  fk_receipts_property→fk_receipts_propertyId, fk_receipts_landlord→fk_receipts_landlordId,
  fk_occupants_landlord→fk_occupants_landlordId.

Constraint renames are **guarded by introspection of `pg_constraint`** (match on conname/contype +
current column attnames), so wrong auto-name guesses skip harmlessly. Constraint rename auto-reparents
any backing implicit index.

## 4. Index renames (Phase 7) — convention `idx_{tableCamel}_{colCamel}`

idx_tenants_qr_key→idx_tenants_qrKey, idx_tenants_landlord_id→idx_tenants_landlordId,
idx_tenants_property_id→idx_tenants_propertyId, idx_tenants_tenant_username→idx_tenants_tenantUsername,
idx_admin_login_otps_admin→idx_adminLoginOtps_adminId,
idx_tenant_password_history_tenantid→idx_tenantPasswordHistory_tenantId,
idx_tenant_password_reset_tenantid→idx_tenantPasswordResetEvents_tenantId,
idx_tenantpin_history_tenantid→idx_tenantPinHistory_tenantId,
idx_payment_entries_bill→idx_paymentEntries_billNo, idx_payment_entries_tenant→idx_paymentEntries_tenantId,
idx_payment_entries_date→idx_paymentEntries_paymentDate, idx_payment_entries_landlord→idx_paymentEntries_landlordId,
idx_payment_entries_status→idx_paymentEntries_status, idx_payment_entries_method→idx_paymentEntries_paymentMethod,
idx_payment_entries_external_id→idx_paymentEntries_externalId,
idx_payment_allocations_tenant→idx_paymentAllocations_tenantId,
idx_payment_allocations_bill→idx_paymentAllocations_billNo,
idx_payment_allocations_payment→idx_paymentAllocations_paymentEntryId,
idx_tenant_qr_feedback_status→idx_tenantQrFeedback_status,
idx_tenant_qr_feedback_landlord→idx_tenantQrFeedback_landlordId,
idx_tenant_recovery_expiry→idx_tenantRecoverySnapshots_expiry,
idx_tenant_recovery_landlord→idx_tenantRecoverySnapshots_landlordId,
idx_landlord_accounts_username→idx_landlordAccounts_username,
idx_landlord_accounts_google_sub→idx_landlordAccounts_googleSub,
idx_landlord_sessions_landlord_id→idx_landlordSessions_landlordId,
idx_landlord_sessions_status→idx_landlordSessions_status,
idx_landlord_audit_logs_landlord_id→idx_landlordAuditLogs_landlordId,
idx_landlord_audit_logs_action→idx_landlordAuditLogs_action,
idx_landlords_uuid→idx_landlordLegacyMappings_landlordUuid,
idx_landlord_properties_landlord→idx_landlordProperties_landlordId,
idx_landlord_privacy_consents_landlord→idx_landlordPrivacyConsents_landlordId,
idx_landlord_terms_consents_landlord→idx_landlordTermsConsents_landlordId,
idx_platform_audit_admin→idx_platformAdminAuditLogs_adminId,
idx_platform_audit_action→idx_platformAdminAuditLogs_action,
idx_receipts_tenant→idx_receipts_tenantName, idx_receipts_status→idx_receipts_status,
idx_receipts_paymentstatus→idx_receipts_paymentStatus, idx_receipts_tenantId→idx_receipts_tenantId,
idx_receipts_landlord_id→idx_receipts_landlordId,
idx_occupants_tenantId→idx_occupants_tenantId, idx_occupants_landlord_id→idx_occupants_landlordId.

New create: **idx_tenantRecoverySnapshots_landlordId** on `tenantRecoverySnapshots(landlordId, status)`
(CREATE IF NOT EXISTS; mirrors service `idx_tenant_recovery_landlord`).

## 5. Down (best-effort)

`down()` reverses in reverse order: index renames (target→old), constraint renames
(camel prefixes→legacy, based on current-column introspection), table renames (camel→folded), column
renames (camel→folded). Guarded identically. Documented as best-effort; primary migration path is `up()`.