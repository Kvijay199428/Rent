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

export async function fetchExportPreview(landlordUuid: string): Promise<ExportPreviewResponse> {
    const [tenantsRes, receiptsRes] = await Promise.all([
        fetch(ROUTES.LANDLORDAPITENANTSLIST(landlordUuid), { credentials: 'include' }),
        fetch(`${ROUTES.LANDLORDAPIBILLINGFILTER(landlordUuid)}?status=active`, { credentials: 'include' }),
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

export async function exportCsv(landlordUuid: string, tenantIds: number[] | 'all'): Promise<Blob> {
    const idsParam = tenantIds === 'all' ? 'all' : tenantIds.join(',');

    const response = await fetch(
        `${ROUTES.LANDLORDAPISYNCEXPORTCSV(landlordUuid)}?tenants_list=${encodeURIComponent(idsParam)}`,
        { credentials: 'include' }
    );

    if (!response.ok) {
        throw new Error(`CSV export failed: ${response.status}`);
    }

    return response.blob();
}

export async function exportZip(landlordUuid: string, tenantIds: number[] | 'all'): Promise<Blob> {
    const idsParam = tenantIds === 'all' ? 'all' : tenantIds.join(',');

    const response = await fetch(
        `${ROUTES.LANDLORDAPISYNCEXPORTZIP(landlordUuid)}?tenants_list=${encodeURIComponent(idsParam)}`,
        { credentials: 'include' }
    );

    if (!response.ok) {
        throw new Error(`ZIP export failed: ${response.status}`);
    }

    return response.blob();
}

export async function exportExcel(landlordUuid: string, format: 'xlsx' | 'csv' | 'zip', tenantIds: number[] | 'all'): Promise<Blob> {
    const idsParam = tenantIds === 'all' ? 'all' : tenantIds.join(',');

    const response = await fetch(
        `${ROUTES.LANDLORDAPISYNCEXPORTEXCEL(landlordUuid, format)}?tenants_list=${encodeURIComponent(idsParam)}`,
        { credentials: 'include' }
    );

    if (!response.ok) {
        throw new Error(`${format.toUpperCase()} export failed: ${response.status}`);
    }

    return response.blob();
}

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
