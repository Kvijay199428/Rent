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
    window.location.href = ROUTES.ADMINPAGELOGIN;
    throw new Error("Unauthorized");
  }
  return res;
}

export const api = {
  // Dashboard
  getDashboardStats: async (): Promise<DashboardStats> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIDASHBOARDSTATS);
    if (!res.ok) throw new Error("Failed to fetch dashboard stats");
    const data = await res.json();
    return data.stats || data;
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

  getTenantReceipts: async (tenantName: string): Promise<Receipt[]> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPITENANTSRECEIPTS(tenantName));
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

  getArchivedReceipts: async (): Promise<Receipt[]> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGARCHIVEDATA);
    if (!res.ok) throw new Error("Failed to fetch receipts");
    const data = await res.json();
    return data.receipts;
  },

  getReceipt: async (billNo: string): Promise<Receipt> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGGET(billNo));
    if (!res.ok) throw new Error("Failed to fetch receipt");
    return res.json();
  },

  createBill: async (data: Record<string, unknown>): Promise<{ status: string; data: Receipt }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGCREATE, {
      method: "POST",
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || "Failed to create bill");
    return result;
  },

  updateBill: async (billNo: string, data: Record<string, unknown>): Promise<{ status: string; data: Receipt }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGUPDATE(billNo), {
      method: "POST",
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || "Failed to update bill");
    return result;
  },

  updatePaymentStatus: async (billNo: string, data: PaymentStatusUpdate): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGUPDATEPAYMENT(billNo), {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to update payment status");
    return res.json();
  },

  archiveBill: async (billNo: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGARCHIVE(billNo), { method: "POST" });
    if (!res.ok) throw new Error("Failed to archive bill");
    return res.json();
  },

  restoreBill: async (billNo: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGRESTORE(billNo), { method: "POST" });
    if (!res.ok) throw new Error("Failed to restore bill");
    return res.json();
  },

  permanentlyDeleteBill: async (billNo: string): Promise<{ status: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIBILLINGDELETE(billNo), { method: "DELETE" });
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
  getPDFViewUrl: (billNo: string): string => ROUTES.ADMINAPIPDFVIEW(billNo),
  getPDFDownloadUrl: (billNo: string): string => ROUTES.ADMINAPIPDFDOWNLOAD(billNo),

  // WhatsApp
  sendWhatsApp: async (billNo: string): Promise<{ status: string; url: string }> => {
    const res = await fetchWithAuth(ROUTES.ADMINAPIWHATSAPPSENDSINGLE(billNo));
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
    const res = await fetchWithAuth(`${ROUTES.ADMINAPIOCCUPANTSLIST}?tenantId=${tenantId}`);
    if (!res.ok) throw new Error("Failed to fetch occupants");
    const data = await res.json();
    return data.occupants || [];
  },

  saveOccupant: async (tenantId: string | number, data: FormData): Promise<{ status: string }> => {
    const res = await fetch(`${ROUTES.ADMINAPIOCCUPANTSLIST}?tenantId=${tenantId}`, {
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
      ROUTES.ADMINAPIOCCUPANTSDELETE(Number(tenantId), occupantUuid),
      { method: "DELETE" }
    );
    if (!res.ok) throw new Error("Failed to delete occupant");
    return res.json();
  },

  // downloadTemplate: (): string => ROUTES.ADMINAPISYNCTEMPLATE,
};
