export interface TenantProfile {
  id: number;
  name: string;
  viewToken: string;
  unlocked: boolean;
  readOnly?: boolean;
  phone?: string;
  email?: string;
  address?: string;
  roomNumber?: string;
  occupation?: string;
  company?: string;
}

export interface Receipt {
  Bill: string;
  Date: string;
  Month: string;
  Tenant: string;
  TenantId: number;
  Previous: number;
  Current: number;
  Units: number;
  Rent: number;
  Additional: number;
  Water: number;
  tankWater: number;
  Electricity: number;
  Total: number;
  PDF: string;
  paymentStatus: "PENDING" | "PARTIAL" | "PAID" | "ADVANCE";
  amountReceived: number;
  previousArrears: number;
  Status: "ACTIVE" | "ARCHIVED";
  MaintenanceCharge: number;
  MaintenanceDesc: string;
}

export interface Occupant {
  "Occupant UUID": string;
  occupantUuid: string;
  name: string;
  mobile: string;
  status: string;
  address: string;
  residentSince: string;
  aadhaarfront: string;
  aadhaarback: string;
  aadhaarcombined: string;
  empfront: string;
  empback: string;
  uploaddate: string;
  uploadmonth: string;
}

export interface PortalResponse {
  tenant: TenantProfile;
  receipts?: Receipt[];
  occupants?: Occupant[];
}

export interface AuthResponse {
  status: string;
  message: string;
  tenant: { id: number; name: string; unlocked: boolean; readOnly?: boolean };
}

export type PaymentState = "PENDING" | "PARTIAL" | "PAID" | "ADVANCE";

// ── QR Login Flow ──
export interface QrTenantProfile {
  id: number;
  name: string;
  viewToken: string;
  unlocked: boolean;
  readOnly: boolean;
}

export interface QrLoginResponse {
  status: "success" | "error";
  message?: string;
  tenant?: QrTenantProfile;
}

// ── Portal Login Flow ──
export interface PortalLoginResponse {
  status: "success" | "error";
  tenant?: {
    id: number;
    name: string;
    landlord_uuid: string;
    view_token: string;
  };
  redirect_url: string | null;
  message?: string;
}

// ── Shared ──
export interface ApiError {
  detail?: string;
  message?: string;
}
