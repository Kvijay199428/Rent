/**
 * Shared API configuration for all Rent frontend apps.
 *
 * Production (Cloudflare Pages): VITE_API_BASE_URL is set at build time.
 * Docker testing: falls back to same-origin (empty string).
 */
export function getApiBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl) return envUrl.replace(/\/+$/, "");
  return "";
}

/**
 * The public frontend origin. All share links / QR codes / deep links that
 * reach users must point here (rent.vijaykrsha.online) — the API host is
 * API-only and never serves frontend pages.
 *
 * Production default:  "https://rent.vijaykrsha.online"
 * Override for testing: VITE_APP_URL
 */
export function getPublicAppUrl(): string {
  const envUrl = import.meta.env.VITE_APP_URL;
  if (envUrl !== undefined && envUrl !== "") return envUrl.replace(/\/+$/, "");
  return "https://rent.vijaykrsha.online";
}

/**
 * Prefix a relative API path with the configured API origin.
 *
 * In production:  getApiUrl("/rent/landlord/api/auth/login")
 *               → "https://api.vijaykrsha.online/rent/landlord/api/auth/login"
 *
 * In Docker:     getApiUrl("/rent/landlord/api/auth/login")
 *               → "/rent/landlord/api/auth/login"
 */
export function getApiUrl(path: string): string {
  const base = getApiBaseUrl();
  return base ? base + path : path;
}
