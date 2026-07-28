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
