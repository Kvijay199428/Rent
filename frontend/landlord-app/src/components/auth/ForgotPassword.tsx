// components/auth/ForgotPassword.tsx
import { useState } from "react";
import { KeyRound, ShieldAlert, ArrowLeft } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PasswordField } from "./PasswordField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ROUTES } from "@/lib/routes";

interface ForgotPasswordProps {
  onCancel: () => void;
  onDone?: () => void;
}

type ForgotStep = "verify" | "reset";

/**
 * TOTP-based password reset for landlords. Step 1 verifies the username + TOTP
 * code, step 2 sets the new password. When the account has no TOTP configured
 * the backend returns `no_totp` and we direct the user to sign in and change
 * the password from Settings.
 */
export function ForgotPassword({ onCancel, onDone }: ForgotPasswordProps) {
  const [step, setStep] = useState<ForgotStep>("verify");
  const [username, setUsername] = useState("");
  const [totpToken, setTotpToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);

  const handleVerify = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    setInfo("");
    if (!username.trim() || totpToken.length !== 6) return;

    setLoading(true);
    try {
      const res = await fetch(ROUTES.LANDLORDAPIPASSWORDFORGOTVERIFY, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), totpToken }),
      });
      const data = await res.json().catch(() => null);

      if (data?.status === "no_totp") {
        setInfo(
          "This account has no authenticator app configured. Sign in and change your password from Settings instead.",
        );
        return;
      }
      if (!res.ok) {
        if (res.status === 429) {
          setError("Too many failed attempts. Try again later.");
        } else if (res.status === 401) {
          setError("Invalid TOTP code. Please try again.");
        } else {
          setError(typeof data?.detail === "string" ? data.detail : "Verification failed.");
        }
        return;
      }
      if (data?.status === "success") {
        setStep("reset");
      }
    } catch {
      setError("Network error. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }
    if (newPassword.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(ROUTES.LANDLORDAPIPASSWORDFORGOTRESET, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: username.trim(),
          totpToken,
          newPassword,
          confirmPassword,
        }),
      });
      const data = await res.json().catch(() => null);

      if (!res.ok) {
        if (res.status === 429) {
          setError("Too many failed attempts. Try again later.");
        } else if (res.status === 401) {
          setError("Invalid TOTP code. Please try again.");
        } else {
          setError(typeof data?.detail === "string" ? data.detail : "Reset failed.");
        }
        return;
      }
      onDone?.();
    } catch {
      setError("Network error. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-md shadow-xl">
      <CardHeader className="space-y-1">
        <div className="flex items-center justify-center mb-4">
          <div className="p-3 bg-primary/10 rounded-full">
            <KeyRound className="h-8 w-8 text-primary" />
          </div>
        </div>
        <CardTitle className="text-2xl text-center">Reset Password</CardTitle>
        <CardDescription className="text-center">
          {step === "verify"
            ? "Enter your username and the 6-digit code from your authenticator app"
            : "Choose a new password"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {info && (
          <Alert className="mb-4">
            <ShieldAlert className="h-4 w-4" />
            <AlertDescription>{info}</AlertDescription>
          </Alert>
        )}
        {error && (
          <Alert variant="destructive" className="mb-4">
            <ShieldAlert className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {step === "verify" ? (
          <form onSubmit={handleVerify} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="forgot-username">Username</Label>
              <Input
                id="forgot-username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Your username"
                autoComplete="username"
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="forgot-totp">TOTP Code</Label>
              <Input
                id="forgot-totp"
                placeholder="Enter 6-digit code from authenticator"
                value={totpToken}
                onChange={(e) => setTotpToken(e.target.value)}
                inputMode="numeric"
                maxLength={6}
                pattern="\d{6}"
                className="font-mono text-lg tracking-widest"
              />
              <p className="text-xs text-muted-foreground">
                Open your authenticator app and enter the 6-digit code
              </p>
            </div>
            <Button type="submit" className="w-full" disabled={loading || totpToken.length !== 6}>
              {loading ? "Verifying…" : "Verify"}
            </Button>
            <Button type="button" variant="ghost" className="w-full" onClick={onCancel}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to sign in
            </Button>
          </form>
        ) : (
          <form onSubmit={handleReset} className="space-y-4">
            <PasswordField label="New Password" value={newPassword} onChange={setNewPassword} autoComplete="new-password" />
            <PasswordField label="Confirm New Password" value={confirmPassword} onChange={setConfirmPassword} autoComplete="new-password" />
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Resetting…" : "Reset Password"}
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="w-full"
              onClick={() => {
                setError("");
                setStep("verify");
              }}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
}