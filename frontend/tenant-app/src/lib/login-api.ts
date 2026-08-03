import { getPublicKey, encryptPayload } from "./encryption";

// ── QR Flow: login via encrypted PIN (scoped to the QR URL) ──
export async function qrLoginByPin(
  basePath: string,
  pin: string
): Promise<{ status: string; message?: string }> {
  const pubKey = await getPublicKey(`${basePath}/api/auth/public-key`);
  const encrypted = await encryptPayload({ pin, rememberme: true }, pubKey);

  const res = await fetch(`${basePath}/api/auth/login`, {
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

// ── Portal Flow: login via username + PIN (global endpoint) ──
export async function portalLoginByUsername(
  username: string,
  pin: string,
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
}> {
  const pubKey = await getPublicKey("/rent/tenant/api/auth/public-key");
  const encrypted = await encryptPayload(
    { username, pin, rememberme: rememberMe, portal_mode: true },
    pubKey
  );

  const res = await fetch("/rent/tenant/api/auth/login-by-username", {
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

// ── Logout (works for both flows) ──
export async function logoutTenant(basePath: string): Promise<void> {
  await fetch(`${basePath}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}
