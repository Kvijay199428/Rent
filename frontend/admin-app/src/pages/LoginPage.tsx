import { useState, useEffect, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { useAuth, OtpCooldownError } from "../contexts/AuthContext";
import AuthLayout from "../components/AuthLayout";
import BrandWave from "@shared/loading/BrandWave";

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

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => setCooldown((c) => Math.max(0, c - 1)), 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  function useTelegram() {
    return method === "telegram" && methods.includes("telegram_otp");
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
        navigate("/dashboard", { replace: true });
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
      navigate("/dashboard", { replace: true });
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
                  sending ? (
                    <div style={{ padding: "14px 0", marginBottom: 16 }}>
                      <BrandWave stacked label="Sending code…" />
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={handleSendOtp}
                      disabled={sending}
                      style={{
                        width: "100%", padding: "12px 0", borderRadius: 8, border: "none",
                        background: "#3b4a6b", color: "#fff",
                        fontSize: 15, fontWeight: 700, cursor: "pointer",
                        transition: "background 0.2s", marginBottom: 16,
                      }}
                    >
                      Send code via Telegram
                    </button>
                  )
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
                    {sending ? (
                      <div style={{ padding: "14px 0", marginBottom: 16 }}>
                        <BrandWave stacked label="Sending code…" />
                      </div>
                    ) : cooldown > 0 ? (
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
          busy ? (
            <div style={{ padding: "14px 0", marginBottom: 16 }}>
              <BrandWave stacked label={totpRequired ? "Verifying…" : "Signing in…"} />
            </div>
          ) : (
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
          )
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
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "10px 12px", borderRadius: 8,
  border: "1.5px solid #d1d5db", fontSize: 14, outline: "none",
  boxSizing: "border-box",
  transition: "border-color 0.15s",
};
