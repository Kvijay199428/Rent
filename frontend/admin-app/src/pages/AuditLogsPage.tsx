import { useState, useEffect, useCallback } from "react";
import Layout from "../components/Layout";
import { API_BASE } from "../lib/runtime";

const ACTION_COLORS: Record<string, { bg: string; fg: string }> = {
  login_success:       { bg: "#dcfce7", fg: "#16a34a" },
  login_password_ok:   { bg: "#dbeafe", fg: "#2563eb" },
  login_failed:        { bg: "#fef2f2", fg: "#dc2626" },
  login_locked_out:    { bg: "#fff7ed", fg: "#ea580c" },
  login_totp_failed:   { bg: "#fef2f2", fg: "#dc2626" },
  logout:              { bg: "#f3f4f6", fg: "#6b7280" },
  totp_regenerated:    { bg: "#f5f3ff", fg: "#7c3aed" },
  totp_enabled:        { bg: "#ecfdf5", fg: "#059669" },
  totp_disabled:       { bg: "#fef2f2", fg: "#dc2626" },
  password_changed:    { bg: "#eff6ff", fg: "#2563eb" },
  password_revealed:   { bg: "#fdf2f8", fg: "#db2777" },
  password_reset:      { bg: "#fef9c3", fg: "#a16207" },
  profile_updated:     { bg: "#ecfdf5", fg: "#059669" },
  landlord_totp_toggled: { bg: "#fefce8", fg: "#ca8a04" },
  tenant_created:      { bg: "#dcfce7", fg: "#16a34a" },
  tenant_updated:      { bg: "#dbeafe", fg: "#2563eb" },
  tenant_archive:      { bg: "#fef9c3", fg: "#a16207" },
  tenant_delete:       { bg: "#fef2f2", fg: "#dc2626" },
  bill_created:        { bg: "#dcfce7", fg: "#16a34a" },
  bill_updated:        { bg: "#dbeafe", fg: "#2563eb" },
  bill_deleted:        { bg: "#fef2f2", fg: "#dc2626" },
  backup_created:      { bg: "#f5f3ff", fg: "#7c3aed" },
  backup_restored:     { bg: "#fef9c3", fg: "#a16207" },
  settings_updated:    { bg: "#ecfdf5", fg: "#059669" },
  Token_Refreshed:     { bg: "#f3f4f6", fg: "#6b7280" },
  "Logout All Devices": { bg: "#fef2f2", fg: "#dc2626" },
};

const APP_SOURCE_COLORS: Record<string, { bg: string; fg: string; label: string }> = {
  platform_admin: { bg: "#ede9fe", fg: "#7c3aed", label: "Platform" },
  landlord:       { bg: "#dbeafe", fg: "#2563eb", label: "Landlord" },
  tenant:         { bg: "#dcfce7", fg: "#16a34a", label: "Tenant" },
};

function actionBadge(action: string) {
  const c = ACTION_COLORS[action] || { bg: "#f3f4f6", fg: "#374151" };
  return (
    <span style={{
      display: "inline-block", padding: "2px 10px", borderRadius: 9999,
      fontSize: 12, fontWeight: 600, background: c.bg, color: c.fg,
      whiteSpace: "nowrap",
    }}>
      {action.replace(/_/g, " ")}
    </span>
  );
}

function appBadge(source: string) {
  const c = APP_SOURCE_COLORS[source] || { bg: "#f3f4f6", fg: "#374151", label: source };
  return (
    <span style={{
      display: "inline-block", padding: "2px 10px", borderRadius: 9999,
      fontSize: 11, fontWeight: 700, background: c.bg, color: c.fg,
      whiteSpace: "nowrap", textTransform: "uppercase", letterSpacing: 0.5,
    }}>
      {c.label}
    </span>
  );
}

function formatTs(ts: string) {
  if (!ts) return "\u2014";
  try {
    const d = new Date(ts + (ts.includes("Z") ? "" : "Z"));
    return d.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
  } catch { return ts; }
}

interface AuditEntry {
  id: number;
  app_source: string;
  actor_id: number;
  actor_name: string;
  action: string;
  target_type: string | null;
  target_id: number | null;
  ip_address: string;
  meta: Record<string, unknown>;
  created_at: string;
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const [limit] = useState(30);

  const [actionFilter, setActionFilter] = useState("");
  const [appFilter, setAppFilter] = useState("");
  const [searchFilter, setSearchFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [actionTypes, setActionTypes] = useState<string[]>([]);

  const [exporting, setExporting] = useState(false);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (actionFilter) params.set("action_type", actionFilter);
      if (appFilter) params.set("app_source", appFilter);
      if (searchFilter) params.set("search", searchFilter);
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      params.set("limit", String(limit));
      params.set("offset", String(offset));

      const res = await fetch(`${API_BASE}/audit-logs?${params}`, { credentials: "include" });
      if (!res.ok) throw new Error("Failed to load");
      const data = await res.json();
      setLogs(data.items);
      setTotal(data.total);
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [actionFilter, appFilter, searchFilter, dateFrom, dateTo, offset, limit]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (appFilter) params.set("app_source", appFilter);
    fetch(`${API_BASE}/audit-logs/actions?${params}`, { credentials: "include" })
      .then((r) => r.ok ? r.json() : [])
      .then((d) => setActionTypes(Array.isArray(d) ? d : []))
      .catch(() => {});
  }, [appFilter]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (actionFilter) params.set("action_type", actionFilter);
      if (appFilter) params.set("app_source", appFilter);
      if (searchFilter) params.set("search", searchFilter);
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);

      const res = await fetch(`${API_BASE}/audit-logs/export?${params}`, { credentials: "include" });
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.jsonl`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      alert("Export failed. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  const resetFilters = () => {
    setActionFilter("");
    setAppFilter("");
    setSearchFilter("");
    setDateFrom("");
    setDateTo("");
    setOffset(0);
  };

  const hasFilters = actionFilter || appFilter || searchFilter || dateFrom || dateTo;
  const totalPages = Math.ceil(total / limit);

  return (
    <Layout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, color: "#1a1d2e" }}>Audit Logs</h1>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "#6b7280" }}>
            Unified activity across Platform, Landlord, and Tenant apps
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={handleExport}
            disabled={exporting || logs.length === 0}
            style={{
              padding: "8px 18px", borderRadius: 8, border: "1.5px solid #d1d5db",
              background: "#fff", fontSize: 13, fontWeight: 600, cursor: exporting ? "wait" : "pointer",
              opacity: logs.length === 0 ? 0.5 : 1,
            }}
          >
            {exporting ? "Exporting\u2026" : "Export JSONL"}
          </button>
        </div>
      </div>

      <div style={{
        display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap", alignItems: "flex-end",
        padding: "14px 16px", borderRadius: 10, background: "#fff", border: "1px solid #e5e7eb",
      }}>
        <div>
          <label style={labelSm}>App</label>
          <select
            value={appFilter}
            onChange={(e) => { setAppFilter(e.target.value); setOffset(0); }}
            style={selectStyle}
          >
            <option value="">All Apps</option>
            <option value="platform_admin">Platform Admin</option>
            <option value="landlord">Landlord</option>
            <option value="tenant">Tenant</option>
          </select>
        </div>
        <div>
          <label style={labelSm}>Action Type</label>
          <select
            value={actionFilter}
            onChange={(e) => { setActionFilter(e.target.value); setOffset(0); }}
            style={selectStyle}
          >
            <option value="">All Actions</option>
            {actionTypes.map((a) => (
              <option key={a} value={a}>{a.replace(/_/g, " ")}</option>
            ))}
          </select>
        </div>
        <div style={{ flex: 1, minWidth: 180 }}>
          <label style={labelSm}>Search</label>
          <input
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { setOffset(0); fetchLogs(); } }}
            placeholder="Action, IP, actor\u2026"
            style={inputStyle}
          />
        </div>
        <div>
          <label style={labelSm}>From</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setOffset(0); }}
            style={inputStyle}
          />
        </div>
        <div>
          <label style={labelSm}>To</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setOffset(0); }}
            style={inputStyle}
          />
        </div>
        {hasFilters && (
          <button onClick={resetFilters} style={{ ...btnSecondary, marginBottom: 1 }}>
            Reset
          </button>
        )}
      </div>

      <div style={{ marginBottom: 12, fontSize: 13, color: "#6b7280" }}>
        {total} total entries{hasFilters ? ` (filtered)` : ""}
      </div>

      <div style={{ borderRadius: 10, border: "1px solid #e5e7eb", overflow: "hidden", background: "#fff" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                <th style={thStyle}>Timestamp</th>
                <th style={thStyle}>App</th>
                <th style={thStyle}>Actor</th>
                <th style={thStyle}>Action</th>
                <th style={thStyle}>Target</th>
                <th style={thStyle}>IP Address</th>
                <th style={thStyle}>Details</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} style={{ padding: 40, textAlign: "center", color: "#9ca3af" }}>
                    Loading\u2026
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: 40, textAlign: "center", color: "#9ca3af" }}>
                    No audit logs found
                  </td>
                </tr>
              ) : logs.map((log) => (
                <tr key={`${log.app_source}-${log.id}`} style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={tdStyle} title={log.created_at}>{formatTs(log.created_at)}</td>
                  <td style={tdStyle}>{appBadge(log.app_source)}</td>
                  <td style={tdStyle}>
                    <span style={{ fontWeight: 600, color: "#1a1d2e" }}>{log.actor_name || "\u2014"}</span>
                  </td>
                  <td style={tdStyle}>{actionBadge(log.action)}</td>
                  <td style={tdStyle}>
                    {log.target_type ? (
                      <span style={{ color: "#6b7280" }}>
                        {log.target_type}{log.target_id ? ` #${log.target_id}` : ""}
                      </span>
                    ) : "\u2014"}
                  </td>
                  <td style={{ ...tdStyle, fontFamily: "monospace", fontSize: 12 }}>{log.ip_address || "\u2014"}</td>
                  <td style={{ ...tdStyle, maxWidth: 220 }}>
                    {log.meta && Object.keys(log.meta).length > 0 ? (
                      <span style={{ color: "#6b7280", fontSize: 12 }} title={JSON.stringify(log.meta, null, 2)}>
                        {Object.entries(log.meta).map(([k, v]) => `${k}=${String(v)}`).join(", ")}
                      </span>
                    ) : "\u2014"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

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

const thStyle: React.CSSProperties = {
  padding: "10px 14px", textAlign: "left", fontWeight: 600, color: "#374151",
  fontSize: 12, textTransform: "uppercase", letterSpacing: 0.5, whiteSpace: "nowrap",
};
const tdStyle: React.CSSProperties = {
  padding: "10px 14px", color: "#374151", verticalAlign: "middle",
};
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
  background: "#fff", minWidth: 150,
};
const btnSecondary: React.CSSProperties = {
  padding: "7px 16px", borderRadius: 6, border: "1.5px solid #d1d5db",
  background: "#fff", fontSize: 13, fontWeight: 500, cursor: "pointer",
};
