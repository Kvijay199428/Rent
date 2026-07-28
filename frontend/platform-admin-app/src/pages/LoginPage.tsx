import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import AuthLayout from "../components/AuthLayout";

export default function LoginPage() {
  const { login, loginTOTP } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [totpRequired, setTotpRequired] = useState(false);
  const [totpCode, setTotpCode] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = await login(username, password, rememberMe);
      if (result.requires_totp) {
        setTotpRequired(true);
      } else {
        navigate("/dashboard", { replace: true });
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleTOTPSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await loginTOTP(totpCode);
      navigate("/dashboard", { replace: true });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "TOTP verification failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout>
      <form
        onSubmit={totpRequired ? handleTOTPSubmit : handleSubmit}
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
            {totpRequired ? "Enter your 6-digit authenticator code" : "Sign in to manage landlords"}
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
          <label style={{ display: "block", marginBottom: 24 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>
              Authenticator Code
            </span>
            <input
              type="text"
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
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
          {busy ? (totpRequired ? "Verifying…" : "Signing in…") : (totpRequired ? "Verify" : "Sign In")}
        </button>

        {totpRequired && (
          <button
            type="button"
            onClick={() => { setTotpRequired(false); setTotpCode(""); setError(null); }}
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
