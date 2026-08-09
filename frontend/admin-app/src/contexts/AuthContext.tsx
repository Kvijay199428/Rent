import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from "react";
import { API_BASE } from "../lib/runtime";
import { useAuthSync } from "../hooks/useAuthSync";

interface Admin {
  id: number;
  username: string;
  email: string | null;
  is_platform_admin: boolean;
  has_totp: boolean;
}

interface TOTPResult {
  requires_totp: boolean;
  methods?: string[];
}

interface AuthContextValue {
  admin: Admin | null;
  loading: boolean;
  login: (username: string, password: string, rememberMe?: boolean) => Promise<TOTPResult>;
  loginTOTP: (totpToken: string) => Promise<void>;
  loginOtpSend: () => Promise<{ status: string; message: string }>;
  loginOtpVerify: (otp: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [admin, setAdmin] = useState<Admin | null>(null);
  const [loading, setLoading] = useState(true);
  const pendingCreds = useRef<{ username: string; password: string; rememberMe: boolean } | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/auth/me`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => { if (data) setAdmin(data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (username: string, password: string, rememberMe = false): Promise<TOTPResult> => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, remember_me: rememberMe }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail ?? "Login failed");
    }
    const data = await res.json();
    if (data.status === "totp_required") {
      pendingCreds.current = { username, password, rememberMe };
      return { requires_totp: true, methods: data.methods ?? ["totp"] };
    }
    const me = await fetch(`${API_BASE}/auth/me`, { credentials: "include" }).then((r) => r.json());
    setAdmin(me);
    return { requires_totp: false };
  }, []);

  const loginTOTP = useCallback(async (totpToken: string) => {
    const creds = pendingCreds.current;
    if (!creds) throw new Error("No pending credentials. Please login again.");
    const res = await fetch(`${API_BASE}/auth/login-totp`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: creds.username,
        password: creds.password,
        totpToken,
        remember_me: creds.rememberMe,
      }),
    });
    pendingCreds.current = null;
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "TOTP verification failed" }));
      throw new Error(err.detail ?? "TOTP verification failed");
    }
    const me = await fetch(`${API_BASE}/auth/me`, { credentials: "include" }).then((r) => r.json());
    setAdmin(me);
  }, []);

  const loginOtpSend = useCallback(async () => {
    const creds = pendingCreds.current;
    if (!creds) throw new Error("No pending credentials. Please login again.");
    const res = await fetch(`${API_BASE}/auth/login-otp-send`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: creds.username,
        password: creds.password,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to send code" }));
      throw new Error(err.detail ?? "Failed to send code");
    }
    return await res.json();
  }, []);

  const loginOtpVerify = useCallback(async (otp: string) => {
    const creds = pendingCreds.current;
    if (!creds) throw new Error("No pending credentials. Please login again.");
    const res = await fetch(`${API_BASE}/auth/login-otp-verify`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: creds.username,
        password: creds.password,
        otp,
        remember_me: creds.rememberMe,
      }),
    });
    pendingCreds.current = null;
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "OTP verification failed" }));
      throw new Error(err.detail ?? "OTP verification failed");
    }
    const me = await fetch(`${API_BASE}/auth/me`, { credentials: "include" }).then((r) => r.json());
    setAdmin(me);
  }, []);

  const logout = useCallback(async () => {
    await fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "include" }).catch(() => {});
    setAdmin(null);
    pendingCreds.current = null;
  }, []);

  const refreshMe = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, { credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        setAdmin(data);
      }
    } catch {
      // Ignore — non-critical
    }
  }, []);

  // Real-time auth state sync via WebSocket
  useAuthSync(
    "platform_admin",
    useCallback(
      (event) => {
        if (
          event.type === "AUTH_STATE_CHANGED" ||
          event.type === "TOTP_STATE_CHANGED" ||
          event.type === "PASSWORD_RESET"
        ) {
          refreshMe();
        }
      },
      [refreshMe]
    ),
    !!admin
  );

  return (
    <AuthContext.Provider value={{ admin, loading, login, loginTOTP, loginOtpSend, loginOtpVerify, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
