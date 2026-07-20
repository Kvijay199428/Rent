import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { ROUTES } from "@/lib/routes";
import { encryptPayload } from "@/lib/encryption";

type LoginStep = "success" | "totp_required" | "failed";

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (
    username: string,
    password: string,
    rememberMe?: boolean
  ) => Promise<LoginStep>;
  verifyTotp: (
    username: string,
    password: string,
    totpToken: string,
    rememberMe?: boolean
  ) => Promise<boolean>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [publicKey, setPublicKey] = useState("");

  useEffect(() => {
    fetch(ROUTES.ADMINAPIAUTHPUBLICKEY)
      .then((response) => response.json())
      .then((data) => setPublicKey(data.publicKey))
      .catch(console.error);
  }, []);

  useEffect(() => {
    fetch(ROUTES.ADMINAPIAUTHME, { credentials: "include" })
      .then((response) => setIsAuthenticated(response.ok))
      .catch(() => setIsAuthenticated(false))
      .finally(() => setIsLoading(false));
  }, []);

  const encryptRequest = useCallback(
    async (payload: Record<string, unknown>) => {
      if (!publicKey) {
        throw new Error("Encryption key is still loading. Please try again.");
      }

      return encryptPayload(payload, publicKey);
    },
    [publicKey]
  );

  const login = useCallback(
    async (
      username: string,
      password: string,
      rememberMe = false
    ): Promise<LoginStep> => {
      setIsLoading(true);

      try {
        const encrypted = await encryptRequest({
          username,
          password,
          remember_me: rememberMe,
        });

        const response = await fetch(ROUTES.ADMINAPIAUTHLOGIN, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...encrypted, remember_me: rememberMe }),
        });

        if (!response.ok) {
          return "failed";
        }

        const data = await response.json();

        if (data.status === "totp_required") {
          return "totp_required";
        }

        if (data.status === "success") {
          setIsAuthenticated(true);
          return "success";
        }

        return "failed";
      } catch {
        return "failed";
      } finally {
        setIsLoading(false);
      }
    },
    [encryptRequest]
  );

  const verifyTotp = useCallback(
    async (
      username: string,
      password: string,
      totpToken: string,
      rememberMe = false
    ): Promise<boolean> => {
      setIsLoading(true);

      try {
        const encrypted = await encryptRequest({
          username,
          password,
          totp_token: totpToken,
          remember_me: rememberMe,
        });

        const response = await fetch(ROUTES.ADMINAPIAUTHLOGINTOTP, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...encrypted, remember_me: rememberMe }),
        });

        if (!response.ok) {
          return false;
        }

        const data = await response.json();

        if (data.status !== "success") {
          return false;
        }

        setIsAuthenticated(true);
        return true;
      } catch {
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [encryptRequest]
  );

  const logout = useCallback(async () => {
    await fetch(ROUTES.ADMINAPIAUTHLOGOUT, {
      method: "POST",
      credentials: "include",
    });

    setIsAuthenticated(false);
    window.location.assign("/rent/admin/login");
  }, []);

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, isLoading, login, verifyTotp, logout }}
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

