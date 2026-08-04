import { useState } from "react";
import { KeyRound, User, Lock, ArrowRight, ArrowLeft, ShieldCheck } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import AuthLayout from "@/components/AuthLayout";
import {
  portalLogin,
  forgotTenantPassword,
  changeTenantPassword,
} from "@/lib/login-api";

type View = "login" | "forgot" | "forced-change";

const USERNAME_RE = /^[a-zA-Z0-9][a-zA-Z0-9\-_.!@#$%^&*+]{2,}$/;

function validateUsername(v: string): string | null {
  if (!v) return "Username is required";
  if (/\s/.test(v)) return "Username must not contain spaces";
  if (v.length < 3) return "Username must be at least 3 characters";
  if (v.length > 50) return "Username must not exceed 50 characters";
  if (!USERNAME_RE.test(v))
    return "Username must start with a letter or digit and contain only letters, digits, and !@#$%^&*_-";
  return null;
}

function validatePassword(v: string): string | null {
  if (!v) return "Password is required";
  if (/\s/.test(v)) return "Password must not contain spaces";
  if (v.length < 8) return "Password must be at least 8 characters";
  return null;
}

export default function PortalLoginPage() {
  const [view, setView] = useState<View>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const go = (next: View) => {
    setError("");
    setInfo("");
    setView(next);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) return;

    const usernameErr = validateUsername(username.trim());
    if (usernameErr) { setError(usernameErr); return; }
    const passwordErr = validatePassword(password);
    if (passwordErr) { setError(passwordErr); return; }

    setError("");
    setInfo("");
    setLoading(true);
    try {
      const data = await portalLogin(username.trim(), password, rememberMe);
      if (data.reset_required) {
        setPassword("");
        setLoading(false);
        setView("forced-change");
        return;
      }
      if (data.redirect_url) {
        window.location.assign(data.redirect_url);
      } else {
        window.location.reload();
      }
    } catch (err: any) {
      setError(err.message || "Login failed. Please check your credentials.");
      setLoading(false);
    }
  };

  const handleForgot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) return;

    const usernameErr = validateUsername(username.trim());
    if (usernameErr) { setError(usernameErr); return; }

    setError("");
    setInfo("");
    setLoading(true);
    try {
      await forgotTenantPassword(username.trim());
      setInfo(
        "If an account exists for that username, the landlord can arrange a password reset."
      );
    } catch (err: any) {
      setError(err.message || "Request failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleForcedChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    const passwordErr = validatePassword(newPassword);
    if (passwordErr) { setError(passwordErr); return; }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setError("");
    setInfo("");
    setLoading(true);
    try {
      await changeTenantPassword(username.trim(), password, newPassword);
      setPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setInfo("Password updated. Please sign in with your new password.");
      go("login");
    } catch (err: any) {
      setError(err.message || "Password change failed. Please try again.");
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <Card className="w-full max-w-md rounded-3xl border shadow-xl">
        <CardContent className="p-8">
          {view === "login" && (
            <>
              <div className="text-center mb-6">
                <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <KeyRound className="w-7 h-7 text-primary" />
                </div>
                <h1 className="text-2xl font-bold tracking-tight">Tenant Portal</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Sign in with your username and password
                </p>
              </div>

              {error && (
                <Alert variant="destructive" className="mb-4 rounded-xl">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              {info && (
                <Alert className="mb-4 rounded-xl">
                  <AlertDescription>{info}</AlertDescription>
                </Alert>
              )}

              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label className="text-sm font-semibold block mb-2">
                    Username
                  </label>
                  <div className="relative">
                    <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      type="text"
                      autoFocus
                      required
                      disabled={loading}
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="Your tenant username"
                      className="h-12 pl-10 rounded-2xl"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-sm font-semibold block mb-2">
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      type="password"
                      required
                      disabled={loading}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="h-12 pl-10 rounded-2xl"
                    />
                  </div>
                </div>

                <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="h-4 w-4 rounded border-border"
                  />
                  Remember me
                </label>

                <Button
                  type="submit"
                  disabled={loading || !username.trim() || !password}
                  className="w-full h-12 rounded-2xl text-base"
                >
                  {loading ? "Signing in…" : "Sign In"}
                  {!loading && <ArrowRight className="w-4 h-4 ml-2" />}
                </Button>
              </form>

              <div className="mt-6 pt-4 border-t text-center">
                <button
                  type="button"
                  onClick={() => {
                    setPassword("");
                    go("forgot");
                  }}
                  className="text-xs font-medium text-primary hover:underline bg-transparent border-none cursor-pointer"
                >
                  Forgot your password?
                </button>
              </div>
            </>
          )}

          {view === "forgot" && (
            <>
              <div className="text-center mb-6">
                <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <ShieldCheck className="w-7 h-7 text-primary" />
                </div>
                <h1 className="text-2xl font-bold tracking-tight">
                  Forgot Password
                </h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Enter your username and the landlord will arrange a reset
                </p>
              </div>

              {info && (
                <Alert className="mb-4 rounded-xl">
                  <AlertDescription>{info}</AlertDescription>
                </Alert>
              )}
              {error && (
                <Alert variant="destructive" className="mb-4 rounded-xl">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <form onSubmit={handleForgot} className="space-y-4">
                <div>
                  <label className="text-sm font-semibold block mb-2">
                    Username
                  </label>
                  <div className="relative">
                    <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      type="text"
                      autoFocus
                      required
                      disabled={loading}
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="Your tenant username"
                      className="h-12 pl-10 rounded-2xl"
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={loading || !username.trim()}
                  className="w-full h-12 rounded-2xl text-base"
                >
                  {loading ? "Submitting…" : "Request Reset"}
                </Button>

                <Button
                  type="button"
                  variant="ghost"
                  disabled={loading}
                  onClick={() => go("login")}
                  className="w-full h-12 rounded-2xl text-sm"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" /> Back to sign in
                </Button>
              </form>
            </>
          )}

          {view === "forced-change" && (
            <>
              <div className="text-center mb-6">
                <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <Lock className="w-7 h-7 text-primary" />
                </div>
                <h1 className="text-2xl font-bold tracking-tight">
                  Set a New Password
                </h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Your temporary password must be changed before you can continue
                </p>
              </div>

              {error && (
                <Alert variant="destructive" className="mb-4 rounded-xl">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <form onSubmit={handleForcedChange} className="space-y-4">
                <div>
                  <label className="text-sm font-semibold block mb-2">
                    Temporary password
                  </label>
                  <Input
                    type="password"
                    required
                    disabled={loading}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Current temporary password"
                    className="h-12 rounded-2xl"
                  />
                </div>

                <div>
                  <label className="text-sm font-semibold block mb-2">
                    New password
                  </label>
                  <Input
                    type="password"
                    required
                    disabled={loading}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    className="h-12 rounded-2xl"
                  />
                </div>

                <div>
                  <label className="text-sm font-semibold block mb-2">
                    Confirm new password
                  </label>
                  <Input
                    type="password"
                    required
                    disabled={loading}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter new password"
                    className="h-12 rounded-2xl"
                  />
                </div>

                <Button
                  type="submit"
                  disabled={loading || !password || newPassword.length < 8}
                  className="w-full h-12 rounded-2xl text-base"
                >
                  {loading ? "Updating…" : "Update Password"}
                </Button>
              </form>
            </>
          )}

          <p className="text-xs text-center text-muted-foreground mt-6 leading-relaxed">
            This portal uses your username and password. QR-code links are a
            separate, direct access method.
          </p>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}
