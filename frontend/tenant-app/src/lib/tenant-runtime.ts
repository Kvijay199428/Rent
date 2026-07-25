// frontend/tenant-app/src/lib/tenant-runtime.ts
const APP_BASE = (import.meta.env.VITE_APP_BASE_PATH || "/rent").replace(/\/+$/, "");

export type TenantRuntime = {
  appBase: string;
  landlordUuid: string | null;
  tenantId: string | null;
  viewToken: string | null;
  tenantBase: string;
};

export function getTenantRuntime(pathname = window.location.pathname): TenantRuntime {
  const cleanPath = pathname.replace(/\/+$/, "");
  const appBase = APP_BASE === "/" ? "" : APP_BASE;

  const escapedBase = appBase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(`^${escapedBase}/([^/]+)/t/([^/]+)/([^/]+)`);
  const match = cleanPath.match(re);

  const landlordUuid = match?.[1] ?? null;
  const tenantId = match?.[2] ?? null;
  const viewToken = match?.[3] ?? null;
  const tenantBase =
    landlordUuid && tenantId && viewToken ? `${appBase}/${landlordUuid}/t/${tenantId}/${viewToken}` : `${appBase}/t`;

  return {
    appBase: appBase || "/",
    landlordUuid,
    tenantId,
    viewToken,
    tenantBase,
  };
}
