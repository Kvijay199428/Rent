import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import Layout from "../components/Layout";
import { fetchApi } from "../api/client";

interface FeedbackItem {
  id: number;
  tenant_id: number | null;
  landlord_id: number | null;
  property_id: number | null;
  tenant_name: string;
  view_token: string;
  qr_key: string;
  message: string;
  diagnostics: Record<string, unknown>;
  failed_attempts: number;
  status: string;
  admin_reply: string | null;
  created_at: string;
  resolved_at: string | null;
  ip_address: string;
}

function formatTs(ts: string) {
  if (!ts) return "\u2014";
  try {
    const d = new Date(ts + (ts.includes("Z") ? "" : "Z"));
    return d.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
  } catch { return ts; }
}

function statusBadge(status: string) {
  const open = status !== "resolved";
  return (
    <span style={{
      display: "inline-block", padding: "2px 10px", borderRadius: 9999,
      fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5,
      background: open ? "#fef3c7" : "#dcfce7",
      color: open ? "#b45309" : "#16a34a",
      whiteSpace: "nowrap",
    }}>
      {open ? "Open" : "Resolved"}
    </span>
  );
}

function Diagnostics({ diagnostics }: { diagnostics: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  const rows: [string, string][] = [];
  const push = (k: string, v: unknown) => {
    if (v === null || v === undefined || v === "") return;
    if (typeof v === "object") {
      try { rows.push([k, JSON.stringify(v)]); } catch { /* ignore */ }
    } else {
      rows.push([k, String(v)]);
    }
  };

  push("Browser", (diagnostics as any).user_agent);
  push("Platform", (diagnostics as any).platform);
  push("Language", (diagnostics as any).language);
  push("Screen", (diagnostics as any).screen);
  push("Viewport", (diagnostics as any).viewport);
  push("Online", (diagnostics as any).online);
  push("Connection", (diagnostics as any).connection);
  push("Page URL", (diagnostics as any).url);
  push("Path", (diagnostics as any).pathname);
  push("Reported attempts", (diagnostics as any).attempts);

  return (
    <div style={{ marginTop: 10 }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          background: "none", border: "none", padding: 0, cursor: "pointer",
          fontSize: 12, fontWeight: 700, color: "#2563eb",
        }}
      >
        {open ? "\u25be Hide device / network details" : "\u25b8 Show device / network details"}
      </button>
      {open && (
        <div style={{
          marginTop: 8, padding: "10px 12px", borderRadius: 8,
          background: "#f8fafc", border: "1px solid #e5e7eb",
          fontSize: 12, overflowX: "auto",
        }}>
          {rows.length === 0 ? (
            <span style={{ color: "#9ca3af" }}>No diagnostics captured.</span>
          ) : (
            <table style={{ borderCollapse: "collapse", width: "100%" }}>
              <tbody>
                {rows.map(([k, v]) => (
                  <tr key={k}>
                    <td style={{ padding: "3px 12px 3px 0", fontWeight: 600, color: "#374151", whiteSpace: "nowrap", verticalAlign: "top" }}>{k}</td>
                    <td style={{ padding: "3px 0", color: "#6b7280", fontFamily: "monospace", wordBreak: "break-all", maxWidth: 380 }}>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

export default function FeedbackInboxPage() {
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [searchFilter, setSearchFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [limit] = useState(30);
  const [replyText, setReplyText] = useState<Record<number, string>>({});
  const [busyId, setBusyId] = useState<number | null>(null);

  const fetchFeedback = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      if (searchFilter) params.set("search", searchFilter);
      params.set("limit", String(limit));
      params.set("offset", String(offset));

      const res = await fetchApi(`/feedback?${params}`);
      if (!res.ok) throw new Error("Failed to load");
      const data = await res.json();
      setItems(data.items);
      setTotal(data.total);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchFilter, offset, limit]);

  useEffect(() => { fetchFeedback(); }, [fetchFeedback]);

  const handleReply = async (id: number) => {
    const reply = (replyText[id] || "").trim();
    if (!reply) {
      toast.error("Write a reply first.");
      return;
    }
    setBusyId(id);
    try {
      const res = await fetchApi(`/feedback/${id}/reply`, {
        method: "POST",
        body: JSON.stringify({ admin_reply: reply }),
      });
      if (!res.ok) throw new Error("Reply failed");
      toast.success("Reply saved and feedback marked resolved.");
      setReplyText((r) => { const n = { ...r }; delete n[id]; return n; });
      await fetchFeedback();
    } catch {
      toast.error("Could not save reply. Please try again.");
    } finally {
      setBusyId(null);
    }
  };

  const handleResolve = async (id: number) => {
    setBusyId(id);
    try {
      const res = await fetchApi(`/feedback/${id}/resolve`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Resolve failed");
      toast.success("Feedback marked resolved.");
      await fetchFeedback();
    } catch {
      toast.error("Could not resolve feedback.");
    } finally {
      setBusyId(null);
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <Layout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, color: "#1a1d2e" }}>QR Feedback Inbox</h1>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "#6b7280" }}>
            Tenants reporting a wrong QR key from the unlock screen
          </p>
        </div>
      </div>

      <div style={{
        display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap", alignItems: "flex-end",
        padding: "14px 16px", borderRadius: 10, background: "#fff", border: "1px solid #e5e7eb",
      }}>
        <div>
          <label style={labelSm}>Status</label>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setOffset(0); }}
            style={selectStyle}
          >
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>
        <div style={{ flex: 1, minWidth: 180 }}>
          <label style={labelSm}>Search</label>
          <input
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { setOffset(0); fetchFeedback(); } }}
            placeholder="Tenant, message, QR key\u2026"
            style={inputStyle}
          />
        </div>
        {(statusFilter || searchFilter) && (
          <button
            onClick={() => { setStatusFilter(""); setSearchFilter(""); setOffset(0); }}
            style={btnSecondary}
          >
            Reset
          </button>
        )}
      </div>

      <div style={{ marginBottom: 12, fontSize: 13, color: "#6b7280" }}>
        {total} total{statusFilter || searchFilter ? " (filtered)" : ""}
      </div>

      {loading ? (
        <p style={{ color: "#9ca3af" }}>Loading…</p>
      ) : items.length === 0 ? (
        <div style={{ background: "#fff", borderRadius: 10, border: "1px solid #e5e7eb", padding: 40, textAlign: "center", color: "#9ca3af" }}>
          No feedback found.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {items.map((item) => (
            <div key={item.id} style={{ background: "#fff", borderRadius: 10, border: "1px solid #e5e7eb", padding: "18px 20px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8, marginBottom: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <strong style={{ fontSize: 15, color: "#1a1d2e" }}>{item.tenant_name || `Tenant #${item.tenant_id ?? "\u2014"}`}</strong>
                  {statusBadge(item.status)}
                  <span style={{ fontSize: 12, color: "#9ca3af" }}>{formatTs(item.created_at)}</span>
                </div>
                <span style={{ fontSize: 12, color: "#6b7280" }}>
                  {item.failed_attempts} attempts {"\u00b7"} IP: <span style={{ fontFamily: "monospace" }}>{item.ip_address || "\u2014"}</span>
                </span>
              </div>

              <div style={{ fontSize: 13, color: "#374151", marginBottom: 6 }}>
                {item.message || <span style={{ color: "#9ca3af" }}>No message included.</span>}
              </div>
              <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 4 }}>
                QR key: <span style={{ fontFamily: "monospace", color: "#374151" }}>{item.qr_key ? item.qr_key.slice(0, 20) + "\u2026" : "\u2014"}</span>
                {item.property_id ? <span style={{ marginLeft: 12 }}>Property #{item.property_id}</span> : null}
              </div>

              <Diagnostics diagnostics={item.diagnostics} />

              {item.admin_reply && (
                <div style={{ marginTop: 10, padding: "10px 12px", borderRadius: 8, background: "#eff6ff", border: "1px solid #bfdbfe", fontSize: 13, color: "#1e40af" }}>
                  <strong>Your reply:</strong> {item.admin_reply}
                </div>
              )}

              {item.status === "open" && (
                <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid #f3f4f6", display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                  <input
                    value={replyText[item.id] || ""}
                    onChange={(e) => setReplyText((r) => ({ ...r, [item.id]: e.target.value }))}
                    placeholder="Provide a solution / fix\u2026"
                    disabled={busyId === item.id}
                    style={{ ...inputStyle, flex: 1, minWidth: 220 }}
                  />
                  <button
                    onClick={() => handleReply(item.id)}
                    disabled={busyId === item.id}
                    style={{ ...btnPrimary, opacity: busyId === item.id ? 0.6 : 1 }}
                  >
                    {busyId === item.id ? "Saving\u2026" : "Reply & Resolve"}
                  </button>
                  <button
                    onClick={() => handleResolve(item.id)}
                    disabled={busyId === item.id}
                    style={{ ...btnSecondary, opacity: busyId === item.id ? 0.6 : 1 }}
                  >
                    Mark resolved
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 12, marginTop: 16 }}>
          <button
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
            style={{ ...btnSecondary, opacity: offset === 0 ? 0.4 : 1 }}
          >
            Previous
          </button>
          <span style={{ fontSize: 13, color: "#6b7280" }}>
            Page {Math.floor(offset / limit) + 1} of {totalPages}
          </span>
          <button
            onClick={() => setOffset(offset + limit)}
            disabled={offset + limit >= total}
            style={{ ...btnSecondary, opacity: offset + limit >= total ? 0.4 : 1 }}
          >
            Next
          </button>
        </div>
      )}
    </Layout>
  );
}

const labelSm: React.CSSProperties = {
  display: "block", marginBottom: 4, fontSize: 11, fontWeight: 600,
  color: "#6b7280", textTransform: "uppercase", letterSpacing: 0.5,
};
const inputStyle: React.CSSProperties = {
  width: "100%", padding: "7px 10px", borderRadius: 6,
  border: "1.5px solid #d1d5db", fontSize: 13, outline: "none",
};
const selectStyle: React.CSSProperties = {
  padding: "7px 10px", borderRadius: 6,
  border: "1.5px solid #d1d5db", fontSize: 13, outline: "none",
  background: "#fff", minWidth: 140,
};
const btnSecondary: React.CSSProperties = {
  padding: "7px 16px", borderRadius: 6, border: "1.5px solid #d1d5db",
  background: "#fff", fontSize: 13, fontWeight: 500, cursor: "pointer",
};
const btnPrimary: React.CSSProperties = {
  padding: "7px 16px", borderRadius: 6, border: "none",
  background: "#3b4a6b", color: "#fff", fontSize: 13, fontWeight: 600, cursor: "pointer",
};
