import { useState } from "react";
import { useNavigate } from "react-router";
import { Lock, ShieldCheck, Receipt, Users, ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import AuthLayout from "@/components/AuthLayout";
import { BrandWave } from "@shared/loading/BrandWave";
import { qrLoginByPin } from "@/lib/login-api";
import type { QrTenantProfile } from "@/types";

interface Props {
  tenant: QrTenantProfile;
  basePath: string;
}

export default function QrUnlockPage({ tenant, basePath }: Props) {
  const navigate = useNavigate();
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const firstName = tenant.name?.split(" ")[0] || "Tenant";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pin.length !== 4) return;

    setError("");
    setLoading(true);
    try {
      await qrLoginByPin(basePath, pin);
      window.location.reload();
    } catch (err: any) {
      setError(err.message || "Invalid PIN. Please try again.");
      setPin("");
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <Card className="w-full max-w-md rounded-3xl border shadow-xl">
        <CardContent className="p-8">
          <div className="text-center mb-6">
            <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <Lock className="w-7 h-7 text-primary" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight">
              Welcome, {firstName}
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Enter your 4-digit PIN to unlock your portal
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-6">
            <div className="rounded-2xl bg-muted p-3 text-center">
              <Receipt className="w-4 h-4 mx-auto mb-1 text-primary" />
              <div className="text-[11px] font-medium text-muted-foreground">Bills</div>
            </div>
            <div className="rounded-2xl bg-muted p-3 text-center">
              <Users className="w-4 h-4 mx-auto mb-1 text-primary" />
              <div className="text-[11px] font-medium text-muted-foreground">Occupants</div>
            </div>
            <div className="rounded-2xl bg-muted p-3 text-center">
              <ShieldCheck className="w-4 h-4 mx-auto mb-1 text-primary" />
              <div className="text-[11px] font-medium text-muted-foreground">Secure</div>
            </div>
          </div>

          {error && (
            <Alert variant="destructive" className="mb-4 rounded-xl">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-semibold block mb-2">
                4-digit PIN
              </label>
              <Input
                type="password"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={4}
                autoFocus
                required
                disabled={loading}
                value={pin}
                onChange={(e) =>
                  setPin(e.target.value.replace(/\D/g, "").slice(0, 4))
                }
                placeholder="• • • •"
                className="h-14 text-center text-2xl tracking-[0.6em] rounded-2xl font-mono"
              />
            </div>

            <Button
              type="submit"
              disabled={loading || pin.length !== 4}
              className="w-full h-12 rounded-2xl text-base"
            >
              {loading ? <BrandWave size="sm" label="Unlocking…" /> : <>Unlock Portal <ArrowRight className="w-4 h-4 ml-2" /></>}
            </Button>
          </form>

          <p className="text-xs text-center text-muted-foreground mt-5 leading-relaxed">
            Your rent receipts and occupant KYC are shown only after PIN verification.
          </p>

          <div className="mt-6 pt-4 border-t text-center">
            <Button
              type="button"
              variant="ghost"
              disabled={loading}
              className="w-full h-11 rounded-2xl text-sm"
              onClick={() => {
                sessionStorage.setItem("tenantLoginMode", "credentials");
                navigate("/tenant/login", { replace: true });
              }}
            >
              Login with username instead
            </Button>
          </div>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}
