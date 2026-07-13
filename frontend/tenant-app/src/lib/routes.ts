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

export const TENANTROUTES = {
    get basePath() { return manifest.basePath; },
    get HEALTHCHECK() { return fullPath(manifest.health.check); },

    // Tenant Pages
    get TENANTPAGEROOT() { return tenantPage("root"); },
    tenantPageProfile(viewToken: string) { return tenantPage("profile", { viewToken }); },

    // Tenant API: Auth
    get TENANTAPIAUTHPUBLICKEY() { return tenantApi("auth", "publicKey"); },
    TENANTAPIAUTHLOGIN(viewToken: string) { return tenantApi("auth", "login", { viewToken }); },
    TENANTAPIAUTHREFRESH(viewToken: string) { return tenantApi("auth", "refresh", { viewToken }); },
    TENANTAPIAUTHLOGOUT(viewToken: string) { return tenantApi("auth", "logout", { viewToken }); },
    TENANTAPIAUTHLOGOUTALL(viewToken: string) { return tenantApi("auth", "logoutAll", { viewToken }); },

    // Tenant API: Profile
    TENANTAPIPROFILEGET(viewToken: string) { return tenantApi("profile", "get", { viewToken }); },

    // Tenant API: PDF — FIXED: proper view/download methods
    TENANTAPIPDFVIEW(viewToken: string, billNo: string) {
        return tenantApi("pdf", "view", { viewToken, billNo });
    },
    TENANTAPIPDFDOWNLOAD(viewToken: string, billNo: string) {
        return tenantApi("pdf", "download", { viewToken, billNo });
    },

    // Tenant API: KYC
    TENANTAPIKYCUPLOAD(viewToken: string) { return tenantApi("kyc", "upload", { viewToken }); },
    TENANTAPIKYCMARKINACTIVE(viewToken: string, occupantUuid: string) {
        return tenantApi("kyc", "markInactive", { viewToken, occupantUuid });
    },
    TENANTAPIKYCDELETE(viewToken: string, occupantUuid: string) {
        return tenantApi("kyc", "delete", { viewToken, occupantUuid });
    },
    TENANTAPIKYCGETFILE(filename: string) { return tenantApi("kyc", "getFile", { filename }); },
} as const;

export type RoutesType = typeof TENANTROUTES;
export default TENANTROUTES;