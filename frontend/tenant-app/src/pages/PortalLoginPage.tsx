import { useState } from "react";
import { KeyRound, User, ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import AuthLayout from "@/components/AuthLayout";
import { portalLoginByUsername } from "@/lib/login-api";

export default function PortalLoginPage() {
  const [username, setUsername] = useState("");
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || pin.length !== 4) return;

    setError("");
    setLoading(true);
    try {
      const data = await portalLoginByUsername(username.trim(), pin);
      if (data.redirect_url) {
        window.location.href = data.redirect_url;
      } else {
        window.location.reload();
      }
    } catch (err: any) {
      setError(err.message || "Login failed. Please check your credentials.");
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <Card className="w-full max-w-md rounded-3xl border shadow-xl">
        <CardContent className="p-8">
          <div className="text-center mb-6">
            <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <KeyRound className="w-7 h-7 text-primary" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight">Tenant Portal</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Sign in with your registered phone or email
            </p>
          </div>

          {error && (
            <Alert variant="destructive" className="mb-4 rounded-xl">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-semibold block mb-2">
                Phone or Email
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
                  placeholder="9876543210 or name@email.com"
                  className="h-12 pl-10 rounded-2xl"
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-semibold block mb-2">
                4-digit PIN
              </label>
              <Input
                type="password"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={4}
                required
                disabled={loading}
                value={pin}
                onChange={(e) =>
                  setPin(e.target.value.replace(/\D/g, "").slice(0, 4))
                }
                placeholder="• • • •"
                className="h-12 text-center text-2xl tracking-[0.6em] rounded-2xl font-mono"
              />
            </div>

            <Button
              type="submit"
              disabled={loading || pin.length !== 4 || !username.trim()}
              className="w-full h-12 rounded-2xl text-base"
            >
              {loading ? "Signing in…" : "Sign In"}
              {!loading && <ArrowRight className="w-4 h-4 ml-2" />}
            </Button>
          </form>

          <p className="text-xs text-center text-muted-foreground mt-6 leading-relaxed">
            This is a generic portal login. If you received a QR code from your landlord, scan it for direct access.
          </p>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}
