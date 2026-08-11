/**
 * src/lib/routes.ts
 * Shared routes manifest — single source of truth for ALL routes.
 * Consumes routes.json from the shared directory.
 */

import routesJson from "@shared/routes.json";
import { getApiUrl } from "@shared/api-config";
import { APP_BASE } from "./runtime";

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
    landlord: {
        pages: Record<string, string>;
        api: {
            auth: Record<string, string>;
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
            totp: Record<string, string>;
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

function clean(part: string): string {
    return part.replace(/^\/+/, "").replace(/\/+$/, "");
}

function build(base: string, ...parts: string[]): string {
    const suffix = parts.filter(Boolean).map(clean).join("/");
    const normalizedBase = (base || "").replace(/\/+$/, "");
    if (!suffix) return normalizedBase || "/";
    if (!normalizedBase) return `/${suffix}`;
    return `${normalizedBase}/${suffix}`;
}

function api(domain: "admin" | "tenant" | "landlord", section: string, key: string, params?: Record<string, string | number>): string {
    const node = (manifest as any)[domain];
    const sectionNode = node?.api?.[section];
    const template = sectionNode?.[key];
    if (typeof template !== "string") throw new Error(`Route ${domain}.api.${section}.${key} not found`);
    
    const path = fullPath(template, params);
    // In production, prefix with API origin (https://api.vijaykrsha.online)
    // In Docker testing, return relative path (same-origin)
    return getApiUrl(path);
}

function page(domain: "admin" | "tenant" | "landlord", key: string, params?: Record<string, string | number>): string {
    const template = (manifest as any)[domain]?.pages?.[key];
    if (typeof template !== "string") throw new Error(`Page route ${domain}.pages.${key} not found`);
    
    // just return the full path since it's absolute
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
    ADMINAPITENANTSRESTORE(tenantId: number) { return api("admin", "tenants", "restore", { tenantId }); },
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

    // Landlord Pages
    get LANDLORDPAGEROOT() { return page("landlord", "root"); },
    get LANDLORDPAGELOGIN() { return page("landlord", "login"); },
    get LANDLORDPAGESIGNUP() { return page("landlord", "signup"); },
    get LANDLORDPAGEDASHBOARD() { return page("landlord", "dashboard"); },
    get LANDLORDPAGELOGOUT() { return page("landlord", "logout"); },
    get LANDLORDPAGEPRIVACYPOLICY() { return page("landlord", "privacyPolicy"); },
    get LANDLORDPAGESETUP() { return page("landlord", "setup"); },

    // Landlord API: Setup wizard
    get LANDLORDAPISETUPREQUIRED() { return api("landlord", "setup", "required"); },
    get LANDLORDAPISETUPCREATE() { return api("landlord", "setup", "create"); },
    get LANDLORDAPISETUPSKIP() { return api("landlord", "setup", "skip"); },

    // Landlord API: Properties
    LANDLORDAPIPROPERTIESLIST(landlordUuid: string) { return api("landlord", "properties", "list", { landlordUuid }); },
    LANDLORDAPIPROPERTIESCREATE(landlordUuid: string) { return api("landlord", "properties", "create", { landlordUuid }); },
    LANDLORDAPIPROPERTIESGET(landlordUuid: string, propertyId: number) { return api("landlord", "properties", "get", { landlordUuid, propertyId }); },
    LANDLORDAPIPROPERTIESUPDATE(landlordUuid: string, propertyId: number) { return api("landlord", "properties", "update", { landlordUuid, propertyId }); },
    LANDLORDAPIPROPERTIESDELETE(landlordUuid: string, propertyId: number) { return api("landlord", "properties", "delete", { landlordUuid, propertyId }); },
    LANDLORDAPIPROPERTIESTENANTS(landlordUuid: string, propertyId: number) { return api("landlord", "properties", "tenants", { landlordUuid, propertyId }); },

    // Landlord API: Auth
    get LANDLORDAPIAUTHPUBLICKEY() { return api("landlord", "auth", "publicKey"); },
    get LANDLORDAPIAUTHGOOGLE() { return api("landlord", "auth", "google"); },
    get LANDLORDAPIAUTHCHECKUSERNAME() { return api("landlord", "auth", "checkUsername"); },
    get LANDLORDAPIAUTHCHECKEMAIL() { return api("landlord", "auth", "checkEmail"); },
    get LANDLORDAPIAUTHSIGNUP() { return api("landlord", "auth", "signup"); },
    get LANDLORDAPIAUTHLOGIN() { return api("landlord", "auth", "login"); },
    get LANDLORDAPIAUTHLOGINTOTP() { return api("landlord", "auth", "loginTotp"); },
    get LANDLORDAPIAUTHREFRESH() { return api("landlord", "auth", "refresh"); },
    get LANDLORDAPIAUTHLOGOUT() { return api("landlord", "auth", "logout"); },
    get LANDLORDAPIAUTHME() { return api("landlord", "auth", "me"); },
    get LANDLORDAPIAUTHCHANGEPASSWORD() { return api("landlord", "auth", "changePassword"); },
    get LANDLORDAPIPRIVACYPOLICY() { return api("landlord", "auth", "privacyPolicy"); },
    get LANDLORDAPIAUTHPRIVACYCONSENT() { return api("landlord", "auth", "privacyConsent"); },

    // Landlord API: Dashboard
    LANDLORDAPIDASHBOARDSTATS(landlordUuid: string) { return api("landlord", "dashboard", "stats", { landlordUuid }); },

    // Landlord API: Config
    LANDLORDAPICONFIGGET(landlordUuid: string) { return api("landlord", "config", "get", { landlordUuid }); },
    LANDLORDAPICONFIGUPDATE(landlordUuid: string) { return api("landlord", "config", "update", { landlordUuid }); },
    LANDLORDAPICONFIGTHEMEGET(landlordUuid: string) { return api("landlord", "config", "themeGet", { landlordUuid }); },
    LANDLORDAPICONFIGTHEME(landlordUuid: string) { return api("landlord", "config", "theme", { landlordUuid }); },

    // Landlord API: Billing
    LANDLORDAPIBILLINGFILTER(landlordUuid: string) { return api("landlord", "billing", "filter", { landlordUuid }); },
    LANDLORDAPIBILLINGMONTHS(landlordUuid: string) { return api("landlord", "billing", "months", { landlordUuid }); },
    LANDLORDAPIBILLINGPREVIEW(landlordUuid: string) { return api("landlord", "billing", "preview", { landlordUuid }); },
    LANDLORDAPIBILLINGCREATE(landlordUuid: string, tenantId: number) { return api("landlord", "billing", "create", { landlordUuid, tenantId }); },
    LANDLORDAPIBILLINGGET(landlordUuid: string, tenantId: number, billNo: string) { return api("landlord", "billing", "get", { landlordUuid, tenantId, billNo }); },
    LANDLORDAPIBILLINGUPDATE(landlordUuid: string, tenantId: number, billNo: string) { return api("landlord", "billing", "update", { landlordUuid, tenantId, billNo }); },
    LANDLORDAPIBILLINGUPDATEPAYMENT(landlordUuid: string, tenantId: number, billNo: string) { return api("landlord", "billing", "updatePayment", { landlordUuid, tenantId, billNo }); },
    LANDLORDAPIBILLINGARCHIVE(landlordUuid: string, tenantId: number, billNo: string) { return api("landlord", "billing", "archive", { landlordUuid, tenantId, billNo }); },
    LANDLORDAPIBILLINGRESTORE(landlordUuid: string, tenantId: number, billNo: string) { return api("landlord", "billing", "restore", { landlordUuid, tenantId, billNo }); },
    LANDLORDAPIBILLINGDELETE(landlordUuid: string, tenantId: number, billNo: string) { return api("landlord", "billing", "delete", { landlordUuid, tenantId, billNo }); },
    LANDLORDAPIBILLINGARCHIVEDATA(landlordUuid: string) { return api("landlord", "billing", "archiveData", { landlordUuid }); },

    // Landlord API: Tenants
    LANDLORDAPITENANTSLIST(landlordUuid: string) { return api("landlord", "tenants", "list", { landlordUuid }); },
    LANDLORDAPITENANTSCREATE(landlordUuid: string) { return api("landlord", "tenants", "create", { landlordUuid }); },
    LANDLORDAPITENANTSGET(landlordUuid: string, tenantId: number) { return api("landlord", "tenants", "get", { landlordUuid, tenantId }); },
    LANDLORDAPITENANTSUPDATE(landlordUuid: string, tenantId: number) { return api("landlord", "tenants", "update", { landlordUuid, tenantId }); },
    LANDLORDAPITENANTSDELETE(landlordUuid: string, tenantId: number) { return api("landlord", "tenants", "delete", { landlordUuid, tenantId }); },
    LANDLORDAPITENANTSRESTORE(landlordUuid: string, tenantId: number) { return api("landlord", "tenants", "restore", { landlordUuid, tenantId }); },
    LANDLORDAPITENANTSCHANGEPIN(landlordUuid: string, tenantId: number) { return api("landlord", "tenants", "changePin", { landlordUuid, tenantId }); },
    LANDLORDAPITENANTSREVEALPIN(landlordUuid: string, tenantId: number) { return api("landlord", "tenants", "revealPin", { landlordUuid, tenantId }); },
    LANDLORDAPITENANTSPORTALAUTH(landlordUuid: string, tenantId: number) { return api("landlord", "tenants", "portalAuth", { landlordUuid, tenantId }); },
    LANDLORDAPITENANTSQRKEY(landlordUuid: string, tenantId: number) { return api("landlord", "tenants", "qrKey", { landlordUuid, tenantId }); },
    LANDLORDAPITENANTSRECEIPTS(landlordUuid: string, tenantId: number | string) { return api("landlord", "tenants", "receipts", { landlordUuid, tenantId }); },
    LANDLORDAPITENANTRECOVERYSNAPSHOTS(landlordUuid: string) { return api("landlord", "tenants", "recoverySnapshots", { landlordUuid }); },
    LANDLORDAPITENANTSNAPSHOT_PREVIEW(landlordUuid: string, snapshotId: string) { return api("landlord", "tenants", "recoverySnapshotPreview", { landlordUuid, snapshotId }); },
    LANDLORDAPITENANTSNAPSHOT_RESTORE(landlordUuid: string, snapshotId: string) { return api("landlord", "tenants", "recoverySnapshotRestore", { landlordUuid, snapshotId }); },

    // Landlord API: Occupants
    LANDLORDAPIOCCUPANTSLIST(landlordUuid: string, tenantId: number) { return api("landlord", "occupants", "list", { landlordUuid, tenantId }); },
    LANDLORDAPIOCCUPANTSCREATE(landlordUuid: string, tenantId: number) { return api("landlord", "occupants", "create", { landlordUuid, tenantId }); },
    LANDLORDAPIOCCUPANTSMARKINACTIVE(landlordUuid: string, tenantId: number, occupantUuid: string) { return api("landlord", "occupants", "markInactive", { landlordUuid, tenantId, occupantUuid }); },
    LANDLORDAPIOCCUPANTSDELETE(landlordUuid: string, tenantId: number, occupantUuid: string) { return api("landlord", "occupants", "delete", { landlordUuid, tenantId, occupantUuid }); },
    LANDLORDAPIOCCUPANTSGETFILE(landlordUuid: string, tenantId: number, filename: string) { return api("landlord", "occupants", "getFile", { landlordUuid, tenantId, filename }); },

    // Landlord API: PDF
    LANDLORDAPIPDFDOWNLOAD(landlordUuid: string, tenantId: number, billNo: string) { return api("landlord", "pdf", "download", { landlordUuid, tenantId, billNo }); },
    LANDLORDAPIPDFVIEW(landlordUuid: string, tenantId: number, billNo: string) { return api("landlord", "pdf", "view", { landlordUuid, tenantId, billNo }); },

    // Landlord API: WhatsApp
    LANDLORDAPIWHATSAPPSENDSINGLE(landlordUuid: string, tenantId: number, billNo: string) { return api("landlord", "whatsapp", "sendSingle", { landlordUuid, tenantId, billNo }); },

    // Landlord API: Sync
    LANDLORDAPISYNCEXPORTCSV(landlordUuid: string) { return api("landlord", "sync", "exportCsv", { landlordUuid }); },
    LANDLORDAPISYNCEXPORTZIP(landlordUuid: string) { return api("landlord", "sync", "exportZip", { landlordUuid }); },
    LANDLORDAPISYNCTEMPLATE(landlordUuid: string) { return api("landlord", "sync", "template", { landlordUuid }); },
    LANDLORDAPISYNCEXPORTEXCEL(landlordUuid: string, format: string) { return api("landlord", "sync", "exportExcel", { landlordUuid, format }); },
    LANDLORDAPISYNCIMPORTPREVIEW(landlordUuid: string) { return api("landlord", "sync", "importPreview", { landlordUuid }); },
    LANDLORDAPISYNCIMPORTEXECUTE(landlordUuid: string) { return api("landlord", "sync", "importExecute", { landlordUuid }); },

    // Landlord API: Backups
    LANDLORDAPIBACKUPSLIST(landlordUuid: string) { return api("landlord", "backups", "list", { landlordUuid }); },
    LANDLORDAPIBACKUPSCREATEMANUAL(landlordUuid: string) { return api("landlord", "backups", "createManual", { landlordUuid }); },
    LANDLORDAPIBACKUPSDELETE(landlordUuid: string, backupId: string) { return api("landlord", "backups", "delete", { landlordUuid, backupId }); },
    LANDLORDAPIBACKUPSVERIFY(landlordUuid: string, backupId: string) { return api("landlord", "backups", "verify", { landlordUuid, backupId }); },
    LANDLORDAPIBACKUPSRESTORE(landlordUuid: string, backupId: string) { return api("landlord", "backups", "restore", { landlordUuid, backupId }); },
    LANDLORDAPIBACKUPSDOWNLOAD(landlordUuid: string, backupId: string) { return api("landlord", "backups", "download", { landlordUuid, backupId }); },
    LANDLORDAPIBACKUPSMETADATA(landlordUuid: string, backupId: string) { return api("landlord", "backups", "metadata", { landlordUuid, backupId }); },

    // Landlord API: Settings
    LANDLORDAPISETTINGSUPLOADSIGNATURE(landlordUuid: string) { return api("landlord", "settings", "uploadSignature", { landlordUuid }); },
    LANDLORDAPISETTINGSDELETESIGNATURE(landlordUuid: string) { return api("landlord", "settings", "deleteSignature", { landlordUuid }); },

    // Landlord API: TOTP
    LANDLORDAPITOTPQR(landlordUuid: string) { return api("landlord", "totp", "qr", { landlordUuid }); },
    LANDLORDAPITOTPREGENERATE(landlordUuid: string) { return api("landlord", "totp", "regenerate", { landlordUuid }); },
    LANDLORDAPITOTPENABLE(landlordUuid: string) { return api("landlord", "totp", "enable", { landlordUuid }); },
    LANDLORDAPITOTPDISABLE(landlordUuid: string) { return api("landlord", "totp", "disable", { landlordUuid }); },

    // Landlord API: Audit Logs
    LANDLORDAPIAUDITLOGS(landlordUuid: string) { return api("landlord", "audit", "logs", { landlordUuid }); },
    LANDLORDAPIAUDITLOGSACTIONS(landlordUuid: string) { return api("landlord", "audit", "actions", { landlordUuid }); },
} as const;

export type RoutesType = typeof ROUTES;
export default ROUTES;
