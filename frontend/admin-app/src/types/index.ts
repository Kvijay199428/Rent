// Types matching backend models

export interface Tenant {
  id: number;
  name: string;
  company?: string;
  phone?: string;
  email?: string;
  address?: string;
  roomNumber?: string;
  occupation?: string;
  notes?: string;
  status: string;
  rent: number;
  water: number;
  defaulttankWaterCharge: number;
  electricityRate: number;
  previousMeter: number;
  additionalPersonCharge: number;
  securityDeposit: number;
  meterId?: string;
  viewToken?: string;
  tenantPin?: string | null;
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
  tankWater: number;
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
  additionalPersonRate: number;
  Receipt_Version: number;
  Generated_By: string;
  paymentStatus: string;
  MaintenanceCharge: number;
  MaintenanceDesc: string;
  previousArrears: number;
  amountReceived: number;
}

export interface BillRequest {
  tenant: string;
  month: string;
  current_reading: number;
  additional_persons: number;
  tankWater: number;
  MaintenanceCharge: number;
  MaintenanceDesc: string;
  previousArrears: number;
  amountReceived?: number;
  paymentStatus: string;
}

export interface PaymentStatusUpdate {
  paymentStatus: string;
  amountReceived?: number;
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
  lifetime_revenue: number;
  prev_monthly_revenue: number;
  revenue_change_str: string;

  total_active_receipts: number;
  total_archived_receipts: number;
  total_receipts_all: number;

  active_tenants: number;
  inactive_tenants: number;
  total_tenants: number;

  highest_meter_reading: number;
  highest_meter_tenant_id: number;
  highest_meter_bill_no: string;

  electricity_consumed: number;

  pending_payments_count: number;
  pending_payments_amount: number;
  pending_receipts_count: number;
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
  billNo: string;
  tenantName: string;
  tenantId: number;
  total: number;
  amountReceived: number;
  month: string;
  paymentStatus: string;
  previousArrears: number;
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
  viewToken: string;
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
//   roomNumber?: string;
//   occupation?: string;
//   notes?: string;
//   status: string;
//   rent: number;
//   water: number;
//   defaulttankWaterCharge: number;
//   electricityRate: number;
//   previousMeter: number;
//   additionalPersonCharge: number;
//   securityDeposit: number;
//   meterId?: string;
//   viewToken?: string;
//   tenantPin?: string;
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
//   tankWater: number;
//   Electricity: number;
//   Total: number;
//   Status: string;
//   paymentStatus: string;
//   previousArrears: number;
//   amountReceived: number;
//   MaintenanceCharge: number;
//   MaintenanceDesc: string;
//   Additional_Persons: number;
//   Archived_Date?: string;
//   tenantId?: number;
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
//   BillNo: string;
//   tenantName: string;
//   month: string;
//   total: number;
//   previousArrears: number;
//   amountReceived: number;
//   paymentStatus: string;
// }

export interface BillingConfig {
  rent: number;
  water: number;
  electricityRate: number;
  previousMeter_reading: number;
  additionalPersonCharge: number;
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
  // Primary key — always present
  occupantUuid: string;
  /** Legacy alias for occupantUuid — kept for backward compat */
  "Occupant UUID"?: string;

  name: string;
  mobile: string;
  address?: string;
  residentSince?: string;
  status: string;

  // Document filenames — camelCase/joined names returned by get_occupants
  aadhaarfront?: string;
  aadhaarback?: string;
  aadhaarcombined?: string;
  empfront?: string;
  empback?: string;

  // Kept for backward compatibility with old DB rows or code
  aadhaar_front?: string;
  aadhaar_back?: string;
  aadhaar_combined?: string;
  emp_front?: string;
  emp_back?: string;
  "Aadhaar Front"?: string;
  "Aadhaar Back"?: string;
  "Aadhaar Combined"?: string;
  "Emp Front"?: string;
  "Emp Back"?: string;

  uploaddate?: string;
  uploadmonth?: string;
  "Upload Date"?: string;
  "Upload Month"?: string;
}

export interface TenantRecoverySnapshot {
  id: string;
  tenant_id: number;
  tenant_name: string;
  created_at: string;
  expires_at: string;
  deleted_by: number | null;
  status: 'AVAILABLE' | 'RESTORED' | 'PURGED';
  archive_path: string;
  sha256: string;
  metadata_json: string;
  restored_at: string | null;
  purged_at: string | null;
  days_remaining: number;
  expired: boolean;
  archive_exists: boolean;
  metadata: Record<string, unknown>;
}

export interface SnapshotConflictInfo {
  tenantId?: number;
  existingTenantName?: string;
  roomNumber?: string;
  roomOccupiedBy?: string;
  phone?: string;
  phoneConflictTenant?: string;
  email?: string;
  emailConflictTenant?: string;
  billNumbers?: string[];
}

export interface SnapshotRestorePreview {
  canRestore: boolean;
  reason: string;
  conflicts: SnapshotConflictInfo;
  options: string[];
  snapshot: TenantRecoverySnapshot;
  receiptCount: number;
}

export interface PermanentDeleteResult {
  status: string;
  action: string;
  snapshotId: string;
  expiresAt: string;
  tenantId: number;
  tenantName: string;
}
