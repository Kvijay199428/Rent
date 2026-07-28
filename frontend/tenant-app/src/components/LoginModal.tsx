import { useState } from "react";
import { Lock, ShieldCheck, Receipt, Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import AuthLayout from "./AuthLayout";

export default function LoginModal({
  tenantName,
  onSubmit,
  error,
  loading,
}: {
  tenantName: string;
  onSubmit: (pin: string) => void;
  error?: string;
  loading: boolean;
}) {
  const [pin, setPin] = useState("");

  return (
    <AuthLayout>
      <Card className="w-full max-w-md rounded-3xl border-0 shadow-xl">
        <CardContent className="p-8">
          <div className="text-center mb-6">
            <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <Lock className="w-7 h-7 text-primary" />
            </div>
            <h1 className="text-2xl font-bold">Tenant Portal</h1>
            <p className="text-muted-foreground mt-2">{tenantName}</p>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-6">
            <div className="rounded-2xl bg-muted p-3 text-center">
              <Receipt className="w-4 h-4 mx-auto mb-1 text-primary" />
              <div className="text-xs text-muted-foreground">Bills</div>
            </div>
            <div className="rounded-2xl bg-muted p-3 text-center">
              <Users className="w-4 h-4 mx-auto mb-1 text-primary" />
              <div className="text-xs text-muted-foreground">Occupants</div>
            </div>
            <div className="rounded-2xl bg-muted p-3 text-center">
              <ShieldCheck className="w-4 h-4 mx-auto mb-1 text-primary" />
              <div className="text-xs text-muted-foreground">Secure</div>
            </div>
          </div>

          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (pin.length === 4) onSubmit(pin);
            }}
            className="space-y-4"
          >
            <div>
              <label className="text-sm font-medium block mb-2">
                Enter 4-digit PIN
              </label>
              <Input
                type="password"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={4}
                autoFocus
                required
                value={pin}
                onChange={(e) =>
                  setPin(e.target.value.replace(/\D/g, "").slice(0, 4))
                }
                placeholder="••••"
                className="h-14 text-center text-2xl tracking-[0.5em] rounded-2xl"
              />
            </div>

            <Button
              type="submit"
              disabled={loading || pin.length !== 4}
              className="w-full h-12 rounded-2xl"
            >
              {loading ? "Unlocking..." : "Unlock Portal"}
            </Button>

            <p className="text-xs text-center text-muted-foreground">
              Your bills and occupant KYC are shown only after PIN verification.
            </p>

            <div className="text-center pt-2 border-t">
              <a
                href="/rent/tenant/login"
                className="text-xs font-medium text-primary hover:underline"
              >
                Login with phone / email
              </a>
            </div>
          </form>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}
