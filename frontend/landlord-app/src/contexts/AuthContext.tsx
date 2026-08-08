import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { ROUTES } from "@/lib/routes";
import { extractLandlordUuid } from "@/lib/runtime";
import { apiPost } from "@/hooks/useApi";
import { useAuthSync } from "@/hooks/useAuthSync";

type LoginResult =
  | { status: "success"; landlordUuid: string }
  | { status: "totp_required" }
  | { status: "password_change_required"; landlordUuid: string }
  | { status: "failed"; message?: string };

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  landlordUuid: string | null;
  username: string | null;
  fullName: string | null;
  hasTotp: boolean;
  totpEnabled: boolean;
  requiresPasswordChange: boolean;
  login: (
    username: string,
    password: string,
    rememberMe?: boolean
  ) => Promise<LoginResult>;
  googleLogin: (
    credential: string,
    rememberMe?: boolean
  ) => Promise<LoginResult>;
  verifyTotp: (
    username: string,
    password: string,
    totpToken: string,
    rememberMe?: boolean
  ) => Promise<LoginResult | false>;
  logout: () => Promise<void>;
  changePassword: (
    currentPassword: string,
    newPassword: string,
    confirmPassword: string
  ) => Promise<{ status: string; message?: string; next_step?: string; totp?: any }>;
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [landlordUuid, setLandlordUuid] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [fullName, setFullName] = useState<string | null>(null);
  const [hasTotp, setHasTotp] = useState(false);
  const [totpEnabled, setTotpEnabled] = useState(false);
  const [requiresPasswordChange, setRequiresPasswordChange] = useState(false);

  const refreshMe = useCallback(async () => {
    try {
      const response = await fetch(ROUTES.LANDLORDAPIAUTHME, { credentials: "include" });
      if (!response.ok) throw new Error("Not authenticated");
      const data = await response.json();
      const uuid = data?.landlord?.landlordUuid ?? null;
      setIsAuthenticated(true);
      setLandlordUuid(uuid);
      setUsername(data?.landlord?.username ?? null);
      setFullName(data?.landlord?.fullName ?? null);
      setHasTotp(data?.landlord?.hasTotp ?? false);
      setTotpEnabled(data?.landlord?.totpEnabled ?? false);
      setRequiresPasswordChange(data?.landlord?.requiresPasswordChange ?? false);
      if (uuid) localStorage.setItem("landlordUuid", uuid);
    } catch {
      setIsAuthenticated(false);
      setLandlordUuid(null);
      setUsername(null);
      setFullName(null);
      setHasTotp(false);
      setTotpEnabled(false);
      setRequiresPasswordChange(false);
      localStorage.removeItem("landlordUuid");
    }
  }, []);

  useEffect(() => {
    // Pre-seed UUID from URL or localStorage before /api/auth/me responds
    const urlUuid = extractLandlordUuid();
    const storedUuid = localStorage.getItem("landlordUuid");
    const initialUuid = urlUuid || storedUuid;
    if (initialUuid) {
      setLandlordUuid(initialUuid);
      setIsAuthenticated(true);
    }

    refreshMe().finally(() => setIsLoading(false));
  }, [refreshMe]);

  const login = useCallback(
    async (
      username: string,
      password: string,
      rememberMe = false
    ): Promise<LoginResult> => {
      setIsLoading(true);

      try {
        const response = await fetch(ROUTES.LANDLORDAPIAUTHLOGIN, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password, rememberMe }),
        });

        if (!response.ok) {
          return { status: "failed" };
        }

        const data = await response.json();

        if (data.status === "totp_required") {
          return { status: "totp_required" };
        }

        if (data.status === "password_change_required") {
          return { status: "password_change_required", landlordUuid: data.landlordUuid };
        }

        if (data.status === "success") {
          const uuid = data?.landlord?.landlordUuid ?? "";
          setIsAuthenticated(true);
          setLandlordUuid(uuid);
          setUsername(data?.landlord?.username ?? null);
          setFullName(data?.landlord?.fullName ?? null);
          localStorage.setItem("landlordUuid", uuid);
          return { status: "success", landlordUuid: uuid };
        }

        return { status: "failed" };
      } catch {
        return { status: "failed" };
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const googleLogin = useCallback(
    async (
      credential: string,
      rememberMe = false
    ): Promise<LoginResult> => {
      setIsLoading(true);

      try {
        const response = await fetch(ROUTES.LANDLORDAPIAUTHGOOGLE, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ credential, rememberMe }),
        });

        const data = await response.json().catch(() => null);

        if (!response.ok) {
          return {
            status: "failed",
            message: data?.detail || "Google authentication failed",
          };
        }

        if (data.status === "password_change_required") {
          return { status: "password_change_required", landlordUuid: data.landlordUuid };
        }

        if (data.status === "success") {
          const uuid = data?.landlord?.landlordUuid ?? "";
          setIsAuthenticated(true);
          setLandlordUuid(uuid);
          setUsername(data?.landlord?.username ?? null);
          setFullName(data?.landlord?.fullName ?? null);
          localStorage.setItem("landlordUuid", uuid);
          return { status: "success", landlordUuid: uuid };
        }

        return {
          status: "failed",
          message: data?.detail || "Google authentication failed",
        };
      } catch {
        return { status: "failed", message: "Network error during Google authentication" };
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const verifyTotp = useCallback(
    async (
      username: string,
      password: string,
      totpToken: string,
      rememberMe = false
    ): Promise<LoginResult | false> => {
      setIsLoading(true);

      try {
        const response = await fetch(ROUTES.LANDLORDAPIAUTHLOGINTOTP, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password, totpToken, rememberMe }),
        });

        if (!response.ok) {
          return false;
        }

        const data = await response.json();

        if (data.status === "password_change_required") {
          return { status: "password_change_required", landlordUuid: data.landlordUuid };
        }

        if (data.status !== "success") {
          return false;
        }

        const uuid = data?.landlord?.landlordUuid ?? "";
        setIsAuthenticated(true);
        setLandlordUuid(uuid);
        setUsername(data?.landlord?.username ?? null);
        setFullName(data?.landlord?.fullName ?? null);
        localStorage.setItem("landlordUuid", uuid);
        return { status: "success", landlordUuid: uuid };
      } catch {
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const changePassword = useCallback(
    async (
      currentPassword: string,
      newPassword: string,
      confirmPassword: string
    ): Promise<{ status: string; message?: string; next_step?: string; totp?: any }> => {
      try {
        const data = await apiPost(ROUTES.LANDLORDAPIAUTHCHANGEPASSWORD, {
          currentPassword,
          newPassword,
          confirmPassword,
        });

        // Refresh auth state after successful password change
        await refreshMe();

        return {
          status: data?.status ?? "error",
          message: data?.message,
          next_step: data?.next_step,
          totp: data?.totp,
        };
      } catch (err: any) {
        return { status: "error", message: err?.message || "Failed to change password" };
      }
    },
    [refreshMe]
  );

  const logout = useCallback(async () => {
    try {
      await fetch(ROUTES.LANDLORDAPIAUTHLOGOUT, {
        method: "POST",
        credentials: "include",
      });
    } finally {
      setIsAuthenticated(false);
      setLandlordUuid(null);
      setUsername(null);
      setFullName(null);
      localStorage.removeItem("landlordUuid");
      window.location.assign(ROUTES.LANDLORDPAGELOGIN);
    }
  }, []);

  // Real-time auth state sync via WebSocket
  const authChannel = landlordUuid ? `landlord:${landlordUuid}` : "";
  useAuthSync(
    authChannel,
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
    isAuthenticated && !!landlordUuid
  );

  // Fallback: periodic refresh in case WebSocket connection drops
  useEffect(() => {
    if (!isAuthenticated || !landlordUuid) return;
    const interval = setInterval(refreshMe, 60000);
    return () => clearInterval(interval);
  }, [isAuthenticated, landlordUuid, refreshMe]);

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, isLoading, landlordUuid, username, fullName, hasTotp, totpEnabled, requiresPasswordChange, login, googleLogin, verifyTotp, logout, changePassword, refreshMe }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return context;
}
