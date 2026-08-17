import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from "react";
import { API_BASE } from "../lib/runtime";
import { useAuthSync } from "../hooks/useAuthSync";
import { onAuthExpired } from "../api/client";

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

interface OtpSendResult {
  status: string;
  message: string;
  cooldown_seconds?: number;
}

export class OtpCooldownError extends Error {
  cooldownSeconds: number;

  constructor(cooldownSeconds: number) {
    super(`Please wait ${cooldownSeconds}s before requesting a new code.`);
    this.cooldownSeconds = cooldownSeconds;
  }
}

interface AuthContextValue {
  admin: Admin | null;
  loading: boolean;
  login: (username: string, password: string, rememberMe?: boolean) => Promise<TOTPResult>;
  loginTOTP: (totpToken: string) => Promise<void>;
  loginOtpSend: () => Promise<OtpSendResult>;
  loginOtpVerify: (otp: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [admin, setAdmin] = useState<Admin | null>(null);
  const [loading, setLoading] = useState(true);
  const pendingCreds = useRef<{ username: string; password: string; rememberMe: boolean } | null>(null);

  useEffect(() => {
    const loadMe = async (): Promise<boolean> => {
      const res = await fetch(`${API_BASE}/auth/me`, { credentials: "include" });
      if (res.ok) {
        setAdmin(await res.json());
        return true;
      }
      if (res.status === 401) {
        // Access token expired — try a silent refresh, then re-check.
        const refreshed = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          credentials: "include",
        }).then((r) => r.ok).catch(() => false);
        if (refreshed) {
          const retry = await fetch(`${API_BASE}/auth/me`, { credentials: "include" });
          if (retry.ok) {
            setAdmin(await retry.json());
            return true;
          }
        }
      }
      return false;
    };

    loadMe().finally(() => setLoading(false));
  }, []);

  // If any authenticated call hits a session that can't be refreshed
  // (e.g. the access token expired and the refresh session is gone), clear
  // admin state so the router bounces back to /login.
  useEffect(() => {
    return onAuthExpired(() => {
      setAdmin(null);
      pendingCreds.current = null;
    });
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
      const err = await res.json().catch(() => ({ detail: undefined }));
      if (err?.detail && typeof err.detail === "object" && "cooldown_seconds" in err.detail) {
        throw new OtpCooldownError(Number(err.detail.cooldown_seconds) || 0);
      }
      const message =
        typeof err?.detail === "string" ? err.detail : (err?.message ?? "Failed to send code");
      throw new Error(message);
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
      let res = await fetch(`${API_BASE}/auth/me`, { credentials: "include" });
      if (!res.ok && res.status === 401) {
        // Access token expired — refresh once, then re-check identity.
        const refreshed = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          credentials: "include",
        }).then((r) => r.ok).catch(() => false);
        if (!refreshed) {
          setAdmin(null);
          return;
        }
        res = await fetch(`${API_BASE}/auth/me`, { credentials: "include" });
      }
      if (res.ok) {
        setAdmin(await res.json());
      } else if (res.status === 401) {
        setAdmin(null);
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
