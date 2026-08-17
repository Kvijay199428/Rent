/**
 * src/lib/auth.ts
 * Silent session-refresh helpers.
 *
 * The backend issues short-lived access tokens (15 min) and a longer-lived
 * refresh session (24h, or 180d with remember-me). The access token is stored
 * in an HttpOnly cookie, so the frontend cannot read its expiry — instead we
 * refresh lazily: whenever a request comes back 401, try the refresh endpoint
 * once, then retry the original request. This keeps the landlord logged in
 * until they explicitly log out or the refresh session itself expires.
 */
import { ROUTES } from "./routes";

export type RefreshResult =
  | { status: "ok" }
  | { status: "expired" } // refresh rejected — session revoked/expired
  | { status: "unreachable" }; // network/server error — keep current session

let refreshInFlight: Promise<RefreshResult> | null = null;

/**
 * POST /landlord/api/auth/refresh with credentials. Single-flight: concurrent
 * callers share one request so cookie rotation (which revokes the previous
 * refresh token) never races itself.
 */
export async function silentRefresh(): Promise<RefreshResult> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async (): Promise<RefreshResult> => {
    try {
      const res = await fetch(ROUTES.LANDLORDAPIAUTHREFRESH, {
        method: "POST",
        credentials: "include",
      });
      return res.ok ? { status: "ok" } : { status: "expired" };
    } catch {
      return { status: "unreachable" };
    }
  })();
  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}
