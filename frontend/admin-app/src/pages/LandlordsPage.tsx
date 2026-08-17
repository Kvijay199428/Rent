import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router";
import Layout from "../components/Layout";
import { fetchApi } from "../api/client";

interface Landlord {
  id: number;
  landlord_uuid: string;
  full_name: string;
  email: string;
  phone: string;
  username: string;
  status: string;
  created_at: string;
  updated_at: string;
  has_totp: boolean;
  failed_attempts: number;
  locked_until: string | null;
  requires_password_change: boolean;
  privacy_consented: boolean;
  privacy_version: string | null;
  privacy_accepted_at: string | null;
  terms_consented: boolean;
  terms_version: string | null;
  terms_accepted_at: string | null;
  tenant_count: number;
  receipt_count: number;
  kyc_count: number;
}

interface ModalData {
  type: "totp" | "password" | "reset" | "reset_whatsapp";
  landlord: Landlord;
  result?: { password?: string; secret?: string; qr_code_base64?: string; message?: string; updated_at?: string; whatsapp_url?: string; requires_password_change?: boolean };
  error?: string;
  loading: boolean;
}

const badgeStyle = (status: string): React.CSSProperties => ({
  display: "inline-block",
  padding: "2px 10px", borderRadius: 99, fontSize: 12, fontWeight: 600,
  background: status === "Active" ? "#dcfce7" : status === "Locked" ? "#fee2e2" : "#f3f4f6",
  color: status === "Active" ? "#16a34a" : status === "Locked" ? "#dc2626" : "#6b7280",
});

export default function LandlordsPage() {
  const [landlords, setLandlords] = useState<Landlord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [modal, setModal] = useState<ModalData | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      if (statusFilter) params.set("status", statusFilter);
      params.set("limit", "50");
      const res = await fetchApi(`/landlords?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setLandlords(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load landlords");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  async function toggleTOTP(l: Landlord) {
    setModal({ type: "totp", landlord: l, loading: true });
    try {
      const res = await fetchApi(`/landlords/${l.id}/totp-toggle`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Failed");
      setModal({ type: "totp", landlord: l, result: data, loading: false });
      fetchData();
    } catch (e: unknown) {
      setModal({ type: "totp", landlord: l, error: e instanceof Error ? e.message : "Failed", loading: false });
    }
  }

  async function revealPassword(l: Landlord) {
    setModal({ type: "password", landlord: l, loading: true });
    try {
      const res = await fetchApi(`/landlords/${l.id}/reveal-password`);
      const data = await res.json();
      if (!res.ok) {
        // Password not in vault — offer reset
        setModal({ type: "password", landlord: l, error: data.detail ?? "Password not available. Use Reset instead.", loading: false });
        return;
      }
      setModal({ type: "password", landlord: l, result: data, loading: false });
    } catch (e: unknown) {
      setModal({ type: "password", landlord: l, error: e instanceof Error ? e.message : "Failed", loading: false });
    }
  }

  async function resetPassword(l: Landlord) {
    if (!confirm(`Reset password for ${l.username}? The new password will be shown once.`)) return;
    setModal({ type: "reset", landlord: l, loading: true });
    try {
      const res = await fetchApi(`/landlords/${l.id}/reset-password`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Failed");
      setModal({ type: "reset", landlord: l, result: data, loading: false });
    } catch (e: unknown) {
      setModal({ type: "reset", landlord: l, error: e instanceof Error ? e.message : "Failed", loading: false });
    }
  }

  async function resetWithWhatsApp(l: Landlord) {
    if (!l.phone) {
      setModal({ type: "reset_whatsapp", landlord: l, error: "No phone number on file. Add one first.", loading: false });
      return;
    }
    setModal({ type: "reset_whatsapp", landlord: l, loading: true });
    try {
      const res = await fetchApi(`/landlords/${l.id}/reset-password`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Failed");
      setModal({ type: "reset_whatsapp", landlord: l, result: data, loading: false });
    } catch (e: unknown) {
      setModal({ type: "reset_whatsapp", landlord: l, error: e instanceof Error ? e.message : "Failed", loading: false });
    }
  }

  return (
    <Layout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, color: "#1a1d2e" }}>Landlords</h1>
      </div>

      <div style={{
        background: "#fff", borderRadius: 14, padding: "16px 20px",
        boxShadow: "0 2px 12px rgba(0,0,0,0.07)", marginBottom: 20,
        display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap",
      }}>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, username, or email…"
          style={{ flex: 1, minWidth: 200, padding: "10px 14px", borderRadius: 8, border: "1.5px solid #d1d5db", fontSize: 14 }}
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ padding: "10px 14px", borderRadius: 8, border: "1.5px solid #d1d5db", fontSize: 14 }}
        >
          <option value="">All statuses</option>
          <option value="Active">Active</option>
          <option value="Locked">Locked</option>
          <option value="Inactive">Inactive</option>
        </select>
      </div>

      {error && (
        <div style={{ background: "#fef2f2", color: "#dc2626", padding: "12px 16px", borderRadius: 8, marginBottom: 20, fontSize: 14 }}>
          {error}
        </div>
      )}

      {loading ? (
        <p style={{ color: "#9ca3af" }}>Loading…</p>
      ) : (
        <div style={{ background: "#fff", borderRadius: 14, boxShadow: "0 2px 12px rgba(0,0,0,0.07)", overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ background: "#f9fafb" }}>
                  {["ID", "Name", "Username", "Status", "Privacy", "Terms", "TOTP", "PW Reset", "Tenants", "Receipts", "KYC", "Joined", "Actions"].map((h) => (
                    <th key={h} style={{ padding: "12px 12px", textAlign: "left", fontWeight: 600, color: "#374151", borderBottom: "1px solid #e5e7eb", fontSize: 13, whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {landlords.length === 0 && (
                  <tr>
                    <td colSpan={12} style={{ padding: "32px 16px", textAlign: "center", color: "#9ca3af" }}>
                      No landlords found.
                    </td>
                  </tr>
                )}
                {landlords.map((l) => (
                  <tr key={l.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={{ padding: "12px 12px", color: "#6b7280" }}>{l.id}</td>
                    <td style={{ padding: "12px 12px", fontWeight: 600, color: "#1a1d2e" }}>
                      <Link to={`/landlords/${l.id}`} style={{ color: "#3b4a6b", textDecoration: "none" }}>
                        {l.full_name || "—"}
                      </Link>
                      {l.email && <div style={{ fontSize: 12, color: "#9ca3af", fontWeight: 400 }}>{l.email}</div>}
                    </td>
                    <td style={{ padding: "12px 12px" }}>
                      <code style={{ background: "#f1f5f9", padding: "2px 8px", borderRadius: 6, fontSize: 13 }}>{l.username}</code>
                    </td>
                    <td style={{ padding: "12px 12px" }}>
                      <span style={badgeStyle(l.status)}>{l.status}</span>
                    </td>
                    <td style={{ padding: "12px 12px" }}>
                      {l.privacy_consented ? (
                        <span
                          style={{ display: "inline-block", padding: "2px 10px", borderRadius: 99, fontSize: 12, fontWeight: 600, background: "#dcfce7", color: "#16a34a", cursor: "help" }}
                          title={[
                            "Privacy Policy accepted",
                            l.privacy_version ? `Version ${l.privacy_version}` : null,
                            l.privacy_accepted_at ? `Accepted ${new Date(l.privacy_accepted_at).toLocaleString()}` : null,
                          ].filter(Boolean).join(" · ")}
                        >
                          Accepted
                        </span>
                      ) : (
                        <span
                          style={{ display: "inline-block", padding: "2px 10px", borderRadius: 99, fontSize: 12, fontWeight: 600, background: "#fef3c7", color: "#92400e", cursor: "help" }}
                          title="Privacy Policy not yet accepted"
                        >
                          Pending
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "12px 12px" }}>
                      {l.terms_consented ? (
                        <span
                          style={{ display: "inline-block", padding: "2px 10px", borderRadius: 99, fontSize: 12, fontWeight: 600, background: "#dcfce7", color: "#16a34a", cursor: "help" }}
                          title={[
                            "Terms and Conditions accepted",
                            l.terms_version ? `Version ${l.terms_version}` : null,
                            l.terms_accepted_at ? `Accepted ${new Date(l.terms_accepted_at).toLocaleString()}` : null,
                          ].filter(Boolean).join(" · ")}
                        >
                          Accepted
                        </span>
                      ) : (
                        <span
                          style={{ display: "inline-block", padding: "2px 10px", borderRadius: 99, fontSize: 12, fontWeight: 600, background: "#fef3c7", color: "#92400e", cursor: "help" }}
                          title="Terms and Conditions not yet accepted"
                        >
                          Pending
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "12px 12px", fontSize: 13 }}>
                      {l.has_totp ? "✅" : "—"}
                    </td>
                    <td style={{ padding: "12px 12px", textAlign: "center" }}>
                      {l.requires_password_change ? (
                        <span style={{ display: "inline-block", padding: "2px 8px", borderRadius: 99, fontSize: 11, fontWeight: 600, background: "#fef3c7", color: "#92400e" }}>
                          PW Pending
                        </span>
                      ) : "—"}
                    </td>
                    <td style={{ padding: "12px 12px", textAlign: "center" }}>{l.tenant_count}</td>
                    <td style={{ padding: "12px 12px", textAlign: "center" }}>{l.receipt_count}</td>
                    <td style={{ padding: "12px 12px", textAlign: "center" }}>{l.kyc_count}</td>
                    <td style={{ padding: "12px 12px", fontSize: 12, color: "#9ca3af", whiteSpace: "nowrap" }}>
                      {l.created_at ? new Date(l.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td style={{ padding: "12px 12px" }}>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        <button
                          onClick={() => toggleTOTP(l)}
                          style={{
                            padding: "4px 10px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 11, fontWeight: 600,
                            background: l.has_totp ? "#fef9c3" : "#dcfce7",
                            color: l.has_totp ? "#92400e" : "#166534",
                          }}
                        >
                          {l.has_totp ? "Disable TOTP" : "Enable TOTP"}
                        </button>
                        <button
                          onClick={() => revealPassword(l)}
                          style={{ padding: "4px 10px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 11, fontWeight: 600, background: "#e0e7ff", color: "#3730a3" }}
                        >
                          Show PW
                        </button>
                        <button
                          onClick={() => resetPassword(l)}
                          style={{ padding: "4px 10px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 11, fontWeight: 600, background: "#fee2e2", color: "#dc2626" }}
                        >
                          Reset PW
                        </button>
                        <button
                          onClick={() => resetWithWhatsApp(l)}
                          style={{ padding: "4px 10px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 11, fontWeight: 600, background: "#dcfce7", color: "#166534" }}
                          title="Reset password and send via WhatsApp"
                        >
                          Send WA
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal */}
      {modal && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 200 }}
          onClick={() => setModal(null)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "#fff", borderRadius: 16, padding: "28px 32px", width: "100%", maxWidth: 440, margin: "0 16px", maxHeight: "80vh", overflowY: "auto",
              boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
            }}
          >
            <h2 style={{ margin: "0 0 16px", fontSize: 17, fontWeight: 700, color: "#1a1d2e" }}>
              {modal.type === "totp" && (modal.landlord.has_totp ? "Disable TOTP" : "Enable TOTP")}
              {modal.type === "password" && "Reveal Password"}
              {modal.type === "reset" && "Reset Password"}
              {modal.type === "reset_whatsapp" && "Reset & Send via WhatsApp"}
              <span style={{ fontWeight: 400, color: "#6b7280", fontSize: 14 }}> — {modal.landlord.username}</span>
            </h2>

            {modal.loading && <p style={{ color: "#9ca3af" }}>Loading…</p>}

            {modal.error && (
              <div style={{ background: "#fef2f2", color: "#dc2626", padding: "10px 14px", borderRadius: 8, fontSize: 13, marginBottom: 12 }}>
                {modal.error}
              </div>
            )}

            {modal.result && (
              <div>
                {modal.type === "totp" && (
                  <div style={{ textAlign: "center" }}>
                    {modal.result.qr_code_base64 && (
                      <>
                        <p style={{ fontSize: 13, color: "#374151", marginBottom: 8 }}>Scan this QR code with the landlord's authenticator app:</p>
                        <img
                          src={`data:image/png;base64,${modal.result.qr_code_base64}`}
                          alt="TOTP QR"
                          style={{ width: 200, height: 200, borderRadius: 8, border: "1px solid #e5e7eb", marginBottom: 12 }}
                        />
                      </>
                    )}
                    {modal.result.secret && (
                      <div style={{ background: "#f1f5f9", padding: "10px 14px", borderRadius: 8, fontSize: 13, fontFamily: "monospace" }}>
                        Secret: {modal.result.secret}
                      </div>
                    )}
                    {modal.result.message && (
                      <p style={{ fontSize: 13, color: "#16a34a", marginTop: 8 }}>{modal.result.message}</p>
                    )}
                  </div>
                )}

                {(modal.type === "password" || modal.type === "reset") && modal.result.password && (
                  <div>
                    <p style={{ fontSize: 13, color: "#374151", marginBottom: 8 }}>
                      {modal.type === "reset" ? "New password (copy now — shown only once):" : "Current password:"}
                    </p>
                    <div style={{
                      background: "#f1f5f9", padding: "12px 16px", borderRadius: 8,
                      fontFamily: "monospace", fontSize: 16, fontWeight: 700, color: "#1a1d2e",
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                    }}>
                      <span>{modal.result.password}</span>
                      <button
                        onClick={() => navigator.clipboard.writeText(modal.result!.password!)}
                        style={{ padding: "4px 10px", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff", fontSize: 12, cursor: "pointer" }}
                      >
                        Copy
                      </button>
                    </div>
                    {modal.result.updated_at && (
                      <p style={{ fontSize: 12, color: "#9ca3af", marginTop: 8 }}>
                        Last updated: {new Date(modal.result.updated_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                )}

                {modal.type === "reset_whatsapp" && modal.result && (
                  <div>
                    {modal.result.password && (
                      <>
                        <p style={{ fontSize: 13, color: "#374151", marginBottom: 8 }}>
                          New password (copy now — shown only once):
                        </p>
                        <div style={{
                          background: "#f1f5f9", padding: "12px 16px", borderRadius: 8,
                          fontFamily: "monospace", fontSize: 16, fontWeight: 700, color: "#1a1d2e",
                          display: "flex", alignItems: "center", justifyContent: "space-between",
                        }}>
                          <span>{modal.result.password}</span>
                          <button
                            onClick={() => navigator.clipboard.writeText(modal.result!.password!)}
                            style={{ padding: "4px 10px", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff", fontSize: 12, cursor: "pointer" }}
                          >
                            Copy
                          </button>
                        </div>
                      </>
                    )}

                    {modal.result.whatsapp_url ? (
                      <div style={{ marginTop: 16 }}>
                        <p style={{ fontSize: 13, color: "#374151", marginBottom: 8 }}>
                          Open WhatsApp to send the credentials:
                        </p>
                        <a
                          href={modal.result.whatsapp_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: "inline-flex", alignItems: "center", gap: 8,
                            padding: "10px 20px", borderRadius: 8,
                            background: "#25D366", color: "#fff", fontWeight: 600, fontSize: 14,
                            textDecoration: "none",
                          }}
                        >
                          Open WhatsApp
                        </a>
                      </div>
                    ) : (
                      <p style={{ fontSize: 13, color: "#9ca3af", marginTop: 12 }}>
                        No phone number on file — WhatsApp URL not generated.
                      </p>
                    )}

                    {modal.result.requires_password_change && (
                      <p style={{ fontSize: 12, color: "#92400e", marginTop: 12, background: "#fef3c7", padding: "8px 12px", borderRadius: 6 }}>
                        The landlord will be required to change their password on next login.
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            <button
              onClick={() => setModal(null)}
              style={{
                marginTop: 20, width: "100%", padding: "10px 0", borderRadius: 8, border: "1.5px solid #d1d5db",
                background: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer",
              }}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </Layout>
  );
}
