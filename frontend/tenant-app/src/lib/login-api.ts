import { getPublicKey, encryptPayload } from "./encryption";
import { getApiBaseUrl } from "@shared/api-config";

// ── QR Flow: login via encrypted PIN (scoped to the QR URL) ──
export async function qrLoginByPin(
  basePath: string,
  pin: string
): Promise<{ status: string; message?: string }> {
  const apiBase = getApiBaseUrl();
  const pubKey = await getPublicKey(`${apiBase}${basePath}/api/auth/public-key`);

  // Bind the login to the printed QR via its qr_key query param.
  const params = new URLSearchParams(window.location.search);
  const qrKey = params.get("qr_key") || "";

  const encrypted = await encryptPayload(
    { pin, rememberme: true, qr_key: qrKey },
    pubKey
  );

  const res = await fetch(`${apiBase}${basePath}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      key: encrypted.key,
      data: encrypted.data,
      nonce: encrypted.nonce,
    }),
  });

  const data = await res.json();
  if (!res.ok || data.status !== "success") {
    throw new Error(data.detail || data.message || "Invalid PIN");
  }
  return data;
}

// ── Portal Flow: login via tenant_username + password (global endpoint) ──
export async function portalLogin(
  username: string,
  password: string,
  rememberMe: boolean = false
): Promise<{
  status: string;
  tenant?: {
    id: number;
    name: string;
    landlord_uuid: string;
    view_token: string;
  };
  redirect_url: string | null;
  reset_required?: boolean;
}> {
  const pubKey = await getPublicKey(`${getApiBaseUrl()}/rent/tenant/api/auth/public-key`);
  const encrypted = await encryptPayload(
    { username, password, rememberme: rememberMe },
    pubKey
  );

  const res = await fetch(`${getApiBaseUrl()}/rent/tenant/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      key: encrypted.key,
      data: encrypted.data,
      nonce: encrypted.nonce,
    }),
  });

  const data = await res.json();
  if (!res.ok || data.status !== "success") {
    throw new Error(data.detail || data.message || "Login failed");
  }
  return data;
}

// ── Portal Flow: forgot password (delivery handled by the landlord in v1) ──
export async function forgotTenantPassword(
  username: string
): Promise<{ status: string; message: string }> {
  const pubKey = await getPublicKey(`${getApiBaseUrl()}/rent/tenant/api/auth/public-key`);
  const encrypted = await encryptPayload({ username }, pubKey);

  const res = await fetch(`${getApiBaseUrl()}/rent/tenant/api/auth/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      key: encrypted.key,
      data: encrypted.data,
      nonce: encrypted.nonce,
    }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || "Request failed");
  }
  return data;
}

// ── Portal Flow: set a new password (forced change after temp password) ──
export async function changeTenantPassword(
  username: string,
  currentPassword: string,
  newPassword: string
): Promise<{ status: string; message: string }> {
  const pubKey = await getPublicKey(`${getApiBaseUrl()}/rent/tenant/api/auth/public-key`);
  const encrypted = await encryptPayload(
    { username, current_password: currentPassword, new_password: newPassword },
    pubKey
  );

  const res = await fetch(`${getApiBaseUrl()}/rent/tenant/api/auth/change-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      key: encrypted.key,
      data: encrypted.data,
      nonce: encrypted.nonce,
    }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || "Password change failed");
  }
  return data;
}

// ── Logout (works for both flows) ──
export async function logoutTenant(basePath: string): Promise<void> {
  await fetch(`${getApiBaseUrl()}${basePath}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}
