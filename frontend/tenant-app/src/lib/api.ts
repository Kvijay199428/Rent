import axios from "axios";
import { getTenantRuntime } from "./tenant-runtime";
import { encryptPayload } from "./encryption";
import { getApiBaseUrl } from "@shared/api-config";

const { tenantBase } = getTenantRuntime();

const http = axios.create({
  baseURL: getApiBaseUrl() + tenantBase,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Single-flight silent refresh: the backend rotates the refresh cookie on
// every successful refresh, so concurrent refreshes would race each other.
let refreshPromise: Promise<boolean> | null = null;

function refreshAccessToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = axios
    .post(`${getApiBaseUrl()}${tenantBase}/api/auth/refresh`, undefined, {
      withCredentials: true,
    })
    .then(() => true)
    .catch(() => false)
    .finally(() => {
      refreshPromise = null;
    });
  return refreshPromise;
}

/** Public single-flight refresh for raw fetch() calls (e.g. PDF fetches). */
export async function silentRefresh(): Promise<boolean> {
  return refreshAccessToken();
}

interface RetriableAxiosRequestConfig {
  _retry?: boolean;
}

http.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config as (RetriableAxiosRequestConfig | undefined) &
      typeof err.config;
    if (err.response?.status !== 401 || !original || original._retry) {
      return Promise.reject(err);
    }

    // Access token expired: silently refresh once, then retry the request.
    // The refresh call uses the bare axios instance so a failed refresh (e.g.
    // the session itself expired) doesn't loop back through this interceptor.
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      original._retry = true;
      return http(original);
    }

    // Session truly expired — surface the 401. The app layer routes to login.
    return Promise.reject(err);
  }
);

export const tenantApi = {
  auth: {
    async login(pin: string, rememberMe = false) {
      const { data: keyRes } = await http.get<{ publicKey: string }>(
        "api/auth/public-key"
      );
      if (!keyRes.publicKey) throw new Error("Failed to load tenant public key");

      const encrypted = await encryptPayload(
        { pin, rememberme: rememberMe },
        keyRes.publicKey
      );
      return http.post("api/auth/login", encrypted);
    },
    refresh() {
      return http.post("api/auth/refresh");
    },
    logout() {
      return http.post("api/auth/logout");
    },
  },

  profile: {
    get() {
      return http.get("api/profile");
    },
  },

  kyc: {
    upload(formData: FormData) {
      return http.post("api/kyc", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    },
    markInactive(occupantUuid: string) {
      return http.put(`api/kyc/${occupantUuid}/inactive`);
    },
    delete(occupantUuid: string) {
      return http.delete(`api/kyc/${occupantUuid}`);
    },
    getFileUrl(filename: string) {
      return `${getApiBaseUrl()}${tenantBase}/api/kyc/file/${encodeURIComponent(filename)}`;
    },
  },

  pdf: {
    viewUrl(billNo: string) {
      return `${getApiBaseUrl()}${tenantBase}/api/pdf/${encodeURIComponent(billNo)}/view`;
    },
    downloadUrl(billNo: string) {
      return `${getApiBaseUrl()}${tenantBase}/api/pdf/${encodeURIComponent(billNo)}/download`;
    },
  },

  audit: {
    getLogs(params: { action_type?: string; search?: string; date_from?: string; date_to?: string; limit?: number; offset?: number } = {}) {
      const qs = new URLSearchParams();
      if (params.action_type) qs.set("action_type", params.action_type);
      if (params.search) qs.set("search", params.search);
      if (params.date_from) qs.set("date_from", params.date_from);
      if (params.date_to) qs.set("date_to", params.date_to);
      if (params.limit) qs.set("limit", String(params.limit));
      if (params.offset) qs.set("offset", String(params.offset));
      return http.get(`api/audit-logs?${qs}`);
    },
  },
};
