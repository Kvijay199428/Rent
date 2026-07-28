import type { Tenant, Receipt, DashboardStats, AppConfig, Backup, PaymentStatusUpdate, Occupant, TenantRecoverySnapshot, SnapshotRestorePreview, PermanentDeleteResult } from "@/types";
import { ROUTES } from "@/lib/routes";

export type ArchiveDataResponse = {
  tenants: Tenant[];
  receipts: Receipt[];
};

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const res = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (res.status === 401 || res.status === 303) {
    window.location.href = ROUTES.LANDLORDPAGELOGIN;
    throw new Error("Unauthorized");
  }
  return res;
}

export const api = {
  // Dashboard
  getDashboardStats: async (landlordUuid: string): Promise<DashboardStats> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIDASHBOARDSTATS(landlordUuid));
    if (!res.ok) throw new Error('Failed to fetch dashboard stats');
    const raw = await res.json();
    const data = raw.stats ?? raw;
    return {
      ...data,
      recent_bills: Array.isArray(data.recent_bills)
        ? data.recent_bills.map((b: any) => ({
            billNo: b.billNo ?? b.BillNo ?? b.bill_no ?? '',
            tenantName: b.tenantName ?? b.Tenant ?? '',
            tenantId: Number(b.tenantId ?? b.TenantId ?? 0),
            month: b.month ?? b.Month ?? '',
            total: Number(b.total ?? b.Total ?? 0),
            previousArrears: Number(b.previousArrears ?? b.previous_arrears ?? 0),
            amountReceived: Number(b.amountReceived ?? b.amount_received ?? 0),
            paymentStatus: b.paymentStatus ?? b.payment_status ?? 'PENDING',
          }))
        : [],
    };
  },

  // Tenants
  getTenants: async (landlordUuid: string): Promise<Tenant[]> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPITENANTSLIST(landlordUuid));
    if (!res.ok) throw new Error("Failed to fetch tenants");
    return res.json();
  },

  getTenant: async (landlordUuid: string, id: number): Promise<Tenant> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPITENANTSGET(landlordUuid, id));
    if (!res.ok) throw new Error("Failed to fetch tenant");
    return res.json();
  },

  addTenant: async (landlordUuid: string, tenant: Omit<Tenant, "id">): Promise<{ status: string; tenant: Tenant }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPITENANTSCREATE(landlordUuid), {
      method: "POST",
      body: JSON.stringify(tenant),
    });
    if (!res.ok) throw new Error("Failed to add tenant");
    return res.json();
  },

  updateTenant: async (landlordUuid: string, id: number, tenant: Tenant): Promise<{ status: string; tenant: Tenant }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPITENANTSUPDATE(landlordUuid, id), {
      method: "PUT",
      body: JSON.stringify(tenant),
    });
    if (!res.ok) throw new Error("Failed to update tenant");
    return res.json();
  },

  revealTenantPin: async (landlordUuid: string, id: number): Promise<{ status: string; pin: string }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPITENANTSREVEALPIN(landlordUuid, id));
    if (!res.ok) throw new Error("Failed to reveal PIN");
    return res.json();
  },

  CHANGETENANTPIN: async (landlordUuid: string, tenantId: number, payload: { pin: string; logout_all?: boolean }) => {
    const res = await fetch(ROUTES.LANDLORDAPITENANTSCHANGEPIN(landlordUuid, tenantId), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to change tenant PIN");
    return data;
  },

  deleteTenant: async (landlordUuid: string, id: number, action: string = "archive"): Promise<{ status: string }> => {
    const res = await fetchWithAuth(`${ROUTES.LANDLORDAPITENANTSDELETE(landlordUuid, id)}?action=${action}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete tenant");
    return res.json();
  },

  getTenantReceipts: async (landlordUuid: string, tenantId: number): Promise<Receipt[]> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPITENANTSRECEIPTS(landlordUuid, tenantId));
    if (!res.ok) throw new Error("Failed to fetch tenant receipts");
    return res.json();
  },

  // Bills / Receipts
  getAllReceipts: async (landlordUuid: string): Promise<Receipt[]> => {
    const res = await fetchWithAuth(`${ROUTES.LANDLORDAPIBILLINGFILTER(landlordUuid)}?status=all`);
    if (!res.ok) throw new Error("Failed to fetch receipts");
    return res.json();
  },

  getActiveReceipts: async (landlordUuid: string): Promise<Receipt[]> => {
    const res = await fetchWithAuth(`${ROUTES.LANDLORDAPIBILLINGFILTER(landlordUuid)}?status=active`);
    if (!res.ok) throw new Error("Failed to fetch receipts");
    return res.json();
  },

  getArchiveData: async (landlordUuid: string): Promise<ArchiveDataResponse> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIBILLINGARCHIVEDATA(landlordUuid));
    if (!res.ok) throw new Error("Failed to fetch archive data");
    const data = await res.json();
    return {
      tenants: Array.isArray(data.tenants) ? data.tenants : [],
      receipts: Array.isArray(data.receipts) ? data.receipts : [],
    };
  },

  getArchivedReceipts: async (landlordUuid: string): Promise<Receipt[]> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIBILLINGARCHIVEDATA(landlordUuid));
    if (!res.ok) throw new Error("Failed to fetch receipts");
    const data = await res.json();
    return Array.isArray(data.receipts) ? data.receipts : [];
  },

  archiveTenant: async (landlordUuid: string, tenantId: number): Promise<{ status: string }> => {
    const res = await fetchWithAuth(`${ROUTES.LANDLORDAPITENANTSDELETE(landlordUuid, tenantId)}?action=archive`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to archive tenant");
    return res.json();
  },

  restoreTenant: async (landlordUuid: string, tenantId: number): Promise<{ status: string; action: string; data: unknown }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPITENANTSRESTORE(landlordUuid, tenantId), {
      method: "POST",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error((err as Record<string, string>).detail || "Failed to restore tenant");
    }
    return res.json();
  },

  permanentlyDeleteArchivedTenant: async (landlordUuid: string, tenantId: number): Promise<PermanentDeleteResult> => {
    const res = await fetchWithAuth(
      `${ROUTES.LANDLORDAPITENANTSDELETE(landlordUuid, tenantId)}?action=permanent-with-recovery`,
      { method: "DELETE" }
    );
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? "Permanent deletion failed");
    return data;
  },

  getTenantRecoverySnapshots: async (landlordUuid: string): Promise<{ status: string; snapshots: TenantRecoverySnapshot[] }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPITENANTRECOVERYSNAPSHOTS(landlordUuid));
    if (!res.ok) throw new Error("Failed to fetch recovery snapshots");
    return res.json();
  },

  getTenantRecoverySnapshotPreview: async (landlordUuid: string, snapshotId: string): Promise<SnapshotRestorePreview & { status: string }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPITENANTSNAPSHOT_PREVIEW(landlordUuid, snapshotId));
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? "Failed to load restore preview");
    return data;
  },

  restoreTenantFromSnapshot: async (
    landlordUuid: string,
    snapshotId: string,
    forceNewId: boolean = false
  ): Promise<{ status: string; original_tenant_id: number; restored_tenant_id: number; id_changed: boolean }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPITENANTSNAPSHOT_RESTORE(landlordUuid, snapshotId), {
      method: "POST",
      body: JSON.stringify({ force_new_id: forceNewId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? "Restore from snapshot failed");
    return data;
  },

  getReceipt: async (landlordUuid: string, tenantId: number, billNo: string): Promise<Receipt> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIBILLINGGET(landlordUuid, tenantId, billNo));
    if (!res.ok) throw new Error("Failed to fetch receipt");
    return res.json();
  },

  createBill: async (landlordUuid: string, tenantId: number, data: Record<string, unknown>): Promise<{ status: string; data: Receipt }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIBILLINGCREATE(landlordUuid, tenantId), {
      method: "POST",
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || "Failed to create bill");
    return result;
  },

  updateBill: async (landlordUuid: string, tenantId: number, billNo: string, data: Record<string, unknown>): Promise<{ status: string; data: Receipt }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIBILLINGUPDATE(landlordUuid, tenantId, billNo), {
      method: "PUT",
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || "Failed to update bill");
    return result;
  },

  updatePaymentStatus: async (landlordUuid: string, tenantId: number, billNo: string, data: PaymentStatusUpdate): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIBILLINGUPDATEPAYMENT(landlordUuid, tenantId, billNo), {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to update payment status");
    return res.json();
  },

  archiveBill: async (landlordUuid: string, tenantId: number, billNo: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIBILLINGARCHIVE(landlordUuid, tenantId, billNo), { method: "POST" });
    if (!res.ok) throw new Error("Failed to archive bill");
    return res.json();
  },

  restoreBill: async (landlordUuid: string, tenantId: number, billNo: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIBILLINGRESTORE(landlordUuid, tenantId, billNo), { method: "POST" });
    if (!res.ok) throw new Error("Failed to restore bill");
    return res.json();
  },

  permanentlyDeleteBill: async (landlordUuid: string, tenantId: number, billNo: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIBILLINGDELETE(landlordUuid, tenantId, billNo), { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete bill");
    return res.json();
  },

  // Billing
  getBillingMonths: async (landlordUuid: string): Promise<{ months: string[]; currentMonth: string }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIBILLINGMONTHS(landlordUuid));
    if (!res.ok) throw new Error("Failed to fetch billing months");
    return res.json();
  },

  previewBilling: async (landlordUuid: string, params: Record<string, string | number>): Promise<Record<string, number>> => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    const res = await fetchWithAuth(`${ROUTES.LANDLORDAPIBILLINGPREVIEW(landlordUuid)}?${query}`);
    if (!res.ok) throw new Error("Failed to preview billing");
    return res.json();
  },

  // Settings
  getConfig: async (landlordUuid: string): Promise<AppConfig> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPICONFIGGET(landlordUuid));
    if (!res.ok) throw new Error('Failed to fetch config');
    return res.json();
  },

  getTotpQr: async (landlordUuid: string): Promise<{ status: string, totp: { secret: string, qr_code_base64: string, provisioning_uri: string } }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPITOTPQR(landlordUuid));
    if (!res.ok) throw new Error('Failed to fetch TOTP QR');
    return res.json();
  },

  regenerateTotp: async (landlordUuid: string): Promise<{ status: string, totp: { secret: string, qr_code_base64: string, provisioning_uri: string } }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPITOTPREGENERATE(landlordUuid), { method: "POST" });
    if (!res.ok) throw new Error('Failed to regenerate TOTP');
    return res.json();
  },

  enableTotp: async (landlordUuid: string): Promise<{ status: string, totp?: { secret: string, qr_code_base64: string, provisioning_uri: string } }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPITOTPENABLE(landlordUuid), { method: "POST" });
    if (!res.ok) throw new Error('Failed to enable TOTP');
    return res.json();
  },

  disableTotp: async (landlordUuid: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPITOTPDISABLE(landlordUuid), { method: "POST" });
    if (!res.ok) throw new Error('Failed to disable TOTP');
    return res.json();
  },

  saveConfig: async (landlordUuid: string, config: Partial<AppConfig>): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPICONFIGUPDATE(landlordUuid), {
      method: 'POST',
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error('Failed to save config');
    return res.json();
  },

  UPDATETHEME: async (landlordUuid: string, theme: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPICONFIGTHEME(landlordUuid), {
      method: 'POST',
      body: JSON.stringify({ theme }),
    });
    if (!res.ok) throw new Error('Failed to update theme');
    return res.json();
  },

  GETTHEME: async (landlordUuid: string): Promise<{ status: string; theme: string }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPICONFIGTHEMEGET(landlordUuid));
    if (!res.ok) throw new Error('Failed to fetch theme');
    return res.json();
  },

  downloadTemplate: (landlordUuid: string): string => ROUTES.LANDLORDAPISYNCTEMPLATE(landlordUuid),

  exportExcel: (landlordUuid: string, format: string): string => ROUTES.LANDLORDAPISYNCEXPORTEXCEL(landlordUuid, format),

  importPreview: async (landlordUuid: string, data: FormData): Promise<any> => {
    const res = await fetch(ROUTES.LANDLORDAPISYNCIMPORTPREVIEW(landlordUuid), {
      method: 'POST',
      body: data,
      credentials: 'include',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || 'Failed to preview import');
    }
    return res.json();
  },

  importExecute: async (landlordUuid: string, data: FormData): Promise<{ status: string }> => {
    const res = await fetch(ROUTES.LANDLORDAPISYNCIMPORTEXECUTE(landlordUuid), {
      method: 'POST',
      body: data,
      credentials: 'include',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || 'Failed to execute import');
    }
    return res.json();
  },

  // Backups
  getBackups: async (landlordUuid: string): Promise<{ backups: Backup[] }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIBACKUPSLIST(landlordUuid));
    if (!res.ok) throw new Error("Failed to fetch backups");
    return res.json();
  },

  createManualBackup: async (landlordUuid: string): Promise<{ status: string; data: Backup }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIBACKUPSCREATEMANUAL(landlordUuid), { method: "POST" });
    if (!res.ok) throw new Error("Failed to create backup");
    return res.json();
  },

  deleteBackup: async (landlordUuid: string, id: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIBACKUPSDELETE(landlordUuid, id), { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete backup");
    return res.json();
  },

  verifyBackup: async (landlordUuid: string, id: string): Promise<{ status: string; message: string }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIBACKUPSVERIFY(landlordUuid, id));
    return res.json();
  },

  restoreBackup: async (landlordUuid: string, id: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIBACKUPSRESTORE(landlordUuid, id), { method: "POST" });
    if (!res.ok) throw new Error("Failed to restore backup");
    return res.json();
  },

  downloadBackup: (landlordUuid: string, id: string): string => ROUTES.LANDLORDAPIBACKUPSDOWNLOAD(landlordUuid, id),

  // PDF
  getPDFViewUrl: (landlordUuid: string, tenantId: number, billNo: string): string => ROUTES.LANDLORDAPIPDFVIEW(landlordUuid, tenantId, billNo),
  getPDFDownloadUrl: (landlordUuid: string, tenantId: number, billNo: string): string => ROUTES.LANDLORDAPIPDFDOWNLOAD(landlordUuid, tenantId, billNo),

  // WhatsApp
  sendWhatsApp: async (landlordUuid: string, tenantId: number, billNo: string): Promise<{ status: string; url: string }> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIWHATSAPPSENDSINGLE(landlordUuid, tenantId, billNo));
    if (!res.ok) throw new Error("Failed to generate WhatsApp link");
    return res.json();
  },

  // Auth (no landlordUuid needed — auth routes don't use it)
  login: async (username: string, password: string, rememberMe: boolean = false): Promise<Response> => {
    return fetch(ROUTES.LANDLORDAPIAUTHLOGIN, {
      method: "POST",
      body: JSON.stringify({ username, password, rememberMe }),
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });
  },

  logout: async (): Promise<void> => {
    await fetch(ROUTES.LANDLORDAPIAUTHLOGOUT, { method: "POST", credentials: "include" });
    window.location.href = ROUTES.LANDLORDPAGELOGIN;
  },

  // Occupants
  getOccupants: async (landlordUuid: string, tenantId: string | number): Promise<Occupant[]> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIOCCUPANTSLIST(landlordUuid, Number(tenantId)));
    if (!res.ok) throw new Error("Failed to fetch occupants");
    const data = await res.json();
    return data.occupants || [];
  },

  saveOccupant: async (landlordUuid: string, tenantId: string | number, data: FormData): Promise<{ status: string; occupantUuid: string }> => {
    const res = await fetch(ROUTES.LANDLORDAPIOCCUPANTSCREATE(landlordUuid, Number(tenantId)), {
      method: "POST",
      body: data,
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error((err as any).detail || "Failed to save occupant");
    }
    return res.json();
  },

  markOccupantInactive: async (landlordUuid: string, tenantId: string | number, occupantUuid: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(
      ROUTES.LANDLORDAPIOCCUPANTSMARKINACTIVE(landlordUuid, Number(tenantId), occupantUuid),
      { method: "PUT" }
    );
    if (!res.ok) throw new Error("Failed to mark occupant inactive");
    return res.json();
  },

  deleteOccupant: async (landlordUuid: string, tenantId: string | number, occupantUuid: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(
      ROUTES.LANDLORDAPIOCCUPANTSDELETE(landlordUuid, Number(tenantId), occupantUuid),
      { method: "DELETE" }
    );
    if (!res.ok) throw new Error("Failed to delete occupant");
    return res.json();
  },

  getOccupantFileUrl: (landlordUuid: string, tenantId: string | number, filename: string): string =>
    ROUTES.LANDLORDAPIOCCUPANTSGETFILE(landlordUuid, Number(tenantId), filename),

  // Audit Logs
  getActivityLogs: async (
    landlordUuid: string,
    params: { action_type?: string; search?: string; date_from?: string; date_to?: string; limit?: number; offset?: number } = {}
  ): Promise<{ items: any[]; total: number }> => {
    const qs = new URLSearchParams();
    if (params.action_type) qs.set("action_type", params.action_type);
    if (params.search) qs.set("search", params.search);
    if (params.date_from) qs.set("date_from", params.date_from);
    if (params.date_to) qs.set("date_to", params.date_to);
    if (params.limit) qs.set("limit", String(params.limit));
    if (params.offset) qs.set("offset", String(params.offset));
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIAUDITLOGS(landlordUuid) + `?${qs}`);
    if (!res.ok) throw new Error("Failed to fetch activity logs");
    return res.json();
  },

  getActivityActionTypes: async (landlordUuid: string): Promise<string[]> => {
    const res = await fetchWithAuth(ROUTES.LANDLORDAPIAUDITLOGSACTIONS(landlordUuid));
    if (!res.ok) throw new Error("Failed to fetch action types");
    return res.json();
  },
};
