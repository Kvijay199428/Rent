/**
 * src/lib/tenant-api-contract.ts
 * 
 * Strict Data Transfer Objects (DTOs) aligned with the backend's SQLite schema 
 * and API responses for the Tenant Portal.
 */

export interface Tenant {
    id: number;
    name: string;
    viewToken: string;
    unlocked: boolean;
    roomnumber?: string;
    phone?: string;
    email?: string;
    rent?: number;
    electricityrate?: number;
}

export interface Receipt {
    billNo: string;
    date: string;
    month: string;
    tenantId: number;
    tenant: string;
    previous: number;
    current: number;
    units: number;
    rent: number;
    additional: number;
    water: number;
    tankWater: number;
    electricity: number;
    total: number;
    pdf?: string;
    status: string;
    paymentstatus: string;
    maintenancecharge: number;
    maintenancedesc?: string;
    previousarrears: number;
    amountreceived: number;
}

export interface Occupant {
    occupantUuid?: string;
    "Occupant UUID"?: string;
    uuid?: string;
    name: string;
    mobile: string;
    status: string;
    aadhaar_front?: string;
    aadhaar_back?: string;
    aadhaar_combined?: string;
    emp_front?: string;
    emp_back?: string;
    uploaddate?: string;
    uploadmonth?: string;
}

export interface TenantProfileResponse {
    tenant: Tenant;
    receipts?: Receipt[];
    occupants?: Occupant[];
}

export interface ApiError {
    detail?: string;
    message?: string;
}

export interface AuthResponse {
    status: string;
    message: string;
}
