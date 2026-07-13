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
 * Preview import data from Excel/Zip files
 */
export async function importPreview(files: File[]): Promise<PreviewResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const basePath = window.location.pathname.startsWith('/rent') ? '/rent' : '';
  const response = await fetch(`${basePath}/admin/api/import-preview`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Preview failed");
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
  selectedTargets: string[]
): Promise<{ status: string; message: string }> {
  const formData = new FormData();

  // Re-append the original files (required by backend)
  files.forEach((file) => formData.append("files", file));

  // CRITICAL: selectedtargets must be a Form field with JSON string value
  // Backend: selectedtargets: str = Form(...)
  formData.append("selectedtargets", JSON.stringify(selectedTargets));

  const basePath = window.location.pathname.startsWith('/rent') ? '/rent' : '';
  const response = await fetch(`${basePath}/admin/api/import-execute`, {
    method: "POST",
    body: formData,
    // DO NOT set Content-Type header - browser will set multipart boundary automatically
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Import failed: ${response.status}`);
  }

  return response.json();
}