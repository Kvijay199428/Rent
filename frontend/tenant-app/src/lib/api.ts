import axios from "axios";
import { getTenantRuntime } from "./tenant-runtime";
import { encryptPayload } from "./encryption";

const { tenantBase } = getTenantRuntime();

const http = axios.create({
  baseURL: tenantBase,
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
      return `${tenantBase}/api/kyc/file/${encodeURIComponent(filename)}`;
    },
  },

  pdf: {
    viewUrl(billNo: string) {
      return `${tenantBase}/api/pdf/${encodeURIComponent(billNo)}/view`;
    },
    downloadUrl(billNo: string) {
      return `${tenantBase}/api/pdf/${encodeURIComponent(billNo)}/download`;
    },
  },
};
