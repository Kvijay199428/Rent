/**
 * src/lib/routes.ts — Tenant App
 * Shared routes manifest from routes.json (via @shared alias).
 */

import routesJson from "@shared/routes.json";

interface RouteManifest {
    basePath: string;
    health: { check: string };
    admin: { pages: Record<string, string>; api: Record<string, any> };
    tenant: {
        pages: Record<string, string>;
        api: {
            auth: Record<string, string>;
            profile: Record<string, string>;
            kyc: Record<string, string>;
            pdf: Record<string, string>;  // ← ADDED
        };
    };
}

const manifest = routesJson as unknown as RouteManifest;

function resolvePath(template: string, params?: Record<string, string | number>): string {
    if (!params) return template;
    return Object.entries(params).reduce(
        (path, [key, value]) => path.replace(`{${key}}`, String(value)),
        template
    );
}

function fullPath(template: string, params?: Record<string, string | number>): string {
    return `${manifest.basePath || ""}${resolvePath(template, params)}`;
}

function tenantApi(section: string, key: string, params?: Record<string, string | number>): string {
    const template = manifest.tenant?.api?.[section as keyof typeof manifest.tenant.api]?.[key];
    if (typeof template !== "string") throw new Error(`Tenant API route ${section}.${key} not found`);
    return fullPath(template, params);
}

function tenantPage(key: string, params?: Record<string, string | number>): string {
    const template = manifest.tenant?.pages?.[key];
    if (typeof template !== "string") throw new Error(`Tenant page route ${key} not found`);
    return fullPath(template, params);
}

export const TENANT_ROUTES = {
    get basePath() { return manifest.basePath; },
    get HEALTH_CHECK() { return fullPath(manifest.health.check); },

    // Tenant Pages
    get TENANT_PAGE_ROOT() { return tenantPage("root"); },
    tenantPageProfile(view_token: string) { return tenantPage("profile", { view_token }); },

    // Tenant API: Auth
    get TENANT_API_AUTH_PUBLIC_KEY() { return tenantApi("auth", "publicKey"); },
    tenantApiAuthLogin(view_token: string) { return tenantApi("auth", "login", { view_token }); },
    tenantApiAuthRefresh(view_token: string) { return tenantApi("auth", "refresh", { view_token }); },
    tenantApiAuthLogout(view_token: string) { return tenantApi("auth", "logout", { view_token }); },
    tenantApiAuthLogoutAll(view_token: string) { return tenantApi("auth", "logoutAll", { view_token }); },

    // Tenant API: Profile
    tenantApiProfileGet(view_token: string) { return tenantApi("profile", "get", { view_token }); },

    // Tenant API: PDF — FIXED: proper view/download methods
    tenantApiPdfView(view_token: string, billno: string) {
        return tenantApi("pdf", "view", { view_token, billno });
    },
    tenantApiPdfDownload(view_token: string, billno: string) {
        return tenantApi("pdf", "download", { view_token, billno });
    },

    // Tenant API: KYC
    tenantApiKycUpload(view_token: string) { return tenantApi("kyc", "upload", { view_token }); },
    tenantApiKycMarkInactive(view_token: string, occupantUuid: string) {
        return tenantApi("kyc", "markInactive", { view_token, occupantUuid });
    },
    tenantApiKycDelete(view_token: string, occupantUuid: string) {
        return tenantApi("kyc", "delete", { view_token, occupantUuid });
    },
    tenantApiKycGetFile(filename: string) { return tenantApi("kyc", "getFile", { filename }); },
} as const;

export type RoutesType = typeof TENANT_ROUTES;
export default TENANT_ROUTES;