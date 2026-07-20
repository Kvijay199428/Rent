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
    get HEALTHCHECK() { return fullPath(manifest.health.check); },

    // Admin Pages
    get ADMINPAGEROOT() { return page("admin", "root"); },
    get ADMINPAGEHOME() { return page("admin", "home"); },
    get ADMINPAGELOGIN() { return page("admin", "login"); },
    get ADMINPAGELOGOUT() { return page("admin", "logout"); },
    get ADMINPAGEDASHBOARD() { return page("admin", "dashboard"); },
    get ADMINPAGEBILLING() { return page("admin", "billing"); },
    get ADMINPAGEHISTORY() { return page("admin", "history"); },
    get ADMINPAGETENANTS() { return page("admin", "tenants"); },
    get ADMINPAGESETTINGS() { return page("admin", "settings"); },
    get ADMINPAGEARCHIVE() { return page("admin", "archive"); },
    get ADMINPAGEBACKUPS() { return page("admin", "backups"); },
    // ADMINPAGETENANTPROFILE(tenantId: number) { return page("admin", "TENANTPROFILE", { tenantId }); },
    ADMINPAGETENANTPROFILE(tenantId: number) { return page("admin", "TENANTPROFILE", { tenantId }); },

    // Admin API: Setup
    get ADMINAPISETUPREQUIRED() { return api("admin", "setup", "required"); },
    get ADMINAPISETUPCREATE() { return api("admin", "setup", "create"); },

    // Admin API: Auth
    get ADMINAPIAUTHPUBLICKEY() { return api("admin", "auth", "publicKey"); },
    get ADMINAPIAUTHLOGIN() { return api("admin", "auth", "login"); },
    get ADMINAPIAUTHLOGINTOTP() { return api("admin", "auth", "loginTotp"); },
    get ADMINAPIAUTHREFRESH() { return api("admin", "auth", "refresh"); },
    get ADMINAPIAUTHLOGOUT() { return api("admin", "auth", "logout"); },
    get ADMINAPIAUTHME() { return api("admin", "auth", "me"); },

    // Admin API: TOTP
    get ADMINAPITOTPQR() { return api("admin", "totp", "qr"); },
    get ADMINAPITOTPREGENERATE() { return api("admin", "totp", "regenerate"); },

    // Admin API: Password
    get ADMINAPIPASSWORDFORGOTVERIFY() { return api("admin", "password", "forgotVerify"); },
    get ADMINAPIPASSWORDFORGOTRESET() { return api("admin", "password", "forgotReset"); },

    // Admin API: Dashboard
    get ADMINAPIDASHBOARDSTATS() { return api("admin", "dashboard", "stats"); },

    // Admin API: Config
    get ADMINAPICONFIGGET() { return api("admin", "config", "get"); },
    get ADMINAPICONFIGUPDATE() { return api("admin", "config", "update"); },
    get ADMINAPICONFIGTHEME() { return api("admin", "config", "theme"); },

    // Admin API: Billing
    get ADMINAPIBILLINGFILTER() { return api("admin", "billing", "filter"); },
    get ADMINAPIBILLINGMONTHS() { return api("admin", "billing", "months"); },
    get ADMINAPIBILLINGPREVIEW() { return api("admin", "billing", "preview"); },
    ADMINAPIBILLINGCREATE(tenantId: number) { return api("admin", "billing", "create", { tenantId }); },
    ADMINAPIBILLINGGET(tenantId: number, billNo: string) { return api("admin", "billing", "get", { tenantId, billNo }); },
    ADMINAPIBILLINGUPDATE(tenantId: number, billNo: string) { return api("admin", "billing", "update", { tenantId, billNo }); },
    ADMINAPIBILLINGUPDATEPAYMENT(tenantId: number, billNo: string) { return api("admin", "billing", "updatePayment", { tenantId, billNo }); },
    ADMINAPIBILLINGARCHIVE(tenantId: number, billNo: string) { return api("admin", "billing", "archive", { tenantId, billNo }); },
    ADMINAPIBILLINGRESTORE(tenantId: number, billNo: string) { return api("admin", "billing", "restore", { tenantId, billNo }); },
    ADMINAPIBILLINGDELETE(tenantId: number, billNo: string) { return api("admin", "billing", "delete", { tenantId, billNo }); },
    get ADMINAPIBILLINGARCHIVEDATA() { return api("admin", "billing", "archiveData"); },

    // Admin API: Tenants
    get ADMINAPITENANTSLIST() { return api("admin", "tenants", "list"); },
    get ADMINAPITENANTSCREATE() { return api("admin", "tenants", "create"); },
    ADMINAPITENANTSGET(tenantId: number) { return api("admin", "tenants", "get", { tenantId }); },
    ADMINAPITENANTSUPDATE(tenantId: number) { return api("admin", "tenants", "update", { tenantId }); },
    ADMINAPITENANTSDELETE(tenantId: number) { return api("admin", "tenants", "delete", { tenantId }); },
    ADMINAPITENANTSRESTORE(tenantId: number) { return `${manifest.basePath || ""}/admin/api/tenants/${tenantId}/restore`; },
    ADMINAPITENANTSCHANGEPIN(tenantId: number) { return api("admin", "tenants", "changePin", { tenantId }); },
    ADMINAPITENANTSREVEALPIN(tenantId: number) { return api("admin", "tenants", "revealPin", { tenantId }); },
    ADMINAPITENANTSRECEIPTS(tenantId: number | string) { return api("admin", "tenants", "receipts", { tenantId }); },
    get ADMINAPITENANTRECOVERYSNAPSHOTS() { return api("admin", "tenants", "recoverySnapshots"); },
    ADMINAPITENANTSNAPSHOT_PREVIEW(snapshotId: string) { return api("admin", "tenants", "recoverySnapshotPreview", { snapshotId }); },
    ADMINAPITENANTSNAPSHOT_RESTORE(snapshotId: string) { return api("admin", "tenants", "recoverySnapshotRestore", { snapshotId }); },

    // Admin API: Occupants
    ADMINAPIOCCUPANTSLIST(tenantId: number) { return api("admin", "occupants", "list", { tenantId }); },
    ADMINAPIOCCUPANTSCREATE(tenantId: number) { return api("admin", "occupants", "create", { tenantId }); },
    ADMINAPIOCCUPANTSMARKINACTIVE(tenantId: number, occupantUuid: string) { return api("admin", "occupants", "markInactive", { tenantId, occupantUuid }); },
    ADMINAPIOCCUPANTSDELETE(tenantId: number, occupantUuid: string) { return api("admin", "occupants", "delete", { tenantId, occupantUuid }); },
    ADMINAPIOCCUPANTSGETFILE(tenantId: number, filename: string) { return api("admin", "occupants", "getFile", { tenantId, filename }); },

    // Admin API: PDF
    ADMINAPIPDFDOWNLOAD(tenantId: number, billNo: string) { return api("admin", "pdf", "download", { tenantId, billNo }); },
    ADMINAPIPDFVIEW(tenantId: number, billNo: string) { return api("admin", "pdf", "view", { tenantId, billNo }); },

    // Admin API: WhatsApp
    ADMINAPIWHATSAPPSENDSINGLE(tenantId: number, billNo: string) { return api("admin", "whatsapp", "sendSingle", { tenantId, billNo }); },

    // Admin API: Sync
    get ADMINAPISYNCEXPORTCSV() { return api("admin", "sync", "exportCsv"); },
    get ADMINAPISYNCEXPORTZIP() { return api("admin", "sync", "exportZip"); },
    get ADMINAPISYNCTEMPLATE() { return api("admin", "sync", "template"); },
    get ADMINAPISYNCIMPORTPREVIEW() { return api("admin", "sync", "importPreview"); },
    get ADMINAPISYNCIMPORTEXECUTE() { return api("admin", "sync", "importExecute"); },
    ADMINAPISYNCEXPORTEXCEL(format: string) { return api("admin", "sync", "exportExcel", { format }); },

    // Admin API: Backups
    get ADMINAPIBACKUPSLIST() { return api("admin", "backups", "list"); },
    get ADMINAPIBACKUPSCREATEMANUAL() { return api("admin", "backups", "createManual"); },
    ADMINAPIBACKUPSDELETE(backupId: string) { return api("admin", "backups", "delete", { backupId }); },
    ADMINAPIBACKUPSVERIFY(backupId: string) { return api("admin", "backups", "verify", { backupId }); },
    ADMINAPIBACKUPSRESTORE(backupId: string) { return api("admin", "backups", "restore", { backupId }); },
    ADMINAPIBACKUPSDOWNLOAD(backupId: string) { return api("admin", "backups", "download", { backupId }); },
    ADMINAPIBACKUPSMETADATA(backupId: string) { return api("admin", "backups", "metadata", { backupId }); },

    // Admin API: Settings
    get ADMINAPISETTINGSUPLOADSIGNATURE() { return api("admin", "settings", "uploadSignature"); },
    get ADMINAPISETTINGSDELETESIGNATURE() { return api("admin", "settings", "deleteSignature"); },

    // Tenant Pages
    TENANTPAGEROOT(tenantId: number | string, viewToken: string) { return page("tenant", "root", { tenantId, viewToken }); },

    // Tenant API: Auth
    get TENANTAPIAUTHPUBLICKEY() { return api("tenant", "auth", "publicKey"); },
    TENANTAPIAUTHLOGIN(viewToken: string) { return api("tenant", "auth", "login", { viewToken }); },
    get TENANTAPIAUTHREFRESH() { return api("tenant", "auth", "refresh"); },
    get TENANTAPIAUTHLOGOUT() { return api("tenant", "auth", "logout"); },
    get TENANTAPIAUTHLOGOUTALL() { return api("tenant", "auth", "logoutAll"); },

    // Tenant API: Profile
    TENANTAPIPROFILEGET(viewToken: string) { return api("tenant", "profile", "get", { viewToken }); },

    // Tenant API: KYC
    TENANTAPIKYCUPLOAD(viewToken: string) { return api("tenant", "kyc", "upload", { viewToken }); },
    TENANTAPIKYCMARKINACTIVE(viewToken: string, occupantUuid: string) { return api("tenant", "kyc", "markInactive", { viewToken, occupantUuid }); },
    TENANTAPIKYCDELETE(viewToken: string, occupantUuid: string) { return api("tenant", "kyc", "delete", { viewToken, occupantUuid }); },
    TENANTAPIKYCGETFILE(filename: string) { return api("tenant", "kyc", "getFile", { filename }); },
} as const;

export type RoutesType = typeof ROUTES;
export default ROUTES;
