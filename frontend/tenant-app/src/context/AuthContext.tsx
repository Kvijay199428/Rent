import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { tenantApi, getTenantParams } from '@/lib/api';

interface AuthContextType {
    isAuthenticated: boolean;
    isLoading: boolean;
    viewToken: string | null;
    tenantId: string | null;
    login: (tenantId: string | number, viewToken: string, pin: string, rememberMe?: boolean) => Promise<void>;
    logout: () => Promise<void>;
    refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [viewToken, setViewToken] = useState<string | null>(null);
    const [tenantId, setTenantId] = useState<string | null>(null);

    // On mount: extract viewToken from URL and check existing session
    useEffect(() => {
        const { tenantId: idFromUrl, viewToken: tokenFromUrl } = getTenantParams();

        if (tokenFromUrl && idFromUrl) {
            setViewToken(tokenFromUrl);
            setTenantId(idFromUrl);
            localStorage.setItem('viewToken', tokenFromUrl);
            localStorage.setItem('tenantId', idFromUrl);

            // Optionally verify session is still valid
            tenantApi.profile.get(idFromUrl, tokenFromUrl)
                .then((data) => {
                    setIsAuthenticated(data.tenant?.unlocked ?? false);
                })
                .catch(() => {
                    setIsAuthenticated(false);
                })
                .finally(() => setIsLoading(false));
        } else {
            setIsLoading(false);
        }
    }, []);

    const login = useCallback(async (tenantIdArg: string | number, token: string, pin: string, rememberMe = false) => {
        await tenantApi.auth.login(tenantIdArg, token, pin, rememberMe);
        setViewToken(token);
        setTenantId(String(tenantIdArg));
        setIsAuthenticated(true);
        localStorage.setItem('viewToken', token);
        localStorage.setItem('tenantId', String(tenantIdArg));
    }, []);

    const logout = useCallback(async () => {
        try {
            if (viewToken && tenantId) {
                await tenantApi.auth.logout();
            }
        } finally {
            setIsAuthenticated(false);
            setViewToken(null);
            setTenantId(null);
            localStorage.removeItem('viewToken');
            localStorage.removeItem('tenantId');
        }
    }, [viewToken, tenantId]);

    const refreshToken = useCallback(async () => {
        // The viewToken is automatically extracted from URL in apiClient
        await tenantApi.auth.refresh();
    }, []);

    return (
        <AuthContext.Provider value={{
            isAuthenticated,
            isLoading,
            viewToken,
            tenantId,
            login,
            logout,
            refreshToken
        }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used within AuthProvider');
    return ctx;
};