import { TENANTROUTES } from "./routes";

// Extract tenantId and viewToken from URL path: /t/{tenantId}/{viewToken}/...
export const getTenantParams = (): { tenantId: string; viewToken: string } => {
    const pathParts = window.location.pathname.split('/');
    const tIndex = pathParts.indexOf('t');
    if (tIndex !== -1 && pathParts[tIndex + 1] && pathParts[tIndex + 2]) {
        return {
            tenantId: pathParts[tIndex + 1],
            viewToken: pathParts[tIndex + 2]
        };
    }
    // Fallback: try from localStorage if stored
    return {
        tenantId: localStorage.getItem('tenantId') || '',
        viewToken: localStorage.getItem('viewToken') || ''
    };
};

export const APP_BASE_PATH = import.meta.env.VITE_APP_BASE_PATH?.replace(/\/$/, "") || "/rent";

// Base API client
const apiClient = {
    async post(url: string, body?: unknown, options?: RequestInit) {
        const res = await fetch(url, {
            method: 'POST',
            credentials: 'include', // Important: send cookies
            headers: {
                'Content-Type': 'application/json',
                ...options?.headers,
            },
            body: body ? JSON.stringify(body) : undefined,
            ...options,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }

        return res.json();
    },

    async put(url: string, body?: unknown, options?: RequestInit) {
        const res = await fetch(url, {
            method: 'PUT',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                ...options?.headers,
            },
            body: body ? JSON.stringify(body) : undefined,
            ...options,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }

        return res.json();
    },

    async delete(url: string, options?: RequestInit) {
        const res = await fetch(url, {
            method: 'DELETE',
            credentials: 'include',
            ...options,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }

        return res.json();
    },

    async get(url: string, options?: RequestInit) {
        const res = await fetch(url, {
            method: 'GET',
            credentials: 'include',
            ...options,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }

        return res.json();
    }
};

// Export route builders that use the shared routes.json structure via TENANTROUTES
export const tenantApi = {
    auth: {
        publicKey: () => apiClient.get(TENANTROUTES.TENANTAPIAUTHPUBLICKEY),

        login: (tenantId: string | number, viewToken: string, pin: string, rememberMe: boolean = false) =>
            apiClient.post(TENANTROUTES.TENANTAPIAUTHLOGIN(tenantId, viewToken), { viewToken, pin, remember_me: rememberMe }),

        refresh: () => {
            const { tenantId, viewToken } = getTenantParams();
            return apiClient.post(TENANTROUTES.TENANTAPIAUTHREFRESH(tenantId, viewToken));
        },

        logout: () => {
            const { tenantId, viewToken } = getTenantParams();
            return apiClient.post(TENANTROUTES.TENANTAPIAUTHLOGOUT(tenantId, viewToken));
        },

        logoutAll: () => {
            const { tenantId, viewToken } = getTenantParams();
            return apiClient.post(TENANTROUTES.TENANTAPIAUTHLOGOUTALL(tenantId, viewToken));
        },
    },

    profile: {
        get: (tenantId: string | number, viewToken: string) => 
            apiClient.get(TENANTROUTES.TENANTAPIPROFILEGET(tenantId, viewToken)),
    },

    kyc: {
        upload: (tenantId: string | number, viewToken: string, formData: FormData) => {
            // Note: FormData requires different headers than standard JSON requests
            return fetch(TENANTROUTES.TENANTAPIKYCUPLOAD(tenantId, viewToken), {
                method: 'POST',
                credentials: 'include',
                body: formData,
            }).then(async res => {
                if (!res.ok) {
                    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
                    throw new Error(err.detail || `HTTP ${res.status}`);
                }
                return res.json();
            });
        },
        markInactive: (tenantId: string | number, viewToken: string, occupantUuid: string) =>
            apiClient.put(TENANTROUTES.TENANTAPIKYCMARKINACTIVE(tenantId, viewToken, occupantUuid)),
        delete: (tenantId: string | number, viewToken: string, occupantUuid: string) =>
            apiClient.delete(TENANTROUTES.TENANTAPIKYCDELETE(tenantId, viewToken, occupantUuid)),
        getFile: (tenantId: string | number, viewToken: string, filename: string) =>
            TENANTROUTES.TENANTAPIKYCGETFILE(tenantId, viewToken, filename),
    },

    pdf: {
        view: (tenantId: number | string, viewToken: string, billNo: string) =>
            TENANTROUTES.TENANTAPIPDFVIEW(tenantId, viewToken, billNo),
        download: (tenantId: number | string, viewToken: string, billNo: string) =>
            TENANTROUTES.TENANTAPIPDFDOWNLOAD(tenantId, viewToken, billNo),
    }
};