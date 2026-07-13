// ExportService.ts
import { ROUTES } from '@/lib/routes';

export type TenantProfile = {
    id: number;
    name: string;
    company?: string;
    phone?: string;
    email?: string;
    address?: string;
    roomNumber?: string;
    meterId?: string;
    status: string;
    rent: number;
    water: number;
    electricityRate: number;
    additionalPersonCharge: number;
    defaulttankWaterCharge: number;
};

export type Receipt = {
    Bill: string;
    Date: string;
    Month: string;
    Tenant: string;
    Previous: number;
    Current: number;
    Units: number;
    Rent: number;
    Additional: number;
    Water: number;
    tankWater: number;
    Electricity: number;
    Total: number;
    paymentStatus: string;
    Status: string;
    MaintenanceCharge: number;
    MaintenanceDesc: string;
    previousArrears: number;
    amountReceived: number;
};

export type ExportPreviewResponse = {
    tenants: TenantProfile[];
    receipts: Receipt[];
};

/**
 * Fetch all tenants and receipts for export preview
 */
export async function fetchExportPreview(): Promise<ExportPreviewResponse> {
    const [tenantsRes, receiptsRes] = await Promise.all([
        fetch(ROUTES.ADMINAPITENANTSLIST, { credentials: 'include' }),
        fetch(`${ROUTES.ADMINAPIBILLINGFILTER}?status=active`, { credentials: 'include' }),
    ]);

    if (!tenantsRes.ok) {
        throw new Error(`Failed to fetch tenants: ${tenantsRes.status}`);
    }
    if (!receiptsRes.ok) {
        throw new Error(`Failed to fetch receipts: ${receiptsRes.status}`);
    }

    const tenants = await tenantsRes.json();
    const receipts = await receiptsRes.json();

    return { tenants, receipts };
}

/**
 * Export selected tenants' data as CSV
 * @param tenantIds - Array of tenant IDs to export, or "all"
 */
export async function exportCsv(tenantIds: number[] | 'all'): Promise<Blob> {
    const idsParam = tenantIds === 'all' ? 'all' : tenantIds.join(',');

    const response = await fetch(
        `${ROUTES.ADMINAPISYNCEXPORTCSV}?tenants_list=${encodeURIComponent(idsParam)}`,
        { credentials: 'include' }
    );

    if (!response.ok) {
        throw new Error(`CSV export failed: ${response.status}`);
    }

    return response.blob();
}

/**
 * Export selected tenants' data as ZIP (with PDFs)
 * @param tenantIds - Array of tenant IDs to export, or "all"
 */
export async function exportZip(tenantIds: number[] | 'all'): Promise<Blob> {
    const idsParam = tenantIds === 'all' ? 'all' : tenantIds.join(',');

    const response = await fetch(
        `${ROUTES.ADMINAPISYNCEXPORTZIP}?tenants_list=${encodeURIComponent(idsParam)}`,
        { credentials: 'include' }
    );

    if (!response.ok) {
        throw new Error(`ZIP export failed: ${response.status}`);
    }

    return response.blob();
}

/**
 * Export selected tenants' data as XLSX/CSV/ZIP via the unified export-excel endpoint
 * @param format - 'xlsx', 'csv', or 'zip'
 * @param tenantIds - Array of tenant IDs to export, or "all"
 */
export async function exportExcel(format: 'xlsx' | 'csv' | 'zip', tenantIds: number[] | 'all'): Promise<Blob> {
    const idsParam = tenantIds === 'all' ? 'all' : tenantIds.join(',');

    const response = await fetch(
        `${ROUTES.ADMINAPISYNCEXPORTEXCEL(format)}&tenants_list=${encodeURIComponent(idsParam)}`,
        { credentials: 'include' }
    );

    if (!response.ok) {
        throw new Error(`${format.toUpperCase()} export failed: ${response.status}`);
    }

    return response.blob();
}

/**
 * Trigger file download from blob
 */
export function downloadBlob(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}