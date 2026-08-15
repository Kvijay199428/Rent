import { useState, useEffect, type FormEvent } from "react";
import { useNavigate, Link } from "react-router";
import { useAuth, OtpCooldownError } from "../contexts/AuthContext";
import AuthLayout from "../components/AuthLayout";
import LoadingOverlay from "@shared/loading/LoadingOverlay";
import { API_BASE } from "../lib/runtime";

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
        style={{
          background: "#fff", borderRadius: 16, padding: "40px 36px",
          width: 360, boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>{totpRequired ? "🔐" : "🏢"}</div>
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: "#1a1d2e" }}>
            {totpRequired ? "Two-Factor Authentication" : "Platform Admin"}
          </h1>
          <p style={{ margin: "6px 0 0", fontSize: 13, color: "#6b7280" }}>
            {totpRequired ? "Verify your identity to continue" : "Sign in to manage landlords"}
          </p>
        </div>

        {error && (
          <div style={{
            background: "#fef2f2", border: "1px solid #fca5a5", color: "#dc2626",
            borderRadius: 8, padding: "10px 14px", marginBottom: 18, fontSize: 13,
          }}>
            {error}
          </div>
        )}

        {otpMsg && (
          <div style={{
            background: "#eff6ff", border: "1px solid #bfdbfe", color: "#1d4ed8",
            borderRadius: 8, padding: "10px 14px", marginBottom: 18, fontSize: 13,
          }}>
            {otpMsg}
          </div>
        )}

        {!totpRequired ? (
          <>
            <label style={{ display: "block", marginBottom: 16 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>
                Username
              </span>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                style={inputStyle}
                placeholder="admin"
              />
            </label>

            <label style={{ display: "block", marginBottom: 16 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>
                Password
              </span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={inputStyle}
                placeholder="••••••••"
              />
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 24, fontSize: 13, color: "#374151", cursor: "pointer" }}>
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
              <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                <button
                  type="button"
                  onClick={() => setMethod("totp")}
                  style={{
                    flex: 1, padding: "9px 0", borderRadius: 8, border: "1.5px solid",
                    borderColor: method === "totp" ? "#3b4a6b" : "#d1d5db",
                    background: method === "totp" ? "#eef2f7" : "#fff",
                    color: method === "totp" ? "#3b4a6b" : "#6b7280",
                    fontSize: 13, fontWeight: 600, cursor: "pointer",
                  }}
                >
                  Authenticator
                </button>
                <button
                  type="button"
                  onClick={() => setMethod("telegram")}
                  style={{
                    flex: 1, padding: "9px 0", borderRadius: 8, border: "1.5px solid",
                    borderColor: method === "telegram" ? "#3b4a6b" : "#d1d5db",
                    background: method === "telegram" ? "#eef2f7" : "#fff",
                    color: method === "telegram" ? "#3b4a6b" : "#6b7280",
                    fontSize: 13, fontWeight: 600, cursor: "pointer",
                  }}
                >
                  Telegram OTP
                </button>
              </div>
            )}

            {useTelegram() ? (
              <>
                {!otpSent ? (
                  <button
                    type="button"
                    onClick={handleSendOtp}
                    disabled={sending}
                    style={{
                      width: "100%", padding: "12px 0", borderRadius: 8, border: "none",
                      background: "#3b4a6b", color: "#fff",
                      fontSize: 15, fontWeight: 700, cursor: sending ? "not-allowed" : "pointer",
                      transition: "background 0.2s", marginBottom: 16,
                    }}
                  >
                    Send code via Telegram
                  </button>
                ) : (
                  <>
                    <label style={{ display: "block", marginBottom: 16 }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>
                        Telegram Code
                      </span>
                      <input
                        type="text"
                        value={code}
                        onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                        required
                        autoFocus
                        maxLength={6}
                        pattern="[0-9]{6}"
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        style={{ ...inputStyle, textAlign: "center", fontSize: 24, letterSpacing: 8 }}
                        placeholder="000000"
                      />
                    </label>
                    {cooldown > 0 ? (
                      <p style={{
                        margin: 0, textAlign: "center", fontSize: 13, color: "#6b7280", marginBottom: 16,
                      }}>
                        Resend available in {formatCountdown(cooldown)}
                      </p>
                    ) : (
                      <button
                        type="button"
                        onClick={handleSendOtp}
                        style={{
                          width: "100%", padding: "12px 0", borderRadius: 8, border: "none",
                          background: "#3b4a6b", color: "#fff",
                          fontSize: 15, fontWeight: 700, cursor: "pointer",
                          transition: "background 0.2s", marginBottom: 16,
                        }}
                      >
                        Resend OTP
                      </button>
                    )}
                  </>
                )}
              </>
            ) : (
              <label style={{ display: "block", marginBottom: 24 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>
                  Authenticator Code
                </span>
                <input
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  required
                  autoFocus
                  maxLength={6}
                  pattern="[0-9]{6}"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  style={{ ...inputStyle, textAlign: "center", fontSize: 24, letterSpacing: 8 }}
                  placeholder="000000"
                />
              </label>
            )}
          </>
        )}

        {!(totpRequired && useTelegram() && !otpSent) && (
          <button
            type="submit"
            disabled={busy}
            style={{
              width: "100%", padding: "12px 0", borderRadius: 8, border: "none",
              background: busy ? "#9ca3af" : "#3b4a6b", color: "#fff",
              fontSize: 15, fontWeight: 700, cursor: busy ? "not-allowed" : "pointer",
              transition: "background 0.2s",
            }}
          >
            {totpRequired ? "Verify" : "Sign In"}
          </button>
        )}

        {totpRequired && (
          <button
            type="button"
            onClick={resetSecondFactor}
            style={{
              width: "100%", padding: "10px 0", borderRadius: 8, border: "1.5px solid #d1d5db",
              background: "transparent", color: "#6b7280",
              fontSize: 13, fontWeight: 600, cursor: "pointer", marginTop: 12,
            }}
          >
            Back to login
          </button>
        )}
      </form>
      </AuthLayout>
      {sending && <LoadingOverlay label="Sending code…" />}
      {!sending && busy && <LoadingOverlay label={totpRequired ? "Verifying…" : "Signing in…"} />}

      {pendingFeedback && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 200,
          background: "rgba(0,0,0,0.45)",
          display: "flex", alignItems: "center", justifyContent: "center",
          padding: 16,
        }}>
          <div style={{
            background: "#fff", borderRadius: 16, padding: "28px 24px",
            width: 460, maxWidth: "100%", maxHeight: "85vh", overflowY: "auto",
            boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
              <span style={{ fontSize: 26 }}>📬</span>
              <div>
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#1a1d2e" }}>
                  Pending QR Feedback
                </h2>
                <p style={{ margin: "2px 0 0", fontSize: 13, color: "#6b7280" }}>
                  Tenants reported a wrong QR key on the unlock screen.
                </p>
              </div>
            </div>

            {pendingFeedback.map((f) => (
              <div key={f.id} style={{
                padding: "12px 14px", borderRadius: 10, border: "1px solid #e5e7eb",
                background: "#f8fafc", marginBottom: 8,
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                  <strong style={{ fontSize: 13, color: "#1a1d2e" }}>{f.tenant_name || `Tenant #${f.id}`}</strong>
                  <span style={{ fontSize: 11, color: "#9ca3af" }}>
                    {new Date(f.created_at + "Z").toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
                  </span>
                </div>
                <p style={{ margin: "4px 0 0", fontSize: 13, color: "#374151" }}>
                  {f.message || <span style={{ color: "#9ca3af" }}>No message included.</span>}
                </p>
              </div>
            ))}

            <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
              <button
                onClick={() => setPendingFeedback(null)}
                style={{
                  flex: 1, padding: "10px 0", borderRadius: 8, border: "1.5px solid #d1d5db",
                  background: "#fff", color: "#6b7280", fontSize: 14, fontWeight: 600, cursor: "pointer",
                }}
              >
                Later
              </button>
              <Link
                to="/feedback"
                onClick={() => setPendingFeedback(null)}
                style={{
                  flex: 1, textAlign: "center", padding: "10px 0", borderRadius: 8, border: "none",
                  background: "#3b4a6b", color: "#fff", fontSize: 14, fontWeight: 700,
                  textDecoration: "none", display: "inline-block",
                }}
              >
                View Inbox
              </Link>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "10px 12px", borderRadius: 8,
  border: "1.5px solid #d1d5db", fontSize: 14, outline: "none",
  boxSizing: "border-box",
  transition: "border-color 0.15s",
};
