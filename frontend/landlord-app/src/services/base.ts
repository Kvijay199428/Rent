// frontend/landlord-app/src/services/base.ts
import { APP_BASE, API_BASE } from "../lib/runtime";

export { APP_BASE, API_BASE };

/** Prepend APP_BASE to any page-level path */
export function withBase(path: string): string {
  const clean = path.startsWith("/") ? path : `/${path}`;
  return `${APP_BASE}${clean}`;
}

/** Prepend API_BASE to any API path */
export function withApi(path: string): string {
  const clean = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${clean}`;
}

/** Centralised fetch through the API base */
export async function apiFetch(path: string, init?: RequestInit): Promise<unknown> {
  const res = await fetch(withApi(path), {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed with ${res.status}`);
  }

  const contentType = res.headers.get("content-type") || "";
  return contentType.includes("application/json") ? res.json() : res.text();
}
