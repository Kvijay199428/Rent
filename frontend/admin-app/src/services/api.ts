import type { Tenant, Receipt, DashboardStats, AppConfig, Backup, PaymentStatusUpdate, Occupant } from "@/types";
import { ROUTES } from "@/lib/routes";

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
    window.location.href = ROUTES.ADMIN_PAGE_LOGIN;
    throw new Error("Unauthorized");
  }
  return res;
}

export const api = {
  // Dashboard
  getDashboardStats: async (): Promise<DashboardStats> => {
    const res = await fetchWithAuth(ROUTES.ADMIN_API_DASHBOARD_STATS);
    if (!res.ok) throw new Error("Failed to fetch dashboard stats");
    const data = await res.json();
    return data.stats || data;
  },

  // Tenants
  getTenants: async (): Promise<Tenant[]> => {
    const res = await fetchWithAuth(ROUTES.ADMIN_API_TENANTS_LIST);
    if (!res.ok) throw new Error("Failed to fetch tenants");
    return res.json();
  },

  getTenant: async (id: number): Promise<Tenant> => {
    const res = await fetchWithAuth(ROUTES.adminApiTenantsGet(id));
    if (!res.ok) throw new Error("Failed to fetch tenant");
    return res.json();
  },

  addTenant: async (tenant: Omit<Tenant, "id">): Promise<{ status: string; tenant: Tenant }> => {
    const res = await fetchWithAuth(ROUTES.ADMIN_API_TENANTS_CREATE, {
      method: "POST",
      body: JSON.stringify(tenant),
    });
    if (!res.ok) throw new Error("Failed to add tenant");
    return res.json();
  },

  updateTenant: async (id: number, tenant: Tenant): Promise<{ status: string; tenant: Tenant }> => {
    const res = await fetchWithAuth(ROUTES.adminApiTenantsUpdate(id), {
      method: "PUT",
      body: JSON.stringify(tenant),
    });
    if (!res.ok) throw new Error("Failed to update tenant");
    return res.json();
  },

  revealTenantPin: async (id: number): Promise<{ status: string; pin: string }> => {
    const res = await fetchWithAuth(ROUTES.adminApiTenantsRevealPin(id));
    if (!res.ok) throw new Error("Failed to reveal PIN");
    return res.json();
  },

  changeTenantPin: async (tenantId: number, payload: { pin: string; logout_all?: boolean }) => {
    const res = await fetch(ROUTES.adminApiTenantsChangePin(tenantId), {
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
    const res = await fetchWithAuth(`${ROUTES.adminApiTenantsDelete(id)}?action=${action}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete tenant");
    return res.json();
  },

  getTenantReceipts: async (tenantName: string): Promise<Receipt[]> => {
    const res = await fetchWithAuth(ROUTES.adminApiTenantsReceipts(tenantName));
    if (!res.ok) throw new Error("Failed to fetch tenant receipts");
    return res.json();
  },

  // Bills / Receipts
  getAllReceipts: async (): Promise<Receipt[]> => {
    const res = await fetchWithAuth(`${ROUTES.ADMIN_API_BILLING_FILTER}?status=all`);
    if (!res.ok) throw new Error("Failed to fetch receipts");
    return res.json();
  },

  getActiveReceipts: async (): Promise<Receipt[]> => {
    const res = await fetchWithAuth(`${ROUTES.ADMIN_API_BILLING_FILTER}?status=active`);
    if (!res.ok) throw new Error("Failed to fetch receipts");
    return res.json();
  },

  getArchivedReceipts: async (): Promise<Receipt[]> => {
    const res = await fetchWithAuth(`${ROUTES.ADMIN_API_BILLING_FILTER}?status=all`);
    if (!res.ok) throw new Error("Failed to fetch receipts");
    const data = await res.json();
    return data.filter((r: Receipt) => r.Status === "ARCHIVED");
  },

  getReceipt: async (billNo: string): Promise<Receipt> => {
    const res = await fetchWithAuth(ROUTES.adminApiBillingGet(billNo));
    if (!res.ok) throw new Error("Failed to fetch receipt");
    return res.json();
  },

  createBill: async (data: Record<string, unknown>): Promise<{ status: string; data: Receipt }> => {
    const res = await fetchWithAuth(ROUTES.ADMIN_API_BILLING_CREATE, {
      method: "POST",
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || "Failed to create bill");
    return result;
  },

  updateBill: async (billNo: string, data: Record<string, unknown>): Promise<{ status: string; data: Receipt }> => {
    const res = await fetchWithAuth(ROUTES.adminApiBillingUpdate(billNo), {
      method: "POST",
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || "Failed to update bill");
    return result;
  },

  updatePaymentStatus: async (billNo: string, data: PaymentStatusUpdate): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.adminApiBillingUpdatePayment(billNo), {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to update payment status");
    return res.json();
  },

  archiveBill: async (billNo: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.adminApiBillingArchive(billNo), { method: "POST" });
    if (!res.ok) throw new Error("Failed to archive bill");
    return res.json();
  },

  restoreBill: async (billNo: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.adminApiBillingRestore(billNo), { method: "POST" });
    if (!res.ok) throw new Error("Failed to restore bill");
    return res.json();
  },

  permanentlyDeleteBill: async (billNo: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.adminApiBillingDelete(billNo), { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete bill");
    return res.json();
  },

  // Billing
  getBillingMonths: async (): Promise<{ months: string[]; currentMonth: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMIN_API_BILLING_MONTHS);
    if (!res.ok) throw new Error("Failed to fetch billing months");
    return res.json();
  },

  previewBilling: async (params: Record<string, string | number>): Promise<Record<string, number>> => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    const res = await fetchWithAuth(`${ROUTES.ADMIN_API_BILLING_PREVIEW}?${query}`);
    if (!res.ok) throw new Error("Failed to preview billing");
    return res.json();
  },

  // Settings
  getConfig: async (): Promise<AppConfig> => {
    const res = await fetchWithAuth(ROUTES.ADMIN_API_CONFIG_GET);
    if (!res.ok) throw new Error('Failed to fetch config');
    return res.json();
  },

  saveConfig: async (config: Partial<AppConfig>): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMIN_API_CONFIG_UPDATE, {
      method: 'POST',
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error('Failed to save config');
    return res.json();
  },

  updateTheme: async (theme: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMIN_API_CONFIG_THEME, {
      method: 'POST',
      body: JSON.stringify({ theme }),
    });
    if (!res.ok) throw new Error('Failed to update theme');
    return res.json();
  },

  downloadTemplate: (): string => ROUTES.ADMIN_API_SYNC_TEMPLATE,

  exportExcel: (format: string): string => ROUTES.adminApiSyncExportExcel(format),

  importPreview: async (data: FormData): Promise<any> => {
    const res = await fetch(ROUTES.ADMIN_API_SYNC_IMPORT_PREVIEW, {
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
    const res = await fetch(ROUTES.ADMIN_API_SYNC_IMPORT_EXECUTE, {
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
    const res = await fetchWithAuth(ROUTES.ADMIN_API_BACKUPS_LIST);
    if (!res.ok) throw new Error("Failed to fetch backups");
    return res.json();
  },

  createManualBackup: async (): Promise<{ status: string; data: Backup }> => {
    const res = await fetchWithAuth(ROUTES.ADMIN_API_BACKUPS_CREATE_MANUAL, { method: "POST" });
    if (!res.ok) throw new Error("Failed to create backup");
    return res.json();
  },

  deleteBackup: async (id: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.adminApiBackupsDelete(id), { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete backup");
    return res.json();
  },

  verifyBackup: async (id: string): Promise<{ status: string; message: string }> => {
    const res = await fetchWithAuth(ROUTES.adminApiBackupsVerify(id));
    return res.json();
  },

  restoreBackup: async (id: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.adminApiBackupsRestore(id), { method: "POST" });
    if (!res.ok) throw new Error("Failed to restore backup");
    return res.json();
  },

  // PDF
  getPDFViewUrl: (billNo: string): string => ROUTES.adminApiPdfView(billNo),
  getPDFDownloadUrl: (billNo: string): string => ROUTES.adminApiPdfDownload(billNo),

  // WhatsApp
  sendWhatsApp: async (billNo: string): Promise<{ status: string; url: string }> => {
    const res = await fetchWithAuth(ROUTES.adminApiWhatsappSendSingle(billNo));
    if (!res.ok) throw new Error("Failed to generate WhatsApp link");
    return res.json();
  },

  // Auth
  login: async (username: string, password: string, rememberMe: boolean = false): Promise<Response> => {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);
    formData.append("remember_me", String(rememberMe));
    return fetch(ROUTES.ADMIN_API_AUTH_LOGIN, {
      method: "POST",
      body: formData,
      credentials: "include",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },

  logout: async (): Promise<void> => {
    await fetch(ROUTES.ADMIN_API_AUTH_LOGOUT, { credentials: "include" });
    window.location.href = ROUTES.ADMIN_PAGE_LOGIN;
  },

  // Occupants
  getOccupants: async (tenantId: string | number): Promise<Occupant[]> => {
    const res = await fetchWithAuth(`${ROUTES.ADMIN_API_OCCUPANTS_LIST}?tenant_id=${tenantId}`);
    if (!res.ok) throw new Error("Failed to fetch occupants");
    const data = await res.json();
    return data.occupants || [];
  },

  saveOccupant: async (tenantId: string | number, data: FormData): Promise<{ status: string }> => {
    const res = await fetch(`${ROUTES.ADMIN_API_OCCUPANTS_LIST}?tenant_id=${tenantId}`, {
      method: "POST",
      body: data,
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to save occupant");
    }
    return res.json();
  },

  deleteOccupant: async (tenantId: string | number, occupantUuid: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(
      ROUTES.adminApiOccupantsDelete(Number(tenantId), occupantUuid),
      { method: "DELETE" }
    );
    if (!res.ok) throw new Error("Failed to delete occupant");
    return res.json();
  },

  // downloadTemplate: (): string => ROUTES.ADMIN_API_SYNC_TEMPLATE,
};
