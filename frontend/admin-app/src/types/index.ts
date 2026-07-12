// Types matching backend models

export interface Tenant {
  id?: number;
  name: string;
  company?: string;
  phone?: string;
  email?: string;
  address?: string;
  room_number?: string;
  occupation?: string;
  notes?: string;
  status: string;
  rent: number;
  water: number;
  default_tank_water_charge: number;
  electricity_rate: number;
  previous_meter: number;
  additional_person_charge: number;
  security_deposit: number;
  meter_id?: string;
  view_token?: string;
  tenant_pin?: string | null;
  arrears: number;
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
  Tank_Water: number;
  Electricity: number;
  Total: number;
  PDF: string;
  Tenant_Phone: string;
  Tenant_Company: string;
  Tenant_Address: string;
  Rate: number;
  Status: string;
  Archived_Date: string;
  Archived_By: string;
  Deleted_Date: string;
  Additional_Persons: number;
  Additional_Person_Rate: number;
  Receipt_Version: number;
  Generated_By: string;
  Payment_Status: string;
  Maintenance_Charge: number;
  Maintenance_Desc: string;
  Previous_Arrears: number;
  Amount_Received: number;
}

export interface BillRequest {
  tenant: string;
  month: string;
  current_reading: number;
  additional_persons: number;
  tank_water: number;
  maintenance_charge: number;
  maintenance_desc: string;
  previous_arrears: number;
  amount_received?: number;
  payment_status: string;
}

export interface PaymentStatusUpdate {
  payment_status: string;
  amount_received?: number;
}

export interface ConfigUpdate {
  landlord: Record<string, unknown>;
  billing: Record<string, unknown>;
  whatsapp?: Record<string, unknown>;
  backup?: Record<string, unknown>;
}

export interface BackupMetadata {
  id: string;
  type: string;
  date: string;
  application_version: string;
  schema_version: number;
  created_by: string;
  machine_name: string;
  os: string;
  receipt_count: number;
  archived_receipt_count: number;
  tenant_count: number;
  inactive_tenant_count: number;
  pdf_count: number;
  theme: string;
  checksums: Record<string, string>;
  verified: boolean;
  compressed: boolean;
  password_protected: boolean;
  size?: string;
  filename?: string;
  path?: string;
  zip_sha256?: string;
  notes?: string;
}

export interface DashboardStats {
  next_bill: string;
  current_month: string;
  monthly_revenue: number;
  prev_monthly_revenue: number;
  revenue_change_str: string;
  total_active_receipts: number;
  total_archived_receipts: number;
  total_receipts_all: number;
  active_tenants: number;
  inactive_tenants: number;
  total_tenants: number;
  highest_meter_reading: number;
  electricity_consumed: number;
  pending_payments_count: number;
  pending_amount: number;
  amount_collected: number;
  paid_bills_count: number;
  advance_bills_count: number;
  collection_rate: number;
  recent_bills: RecentBill[];
  chart_labels: string[];
  chart_revenue: number[];
  chart_electricity: number[];
}

export interface RecentBill {
  billno: string;
  tenant_name: string;
  total: number;
  amount_received: number;
  month: string;
  payment_status: string;
  Previous_Arrears?: number;
}

export interface ImportPreviewResponse {
  status: string;
  files: Record<string, Record<string, { profile: Record<string, string>; receipts: Record<string, string>[] }>>;
}

export interface ImportExecuteResponse {
  status: string;
  message: string;
  tenants: number;
  receipts: number;
  unmatched_targets: string[];
}

export interface LoginRequest {
  view_token: string;
  pin: string;
  remember_me: boolean;
}

export interface ChangePinRequest {
  current_pin: string;
  new_pin: string;
}

export interface DeviceSession {
  session_id: string;
  device_name: string;
  ip_address: string;
  last_activity: string;
  status: string;
}

export interface EncryptedPayload {
  encryptedKey: string;
  encryptedData: string;
  nonce: string;
  remember_me?: boolean;
}

export interface ApiResponse<T = unknown> {
  status: string;
  data?: T;
  message?: string;
  [key: string]: unknown;
}

// export interface Tenant {
//   id: number;
//   name: string;
//   company?: string;
//   phone?: string;
//   email?: string;
//   address?: string;
//   room_number?: string;
//   occupation?: string;
//   notes?: string;
//   status: string;
//   rent: number;
//   water: number;
//   default_tank_water_charge: number;
//   electricity_rate: number;
//   previous_meter: number;
//   additional_person_charge: number;
//   security_deposit: number;
//   meter_id?: string;
//   view_token?: string;
//   tenant_pin?: string;
//   arrears: number;
// }

// export interface Receipt {
//   Bill: string;
//   Date: string;
//   Month: string;
//   Tenant: string;
//   Previous: number;
//   Current: number;
//   Units: number;
//   Rent: number;
//   Additional: number;
//   Water: number;
//   Tank_Water: number;
//   Electricity: number;
//   Total: number;
//   Status: string;
//   Payment_Status: string;
//   Previous_Arrears: number;
//   Amount_Received: number;
//   Maintenance_Charge: number;
//   Maintenance_Desc: string;
//   Additional_Persons: number;
//   Archived_Date?: string;
//   tenant_id?: number;
// }

// export interface DashboardStats {
//   current_month: string;
//   monthly_revenue: number;
//   prev_monthly_revenue: number;
//   revenue_change_str: string;
//   paid_bills_count: number;
//   advance_bills_count: number;
//   pending_payments_count: number;
//   pending_amount: number;
//   amount_collected: number;
//   active_tenants: number;
//   inactive_tenants: number;
//   highest_meter_reading: number;
//   electricity_consumed: number;
//   collection_rate: number;
//   recent_bills: RecentBill[];
//   chart_labels: string[];
//   chart_revenue: number[];
//   chart_electricity: number[];
// }

// export interface RecentBill {
//   bill_no: string;
//   tenant_name: string;
//   month: string;
//   total: number;
//   previous_arrears: number;
//   amount_received: number;
//   payment_status: string;
// }

export interface BillingConfig {
  rent: number;
  water: number;
  electricity_rate: number;
  previous_meter_reading: number;
  additional_person_charge: number;
}

export interface LandlordConfig {
  name: string;
  phone: string;
  email: string;
  address: string;
  pan: string;
  bank_account_name: string;
  bank_account_number: string;
  bank_name: string;
  bank_branch: string;
  bank_ifsc: string;
  mask_bank_account: boolean;
  signature_text: string;
  signature_image: string;
}

export interface WhatsappConfig {
  enabled?: boolean;
  single_template: {
    label?: string;
    readonly_by_default?: boolean;
    message: string;
    default_message: string;
    allowed_variables: string[];
  };
  country_code: string;
}

export interface AppConfig {
  landlord: LandlordConfig;
  billing: BillingConfig;
  ui: { theme: string };
  backup: Record<string, unknown>;
  whatsapp: WhatsappConfig;
}

export interface Backup {
  id: string;
  type: string;
  subtype: string;
  date: string;
  size: string;
  filename: string;
  notes: string;
  verified: boolean;
  receipt_count: number;
  tenant_count: number;
}

export interface Occupant {
  "Occupant UUID": string;
  name: string;
  mobile: string;
  status: string;
  "Aadhaar Front": string;
  "Aadhaar Back": string;
  "Aadhaar Combined": string;
  "Emp Front": string;
  "Emp Back": string;
  "Upload Date": string;
  "Upload Month": string;
}
