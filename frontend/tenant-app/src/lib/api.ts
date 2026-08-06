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

http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      window.location.reload();
    }
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
