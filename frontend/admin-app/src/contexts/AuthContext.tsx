import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';

interface AuthContextType {
  isAuthenticated: boolean;
  login: (username: string, password: string, rememberMe?: boolean) => Promise<boolean>;
  logout: () => Promise<void>;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return document.cookie.includes('admin_access_token');
  });
  const [isLoading, setIsLoading] = useState(false);
  const [publicKey, setPublicKey] = useState<string>('');

  useEffect(() => {
    fetch('/rent/admin/api/auth/public-key')
      .then(r => r.json())
      .then(d => setPublicKey(d.publicKey))
      .catch(console.error);
  }, []);

  const login = useCallback(async (username: string, password: string, rememberMe: boolean = false): Promise<boolean> => {
    setIsLoading(true);
    try {
      if (!publicKey) throw new Error("Public key not loaded");
      const { encryptPayload } = await import("../lib/encryption");
      const payload = { username, password, remember_me: rememberMe };
      const encrypted = await encryptPayload(payload, publicKey);

      const res = await fetch('/rent/admin/api/login/json', {
        method: 'POST',
        body: JSON.stringify({ ...encrypted, remember_me: rememberMe }),
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      if (res.ok || res.status === 303) {
        setIsAuthenticated(true);
        return true;
      }
      return false;
    } catch {
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    await fetch('/rent/admin/logout', { credentials: 'include' });
    setIsAuthenticated(false);
    window.location.href = '/rent/admin/login';
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
