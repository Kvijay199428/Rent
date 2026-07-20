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

export const APP_BASE_PATH = import.meta.env.VITE_APP_BASE_PATH?.replace(/\/$/, "") || "/rent";

function resolvePath(template: string, params?: Record<string, string | number>): string {
    if (!params) return template;
    return Object.entries(params).reduce(
        (path, [key, value]) => path.replace(`{${key}}`, String(value)),
        template
    );
}

function fullPath(template: string, params?: Record<string, string | number>): string {
    return `${APP_BASE_PATH}${resolvePath(template, params)}`;
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

export const TENANTROUTES = {
    get basePath() { return APP_BASE_PATH; },
    get HEALTHCHECK() { return fullPath(manifest.health.check); },

    // Tenant Pages
    TENANTPAGEROOT(tenantId: string | number, viewToken: string) { return tenantPage("root", { tenantId, viewToken }); },
    tenantPageProfile(tenantId: string | number, viewToken: string) { return tenantPage("profile", { tenantId, viewToken }); },

    // Tenant API: Auth
    get TENANTAPIAUTHPUBLICKEY() { return tenantApi("auth", "publicKey"); },
    TENANTAPIAUTHLOGIN(tenantId: string | number, viewToken: string) { return tenantApi("auth", "login", { tenantId, viewToken }); },
    TENANTAPIAUTHREFRESH(tenantId: string | number, viewToken: string) { return tenantApi("auth", "refresh", { tenantId, viewToken }); },
    TENANTAPIAUTHLOGOUT(tenantId: string | number, viewToken: string) { return tenantApi("auth", "logout", { tenantId, viewToken }); },
    TENANTAPIAUTHLOGOUTALL(tenantId: string | number, viewToken: string) { return tenantApi("auth", "logoutAll", { tenantId, viewToken }); },

    // Tenant API: Profile
    TENANTAPIPROFILEGET(tenantId: string | number, viewToken: string) { return tenantApi("profile", "get", { tenantId, viewToken }); },

    // Tenant API: PDF — FIXED: proper view/download methods
    TENANTAPIPDFVIEW(tenantId: number | string, viewToken: string, billNo: string) {
        return tenantApi("pdf", "view", { tenantId, viewToken, billNo });
    },
    TENANTAPIPDFDOWNLOAD(tenantId: number | string, viewToken: string, billNo: string) {
        return tenantApi("pdf", "download", { tenantId, viewToken, billNo });
    },

    // Tenant API: KYC
    TENANTAPIKYCUPLOAD(tenantId: string | number, viewToken: string) { return tenantApi("kyc", "upload", { tenantId, viewToken }); },
    TENANTAPIKYCMARKINACTIVE(tenantId: string | number, viewToken: string, occupantUuid: string) {
        return tenantApi("kyc", "markInactive", { tenantId, viewToken, occupantUuid });
    },
    TENANTAPIKYCDELETE(tenantId: string | number, viewToken: string, occupantUuid: string) {
        return tenantApi("kyc", "delete", { tenantId, viewToken, occupantUuid });
    },
    TENANTAPIKYCGETFILE(tenantId: string | number, viewToken: string, filename: string) { return tenantApi("kyc", "getFile", { tenantId, viewToken, filename }); },
} as const;

export type RoutesType = typeof TENANTROUTES;
export default TENANTROUTES;