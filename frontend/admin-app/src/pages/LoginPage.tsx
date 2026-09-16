import { useState, useEffect, type FormEvent } from "react";
import { useNavigate, Link } from "react-router";
import { useAuth, OtpCooldownError } from "../contexts/AuthContext";
import AuthLayout from "../components/AuthLayout";
import LoadingOverlay from "@shared/loading/LoadingOverlay";
import useCapsLock from "@shared/capslock/useCapsLock";
import CapsLockWarning from "@shared/capslock/CapsLockWarning";
import { API_BASE } from "../lib/runtime";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Dialog,
  DialogContent,
} from "../components/ui/dialog";

type OtpMethod = "totp" | "telegram";

const COOLDOWN_SECONDS = 60;

function formatCountdown(s: number) {
  const m = Math.floor(s / 60);
  const ss = s % 60;
  return `${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
}

export default function LoginPage() {
  const { login, loginTOTP, loginOtpSend, loginOtpVerify } = useAuth();
  const navigate = useNavigate();
  const capsLockOn = useCapsLock();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [totpRequired, setTotpRequired] = useState(false);
  const [methods, setMethods] = useState<string[]>([]);
  const [method, setMethod] = useState<OtpMethod>("totp");
  const [code, setCode] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [otpMsg, setOtpMsg] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [pendingFeedback, setPendingFeedback] = useState<{
    id: number;
    tenant_name: string;
    message: string;
    created_at: string;
  }[] | null>(null);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => setCooldown((c) => Math.max(0, c - 1)), 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  function useTelegram() {
    return method === "telegram" && methods.includes("telegram_otp");
  }

  async function checkPendingFeedback(): Promise<number> {
    try {
      const res = await fetch(`${API_BASE}/feedback?status=open&limit=10`, { credentials: "include" });
      if (!res.ok) return 0;
      const data = await res.json();
      const total = data.total || 0;
      if (total > 0) setPendingFeedback((data.items || []).slice(0, 10));
      return total;
    } catch {
      // Non-critical — the dashboard banner still surfaces feedback.
      return 0;
    }
  }

  function resetSecondFactor() {
    setTotpRequired(false);
    setMethods([]);
    setMethod("totp");
    setCode("");
    setOtpSent(false);
    setOtpMsg(null);
    setCooldown(0);
    setError(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = await login(username, password, rememberMe);
      if (result.requires_totp) {
        const m = result.methods ?? ["totp"];
        setMethods(m);
        setMethod(m.includes("totp") ? "totp" : "telegram");
        setTotpRequired(true);
        if (m.length === 1 && m[0] === "telegram_otp") {
          handleSendOtp();
        }
      } else {
        const total = await checkPendingFeedback();
        if (total === 0) navigate("/dashboard", { replace: true });
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleCodeSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (useTelegram()) {
        await loginOtpVerify(code);
      } else {
        await loginTOTP(code);
      }
      const total = await checkPendingFeedback();
      if (total === 0) navigate("/dashboard", { replace: true });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleSendOtp() {
    setError(null);
    setSending(true);
    setOtpMsg(null);
    try {
      const res = await loginOtpSend();
      setOtpSent(true);
      setOtpMsg("Code sent to your Telegram. Check your chat and enter the code below.");
      setCooldown(res.cooldown_seconds ?? COOLDOWN_SECONDS);
    } catch (err) {
      if (err instanceof OtpCooldownError) {
        setOtpSent(true);
        setOtpMsg(null);
        setError(null);
        setCooldown(err.cooldownSeconds);
      } else {
        setError(err instanceof Error ? err.message : "Failed to send code");
      }
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <AuthLayout>
      <form
        onSubmit={totpRequired ? handleCodeSubmit : handleSubmit}
        className="motion-fade-up w-[360px] rounded-2xl bg-white p-9 shadow-[0_20px_60px_rgba(0,0,0,0.3)]"
      >
        <div className="mb-7 text-center">
          <div className="mb-2 text-[32px]">{totpRequired ? "🔐" : "🏢"}</div>
          <h1 className="m-0 text-xl font-bold text-[#1a1d2e]">
            {totpRequired ? "Two-Factor Authentication" : "Platform Admin"}
          </h1>
          <p className="mt-1.5 text-[13px] text-gray-500">
            {totpRequired ? "Verify your identity to continue" : "Sign in to manage landlords"}
          </p>
        </div>

        {error && (
          <div className="mb-[18px] rounded-lg border border-red-300 bg-red-50 px-3.5 py-2.5 text-[13px] text-red-600">
            {error}
          </div>
        )}

        {otpMsg && (
          <div className="mb-[18px] rounded-lg border border-blue-200 bg-blue-50 px-3.5 py-2.5 text-[13px] text-blue-700">
            {otpMsg}
          </div>
        )}

        <CapsLockWarning isCapsLockOn={capsLockOn} />

        {!totpRequired ? (
          <>
            <div className="mb-4">
              <Label htmlFor="username" className="mb-1.5 block text-[13px] font-semibold text-gray-700">
                Username
              </Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                placeholder="admin"
              />
            </div>

            <div className="mb-4">
              <Label htmlFor="password" className="mb-1.5 block text-[13px] font-semibold text-gray-700">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
              />
            </div>

            <label className="mb-6 flex cursor-pointer items-center gap-2 text-[13px] text-gray-700">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
              />
              Remember me for 180 days
            </label>
          </>
        ) : (
          <>
            {methods.length > 1 && (
              <div className="mb-4 flex gap-2">
                <button
                  type="button"
                  onClick={() => setMethod("totp")}
                  className={`flex-1 rounded-lg border-[1.5px] py-2.5 text-[13px] font-semibold transition-colors ${
                    method === "totp"
                      ? "border-[#3b4a6b] bg-[#eef2f7] text-[#3b4a6b]"
                      : "border-gray-300 bg-white text-gray-500 hover:bg-gray-50"
                  }`}
                >
                  Authenticator
                </button>
                <button
                  type="button"
                  onClick={() => setMethod("telegram")}
                  className={`flex-1 rounded-lg border-[1.5px] py-2.5 text-[13px] font-semibold transition-colors ${
                    method === "telegram"
                      ? "border-[#3b4a6b] bg-[#eef2f7] text-[#3b4a6b]"
                      : "border-gray-300 bg-white text-gray-500 hover:bg-gray-50"
                  }`}
                >
                  Telegram OTP
                </button>
              </div>
            )}

            {useTelegram() ? (
              <>
                {!otpSent ? (
                  <Button
                    type="button"
                    onClick={handleSendOtp}
                    disabled={sending}
                    className="mb-4 w-full bg-[#3b4a6b] py-3 text-[15px] font-bold text-white hover:bg-[#34405a] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    Send code via Telegram
                  </Button>
                ) : (
                  <>
                    <div className="mb-4">
                      <Label htmlFor="telegram-code" className="mb-1.5 block text-[13px] font-semibold text-gray-700">
                        Telegram Code
                      </Label>
                      <Input
                        id="telegram-code"
                        type="text"
                        value={code}
                        onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                        required
                        autoFocus
                        maxLength={6}
                        pattern="[0-9]{6}"
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        className="text-center text-2xl tracking-[8px]"
                        placeholder="000000"
                      />
                    </div>
                    {cooldown > 0 ? (
                      <p className="mb-4 text-center text-[13px] text-gray-500">
                        Resend available in {formatCountdown(cooldown)}
                      </p>
                    ) : (
                      <Button
                        type="button"
                        onClick={handleSendOtp}
                        className="mb-4 w-full bg-[#3b4a6b] py-3 text-[15px] font-bold text-white hover:bg-[#34405a]"
                      >
                        Resend OTP
                      </Button>
                    )}
                  </>
                )}
              </>
            ) : (
              <div className="mb-6">
                <Label htmlFor="auth-code" className="mb-1.5 block text-[13px] font-semibold text-gray-700">
                  Authenticator Code
                </Label>
                <Input
                  id="auth-code"
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  required
                  autoFocus
                  maxLength={6}
                  pattern="[0-9]{6}"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  className="text-center text-2xl tracking-[8px]"
                  placeholder="000000"
                />
              </div>
            )}
          </>
        )}

        {!(totpRequired && useTelegram() && !otpSent) && (
          <Button
            type="submit"
            disabled={busy}
            className={`w-full py-3 text-[15px] font-bold ${
              busy
                ? "cursor-not-allowed bg-gray-400 text-white hover:bg-gray-400"
                : "bg-[#3b4a6b] text-white hover:bg-[#34405a]"
            }`}
          >
            {totpRequired ? "Verify" : "Sign In"}
          </Button>
        )}

        {totpRequired && (
          <Button
            type="button"
            onClick={resetSecondFactor}
            variant="outline"
            className="mt-3 w-full text-[13px] font-semibold text-gray-500"
          >
            Back to login
          </Button>
        )}
      </form>
      </AuthLayout>
      {sending && <LoadingOverlay label="Sending code…" />}
      {!sending && busy && <LoadingOverlay label={totpRequired ? "Verifying…" : "Signing in…"} />}

      <Dialog
        open={pendingFeedback !== null}
        onOpenChange={(open) => {
          if (!open) setPendingFeedback(null);
        }}
      >
        <DialogContent className="max-h-[85vh] max-w-[460px] overflow-y-auto">
          <div className="mb-4 flex items-center gap-2.5">
            <span className="text-[26px]">📬</span>
            <div>
              <h2 className="m-0 text-lg font-bold text-[#1a1d2e]">
                Pending QR Feedback
              </h2>
              <p className="mt-0.5 text-[13px] text-gray-500">
                Tenants reported a wrong QR key on the unlock screen.
              </p>
            </div>
          </div>

          {pendingFeedback?.map((f) => (
            <div key={f.id} className="mb-2 rounded-[10px] border border-gray-200 bg-slate-50 p-3.5">
              <div className="flex flex-wrap justify-between gap-2">
                <strong className="text-[13px] text-[#1a1d2e]">{f.tenant_name || `Tenant #${f.id}`}</strong>
                <span className="text-[11px] text-gray-400">
                  {new Date(f.created_at + "Z").toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
                </span>
              </div>
              <p className="mt-1 text-[13px] text-gray-700">
                {f.message || <span className="text-gray-400">No message included.</span>}
              </p>
            </div>
          ))}

          <div className="mt-[18px] flex gap-2.5">
            <Button
              variant="outline"
              onClick={() => setPendingFeedback(null)}
              className="flex-1 text-sm font-semibold text-gray-500"
            >
              Later
            </Button>
            <Button asChild className="flex-1 bg-[#3b4a6b] text-sm font-bold text-white hover:bg-[#34405a]">
              <Link to="/feedback" onClick={() => setPendingFeedback(null)}>
                View Inbox
              </Link>
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}