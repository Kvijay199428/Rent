import { useState, useEffect, type FormEvent } from "react";
import Layout from "../components/Layout";
import { fetchApi } from "../api/client";
import { useHealthStream } from "../hooks/useHealthStream";
import { Button } from "../components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";

interface Profile {
  id: number;
  username: string;
  email: string | null;
  is_platform_admin: boolean;
  has_totp: boolean;
  created_at: string;
  updated_at: string;
}

const inputClass =
  "w-full rounded-lg border-[1.5px] border-gray-300 px-3 py-2.5 text-sm outline-none";

const successClass = "mb-4 rounded-lg bg-green-100 px-3.5 py-2.5 text-[13px] text-green-600";
const errorClass = "mb-4 rounded-lg bg-red-100 px-3.5 py-2.5 text-[13px] text-red-600";
const hintClass = "mb-4 rounded-lg bg-amber-50 px-3.5 py-2.5 text-[13px] text-amber-700";

const outlineBtn =
  "cursor-pointer whitespace-nowrap rounded-lg border-[1.5px] border-gray-300 bg-white px-3.5 py-2 text-[13px] font-semibold disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-400";
const dangerBtn =
  "cursor-pointer whitespace-nowrap rounded-lg border-[1.5px] border-red-300 bg-red-50 px-3.5 py-2 text-[13px] font-semibold text-red-600";

const cardClass =
  "rounded-2xl bg-white p-7 shadow-[0_2px_12px_rgba(0,0,0,0.07)]";

export default function SettingsPage() {
  const health = useHealthStream();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [profileLoadErr, setProfileLoadErr] = useState(false);
  const [auditSettingsLoadErr, setAuditSettingsLoadErr] = useState(false);
  const [tgStatusLoadErr, setTgStatusLoadErr] = useState(false);

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
      .catch(() => setProfileLoadErr(true));
  }, []);

  useEffect(() => {
    fetchApi("/settings/audit")
      .then((r) => r.json())
      .then((d) => { if (d.retention_days) setRetentionDays(d.retention_days); })
      .catch(() => setAuditSettingsLoadErr(true));
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
      .catch(() => setTgStatusLoadErr(true));
  }, []);

  async function handleSaveProfile(e: FormEvent) {
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

  async function handleChangePassword(e: FormEvent) {
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

  async function handleSaveAudit(e: FormEvent) {
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
      <h1 className="mb-6 text-[26px] font-bold text-[#1a1d2e]">Settings</h1>

      <div className="motion-stagger grid max-w-[900px] grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Profile */}
        <form onSubmit={handleSaveProfile} className={cardClass}>
          <h2 className="mb-5 text-[17px] font-semibold text-gray-700">Profile</h2>

          {saveMsg && <div className={successClass}>{saveMsg}</div>}
          {saveErr && <div className={errorClass}>{saveErr}</div>}
          {profileLoadErr && (
            <div className={hintClass}>
              Profile details couldn't be loaded — saving may fail until this resolves.
            </div>
          )}

          <label className="mb-4 block">
            <span>Username</span>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required className={`mt-1.5 ${inputClass}`} />
          </label>
          <label className="mb-4 block">
            <span>Email</span>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className={`mt-1.5 ${inputClass}`} placeholder="admin@example.com" />
          </label>

          <div className="mt-4 space-y-0.5 text-[13px] text-gray-500">
            <div>ID: {profile?.id ?? "—"}</div>
            <div>Role: Platform Super Admin</div>
            {profile?.created_at && <div>Created: {new Date(profile.created_at).toLocaleString()}</div>}
          </div>

          <Button type="submit" disabled={saving} className="mt-2 bg-[#3b4a6b] text-white">
            {saving ? "Saving…" : "Save Changes"}
          </Button>
        </form>

        {/* Password */}
        <form onSubmit={handleChangePassword} className={cardClass}>
          <h2 className="mb-5 text-[17px] font-semibold text-gray-700">Change Password</h2>

          {pwMsg && <div className={successClass}>{pwMsg}</div>}
          {pwErr && <div className={errorClass}>{pwErr}</div>}

          <label className="mb-4 block">
            <span>Current Password</span>
            <input type="password" value={currentPw} onChange={(e) => setCurrentPw(e.target.value)} required className={`mt-1.5 ${inputClass}`} />
          </label>
          <label className="mb-4 block">
            <span>New Password</span>
            <input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} required minLength={6} className={`mt-1.5 ${inputClass}`} />
          </label>
          <label className="mb-4 block">
            <span>Confirm New Password</span>
            <input type="password" value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} required minLength={6} className={`mt-1.5 ${inputClass}`} />
          </label>

          <Button type="submit" disabled={pwSaving} className="mt-2 bg-[#3b4a6b] text-white">
            {pwSaving ? "Changing…" : "Change Password"}
          </Button>
        </form>
      </div>

      {/* TOTP */}
      <div className={`motion-fade-up ${cardClass} mt-5 max-w-[900px]`}>
        <h2 className="mb-4 text-[17px] font-semibold text-gray-700">Two-Factor Authentication</h2>
        <p className="mb-4 text-sm text-gray-500">
          {profile?.has_totp
            ? "TOTP is currently enabled. You must enter a verification code after your password to login."
            : "Two-factor authentication adds an extra layer of security to your account."}
        </p>

        {totpErr && <div className={errorClass}>{totpErr}</div>}
        {totpSuccess && <div className={successClass}>{totpSuccess}</div>}

        {totpQr && (
          <div className="mb-5 text-center">
            <p className="mb-2 text-[13px] text-gray-700">Scan this QR code with your authenticator app:</p>
            <img src={`data:image/png;base64,${totpQr}`} alt="TOTP QR Code" className="h-[200px] w-[200px] rounded-lg border border-gray-200" />
          </div>
        )}

        {totpSecret && (
          <div className="mb-5">
            <p className="mb-1.5 text-[13px] font-semibold text-gray-700">TOTP Secret (Manual Entry)</p>
            <div className="flex items-center gap-2">
              <div className="flex-1 break-all rounded-lg border-[1.5px] border-gray-300 bg-gray-50 px-3 py-2.5 font-mono text-sm">
                {showTotpSecret ? totpSecret : "•".repeat(totpSecret.length)}
              </div>
              <button
                type="button"
                onClick={() => setShowTotpSecret(!showTotpSecret)}
                className={outlineBtn}
              >
                {showTotpSecret ? "Hide" : "Show"}
              </button>
              <button
                type="button"
                onClick={() => { navigator.clipboard.writeText(totpSecret); }}
                className={outlineBtn}
              >
                Copy
              </button>
            </div>
          </div>
        )}

        <div className="flex gap-2.5">
          {profile?.has_totp && (
            <button
              onClick={handleShowTotpQr}
              className="cursor-pointer rounded-lg border-[1.5px] border-gray-300 bg-white px-5 py-2.5 text-sm font-semibold"
            >
              {totpQr ? "Hide TOTP QR" : "Show TOTP QR"}
            </button>
          )}
          <button
            onClick={() => openTotpDialog(profile?.has_totp ? "regenerate" : "setup")}
            className={profile?.has_totp ? dangerBtn : "cursor-pointer rounded-lg border-[1.5px] border-gray-300 bg-white px-5 py-2.5 text-sm font-semibold text-gray-700"}
          >
            {profile?.has_totp ? "Regenerate TOTP Secret" : "Set Up TOTP"}
          </button>
        </div>
      </div>

      {/* Telegram OTP */}
      <div className={`motion-fade-up ${cardClass} mt-5 max-w-[900px]`}>
        <h2 className="mb-3 text-[17px] font-semibold text-gray-700">Telegram OTP Login</h2>
        <p className="mb-4 text-sm text-gray-500">
          Receive a one-time login code in Telegram as an alternative to your authenticator app.
        </p>

        {tgErr && <div className={errorClass}>{tgErr}</div>}
        {tgStatusLoadErr && (
          <div className={hintClass}>Telegram status couldn't be loaded — refresh to retry.</div>
        )}
        {tgMsg && <div className={successClass}>{tgMsg}</div>}

        <div className="mb-4 flex flex-col gap-1.5 text-[13px]">
          <div>
            Bot configured:{" "}
            <strong className={tgBotConfigured ? "text-green-600" : "text-red-600"}>
              {tgBotConfigured ? "Yes" : "No"}
            </strong>
            {!tgBotConfigured && " — add TELEGRAM_BOT_TOKEN to the backend .env and redeploy."}
          </div>
          <div>
            Telegram chat linked:{" "}
            <strong className={tgChatLinked ? "text-green-600" : "text-gray-500"}>
              {tgChatLinked ? (tgChatMasked ? `Yes (${tgChatMasked})` : "Yes") : "No"}
            </strong>
          </div>
        </div>

        <div className="flex flex-wrap gap-2.5">
          <button
            onClick={() => handleTgAction("link")}
            disabled={tgBusy || !tgBotConfigured}
            className={outlineBtn}
          >
            {tgBusy ? "Working…" : "Link Telegram"}
          </button>
          {tgChatLinked && (
            <>
              <button
                onClick={() => handleTgAction("test")}
                disabled={tgBusy}
                className={outlineBtn}
              >
                Send Test Message
              </button>
              <button
                onClick={() => handleTgAction("unlink")}
                disabled={tgBusy}
                className={dangerBtn}
              >
                Unlink
              </button>
            </>
          )}
        </div>
        {tgBotConfigured && !tgChatLinked && (
          <p className="mt-3 text-xs text-gray-400">
            Open <strong>@propauraBot</strong> on your Telegram, send{" "}
            <strong>/start</strong>, then click <strong>Link Telegram</strong> above to capture your chat.
          </p>
        )}
      </div>

      {/* System Info */}
      <div className={`motion-fade-up ${cardClass} mt-5 max-w-[900px]`}>
        <h2 className="mb-3 text-[17px] font-semibold text-gray-700">System Info</h2>
        <div className="divide-y divide-gray-100 text-sm">
          {[
            ["API Base", "/admin/api"],
            ["Frontend Base", "/admin"],
            ["Auth Scope", "Cookie: access_token"],
          ].map(([label, value]) => (
            <div key={label} className="flex gap-4 py-3">
              <span className="w-40 shrink-0 font-semibold text-gray-500">{label}</span>
              <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-[13px]">{value}</span>
            </div>
          ))}
        </div>

        {health && (
          <>
            <h2 className="mb-3 mt-5 text-[17px] font-semibold text-gray-700">Live Health</h2>
            <div className="divide-y divide-gray-100 text-sm">
              {[
                ["Status", health.status],
                ["Database", health.database],
                ["Active Connections", String(health.active_connections)],
                ["Uptime", health.uptime],
                ["Last Update", new Date(health.timestamp).toLocaleTimeString()],
              ].map(([label, value]) => (
                <div key={label} className="flex gap-4 py-3">
                  <span className="w-40 shrink-0 font-semibold text-gray-500">{label}</span>
                  {label === "Status" || label === "Database" ? (
                    <span className={`rounded-md px-2 py-0.5 font-mono text-[13px] ${value === "ok" ? "bg-green-100 text-green-600" : "bg-red-100 text-red-600"}`}>
                      {value}
                    </span>
                  ) : (
                    <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-[13px]">{value}</span>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Audit Log Settings */}
      <form onSubmit={handleSaveAudit} className={`motion-fade-up ${cardClass} mt-5 max-w-[900px]`}>
        <h2 className="mb-1 text-[17px] font-semibold text-gray-700">Audit Log Settings</h2>
        <p className="mb-4 text-[13px] text-gray-500">
          Configure how long audit log entries are retained before cleanup.
        </p>
        {auditMsg && <p className={successClass}>{auditMsg}</p>}
        {auditErr && <p className={errorClass}>{auditErr}</p>}
        {auditSettingsLoadErr && (
          <p className={hintClass}>Current retention setting couldn't be loaded.</p>
        )}
        <div className="flex items-end gap-4">
          <div>
            <label className="mb-1.5 block text-sm font-semibold text-gray-700">
              Retention Period (days)
            </label>
            <input
              type="number"
              min={1}
              max={365}
              value={retentionDays}
              onChange={(e) => setRetentionDays(Math.max(1, Math.min(365, Number(e.target.value) || 30)))}
              className={`${inputClass} w-[120px]`}
            />
          </div>
          <Button
            type="submit"
            disabled={auditSaving}
            className="bg-[#3b4a6b] text-white"
          >
            {auditSaving ? "Saving…" : "Save"}
          </Button>
        </div>
        <p className="mt-2.5 text-xs text-gray-400">
          Logs older than this period are automatically cleaned up. Default: 30 days.
        </p>
      </form>

      {/* Password Confirmation Dialog */}
      <Dialog open={showTotpDialog} onOpenChange={(open) => {
        setShowTotpDialog(open);
        if (!open) {
          setTotpPassword("");
          setTotpErr(null);
        }
      }}>
        <DialogContent className="max-w-[380px]">
          <DialogHeader>
            <DialogTitle>
              {totpAction === "setup" ? "Set Up Two-Factor Authentication" : "Regenerate TOTP Secret"}
            </DialogTitle>
          </DialogHeader>
          <p className="mb-4 text-[13px] text-gray-500">
            {totpAction === "setup"
              ? "Enter your current password to set up TOTP for your account."
              : "Enter your current password to regenerate your TOTP secret. Your old authenticator codes will stop working."}
          </p>
          {totpErr && <div className={errorClass}>{totpErr}</div>}
          <label className="mb-4 block">
            <span className="mb-1.5 block text-[13px] font-semibold text-gray-700">Current Password</span>
            <div className="relative">
              <input
                type={showPwText ? "text" : "password"}
                value={totpPassword}
                onChange={(e) => setTotpPassword(e.target.value)}
                placeholder="Enter your password"
                autoFocus
                onKeyDown={(e) => { if (e.key === "Enter") handleTotpConfirm(); }}
                className={`${inputClass} pr-14`}
              />
              <button
                type="button"
                onClick={() => setShowPwText(!showPwText)}
                className="absolute top-1/2 right-2.5 -translate-y-1/2 cursor-pointer border-none bg-transparent text-[13px] text-gray-500"
              >
                {showPwText ? "Hide" : "Show"}
              </button>
            </div>
          </label>
          <div className="flex justify-end gap-2.5">
            <Button
              type="button"
              variant="outline"
              onClick={() => { setShowTotpDialog(false); setTotpPassword(""); setTotpErr(null); }}
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleTotpConfirm}
              disabled={totpBusy || !totpPassword}
              className={totpAction === "regenerate" ? "bg-red-600 text-white hover:bg-red-700" : "bg-[#3b4a6b] text-white"}
            >
              {totpBusy ? "Processing..." : totpAction === "setup" ? "Set Up TOTP" : "Regenerate Secret"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}