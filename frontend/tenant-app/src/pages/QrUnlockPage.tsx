import { useState, useRef } from "react";
import { useNavigate } from "react-router";
import { Lock, ShieldCheck, Receipt, Users, ArrowRight, AlertTriangle, Send } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import AuthLayout from "@/components/AuthLayout";
import LoadingOverlay from "@shared/loading/LoadingOverlay";
import { qrLoginByPin, submitQrFeedback } from "@/lib/login-api";
import type { QrTenantProfile } from "@/types";

interface Props {
  tenant: QrTenantProfile;
  basePath: string;
}

const MAX_FAILURES_BEFORE_FEEDBACK = 2;

function collectDiagnostics(qrKey: string, attempts: number): Record<string, unknown> {
  const nav = typeof navigator !== "undefined" ? navigator : ({} as Navigator);
  const con = (nav as any)?.connection;
  return {
    url: typeof window !== "undefined" ? window.location.href : "",
    pathname: typeof window !== "undefined" ? window.location.pathname : "",
    qr_key: qrKey,
    attempts,
    user_agent: nav.userAgent || "",
    platform: nav.platform || "",
    language: nav.language || "",
    languages: Array.isArray(nav.languages) ? nav.languages : [],
    screen: typeof window !== "undefined" && window.screen
      ? { width: window.screen.width, height: window.screen.height }
      : {},
    viewport:
      typeof window !== "undefined"
        ? { width: window.innerWidth, height: window.innerHeight }
        : {},
    online: typeof nav !== "undefined" ? nav.onLine : null,
    connection: con
      ? {
          effectiveType: con.effectiveType ?? null,
          downlink: con.downlink ?? null,
          rtt: con.rtt ?? null,
        }
      : {},
  };
}

export default function QrUnlockPage({ tenant, basePath }: Props) {
  const navigate = useNavigate();
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [feedbackDone, setFeedbackDone] = useState(false);
  const [feedbackError, setFeedbackError] = useState("");
  const consecutiveFailures = useRef(0);

  const firstName = tenant.name?.split(" ")[0] || "Tenant";

  const qrKey = new URLSearchParams(window.location.search).get("qr_key") || "";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pin.length !== 4) return;

    setError("");
    setLoading(true);
    try {
      // Hold the PROPAURA loading animation for at least 5 seconds while the
      // server validates the QR key — no countdown, just the brand overlay.
      await Promise.all([
        qrLoginByPin(basePath, pin),
        new Promise((resolve) => setTimeout(resolve, 5000)),
      ]);
      window.location.reload();
    } catch (err: any) {
      consecutiveFailures.current += 1;
      setError(err.message || "wrong qrKey or pin rescan the qr");
      setPin("");
      setLoading(false);
      if (consecutiveFailures.current >= MAX_FAILURES_BEFORE_FEEDBACK) {
        consecutiveFailures.current = 0;
        setFeedbackDone(false);
        setFeedbackError("");
        setFeedbackMessage("");
        setShowFeedback(true);
      }
    }
  };

  const handleSubmitFeedback = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFeedbackError("");
    try {
      await submitQrFeedback(basePath, {
        message: feedbackMessage,
        qr_key: qrKey,
        diagnostics: collectDiagnostics(qrKey, MAX_FAILURES_BEFORE_FEEDBACK),
      });
      setFeedbackDone(true);
    } catch (err: any) {
      setFeedbackError(err.message || "Could not submit feedback. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
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
              Unlock Portal <ArrowRight className="w-4 h-4 ml-2" />
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
      {loading && <LoadingOverlay label="Unlocking…" />}

      <Dialog open={showFeedback} onOpenChange={(open) => { if (!submitting) setShowFeedback(open); }}>
        <DialogContent className="max-w-md rounded-3xl">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-amber-100 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-6 h-6 text-amber-600" />
              </div>
              <div>
                <DialogTitle className="text-lg">This QR key looks invalid</DialogTitle>
                <DialogDescription className="mt-1 text-sm">
                  Your QR key did not unlock after several tries. Report it to the
                  admin so they can issue a fix.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {feedbackDone ? (
            <div className="space-y-4">
              <Alert className="rounded-xl">
                <AlertDescription>
                  Feedback submitted. The admin will review and fix your QR link. Please try again later.
                </AlertDescription>
              </Alert>
              <Button
                className="w-full h-11 rounded-2xl"
                onClick={() => setShowFeedback(false)}
              >
                Close
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmitFeedback} className="space-y-4">
              <label className="block">
                <span className="text-sm font-semibold block mb-2">
                  Anything we should know? (optional)
                </span>
                <textarea
                  value={feedbackMessage}
                  onChange={(e) => setFeedbackMessage(e.target.value.slice(0, 2000))}
                  placeholder="e.g. My QR stopped working after the update…"
                  rows={3}
                  className="w-full rounded-2xl border bg-muted/30 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary resize-none"
                />
              </label>

              {feedbackError && (
                <Alert variant="destructive" className="rounded-xl">
                  <AlertDescription>{feedbackError}</AlertDescription>
                </Alert>
              )}

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="ghost"
                  disabled={submitting}
                  className="h-11 rounded-2xl flex-1"
                  onClick={() => setShowFeedback(false)}
                >
                  Not now
                </Button>
                <Button
                  type="submit"
                  disabled={submitting}
                  className="h-11 rounded-2xl flex-1 gap-2"
                >
                  <Send className="w-4 h-4" />
                  {submitting ? "Sending…" : "Report to Admin"}
                </Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
