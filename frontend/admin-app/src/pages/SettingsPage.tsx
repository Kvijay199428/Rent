import { useState, useEffect } from "react";
import Layout from "../components/Layout";
import { fetchApi } from "../api/client";
import { useHealthStream } from "../hooks/useHealthStream";

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
  const health = useHealthStream();
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

  const [retentionDays, setRetentionDays] = useState(30);
  const [auditSaving, setAuditSaving] = useState(false);
  const [auditMsg, setAuditMsg] = useState<string | null>(null);
  const [auditErr, setAuditErr] = useState<string | null>(null);

  const [totpQr, setTotpQr] = useState<string | null>(null);
  const [totpSecret, setTotpSecret] = useState<string | null>(null);
  const [totpPassword, setTotpPassword] = useState("");
  const [totpAction, setTotpAction] = useState<"setup" | "regenerate">("setup");
  const [totpBusy, setTotpBusy] = useState(false);
  const [totpErr, setTotpErr] = useState<string | null>(null);
  const [totpSuccess, setTotpSuccess] = useState<string | null>(null);
  const [showTotpDialog, setShowTotpDialog] = useState(false);
  const [showPwText, setShowPwText] = useState(false);
  const [showTotpSecret, setShowTotpSecret] = useState(false);

  const [tgBotConfigured, setTgBotConfigured] = useState(false);
  const [tgChatLinked, setTgChatLinked] = useState(false);
  const [tgChatMasked, setTgChatMasked] = useState<string | null>(null);
  const [tgBusy, setTgBusy] = useState(false);
  const [tgMsg, setTgMsg] = useState<string | null>(null);
  const [tgErr, setTgErr] = useState<string | null>(null);

  useEffect(() => {
    fetchApi("/settings/profile")
      .then((r) => r.json())
      .then((p) => {
        setProfile(p);
        setUsername(p.username);
        setEmail(p.email ?? "");
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchApi("/settings/audit")
      .then((r) => r.json())
      .then((d) => { if (d.retention_days) setRetentionDays(d.retention_days); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchApi("/settings/telegram/status")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d) {
          setTgBotConfigured(!!d.bot_configured);
          setTgChatLinked(!!d.chat_linked);
          setTgChatMasked(d.chat_id_masked ?? null);
        }
      })
      .catch(() => {});
  }, []);

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveMsg(null);
    setSaveErr(null);
    try {
      const res = await fetchApi("/settings/profile", {
        method: "PUT",
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
      const res = await fetchApi("/settings/change-password", {
        method: "POST",
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

  function openTotpDialog(action: "setup" | "regenerate") {
    setTotpAction(action);
    setTotpPassword("");
    setTotpErr(null);
    setTotpSuccess(null);
    setShowTotpDialog(true);
  }

  async function handleShowTotpQr() {
    setTotpErr(null);
    if (totpQr) {
      setTotpQr(null);
      setTotpSecret(null);
      return;
    }
    try {
      const res = await fetchApi("/auth/totp-qr");
      if (!res.ok) throw new Error("Failed to load QR");
      const data = await res.json();
      if (data.qr_code_base64) { setTotpQr(data.qr_code_base64); setTotpSecret(data.secret ?? null); }
    } catch {
      setTotpErr("Failed to load TOTP QR code.");
    }
  }

  async function handleTotpConfirm() {
    if (!totpPassword) return;
    setTotpBusy(true);
    setTotpErr(null);
    setTotpSuccess(null);
    try {
      const res = await fetchApi("/auth/totp-regenerate", {
        method: "POST",
        body: JSON.stringify({ current_password: totpPassword }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Operation failed" }));
        throw new Error(err.detail ?? "Operation failed");
      }
      const data = await res.json();
      if (data.qr_code_base64) { setTotpQr(data.qr_code_base64); setTotpSecret(data.secret ?? null); }
      setTotpSuccess(totpAction === "setup" ? "TOTP configured successfully! Scan the QR code with your authenticator app." : "TOTP secret regenerated! Update your authenticator app.");
      setShowTotpDialog(false);
      setTotpPassword("");
      // Refresh profile to update has_totp
      const pRes = await fetchApi("/settings/profile");
      if (pRes.ok) {
        const p = await pRes.json();
        setProfile(p);
      }
    } catch (err: unknown) {
      setTotpErr(err instanceof Error ? err.message : "Operation failed");
    } finally {
      setTotpBusy(false);
    }
  }

  async function handleSaveAudit(e: React.FormEvent) {
    e.preventDefault();
    setAuditSaving(true);
    setAuditMsg(null);
    setAuditErr(null);
    try {
      const res = await fetchApi("/settings/audit", {
        method: "PUT",
        body: JSON.stringify({ retention_days: retentionDays }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Save failed" }));
        throw new Error(err.detail ?? "Save failed");
      }
      setAuditMsg("Audit log retention updated successfully.");
    } catch (err: unknown) {
      setAuditErr(err instanceof Error ? err.message : "Save failed");
    } finally {
      setAuditSaving(false);
    }
  }

  async function handleTgAction(action: "link" | "unlink" | "test") {
    setTgBusy(true);
    setTgMsg(null);
    setTgErr(null);
    try {
      const res = await fetchApi(`/settings/telegram/${action}`, {
        method: "POST",
      });
      const data = await res.json().catch(() => ({ detail: "Operation failed" }));
      if (!res.ok) {
        throw new Error(data.detail ?? "Operation failed");
      }
      setTgMsg(data.message ?? "Done.");
      if (action === "link") setTgChatMasked(data.chat_id_masked ?? null);
      if (action === "unlink") setTgChatMasked(null);
      setTgChatLinked(action !== "unlink");
      setTgBotConfigured(true);
    } catch (err: unknown) {
      setTgErr(err instanceof Error ? err.message : "Operation failed");
    } finally {
      setTgBusy(false);
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
            ? "TOTP is currently enabled. You must enter a verification code after your password to login."
            : "Two-factor authentication adds an extra layer of security to your account."}
        </p>

        {totpErr && <div style={errorStyle}>{totpErr}</div>}
        {totpSuccess && <div style={successStyle}>{totpSuccess}</div>}

        {totpQr && (
          <div style={{ marginBottom: 20, textAlign: "center" }}>
            <p style={{ fontSize: 13, color: "#374151", marginBottom: 8 }}>Scan this QR code with your authenticator app:</p>
            <img src={`data:image/png;base64,${totpQr}`} alt="TOTP QR Code" style={{ width: 200, height: 200, borderRadius: 8, border: "1px solid #e5e7eb" }} />
          </div>
        )}

        {totpSecret && (
          <div style={{ marginBottom: 20 }}>
            <p style={{ fontSize: 13, color: "#374151", marginBottom: 6, fontWeight: 600 }}>TOTP Secret (Manual Entry)</p>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{
                flex: 1, padding: "10px 12px", borderRadius: 8,
                border: "1.5px solid #d1d5db", fontFamily: "monospace", fontSize: 14,
                background: "#f9fafb", wordBreak: "break-all",
              }}>
                {showTotpSecret ? totpSecret : "•".repeat(totpSecret.length)}
              </div>
              <button
                type="button"
                onClick={() => setShowTotpSecret(!showTotpSecret)}
                style={{
                  padding: "8px 14px", borderRadius: 8, border: "1.5px solid #d1d5db",
                  background: "#fff", fontSize: 13, fontWeight: 600, cursor: "pointer",
                  whiteSpace: "nowrap",
                }}
              >
                {showTotpSecret ? "Hide" : "Show"}
              </button>
              <button
                type="button"
                onClick={() => { navigator.clipboard.writeText(totpSecret); }}
                style={{
                  padding: "8px 14px", borderRadius: 8, border: "1.5px solid #d1d5db",
                  background: "#fff", fontSize: 13, fontWeight: 600, cursor: "pointer",
                  whiteSpace: "nowrap",
                }}
              >
                Copy
              </button>
            </div>
          </div>
        )}

        <div style={{ display: "flex", gap: 10 }}>
          {profile?.has_totp && (
            <button
              onClick={handleShowTotpQr}
              style={{
                padding: "10px 20px", borderRadius: 8, border: "1.5px solid #d1d5db",
                background: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer",
              }}
            >
              {totpQr ? "Hide TOTP QR" : "Show TOTP QR"}
            </button>
          )}
          <button
            onClick={() => openTotpDialog(profile?.has_totp ? "regenerate" : "setup")}
            style={{
              padding: "10px 20px", borderRadius: 8,
              border: profile?.has_totp ? "1.5px solid #fca5a5" : "1.5px solid #d1d5db",
              background: profile?.has_totp ? "#fef2f2" : "#fff",
              color: profile?.has_totp ? "#dc2626" : "#374151",
              fontSize: 14, fontWeight: 600, cursor: "pointer",
            }}
          >
            {profile?.has_totp ? "Regenerate TOTP Secret" : "Set Up TOTP"}
          </button>
        </div>
      </div>

      {/* Telegram OTP */}
      <div style={{
        background: "#fff", borderRadius: 14, padding: "28px 32px",
        boxShadow: "0 2px 12px rgba(0,0,0,0.07)", maxWidth: 900, marginTop: 20,
      }}>
        <h2 style={{ margin: "0 0 12px", fontSize: 17, fontWeight: 600, color: "#374151" }}>Telegram OTP Login</h2>
        <p style={{ fontSize: 14, color: "#6b7280", marginBottom: 16 }}>
          Receive a one-time login code in Telegram as an alternative to your authenticator app.
        </p>

        {tgErr && <div style={errorStyle}>{tgErr}</div>}
        {tgMsg && <div style={successStyle}>{tgMsg}</div>}

        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 16, fontSize: 13 }}>
          <div>
            Bot configured:{" "}
            <strong style={{ color: tgBotConfigured ? "#16a34a" : "#dc2626" }}>
              {tgBotConfigured ? "Yes" : "No"}
            </strong>
            {!tgBotConfigured && " — add TELEGRAM_BOT_TOKEN to the backend .env and redeploy."}
          </div>
          <div>
            Telegram chat linked:{" "}
            <strong style={{ color: tgChatLinked ? "#16a34a" : "#6b7280" }}>
              {tgChatLinked ? (tgChatMasked ? `Yes (${tgChatMasked})` : "Yes") : "No"}
            </strong>
          </div>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
          <button
            onClick={() => handleTgAction("link")}
            disabled={tgBusy || !tgBotConfigured}
            style={{
              padding: "10px 20px", borderRadius: 8, border: "1.5px solid #d1d5db",
              background: tgBusy || !tgBotConfigured ? "#f3f4f6" : "#fff",
              color: tgBusy || !tgBotConfigured ? "#9ca3af" : "#374151",
              fontSize: 14, fontWeight: 600, cursor: tgBusy || !tgBotConfigured ? "not-allowed" : "pointer",
            }}
          >
            {tgBusy ? "Working…" : "Link Telegram"}
          </button>
          {tgChatLinked && (
            <>
              <button
                onClick={() => handleTgAction("test")}
                disabled={tgBusy}
                style={{
                  padding: "10px 20px", borderRadius: 8, border: "1.5px solid #d1d5db",
                  background: "#fff", fontSize: 14, fontWeight: 600, cursor: tgBusy ? "not-allowed" : "pointer",
                }}
              >
                Send Test Message
              </button>
              <button
                onClick={() => handleTgAction("unlink")}
                disabled={tgBusy}
                style={{
                  padding: "10px 20px", borderRadius: 8, border: "1.5px solid #fca5a5",
                  background: "#fef2f2", color: "#dc2626",
                  fontSize: 14, fontWeight: 600, cursor: tgBusy ? "not-allowed" : "pointer",
                }}
              >
                Unlink
              </button>
            </>
          )}
        </div>
        {tgBotConfigured && !tgChatLinked && (
          <p style={{ margin: "12px 0 0", fontSize: 12, color: "#9ca3af" }}>
            Open <strong>@propauraBot</strong> on your Telegram, send{" "}
            <strong>/start</strong>, then click <strong>Link Telegram</strong> above to capture your chat.
          </p>
        )}
      </div>

      {/* Password Confirmation Dialog */}
      {showTotpDialog && (
        <div style={overlayStyle} onClick={() => setShowTotpDialog(false)}>
          <div style={dialogStyle} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ margin: "0 0 8px", fontSize: 16, fontWeight: 700, color: "#1a1d2e" }}>
              {totpAction === "setup" ? "Set Up Two-Factor Authentication" : "Regenerate TOTP Secret"}
            </h3>
            <p style={{ fontSize: 13, color: "#6b7280", marginBottom: 16 }}>
              {totpAction === "setup"
                ? "Enter your current password to set up TOTP for your account."
                : "Enter your current password to regenerate your TOTP secret. Your old authenticator codes will stop working."}
            </p>
            {totpErr && <div style={errorStyle}>{totpErr}</div>}
            <label style={{ display: "block", marginBottom: 16 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "#374151", display: "block", marginBottom: 6 }}>Current Password</span>
              <div style={{ position: "relative" }}>
                <input
                  type={showPwText ? "text" : "password"}
                  value={totpPassword}
                  onChange={(e) => setTotpPassword(e.target.value)}
                  placeholder="Enter your password"
                  autoFocus
                  onKeyDown={(e) => { if (e.key === "Enter") handleTotpConfirm(); }}
                  style={inputStyle}
                />
                <button
                  type="button"
                  onClick={() => setShowPwText(!showPwText)}
                  style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "#6b7280", fontSize: 13 }}
                >
                  {showPwText ? "Hide" : "Show"}
                </button>
              </div>
            </label>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button
                onClick={() => { setShowTotpDialog(false); setTotpPassword(""); setTotpErr(null); }}
                style={{ padding: "8px 16px", borderRadius: 8, border: "1.5px solid #d1d5db", background: "#fff", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                onClick={handleTotpConfirm}
                disabled={totpBusy || !totpPassword}
                style={{
                  padding: "8px 16px", borderRadius: 8, border: "none",
                  background: totpBusy || !totpPassword ? "#9ca3af" : totpAction === "regenerate" ? "#dc2626" : "#3b4a6b",
                  color: "#fff", fontSize: 13, fontWeight: 700,
                  cursor: totpBusy || !totpPassword ? "not-allowed" : "pointer",
                }}
              >
                {totpBusy ? "Processing..." : totpAction === "setup" ? "Set Up TOTP" : "Regenerate Secret"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* System Info */}
      <div style={{
        background: "#fff", borderRadius: 14, padding: "28px 32px",
        boxShadow: "0 2px 12px rgba(0,0,0,0.07)", maxWidth: 900, marginTop: 20,
      }}>
        <h2 style={{ margin: "0 0 12px", fontSize: 17, fontWeight: 600, color: "#374151" }}>System Info</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <tbody>
            {[
              ["API Base", "/rent/admin/api"],
              ["Frontend Base", "/rent/admin"],
              ["Auth Scope", "Cookie: access_token"],
            ].map(([label, value]) => (
              <tr key={label} style={{ borderBottom: "1px solid #f3f4f6" }}>
                <td style={{ padding: "12px 0", fontWeight: 600, color: "#6b7280", width: 160 }}>{label}</td>
                <td style={{ padding: "12px 0" }}><code style={{ background: "#f1f5f9", padding: "2px 8px", borderRadius: 6 }}>{value}</code></td>
              </tr>
            ))}
          </tbody>
        </table>

        {health && (
          <>
            <h2 style={{ margin: "20px 0 12px", fontSize: 17, fontWeight: 600, color: "#374151" }}>Live Health</h2>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <tbody>
                {[
                  ["Status", health.status],
                  ["Database", health.database],
                  ["Active Connections", String(health.active_connections)],
                  ["Uptime", health.uptime],
                  ["Last Update", new Date(health.timestamp).toLocaleTimeString()],
                ].map(([label, value]) => (
                  <tr key={label} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={{ padding: "12px 0", fontWeight: 600, color: "#6b7280", width: 160 }}>{label}</td>
                    <td style={{ padding: "12px 0" }}>
                      <code style={{
                        background: label === "Status" || label === "Database"
                          ? value === "ok" ? "#dcfce7" : "#fef2f2"
                          : "#f1f5f9",
                        color: label === "Status" || label === "Database"
                          ? value === "ok" ? "#16a34a" : "#dc2626"
                          : "inherit",
                        padding: "2px 8px", borderRadius: 6,
                      }}>{value}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>

      {/* Audit Log Settings */}
      <form onSubmit={handleSaveAudit} style={{
        background: "#fff", borderRadius: 14, padding: "28px 32px",
        boxShadow: "0 2px 12px rgba(0,0,0,0.07)", maxWidth: 900, marginTop: 20,
      }}>
        <h2 style={{ margin: "0 0 4px", fontSize: 17, fontWeight: 600, color: "#374151" }}>Audit Log Settings</h2>
        <p style={{ margin: "0 0 16px", fontSize: 13, color: "#6b7280" }}>
          Configure how long audit log entries are retained before cleanup.
        </p>
        {auditMsg && <p style={successStyle}>{auditMsg}</p>}
        {auditErr && <p style={errorStyle}>{auditErr}</p>}
        <div style={{ display: "flex", alignItems: "flex-end", gap: 16 }}>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 600, color: "#374151" }}>
              Retention Period (days)
            </label>
            <input
              type="number"
              min={1}
              max={365}
              value={retentionDays}
              onChange={(e) => setRetentionDays(Math.max(1, Math.min(365, Number(e.target.value) || 30)))}
              style={{ ...inputStyle, width: 120 }}
            />
          </div>
          <button
            type="submit"
            disabled={auditSaving}
            style={{
              ...primaryBtn,
              opacity: auditSaving ? 0.6 : 1,
            }}
          >
            {auditSaving ? "Saving…" : "Save"}
          </button>
        </div>
        <p style={{ margin: "10px 0 0", fontSize: 12, color: "#9ca3af" }}>
          Logs older than this period are automatically cleaned up. Default: 30 days.
        </p>
      </form>
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
const overlayStyle: React.CSSProperties = {
  position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex",
  alignItems: "center", justifyContent: "center", zIndex: 1000,
};
const dialogStyle: React.CSSProperties = {
  background: "#fff", borderRadius: 14, padding: "24px 28px", width: "100%", maxWidth: 380, margin: "0 16px",
  boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
};
