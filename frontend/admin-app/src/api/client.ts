import { getApiUrl } from "@shared/api-config";

export const API_PREFIX = "/rent/admin/api";

// Single-flight silent refresh: the backend rotates the refresh cookie on each
// successful refresh, so concurrent refreshes must share one request.
let refreshInFlight: Promise<boolean> | null = null;

function refreshAccessToken(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = fetch(getApiUrl(`${API_PREFIX}/auth/refresh`), {
    method: "POST",
    credentials: "include",
  })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
}

/** Fired when the session is definitively expired (refresh rejected). */
export const AUTH_EXPIRED_EVENT = "auth:expired";

export function onAuthExpired(handler: () => void): () => void {
  window.addEventListener(AUTH_EXPIRED_EVENT, handler);
  return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handler);
}

/**
 * Authenticated fetch with credentials + automatic silent refresh on 401.
 * Retries the original request once after a successful refresh. If the
 * refresh itself is rejected, dispatches AUTH_EXPIRED_EVENT so the app can
 * clear its auth state and route back to login.
 */
export async function fetchApi(path: string, init: RequestInit = {}): Promise<Response> {
  const url = /^https?:\/\//i.test(path)
    ? path
    : getApiUrl(`${API_PREFIX}${path.startsWith("/") ? path : `/${path}`}`);

  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
  const doFetch = (): Promise<Response> =>
    fetch(url, {
      ...init,
      credentials: "include",
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(init.headers || {}),
      },
    });

  let res = await doFetch();
  if (res.status === 401) {
    if (await refreshAccessToken()) {
      const retry = await doFetch();
      if (retry.status !== 401) return retry;
    }
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
  }
  return res;
}
