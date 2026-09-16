import { ROUTES } from '@/lib/routes';
import type { SchemaMismatchInfo } from './SchemaMismatchDialog';

export interface PreviewResponse {
  status: string;
  files: {
    [filename: string]: {
      [tenantId: string]: {
        profile: {
          tenantId: string;
          tenantName: string;
          Phone: string;
          Email: string;
          Company: string;
          Address: string;
          Room: string;
          meterId: string;
          PIN: string;
          Rent: string;
          Water: string;
          electricityRate: string;
          additionalPersonRate: string;
          tankWater: string;
          Status: string;
        };
        receipts: Array<{
          BillNo: string;
          tenantId: string;
          Month: string;
          Date: string;
          Previous: string;
          Current: string;
          Units: string;
          Rent: string;
          Water: string;
          Electricity: string;
          Additional: string;
          tankWater: string;
          Maintenance: string;
          Arrears: string;
          amountReceived: string;
          Total: string;
          paymentStatus: string;
          receiptStatus: string;
        }>;
      };
    };
  };
  conflicts?: {
    [filename: string]: {
      [tenantId: string]: {
        importTenant: { tenantId: string; tenantName: string };
        matches: Array<{ type: string; existingTenantId: number; existingTenantName: string }>;
        receiptConflicts: Array<{ billNo: string; month: string; reason: string; actionRequired: boolean }>;
      };
    };
  };
  encrypted_pins?: {
    [filename: string]: {
      [tenantId: string]: {
        tenantId: string;
        tenantName: string;
        pin_value: string;
        pin_length: number;
        is_encrypted: boolean;
      };
    };
  };
  requires_resolution?: boolean;
  predicted_next_tenant_id?: number;
}

// ─── V2 (canonical import) wire types ──────────────────────────────────

export interface V2TenantProfile {
  tenantId: number;
  tenantName: string;
  Phone: string;
  Email: string;
  Company: string;
  Address: string;
  Room: string;
  meterId: string;
  PIN: string;
  Rent: number | string;
  Water: number | string;
  electricityRate: number | string;
  additionalPersonRate: number | string;
  tankWater: number | string;
  Status: string;
}

export interface V2Bill {
  billNo: string;
  tenantId: number;
  Month: string;
  Date: string;
  Previous: number | string;
  Current: number | string;
  Units: number | string;
  Rent: number | string;
  Water: number | string;
  Electricity: number | string;
  Additional: number | string;
  tankWater: number | string;
  Maintenance: number | string;
  Arrears: number | string;
  Total: number | string;
  amountReceived: number | string;
  paymentStatus: string;
  receiptStatus: string;
}

export interface V2PreviewFile {
  meta?: Record<string, unknown>;
  tenants: Record<string, V2TenantProfile>;
  bills: V2Bill[];
}

export interface V2PreviewResponse {
  status: string;
  meta?: Record<string, unknown>;
  files: Record<string, V2PreviewFile>;
  canonical?: {
    tenants: Record<string, V2TenantProfile>;
    bills: V2Bill[];
  };
  conflicts?: PreviewResponse["conflicts"];
  encrypted_pins?: PreviewResponse["encrypted_pins"];
  requires_resolution?: boolean;
  predicted_next_tenant_id?: number;
  warnings?: string[];
}

function _str(value: unknown): string {
  return value === null || value === undefined ? "" : String(value);
}

/** String-formatted tenant key ("T101"), matching backend format_tenant_id. */
function _tenantKey(profile: V2TenantProfile): string {
  const n = Math.trunc(Number(profile.tenantId) || 0);
  return `T${String(n).padStart(3, "0")}`;
}

function _toV1Profile(p: V2TenantProfile): PreviewResponse["files"][string][string]["profile"] {
  return {
    tenantId: _tenantKey(p),
    tenantName: _str(p.tenantName),
    Phone: _str(p.Phone),
    Email: _str(p.Email),
    Company: _str(p.Company),
    Address: _str(p.Address),
    Room: _str(p.Room),
    meterId: _str(p.meterId),
    PIN: _str(p.PIN),
    Rent: _str(p.Rent),
    Water: _str(p.Water),
    electricityRate: _str(p.electricityRate),
    additionalPersonRate: _str(p.additionalPersonRate),
    tankWater: _str(p.tankWater),
    Status: _str(p.Status),
  };
}

function _toV1Receipt(
  b: V2Bill,
  tenantKey: string,
): PreviewResponse["files"][string][string]["receipts"][number] {
  return {
    BillNo: _str(b.billNo),
    tenantId: tenantKey,
    Month: _str(b.Month),
    Date: _str(b.Date),
    Previous: _str(b.Previous),
    Current: _str(b.Current),
    Units: _str(b.Units),
    Rent: _str(b.Rent),
    Water: _str(b.Water),
    Electricity: _str(b.Electricity),
    Additional: _str(b.Additional),
    tankWater: _str(b.tankWater),
    Maintenance: _str(b.Maintenance),
    Arrears: _str(b.Arrears),
    amountReceived: _str(b.amountReceived),
    Total: _str(b.Total),
    paymentStatus: _str(b.paymentStatus),
    receiptStatus: _str(b.receiptStatus),
  };
}

/**
 * Map the V2 (canonical) preview shape onto the legacy PreviewResponse the
 * modal already understands. Target keys become `file::T101` (string-formatted
 * tenantId), matching the backend's own conflict-detection/execute keyspace, so
 * the selectedtargets the modal emits stay valid for V2 execute.
 *
 * Receipts are grouped per file by matching merged canonical bills to that
 * file's per-file bills (by tenantId and billNo). Merged canonical bills carry
 * the engine-derived amountReceived/paymentStatus — per-file bill values are
 * never re-derived by the backend, so they are used only as a fallback.
 */
function toV1PreviewResponse(v2: V2PreviewResponse): PreviewResponse {
  const files: PreviewResponse["files"] = {};
  const mergedBills = v2.canonical?.bills || [];

  for (const [filename, file] of Object.entries(v2.files || {})) {
    const tenants = file.tenants || {};
    const fileEntry: PreviewResponse["files"][string] = {};

    for (const tenantNumKey of Object.keys(tenants)) {
      const profile = _toV1Profile(tenants[tenantNumKey]);
      const tKey = profile.tenantId;

      const fileBills = (file.bills || []).filter((b) => _str(b.tenantId) === tenantNumKey);
      const fileBillNos = new Set(fileBills.map((b) => _str(b.billNo)));
      const mergedForTenant = mergedBills.filter(
        (b) =>
          String(b.tenantId) === String(tenantNumKey) ||
          (fileBillNos.size > 0 && fileBillNos.has(_str(b.billNo))),
      );

      const receipts = (mergedForTenant.length > 0 ? mergedForTenant : fileBills).map((b) =>
        _toV1Receipt(b, tKey),
      );
      fileEntry[tKey] = { profile, receipts };
    }

    files[filename] = fileEntry;
  }

  return {
    status: v2.status,
    files,
    conflicts: v2.conflicts,
    encrypted_pins: v2.encrypted_pins,
    requires_resolution: v2.requires_resolution,
    predicted_next_tenant_id: v2.predicted_next_tenant_id,
  };
}

/**
 * Upload files for import preview. Returns parsed data or throws with schema mismatch info.
 */
export async function importPreview(landlordUuid: string, files: File[]): Promise<PreviewResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const response = await fetch(ROUTES.LANDLORDAPISYNCIMPORTPREVIEWV2(landlordUuid), {
    method: "POST",
    body: formData,
    credentials: 'include',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));

    // Check if this is a schema mismatch error
    const detail = errorData.detail || '';
    if (
        detail.includes('missing required sheets') ||
        detail.includes('Tenant_Profile') ||
        detail.includes('Rent_Receipts') ||
        response.status === 400
    ) {
        // Try to extract mismatch info from error
        const mismatch: SchemaMismatchInfo = {
            filename: files[0]?.name || 'unknown',
            expected: 'Tenant_Profile, Rent_Receipts',
            actual: detail,
            missingSheets: extractMissingSheets(detail),
        };
        throw new SchemaMismatchError(mismatch);
    }

    throw new Error(detail || `Import preview failed: ${response.status}`);
  }

  return toV1PreviewResponse(await response.json());
}

/**
 * Execute the import with selected targets
 * 
 * CRITICAL FIX: Must use FormData with files + selectedtargets as form field.
 * The backend uses `selectedtargets: str = Form(...)` which requires multipart
 * form data, NOT a JSON request body.
 */
export async function importExecute(
  landlordUuid: string,
  files: File[],
  selectedTargets: string[],
  targetStatuses: Record<string, string> = {},
  idResolutions?: Record<string, string>,
  pinResolutions?: Record<string, string>,
  pinHandling?: 'prompt' | 'skip' | 'assign_random',
  receiptStrategies?: Record<string, string>
): Promise<{
  status: string;
  message: string;
  tenants?: number;
  receipts?: number;
  payments?: number;
  imported_tenants?: number;
  unmatched_targets?: string[];
  auto_assigned_pins?: any[];
}> {
  const formData = new FormData();

  // Re-append the original files (required by backend)
  files.forEach((file) => formData.append("files", file));

  // CRITICAL: selectedtargets must be a Form field with JSON string value
  // Backend: selectedtargets: str = Form(...)
  formData.append("selectedtargets", JSON.stringify(selectedTargets));
  formData.append("targetstatuses", JSON.stringify(targetStatuses));
  
  if (idResolutions) formData.append("idresolutions", JSON.stringify(idResolutions));
  if (pinResolutions) formData.append("pinresolutions", JSON.stringify(pinResolutions));
  if (pinHandling) formData.append("pinhandling", pinHandling);
  if (receiptStrategies) formData.append("receiptstrategies", JSON.stringify(receiptStrategies));

  const response = await fetch(ROUTES.LANDLORDAPISYNCIMPORTEXECUTEV2(landlordUuid), {
    method: "POST",
    body: formData,
    credentials: 'include',
    // DO NOT set Content-Type header - browser will set multipart boundary automatically
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail?.message || errorData.detail || `Import failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Download the V2 import template (canonical columns).
 */
export async function downloadImportTemplateV2(landlordUuid: string, format: 'xlsx' | 'csv' = 'xlsx'): Promise<Blob> {
    const response = await fetch(
        `${ROUTES.LANDLORDAPISYNCIMPORTTEMPLATEV2(landlordUuid)}?format=${encodeURIComponent(format)}`,
        { credentials: 'include' }
    );

    if (!response.ok) {
        throw new Error(`Failed to download template: ${response.status}`);
    }

    return response.blob();
}

/**
 * Download the import template.
 */
export async function downloadImportTemplate(landlordUuid: string): Promise<Blob> {
    return downloadImportTemplateV2(landlordUuid, 'xlsx');
}

// ─── Schema Mismatch Error Class ───────────────────────────────────────

export class SchemaMismatchError extends Error {
    public mismatch: SchemaMismatchInfo;

    constructor(mismatch: SchemaMismatchInfo) {
        super('Schema mismatch detected');
        this.name = 'SchemaMismatchError';
        this.mismatch = mismatch;
    }
}

// ─── Helpers ───────────────────────────────────────────────────────────

function extractMissingSheets(detail: string): string[] | undefined {
    const missing: string[] = [];
    if (detail.includes('Tenant_Profile')) {
        // If the error mentions Tenant_Profile is missing
        if (detail.includes('missing') && detail.includes('Tenant_Profile')) {
            missing.push('Tenant_Profile');
        }
    }
    if (detail.includes('Rent_Receipts')) {
        if (detail.includes('missing') && detail.includes('Rent_Receipts')) {
            missing.push('Rent_Receipts');
        }
    }
    return missing.length > 0 ? missing : undefined;
}

/**
 * Check if an error is a schema mismatch error.
 */
export function isSchemaMismatchError(error: unknown): error is SchemaMismatchError {
    return error instanceof SchemaMismatchError;
}

/**
 * Parse schema mismatch from a generic API error response.
 * Use this when the backend returns 400 with sheet/header mismatch details.
 */
export function parseSchemaMismatch(
    filename: string,
    detail: string
): SchemaMismatchInfo {
    const info: SchemaMismatchInfo = {
        filename,
        expected: 'Tenant_Profile, Rent_Receipts sheets with specific headers',
        actual: detail,
    };

    // Extract missing sheets
    const missingSheets: string[] = [];
    for (const sheet of ['Tenant_Profile', 'Rent_Receipts']) {
        if (detail.includes(sheet) && detail.toLowerCase().includes('missing')) {
            missingSheets.push(sheet);
        }
    }
    if (missingSheets.length > 0) {
        info.missingSheets = missingSheets;
    }

    return info;
}
