import { useState, useCallback } from "react";
import { encryptPayload } from "../lib/encryption";
import { ROUTES } from "../lib/routes";
import { API_BASE } from "../lib/runtime";

export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  status: "idle" | "loading" | "success" | "error";
}

function buildUrl(endpoint: string): string {
  if (/^https?:\/\//i.test(endpoint)) return endpoint;
  if (endpoint.startsWith("/")) return endpoint;
  return `${API_BASE}/${endpoint.replace(/^\/+/, "")}`;
}

async function readJsonSafe(res: Response) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

async function getErrorMessage(res: Response): Promise<string> {
  const data = await readJsonSafe(res);
  return data?.detail || data?.message || `HTTP ${res.status}`;
}

export function useApi() {
  const [response, setResponse] = useState<ApiResponse>({ status: "idle" });

  const request = useCallback(async <T = any>(endpoint: string, options: RequestInit = {}) => {
    setResponse({ status: "loading" });

    try {
      const res = await fetch(buildUrl(endpoint), {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
        credentials: "include",
      });

      const data = await readJsonSafe(res);

      if (!res.ok) {
        const errorMsg = data?.detail || data?.message || `HTTP ${res.status}`;
        setResponse({ status: "error", error: errorMsg });
        throw new Error(errorMsg);
      }

      setResponse({ status: "success", data });
      return data as T;
    } catch (err: any) {
      const errorMsg = err?.message || "Network error";
      setResponse({ status: "error", error: errorMsg });
      return null;
    }
  }, []);

  return { request, response };
}

export async function apiGet(endpoint: string) {
  const res = await fetch(buildUrl(endpoint), {
    credentials: "include",
  });

  if (!res.ok) {
    throw new Error(await getErrorMessage(res));
  }

  return readJsonSafe(res);
}

export async function apiPost(endpoint: string, body: any) {
  let finalBody = body;

  if (
    body?.password ||
    body?.totptoken ||
    body?.newpassword ||
    body?.confirmpassword ||
    body?.new_password ||
    body?.confirm_password ||
    body?.totp_token ||
    body?.currentPassword ||
    body?.newPassword ||
    body?.confirmPassword
  ) {
    const pubKeyRes = await fetch(ROUTES.LANDLORDAPIAUTHPUBLICKEY, {
      credentials: "include",
    });

    if (pubKeyRes.ok) {
      const publicKeyData = await readJsonSafe(pubKeyRes);
      if (publicKeyData?.publicKey) {
        const encrypted = await encryptPayload(body, publicKeyData.publicKey);
        finalBody = {
          ...encrypted,
          remember_me: body?.remember_me ?? body?.rememberMe ?? false,
        };
      }
    }
  }

  const res = await fetch(buildUrl(endpoint), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(finalBody),
    credentials: "include",
  });

  if (!res.ok) {
    throw new Error(await getErrorMessage(res));
  }

  return readJsonSafe(res);
}
