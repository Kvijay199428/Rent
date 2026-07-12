// Extract view_token from URL path: /t/{view_token}/...
const getViewToken = (): string => {
    const pathParts = window.location.pathname.split('/');
    // Handle paths like /t/abc123 or /t/abc123/receipts
    const tIndex = pathParts.indexOf('t');
    if (tIndex !== -1 && pathParts[tIndex + 1]) {
        return pathParts[tIndex + 1];
    }
    // Fallback: try from localStorage if stored
    return localStorage.getItem('view_token') || '';
};

// Base API client that injects view_token into auth endpoints
const apiClient = {
    async post(url: string, body?: unknown, options?: RequestInit) {
        const viewToken = getViewToken();

        // Replace {view_token} placeholder in URL if present
        const resolvedUrl = url.replace(/{view_token}/g, viewToken);

        const res = await fetch(resolvedUrl, {
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

    async get(url: string, options?: RequestInit) {
        const viewToken = getViewToken();
        const resolvedUrl = url.replace(/{view_token}/g, viewToken);

        const res = await fetch(resolvedUrl, {
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

// Export route builders that use the shared routes.json structure
export const tenantApi = {
    auth: {
        publicKey: () => apiClient.get('/api/auth/public-key'),

        login: (viewToken: string, pin: string, rememberMe: boolean = false) =>
            apiClient.post(`/api/auth/login/${viewToken}`, { view_token: viewToken, pin, remember_me: rememberMe }),

        // These now include view_token in the path
        refresh: () => {
            const viewToken = getViewToken();
            return apiClient.post(`/api/auth/refresh/${viewToken}`);
        },

        logout: () => {
            const viewToken = getViewToken();
            return apiClient.post(`/api/auth/logout/${viewToken}`);
        },

        logoutAll: () => {
            const viewToken = getViewToken();
            return apiClient.post(`/api/auth/logout-all/${viewToken}`);
        },
    },

    profile: {
        get: (viewToken: string) => apiClient.get(`/api/${viewToken}`),
    },

    kyc: {
        upload: (viewToken: string, formData: FormData) =>
            apiClient.post(`/api/${viewToken}/kyc`, formData),
        markInactive: (viewToken: string, occupantUuid: string) =>
            apiClient.post(`/api/${viewToken}/kyc/${occupantUuid}/inactive`),
        delete: (viewToken: string, occupantUuid: string) =>
            apiClient.post(`/api/${viewToken}/kyc/${occupantUuid}`),
        getFile: (viewToken: string, filename: string) =>
            `/api/${viewToken}/kyc/file/${filename}`,
    },

    pdf: {
        view: (viewToken: string, billNo: string) =>
            `/t/api/${viewToken}/pdf/${billNo}/view`,
        download: (viewToken: string, billNo: string) =>
            `/t/api/${viewToken}/pdf/${billNo}/download`,
    }
};