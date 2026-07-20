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
    window.location.href = ROUTES.ADMINPAGELOGIN;
    throw new Error("Unauthorized");
  }
  return res;
}

export const api = {
  // Dashboard
  getDashboardStats: async (): Promise<DashboardStats> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIDASHBOARDSTATS);
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
  getTenants: async (): Promise<Tenant[]> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPITENANTSLIST);
    if (!res.ok) throw new Error("Failed to fetch tenants");
    return res.json();
  },

  getTenant: async (id: number): Promise<Tenant> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPITENANTSGET(id));
    if (!res.ok) throw new Error("Failed to fetch tenant");
    return res.json();
  },

  addTenant: async (tenant: Omit<Tenant, "id">): Promise<{ status: string; tenant: Tenant }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPITENANTSCREATE, {
      method: "POST",
      body: JSON.stringify(tenant),
    });
    if (!res.ok) throw new Error("Failed to add tenant");
    return res.json();
  },

  updateTenant: async (id: number, tenant: Tenant): Promise<{ status: string; tenant: Tenant }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPITENANTSUPDATE(id), {
      method: "PUT",
      body: JSON.stringify(tenant),
    });
    if (!res.ok) throw new Error("Failed to update tenant");
    return res.json();
  },

  revealTenantPin: async (id: number): Promise<{ status: string; pin: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPITENANTSREVEALPIN(id));
    if (!res.ok) throw new Error("Failed to reveal PIN");
    return res.json();
  },

  CHANGETENANTPIN: async (tenantId: number, payload: { pin: string; logout_all?: boolean }) => {
    const res = await fetch(ROUTES.ADMINAPITENANTSCHANGEPIN(tenantId), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to change tenant PIN");
    return data;
  },

  deleteTenant: async (id: number, action: string = "archive"): Promise<{ status: string }> => {
    const res = await fetchWithAuth(`${ROUTES.ADMINAPITENANTSDELETE(id)}?action=${action}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete tenant");
    return res.json();
  },

  getTenantReceipts: async (tenantId: number): Promise<Receipt[]> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPITENANTSRECEIPTS(tenantId));
    if (!res.ok) throw new Error("Failed to fetch tenant receipts");
    return res.json();
  },

  // Bills / Receipts
  getAllReceipts: async (): Promise<Receipt[]> => {
    const res = await fetchWithAuth(`${ROUTES.ADMINAPIBILLINGFILTER}?status=all`);
    if (!res.ok) throw new Error("Failed to fetch receipts");
    return res.json();
  },

  getActiveReceipts: async (): Promise<Receipt[]> => {
    const res = await fetchWithAuth(`${ROUTES.ADMINAPIBILLINGFILTER}?status=active`);
    if (!res.ok) throw new Error("Failed to fetch receipts");
    return res.json();
  },

  // Returns both archived tenants and archived receipts — use this for the Archive page.
  // Groups receipts by TenantId on the frontend to avoid name-based contamination.
  getArchiveData: async (): Promise<ArchiveDataResponse> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGARCHIVEDATA);
    if (!res.ok) throw new Error("Failed to fetch archive data");
    const data = await res.json();
    return {
      tenants: Array.isArray(data.tenants) ? data.tenants : [],
      receipts: Array.isArray(data.receipts) ? data.receipts : [],
    };
  },

  // Legacy: flat receipts only — prefer getArchiveData() for the Archive page.
  getArchivedReceipts: async (): Promise<Receipt[]> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGARCHIVEDATA);
    if (!res.ok) throw new Error("Failed to fetch receipts");
    const data = await res.json();
    return Array.isArray(data.receipts) ? data.receipts : [];
  },

  // Archive a tenant (marks tenant + all their receipts as Archived)
  archiveTenant: async (tenantId: number): Promise<{ status: string }> => {
    const res = await fetchWithAuth(`${ROUTES.ADMINAPITENANTSDELETE(tenantId)}?action=archive`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to archive tenant");
    return res.json();
  },

  // Restore an archived tenant back to Active — uses dedicated POST endpoint.
  // Must NOT use DELETE ?action=restore: archived tenants fail the delete route's pre-check.
  restoreTenant: async (tenantId: number): Promise<{ status: string; action: string; data: unknown }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPITENANTSRESTORE(tenantId), {
      method: "POST",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error((err as Record<string, string>).detail || "Failed to restore tenant");
    }
    return res.json();
  },

  // Permanently delete an archived tenant with synchronous recovery snapshot.
  // Recovery is available until the admin-configured retention deadline.
  permanentlyDeleteArchivedTenant: async (tenantId: number): Promise<PermanentDeleteResult> => {
    const res = await fetchWithAuth(
      `${ROUTES.ADMINAPITENANTSDELETE(tenantId)}?action=permanent-with-recovery`,
      { method: "DELETE" }
    );
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? "Permanent deletion failed");
    return data;
  },

  // List all tenant recovery snapshots (triggers expiry purge on backend first).
  getTenantRecoverySnapshots: async (): Promise<{ status: string; snapshots: TenantRecoverySnapshot[] }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPITENANTRECOVERYSNAPSHOTS);
    if (!res.ok) throw new Error("Failed to fetch recovery snapshots");
    return res.json();
  },

  // Get conflict preview for a specific snapshot before restoring.
  getTenantRecoverySnapshotPreview: async (snapshotId: string): Promise<SnapshotRestorePreview & { status: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPITENANTSNAPSHOT_PREVIEW(snapshotId));
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? "Failed to load restore preview");
    return data;
  },

  // Execute restore of a tenant from a recovery snapshot.
  restoreTenantFromSnapshot: async (
    snapshotId: string,
    forceNewId: boolean = false
  ): Promise<{ status: string; original_tenant_id: number; restored_tenant_id: number; id_changed: boolean }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPITENANTSNAPSHOT_RESTORE(snapshotId), {
      method: "POST",
      body: JSON.stringify({ force_new_id: forceNewId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? "Restore from snapshot failed");
    return data;
  },

  getReceipt: async (tenantId: number, billNo: string): Promise<Receipt> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGGET(tenantId, billNo));
    if (!res.ok) throw new Error("Failed to fetch receipt");
    return res.json();
  },

  createBill: async (tenantId: number, data: Record<string, unknown>): Promise<{ status: string; data: Receipt }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGCREATE(tenantId), {
      method: "POST",
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || "Failed to create bill");
    return result;
  },

  updateBill: async (tenantId: number, billNo: string, data: Record<string, unknown>): Promise<{ status: string; data: Receipt }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGUPDATE(tenantId, billNo), {
      method: "PUT",
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || "Failed to update bill");
    return result;
  },

  updatePaymentStatus: async (tenantId: number, billNo: string, data: PaymentStatusUpdate): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGUPDATEPAYMENT(tenantId, billNo), {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to update payment status");
    return res.json();
  },

  archiveBill: async (tenantId: number, billNo: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGARCHIVE(tenantId, billNo), { method: "POST" });
    if (!res.ok) throw new Error("Failed to archive bill");
    return res.json();
  },

  restoreBill: async (tenantId: number, billNo: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGRESTORE(tenantId, billNo), { method: "POST" });
    if (!res.ok) throw new Error("Failed to restore bill");
    return res.json();
  },

  permanentlyDeleteBill: async (tenantId: number, billNo: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGDELETE(tenantId, billNo), { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete bill");
    return res.json();
  },

  // Billing
  getBillingMonths: async (): Promise<{ months: string[]; currentMonth: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGMONTHS);
    if (!res.ok) throw new Error("Failed to fetch billing months");
    return res.json();
  },

  previewBilling: async (params: Record<string, string | number>): Promise<Record<string, number>> => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    const res = await fetchWithAuth(`${ROUTES.ADMINAPIBILLINGPREVIEW}?${query}`);
    if (!res.ok) throw new Error("Failed to preview billing");
    return res.json();
  },

  // Settings
  getConfig: async (): Promise<AppConfig> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPICONFIGGET);
    if (!res.ok) throw new Error('Failed to fetch config');
    return res.json();
  },

  getTotpQr: async (): Promise<{ status: string, totp: { secret: string, qr_code_base64: string, provisioning_uri: string } }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPITOTPQR);
    if (!res.ok) throw new Error('Failed to fetch TOTP QR');
    return res.json();
  },

  saveConfig: async (config: Partial<AppConfig>): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPICONFIGUPDATE, {
      method: 'POST',
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error('Failed to save config');
    return res.json();
  },

  UPDATETHEME: async (theme: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPICONFIGTHEME, {
      method: 'POST',
      body: JSON.stringify({ theme }),
    });
    if (!res.ok) throw new Error('Failed to update theme');
    return res.json();
  },

  downloadTemplate: (): string => ROUTES.ADMINAPISYNCTEMPLATE,

  exportExcel: (format: string): string => ROUTES.ADMINAPISYNCEXPORTEXCEL(format),

  importPreview: async (data: FormData): Promise<any> => {
    const res = await fetch(ROUTES.ADMINAPISYNCIMPORTPREVIEW, {
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

  importExecute: async (data: FormData): Promise<{ status: string }> => {
    const res = await fetch(ROUTES.ADMINAPISYNCIMPORTEXECUTE, {
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
  getBackups: async (): Promise<{ backups: Backup[] }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBACKUPSLIST);
    if (!res.ok) throw new Error("Failed to fetch backups");
    return res.json();
  },

  createManualBackup: async (): Promise<{ status: string; data: Backup }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBACKUPSCREATEMANUAL, { method: "POST" });
    if (!res.ok) throw new Error("Failed to create backup");
    return res.json();
  },

  deleteBackup: async (id: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBACKUPSDELETE(id), { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete backup");
    return res.json();
  },

  verifyBackup: async (id: string): Promise<{ status: string; message: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBACKUPSVERIFY(id));
    return res.json();
  },

  restoreBackup: async (id: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBACKUPSRESTORE(id), { method: "POST" });
    if (!res.ok) throw new Error("Failed to restore backup");
    return res.json();
  },

  // PDF
  getPDFViewUrl: (tenantId: number, billNo: string): string => ROUTES.ADMINAPIPDFVIEW(tenantId, billNo),
  getPDFDownloadUrl: (tenantId: number, billNo: string): string => ROUTES.ADMINAPIPDFDOWNLOAD(tenantId, billNo),

  // WhatsApp
  sendWhatsApp: async (tenantId: number, billNo: string): Promise<{ status: string; url: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIWHATSAPPSENDSINGLE(tenantId, billNo));
    if (!res.ok) throw new Error("Failed to generate WhatsApp link");
    return res.json();
  },

  // Auth
  login: async (username: string, password: string, rememberMe: boolean = false): Promise<Response> => {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);
    formData.append("remember_me", String(rememberMe));
    return fetch(ROUTES.ADMINAPIAUTHLOGIN, {
      method: "POST",
      body: formData,
      credentials: "include",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },

  logout: async (): Promise<void> => {
    await fetch(ROUTES.ADMINAPIAUTHLOGOUT, { credentials: "include" });
    window.location.href = ROUTES.ADMINPAGELOGIN;
  },

  // Occupants
  getOccupants: async (tenantId: string | number): Promise<Occupant[]> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIOCCUPANTSLIST(Number(tenantId)));
    if (!res.ok) throw new Error("Failed to fetch occupants");
    const data = await res.json();
    return data.occupants || [];
  },

  saveOccupant: async (tenantId: string | number, data: FormData): Promise<{ status: string; occupantUuid: string }> => {
    const res = await fetch(ROUTES.ADMINAPIOCCUPANTSCREATE(Number(tenantId)), {
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

  markOccupantInactive: async (tenantId: string | number, occupantUuid: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(
      ROUTES.ADMINAPIOCCUPANTSMARKINACTIVE(Number(tenantId), occupantUuid),
      { method: "PUT" }
    );
    if (!res.ok) throw new Error("Failed to mark occupant inactive");
    return res.json();
  },

  deleteOccupant: async (tenantId: string | number, occupantUuid: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(
      ROUTES.ADMINAPIOCCUPANTSDELETE(Number(tenantId), occupantUuid),
      { method: "DELETE" }
    );
    if (!res.ok) throw new Error("Failed to delete occupant");
    return res.json();
  },

  // Returns a direct URL — use as img src / iframe src so browser sends cookies automatically
  getOccupantFileUrl: (tenantId: string | number, filename: string): string =>
    ROUTES.ADMINAPIOCCUPANTSGETFILE(Number(tenantId), filename),

  // downloadTemplate: (): string => ROUTES.ADMINAPISYNCTEMPLATE,
};
