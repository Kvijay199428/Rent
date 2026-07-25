import { useState, useEffect } from "react";
import Layout from "../components/Layout";
import { API_BASE } from "../lib/runtime";

interface Profile {
  id: number;
  username: string;
  email: string | null;
  is_platform_admin: boolean;
  has_totp: boolean;
  created_at: string;
  updated_at: string;
}

export default function SettingsPage() {
  const [profile, setProfile] = useState<Profile | null>(null);

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [saveErr, setSaveErr] = useState<string | null>(null);

  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwSaving, setPwSaving] = useState(false);
  const [pwMsg, setPwMsg] = useState<string | null>(null);
  const [pwErr, setPwErr] = useState<string | null>(null);

  const [totpQr, setTotpQr] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/settings/profile`, { credentials: "include" })
      .then((r) => r.json())
      .then((p) => {
        setProfile(p);
        setUsername(p.username);
        setEmail(p.email ?? "");
      })
      .catch(() => {});
  }, []);

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveMsg(null);
    setSaveErr(null);
    try {
      const res = await fetch(`${API_BASE}/settings/profile`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Save failed" }));
        throw new Error(err.detail ?? "Save failed");
      }
      setSaveMsg("Profile updated successfully");
    } catch (err: unknown) {
      setSaveErr(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    if (newPw !== confirmPw) { setPwErr("Passwords do not match"); return; }
    setPwSaving(true);
    setPwMsg(null);
    setPwErr(null);
    try {
      const res = await fetch(`${API_BASE}/settings/change-password`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: currentPw, new_password: newPw, confirm_password: confirmPw }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Change failed" }));
        throw new Error(err.detail ?? "Change failed");
      }
      setPwMsg("Password changed successfully");
      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");
    } catch (err: unknown) {
      setPwErr(err instanceof Error ? err.message : "Change failed");
    } finally {
      setPwSaving(false);
    }
  }

  async function handleRegenerateTOTP() {
    setRegenerating(true);
    try {
      const res = await fetch(`${API_BASE}/totp-regenerate`, { method: "POST", credentials: "include" });
      if (!res.ok) throw new Error("Failed to regenerate");
      const data = await res.json();
      setTotpQr(data.qr_base64);
    } catch {
    } finally {
      setRegenerating(false);
    }
  }

  return (
    <Layout>
      <h1 style={{ margin: "0 0 24px", fontSize: 26, fontWeight: 700, color: "#1a1d2e" }}>Settings</h1>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, maxWidth: 900 }}>
        {/* Profile */}
        <form onSubmit={handleSaveProfile} style={{
          background: "#fff", borderRadius: 14, padding: "28px 32px",
          boxShadow: "0 2px 12px rgba(0,0,0,0.07)",
        }}>
          <h2 style={{ margin: "0 0 20px", fontSize: 17, fontWeight: 600, color: "#374151" }}>Profile</h2>

          {saveMsg && <div style={successStyle}>{saveMsg}</div>}
          {saveErr && <div style={errorStyle}>{saveErr}</div>}

          <label style={labelStyle}>
            <span>Username</span>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required style={inputStyle} />
          </label>
          <label style={labelStyle}>
            <span>Email</span>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} style={inputStyle} placeholder="admin@example.com" />
          </label>

          <div style={{ marginTop: 16, fontSize: 13, color: "#6b7280" }}>
            <div>ID: {profile?.id ?? "—"}</div>
            <div>Role: Platform Super Admin</div>
            {profile?.created_at && <div>Created: {new Date(profile.created_at).toLocaleString()}</div>}
          </div>

          <button type="submit" disabled={saving} style={primaryBtn}>
            {saving ? "Saving…" : "Save Changes"}
          </button>
        </form>

        {/* Password */}
        <form onSubmit={handleChangePassword} style={{
          background: "#fff", borderRadius: 14, padding: "28px 32px",
          boxShadow: "0 2px 12px rgba(0,0,0,0.07)",
        }}>
          <h2 style={{ margin: "0 0 20px", fontSize: 17, fontWeight: 600, color: "#374151" }}>Change Password</h2>

          {pwMsg && <div style={successStyle}>{pwMsg}</div>}
          {pwErr && <div style={errorStyle}>{pwErr}</div>}

          <label style={labelStyle}>
            <span>Current Password</span>
            <input type="password" value={currentPw} onChange={(e) => setCurrentPw(e.target.value)} required style={inputStyle} />
          </label>
          <label style={labelStyle}>
            <span>New Password</span>
            <input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} required minLength={6} style={inputStyle} />
          </label>
          <label style={labelStyle}>
            <span>Confirm New Password</span>
            <input type="password" value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} required minLength={6} style={inputStyle} />
          </label>

          <button type="submit" disabled={pwSaving} style={primaryBtn}>
            {pwSaving ? "Changing…" : "Change Password"}
          </button>
        </form>
      </div>

      {/* TOTP */}
      <div style={{
        background: "#fff", borderRadius: 14, padding: "28px 32px",
        boxShadow: "0 2px 12px rgba(0,0,0,0.07)", maxWidth: 900, marginTop: 20,
      }}>
        <h2 style={{ margin: "0 0 16px", fontSize: 17, fontWeight: 600, color: "#374151" }}>Two-Factor Authentication</h2>
        <p style={{ fontSize: 14, color: "#6b7280", marginBottom: 16 }}>
          {profile?.has_totp
            ? "TOTP is currently enabled. Regenerating will invalidate your current authenticator."
            : "TOTP is not configured. Regenerating will create a new secret and show the QR code."}
        </p>

        {totpQr && (
          <div style={{ marginBottom: 20, textAlign: "center" }}>
            <p style={{ fontSize: 13, color: "#374151", marginBottom: 8 }}>Scan this QR code with your authenticator app:</p>
            <img src={`data:image/png;base64,${totpQr}`} alt="TOTP QR Code" style={{ width: 200, height: 200, borderRadius: 8, border: "1px solid #e5e7eb" }} />
          </div>
        )}

        <button
          onClick={handleRegenerateTOTP}
          disabled={regenerating}
          style={{
            padding: "10px 20px", borderRadius: 8, border: "1.5px solid #d1d5db",
            background: regenerating ? "#f3f4f6" : "#fff",
            fontSize: 14, fontWeight: 600, cursor: regenerating ? "not-allowed" : "pointer",
          }}
        >
          {regenerating ? "Regenerating…" : "Regenerate TOTP Secret"}
        </button>
      </div>

      {/* System Info */}
      <div style={{
        background: "#fff", borderRadius: 14, padding: "28px 32px",
        boxShadow: "0 2px 12px rgba(0,0,0,0.07)", maxWidth: 900, marginTop: 20,
      }}>
        <h2 style={{ margin: "0 0 12px", fontSize: 17, fontWeight: 600, color: "#374151" }}>System Info</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <tbody>
            {[
              ["API Base", "/rent/platform-admin/api"],
              ["Frontend Base", "/rent/platform-admin"],
              ["Auth Scope", "Cookie: platform_access_token"],
            ].map(([label, value]) => (
              <tr key={label} style={{ borderBottom: "1px solid #f3f4f6" }}>
                <td style={{ padding: "12px 0", fontWeight: 600, color: "#6b7280", width: 160 }}>{label}</td>
                <td style={{ padding: "12px 0" }}><code style={{ background: "#f1f5f9", padding: "2px 8px", borderRadius: 6 }}>{value}</code></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "10px 12px", borderRadius: 8,
  border: "1.5px solid #d1d5db", fontSize: 14, outline: "none", boxSizing: "border-box",
};
const labelStyle: React.CSSProperties = {
  display: "block", marginBottom: 16,
};
const primaryBtn: React.CSSProperties = {
  marginTop: 8, padding: "10px 24px", borderRadius: 8, border: "none",
  background: "#3b4a6b", color: "#fff", fontSize: 14, fontWeight: 700, cursor: "pointer",
};
const successStyle: React.CSSProperties = {
  background: "#dcfce7", color: "#16a34a", padding: "10px 14px", borderRadius: 8, marginBottom: 16, fontSize: 13,
};
const errorStyle: React.CSSProperties = {
  background: "#fef2f2", color: "#dc2626", padding: "10px 14px", borderRadius: 8, marginBottom: 16, fontSize: 13,
};
