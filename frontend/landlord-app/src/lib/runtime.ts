/**
 * src/lib/runtime.ts
 * Determines base paths dynamically at runtime based on the actual URL.
 */

function getAppBase(): string {
  const path = window.location.pathname;
  // Match /{prefix}/landlord/{uuid} when accessed through proxy (e.g. /rent/landlord/abc-123/dashboard)
  // Match /landlord/{uuid} when accessed directly (e.g. /landlord/abc-123/dashboard)
  // Falls back to /{prefix}/landlord or /landlord for login/signup (no UUID in URL)
  const match = path.match(/^(\/[^/]+)?\/landlord(\/[a-f0-9-]+)?/);
  return match ? match[0] : '/landlord';
}

export const APP_BASE = getAppBase();
export const API_BASE = APP_BASE;

export function extractLandlordUuid(): string | null {
  const path = window.location.pathname;
  const match = path.match(/\/landlord\/([a-f0-9-]{36})/);
  return match ? match[1] : null;
}

export function getFullApiUrl(path: string): string {
  // path from ROUTES already includes /landlord if it's a page, but API routes
  // from shared/routes.json might have /landlord/api/...
  // Usually, just return the path directly as long as it starts with /
  if (path.startsWith('http')) return path;
  return path;
}
