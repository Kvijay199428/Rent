import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { useGoogleLogin } from "@react-oauth/google";
import { ArrowLeft, KeyRound, AlertTriangle } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import AuthLayout from "@/components/layout/AuthLayout";
import { AuthFlow } from "@/components/auth";
import type { LoginValues, SignupValues } from "@/components/auth";
import { PrivacyPolicyBody, TermsConditionsBody } from "@/components/auth/PolicyContents";
import { Logo } from "@shared/brand/Logo";
import LoadingOverlay from "@shared/loading/LoadingOverlay";
import { ROUTES } from "@/lib/routes";
import { PRIVACY_POLICY_VERSION, TERMS_CONDITIONS_VERSION } from "@/lib/privacy";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface Conflict {
  field: string;
  message: string;
  suggestions?: string[];
}

type Step = "auth" | "totp";

interface PendingCreds {
  username: string;
  password: string;
  remember: boolean;
}

interface LandlordAuthPageProps {
  defaultTab?: "login" | "signup";
}

export default function LandlordAuthPage({ defaultTab = "login" }: LandlordAuthPageProps) {
  const navigate = useNavigate();
  const { login, verifyTotp, googleLogin: googleAuth, isAuthenticated, isLoading, landlordUuid } = useAuth();

  const [step, setStep] = useState<Step>("auth");
  const [totpToken, setTotpToken] = useState("");
  const [pendingCreds, setPendingCreds] = useState<PendingCreds | null>(null);
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingLabel, setLoadingLabel] = useState("Signing in…");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isLoading && isAuthenticated && landlordUuid) {
      navigate(`/${landlordUuid}/dashboard`, { replace: true });
    }
  }, [isLoading, isAuthenticated, landlordUuid, navigate]);

  const startLoading = (label: string) => {
    setError("");
    setLoading(true);
    setLoadingLabel(label);
  };

  const stopLoading = () => setLoading(false);

  const handleTabChange = (tab: "login" | "signup") => {
    setError("");
    setStep("auth");
    setTotpToken("");
    setPendingCreds(null);
    navigate(tab === "signup" ? "/signup" : "/login", { replace: true });
  };

  const handleLogin = async (values: LoginValues) => {
    startLoading("Signing in…");
    try {
      setRememberMe(values.remember);
      const result = await login(values.identifier, values.password, values.remember);

      if (result.status === "totp_required") {
        setPendingCreds({ username: values.identifier, password: values.password, remember: values.remember });
        setStep("totp");
        return;
      }
      if (result.status === "password_change_required") {
        navigate("/change-password", { replace: true });
        return;
      }
      if (result.status === "success") {
        navigate(`/${result.landlordUuid}/dashboard`, { replace: true });
        return;
      }
      setError("Invalid username or password.");
    } catch {
      setError("Network error during login. Please try again.");
    } finally {
      stopLoading();
    }
  };

  const handleVerifyTotp = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!pendingCreds) return;
    startLoading("Verifying…");
    try {
      const result = await verifyTotp(
        pendingCreds.username,
        pendingCreds.password,
        totpToken,
        pendingCreds.remember,
      );

      if (!result) {
        setError("Invalid TOTP code. Please try again.");
        return;
      }
      if (result.status === "password_change_required") {
        navigate("/change-password", { replace: true });
        return;
      }
      if (result.status === "success") {
        navigate(`/${result.landlordUuid}/dashboard`, { replace: true });
        return;
      }
      setError("Invalid TOTP code. Please try again.");
    } finally {
      stopLoading();
    }
  };

  const handleSignup = async (values: SignupValues) => {
    startLoading("Creating Account…");
    try {
      const response = await fetch(ROUTES.LANDLORDAPIAUTHSIGNUP, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...values,
          confirmPassword: values.password,
          privacyAccepted: true,
          privacyVersion: PRIVACY_POLICY_VERSION,
          termsAccepted: true,
          termsVersion: TERMS_CONDITIONS_VERSION,
        }),
      });
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        if (data?.detail?.conflicts) {
          const conflicts: Conflict[] = data.detail.conflicts;
          conflicts.forEach((c) => {
            toast.error(c.message, {
              description: c.suggestions ? `Try: ${c.suggestions.slice(0, 3).join(", ")}` : undefined,
              duration: 6000,
            });
          });
          setError(data.detail.message || "Some fields need attention.");
        } else if (typeof data?.detail === "string") {
          setError(data.detail);
        } else {
          setError("Signup failed. Please check your information.");
        }
        return;
      }

      if (data?.status === "success") {
        toast.success("Account created!", { description: "Redirecting to login…" });
        setTimeout(() => navigate("/login", { replace: true }), 1200);
        return;
      }
      setError("An unexpected error occurred.");
    } catch {
      setError("Network error. Please try again later.");
    } finally {
      stopLoading();
    }
  };

  const googleSignIn = useGoogleLogin({
    flow: "auth-code",
    onSuccess: async (codeResponse) => {
      startLoading("Signing in…");
      try {
        const code = codeResponse.code;
        if (!code) {
          setError("Google authentication failed");
          return;
        }
        const result = await googleAuth(code, rememberMe);

        if (result.status === "failed") {
          setError(result.message || "Google authentication failed");
          return;
        }
        if (result.status === "password_change_required") {
          navigate("/change-password?from=google", { replace: true });
          return;
        }
        if (result.status === "success") {
          navigate(`/${result.landlordUuid}/dashboard`, { replace: true });
        }
      } catch {
        setError("Network error during Google authentication");
      } finally {
        stopLoading();
      }
    },
    onError: () => setError("Google Sign-In failed"),
  });

  const backToAuth = () => {
    setStep("auth");
    setTotpToken("");
    setPendingCreds(null);
    setError("");
  };

  return (
    <>
      <AuthLayout>
        {step === "totp" && pendingCreds ? (
          <Card className="w-full max-w-md shadow-xl">
            <CardHeader className="space-y-1">
              <div className="flex items-center justify-center mb-4">
                <div className="p-3 bg-primary/10 rounded-full">
                  <KeyRound className="h-8 w-8 text-primary" />
                </div>
              </div>
              <CardTitle className="text-2xl text-center">Two-Factor Authentication</CardTitle>
              <CardDescription className="text-center">
                Open your authenticator app and enter the 6-digit code
              </CardDescription>
            </CardHeader>
            <CardContent>
              {error && (
                <Alert variant="destructive" className="mb-4">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <form onSubmit={handleVerifyTotp} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="totp">TOTP Code</Label>
                  <Input
                    id="totp"
                    placeholder="Enter 6-digit code from authenticator"
                    value={totpToken}
                    onChange={(e) => setTotpToken(e.target.value)}
                    required
                    maxLength={6}
                    pattern="\d{6}"
                    className="font-mono text-lg tracking-widest"
                    autoFocus
                  />
                  <p className="text-xs text-muted-foreground">
                    Open your authenticator app and enter the 6-digit code
                  </p>
                </div>

                <Button type="submit" className="w-full" disabled={loading || totpToken.length !== 6}>
                  Verify & Login
                </Button>

                <Button type="button" variant="ghost" className="w-full" onClick={backToAuth}>
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to password
                </Button>
              </form>
            </CardContent>
          </Card>
        ) : (
          <AuthFlow
            logo={<Logo height={36} />}
            brandName="PROPAURA"
            tagline="Manage your properties with confidence"
            defaultTab={defaultTab}
            error={error}
            onTabChange={handleTabChange}
            socialProviders={[{ id: "google", label: "Google", onClick: () => googleSignIn() }]}
            onLogin={handleLogin}
            onSignup={handleSignup}
            termsContent={<TermsConditionsBody />}
            privacyContent={<PrivacyPolicyBody />}
          />
        )}
      </AuthLayout>
      {loading && <LoadingOverlay label={loadingLabel} />}
    </>
  );
}