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
}

/**
 * Upload files for import preview. Returns parsed data or throws with schema mismatch info.
 */
export async function importPreview(files: File[]): Promise<PreviewResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const response = await fetch(ROUTES.ADMINAPISYNCIMPORTPREVIEW, {
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

  return response.json();
}

/**
 * Execute the import with selected targets
 * 
 * CRITICAL FIX: Must use FormData with files + selectedtargets as form field.
 * The backend uses `selectedtargets: str = Form(...)` which requires multipart
 * form data, NOT a JSON request body.
 */
export async function importExecute(
  files: File[],
  selectedTargets: string[],
  targetStatuses: Record<string, string> = {}
): Promise<{ status: string; message: string; tenants?: number; receipts?: number }> {
  const formData = new FormData();

  // Re-append the original files (required by backend)
  files.forEach((file) => formData.append("files", file));

  // CRITICAL: selectedtargets must be a Form field with JSON string value
  // Backend: selectedtargets: str = Form(...)
  formData.append("selectedtargets", JSON.stringify(selectedTargets));
  formData.append("targetstatuses", JSON.stringify(targetStatuses));

  const response = await fetch(ROUTES.ADMINAPISYNCIMPORTEXECUTE, {
    method: "POST",
    body: formData,
    credentials: 'include',
    // DO NOT set Content-Type header - browser will set multipart boundary automatically
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Import failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Download the import template.
 */
export async function downloadImportTemplate(): Promise<Blob> {
    const response = await fetch(ROUTES.ADMINAPISYNCTEMPLATE, {
        credentials: 'include',
    });

    if (!response.ok) {
        throw new Error(`Failed to download template: ${response.status}`);
    }

    return response.blob();
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