import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { tenantApi } from '@/lib/api';

interface AuthContextType {
    isAuthenticated: boolean;
    isLoading: boolean;
    viewToken: string | null;
    login: (viewToken: string, pin: string, rememberMe?: boolean) => Promise<void>;
    logout: () => Promise<void>;
    refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [viewToken, setViewToken] = useState<string | null>(null);

    // On mount: extract viewToken from URL and check existing session
    useEffect(() => {
        const pathParts = window.location.pathname.split('/');
        const tIndex = pathParts.indexOf('t');
        const tokenFromUrl = tIndex !== -1 ? pathParts[tIndex + 1] : null;

        if (tokenFromUrl) {
            setViewToken(tokenFromUrl);
            localStorage.setItem('viewToken', tokenFromUrl);

            // Optionally verify session is still valid
            tenantApi.profile.get(tokenFromUrl)
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

    const login = useCallback(async (token: string, pin: string, rememberMe = false) => {
        await tenantApi.auth.login(token, pin, rememberMe);
        setViewToken(token);
        setIsAuthenticated(true);
        localStorage.setItem('viewToken', token);
    }, []);

    const logout = useCallback(async () => {
        try {
            if (viewToken) {
                await tenantApi.auth.logout();
            }
        } finally {
            setIsAuthenticated(false);
            setViewToken(null);
            localStorage.removeItem('viewToken');
        }
    }, [viewToken]);

    const refreshToken = useCallback(async () => {
        // The viewToken is automatically extracted from URL in apiClient
        await tenantApi.auth.refresh();
    }, []);

    return (
        <AuthContext.Provider value={{
            isAuthenticated,
            isLoading,
            viewToken,
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