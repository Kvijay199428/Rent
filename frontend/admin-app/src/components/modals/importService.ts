export interface PreviewResponse {
  status: string;
  files: {
    [filename: string]: {
      [tenantId: string]: {
        profile: {
          Tenant_ID: string;
          Tenant_Name: string;
          Phone: string;
          Email: string;
          Company: string;
          Address: string;
          Room: string;
          Meter_ID: string;
          PIN: string;
          Rent: string;
          Water: string;
          Electricity_Rate: string;
          Additional_Person_Rate: string;
          Tank_Water: string;
          Status: string;
        };
        receipts: Array<{
          Bill_No: string;
          Tenant_ID: string;
          Month: string;
          Date: string;
          Previous: string;
          Current: string;
          Units: string;
          Rent: string;
          Water: string;
          Electricity: string;
          Additional: string;
          Tank_Water: string;
          Maintenance: string;
          Arrears: string;
          Amount_Received: string;
          Total: string;
          Payment_Status: string;
          Receipt_Status: string;
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
// import { toast } from "sonner";

// import type { ImportPreviewResponse as PreviewResponse, ImportExecuteResponse as ImportResponse } from "../../types";
// export type { PreviewResponse, ImportResponse };

// const API_BASE = import.meta.env.VITE_API_BASE || "";

// function getBasePath(): string {
//   // Handle proxy paths like /rent
//   const rootPath = document.querySelector('base')?.getAttribute('href') || "";
//   if (rootPath) return rootPath.replace(/\/$/, "");
//   return window.location.pathname.startsWith('/rent/') ? '/rent' : '';
// }

// /**
//  * Preview import files - sends multipart/form-data with Excel/Zip files
//  */
// export async function importPreview(files: File[]): Promise<PreviewResponse> {
//   const basePath = getBasePath();
//   const formData = new FormData();

//   files.forEach((file) => {
//     formData.append("files", file);
//   });

//   const response = await fetch(`${basePath}/admin/api/import-preview`, {
//     method: "POST",
//     body: formData,
//     // DO NOT set Content-Type header - browser sets it with boundary for multipart
//   });

//   if (!response.ok) {
//     const errorText = await response.text();
//     throw new Error(`Preview failed (${response.status}): ${errorText}`);
//   }

//   return response.json();
// }

// /**
//  * Execute import - sends files + selectedtargets as FormData
//  * CRITICAL: selectedtargets must be a JSON string array in a Form field
//  */
// export async function importExecute(
//   files: File[],
//   selectedTargets: string[]
// ): Promise<ImportResponse> {
//   const basePath = getBasePath();
//   const formData = new FormData();

//   // Re-attach the original files (backend needs them again)
//   files.forEach((file) => {
//     formData.append("files", file);
//   });

//   // selectedtargets MUST be sent as a Form field with JSON string value
//   // Backend does: json.loads(selectedtargets) expecting a list
//   formData.append("selectedtargets", JSON.stringify(selectedTargets));

//   const response = await fetch(`${basePath}/admin/api/import-execute`, {
//     method: "POST",
//     body: formData,
//     // DO NOT set Content-Type - let browser set multipart boundary automatically
//   });

//   if (!response.ok) {
//     const errorText = await response.text();
//     throw new Error(`Import failed (${response.status}): ${errorText}`);
//   }

//   return response.json();
// }