// frontend/tenant-app/src/lib/tenant-runtime.ts
const APP_BASE = (import.meta.env.VITE_APP_BASE_PATH || "").replace(/\/+$/, "");

export type TenantRuntime = {
  appBase: string;
  landlordUuid: string | null;
  propertyId: string | null;
  tenantId: string | null;
  viewToken: string | null;
  tenantBase: string;
};

export function getTenantRuntime(pathname = window.location.pathname): TenantRuntime {
  const cleanPath = pathname.replace(/\/+$/, "");
  const appBase = APP_BASE === "/" ? "" : APP_BASE;

  const escapedBase = appBase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // Canonical tenant portal URL: /tenant/{landlordUuid}/QR/{propertyId}/{tenantId}/{viewToken}
  // (the /QR/ marker keeps it distinct from /tenant/login).
  const re = new RegExp(`^${escapedBase}/tenant/([^/]+)/QR/([^/]+)/([^/]+)/([^/]+)`);
  const match = cleanPath.match(re);

  const landlordUuid = match?.[1] ?? null;
  const propertyId = match?.[2] ?? null;
  const tenantId = match?.[3] ?? null;
  const viewToken = match?.[4] ?? null;
  // The tenant API base stays /{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}/api/...
  // (cookie scope + backend auth), decoupled from the portal path above.
  const tenantBase =
    landlordUuid && propertyId && tenantId && viewToken
      ? `${appBase}/${landlordUuid}/t/${propertyId}/${tenantId}/${viewToken}`
      : `${appBase}/t`;

  return {
    appBase: appBase || "/",
    landlordUuid,
    propertyId,
    tenantId,
    viewToken,
    tenantBase,
  };
}
