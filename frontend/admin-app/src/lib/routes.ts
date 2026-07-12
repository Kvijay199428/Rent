/**
 * src/lib/routes.ts
 * Shared routes manifest — single source of truth for ALL routes.
 * Consumes routes.json from the shared directory.
 */

import routesJson from "@shared/routes.json";

interface RouteManifest {
    basePath: string;
    health: { check: string };
    admin: {
        pages: Record<string, string>;
        api: {
            setup: Record<string, string>;
            auth: Record<string, string>;
            totp: Record<string, string>;
            password: Record<string, string>;
            dashboard: Record<string, string>;
            config: Record<string, string>;
            billing: Record<string, string>;
            tenants: Record<string, string>;
            occupants: Record<string, string>;
            pdf: Record<string, string>;
            whatsapp: Record<string, string>;
            sync: Record<string, string>;
            backups: Record<string, string>;
            settings: Record<string, string>;
        };
    };
    tenant: {
        pages: Record<string, string>;
        api: {
            auth: Record<string, string>;
            profile: Record<string, string>;
            kyc: Record<string, string>
        };
    };
    static: {
        uploads: string;
        static: string;
        adminAssets: string;
        tenantAssets: string;
        favicon: string
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

function api(domain: "admin" | "tenant", section: string, key: string, params?: Record<string, string | number>): string {
    const node = (manifest as any)[domain];
    const sectionNode = node?.api?.[section];
    const template = sectionNode?.[key];
    if (typeof template !== "string") throw new Error(`Route ${domain}.api.${section}.${key} not found`);
    return fullPath(template, params);
}

function page(domain: "admin" | "tenant", key: string, params?: Record<string, string | number>): string {
    const template = (manifest as any)[domain]?.pages?.[key];
    if (typeof template !== "string") throw new Error(`Page route ${domain}.pages.${key} not found`);
    return fullPath(template, params);
}

export const ROUTES = {
    get basePath() { return manifest.basePath; },
    get HEALTH_CHECK() { return fullPath(manifest.health.check); },

    // Admin Pages
    get ADMIN_PAGE_ROOT() { return page("admin", "root"); },
    get ADMIN_PAGE_HOME() { return page("admin", "home"); },
    get ADMIN_PAGE_LOGIN() { return page("admin", "login"); },
    get ADMIN_PAGE_LOGOUT() { return page("admin", "logout"); },
    get ADMIN_PAGE_DASHBOARD() { return page("admin", "dashboard"); },
    get ADMIN_PAGE_BILLING() { return page("admin", "billing"); },
    get ADMIN_PAGE_HISTORY() { return page("admin", "history"); },
    get ADMIN_PAGE_TENANTS() { return page("admin", "tenants"); },
    get ADMIN_PAGE_SETTINGS() { return page("admin", "settings"); },
    get ADMIN_PAGE_ARCHIVE() { return page("admin", "archive"); },
    get ADMIN_PAGE_BACKUPS() { return page("admin", "backups"); },
    // adminPageTenantProfile(tenant_id: number) { return page("admin", "tenantProfile", { tenant_id }); },
    adminPageTenantProfile(tenant_id: number) { return page("admin", "tenantProfile", { tenant_id }); },

    // Admin API: Setup
    get ADMIN_API_SETUP_REQUIRED() { return api("admin", "setup", "required"); },
    get ADMIN_API_SETUP_CREATE() { return api("admin", "setup", "create"); },

    // Admin API: Auth
    get ADMIN_API_AUTH_PUBLIC_KEY() { return api("admin", "auth", "publicKey"); },
    get ADMIN_API_AUTH_LOGIN() { return api("admin", "auth", "login"); },
    get ADMIN_API_AUTH_LOGIN_TOTP() { return api("admin", "auth", "loginTotp"); },
    get ADMIN_API_AUTH_REFRESH() { return api("admin", "auth", "refresh"); },
    get ADMIN_API_AUTH_LOGOUT() { return api("admin", "auth", "logout"); },
    get ADMIN_API_AUTH_ME() { return api("admin", "auth", "me"); },

    // Admin API: TOTP
    get ADMIN_API_TOTP_QR() { return api("admin", "totp", "qr"); },
    get ADMIN_API_TOTP_REGENERATE() { return api("admin", "totp", "regenerate"); },

    // Admin API: Password
    get ADMIN_API_PASSWORD_FORGOT_VERIFY() { return api("admin", "password", "forgotVerify"); },
    get ADMIN_API_PASSWORD_FORGOT_RESET() { return api("admin", "password", "forgotReset"); },

    // Admin API: Dashboard
    get ADMIN_API_DASHBOARD_STATS() { return api("admin", "dashboard", "stats"); },

    // Admin API: Config
    get ADMIN_API_CONFIG_GET() { return api("admin", "config", "get"); },
    get ADMIN_API_CONFIG_UPDATE() { return api("admin", "config", "update"); },
    get ADMIN_API_CONFIG_THEME() { return api("admin", "config", "theme"); },

    // Admin API: Billing
    get ADMIN_API_BILLING_FILTER() { return api("admin", "billing", "filter"); },
    get ADMIN_API_BILLING_MONTHS() { return api("admin", "billing", "months"); },
    get ADMIN_API_BILLING_PREVIEW() { return api("admin", "billing", "preview"); },
    get ADMIN_API_BILLING_CREATE() { return api("admin", "billing", "create"); },
    adminApiBillingGet(billno: string) { return api("admin", "billing", "get", { billno }); },
    adminApiBillingUpdate(billno: string) { return api("admin", "billing", "update", { billno }); },
    adminApiBillingUpdatePayment(billno: string) { return api("admin", "billing", "updatePayment", { billno }); },
    adminApiBillingArchive(billno: string) { return api("admin", "billing", "archive", { billno }); },
    adminApiBillingRestore(billno: string) { return api("admin", "billing", "restore", { billno }); },
    adminApiBillingDelete(billno: string) { return api("admin", "billing", "delete", { billno }); },

    // Admin API: Tenants
    get ADMIN_API_TENANTS_LIST() { return api("admin", "tenants", "list"); },
    get ADMIN_API_TENANTS_CREATE() { return api("admin", "tenants", "create"); },
    adminApiTenantsGet(tenant_id: number) { return api("admin", "tenants", "get", { tenant_id }); },
    adminApiTenantsUpdate(tenant_id: number) { return api("admin", "tenants", "update", { tenant_id }); },
    adminApiTenantsDelete(tenant_id: number) { return api("admin", "tenants", "delete", { tenant_id }); },
    adminApiTenantsChangePin(tenant_id: number) { return api("admin", "tenants", "changePin", { tenant_id }); },
    adminApiTenantsRevealPin(tenant_id: number) { return api("admin", "tenants", "revealPin", { tenant_id }); },
    adminApiTenantsReceipts(tenant_name: string) { return api("admin", "tenants", "receipts", { tenant_name }); },

    // Admin API: Occupants
    get ADMIN_API_OCCUPANTS_LIST() { return api("admin", "occupants", "list"); },
    get ADMIN_API_OCCUPANTS_CREATE() { return api("admin", "occupants", "create"); },
    adminApiOccupantsMarkInactive(tenant_id: number, occupant_uuid: string) { return api("admin", "occupants", "markInactive", { tenant_id, occupant_uuid }); },
    adminApiOccupantsDelete(tenant_id: number, occupant_uuid: string) { return api("admin", "occupants", "delete", { tenant_id, occupant_uuid }); },
    adminApiOccupantsGetFile(filename: string) { return api("admin", "occupants", "getFile", { filename }); },

    // Admin API: PDF
    adminApiPdfDownload(billno: string) { return api("admin", "pdf", "download", { billno }); },
    adminApiPdfView(billno: string) { return api("admin", "pdf", "view", { billno }); },

    // Admin API: WhatsApp
    adminApiWhatsappSendSingle(billno: string) { return api("admin", "whatsapp", "sendSingle", { billno }); },

    // Admin API: Sync
    get ADMIN_API_SYNC_EXPORT_CSV() { return api("admin", "sync", "exportCsv"); },
    get ADMIN_API_SYNC_EXPORT_ZIP() { return api("admin", "sync", "exportZip"); },
    get ADMIN_API_SYNC_TEMPLATE() { return api("admin", "sync", "template"); },
    get ADMIN_API_SYNC_IMPORT_PREVIEW() { return api("admin", "sync", "importPreview"); },
    get ADMIN_API_SYNC_IMPORT_EXECUTE() { return api("admin", "sync", "importExecute"); },
    adminApiSyncExportExcel(format: string) { return api("admin", "sync", "exportExcel", { format }); },

    // Admin API: Backups
    get ADMIN_API_BACKUPS_LIST() { return api("admin", "backups", "list"); },
    get ADMIN_API_BACKUPS_CREATE_MANUAL() { return api("admin", "backups", "createManual"); },
    adminApiBackupsDelete(backup_id: string) { return api("admin", "backups", "delete", { backup_id }); },
    adminApiBackupsVerify(backup_id: string) { return api("admin", "backups", "verify", { backup_id }); },
    adminApiBackupsRestore(backup_id: string) { return api("admin", "backups", "restore", { backup_id }); },
    adminApiBackupsDownload(backup_id: string) { return api("admin", "backups", "download", { backup_id }); },
    adminApiBackupsMetadata(backup_id: string) { return api("admin", "backups", "metadata", { backup_id }); },

    // Admin API: Settings
    get ADMIN_API_SETTINGS_UPLOAD_SIGNATURE() { return api("admin", "settings", "uploadSignature"); },
    get ADMIN_API_SETTINGS_DELETE_SIGNATURE() { return api("admin", "settings", "deleteSignature"); },

    // Tenant Pages
    tenantPageRoot(view_token: string) { return page("tenant", "root", { view_token }); },

    // Tenant API: Auth
    get TENANT_API_AUTH_PUBLIC_KEY() { return api("tenant", "auth", "publicKey"); },
    tenantApiAuthLogin(view_token: string) { return api("tenant", "auth", "login", { view_token }); },
    get TENANT_API_AUTH_REFRESH() { return api("tenant", "auth", "refresh"); },
    get TENANT_API_AUTH_LOGOUT() { return api("tenant", "auth", "logout"); },
    get TENANT_API_AUTH_LOGOUT_ALL() { return api("tenant", "auth", "logoutAll"); },

    // Tenant API: Profile
    tenantApiProfileGet(view_token: string) { return api("tenant", "profile", "get", { view_token }); },

    // Tenant API: KYC
    tenantApiKycUpload(view_token: string) { return api("tenant", "kyc", "upload", { view_token }); },
    tenantApiKycMarkInactive(view_token: string, occupant_uuid: string) { return api("tenant", "kyc", "markInactive", { view_token, occupant_uuid }); },
    tenantApiKycDelete(view_token: string, occupant_uuid: string) { return api("tenant", "kyc", "delete", { view_token, occupant_uuid }); },
    tenantApiKycGetFile(filename: string) { return api("tenant", "kyc", "getFile", { filename }); },
} as const;

export type RoutesType = typeof ROUTES;
export default ROUTES;
