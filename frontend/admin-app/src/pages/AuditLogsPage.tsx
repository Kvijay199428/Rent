import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { fetchApi } from "../api/client";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";

interface AuditLog {
  id: number;
  app_source: string;
  action: string;
  actor_name: string | null;
  username: string | null;
  email: string | null;
  target_type: string | null;
  target_id: number | null;
  meta: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

function formatTs(ts: string): string {
  const d = new Date(ts);
  const date = d.toISOString().slice(0, 10);
  const time = d.toISOString().slice(11, 16);
  return `${date} ${time} (UTC)`;
}

const ACTION_CLASSES: Record<string, string> = {
  login_success: "bg-green-100 text-green-600",
  login_failed: "bg-red-100 text-red-600",
  logout: "bg-gray-100 text-gray-500",
  create_billing: "bg-blue-100 text-blue-600",
  create_tenant_guard: "bg-blue-100 text-blue-600",
  create_kyc: "bg-blue-100 text-blue-600",
  register_tenant: "bg-blue-100 text-blue-600",
  update_tenant: "bg-purple-100 text-purple-600",
  update_kyc: "bg-purple-100 text-purple-600",
  update_note: "bg-orange-50 text-orange-600",
  update_admin_reply: "bg-orange-50 text-orange-600",
  update_profile: "bg-orange-50 text-orange-600",
  update_preferences: "bg-orange-50 text-orange-600",
  delete_tenant: "bg-red-100 text-red-600",
  delete_kyc: "bg-red-100 text-red-600",
  submit_billing: "bg-blue-100 text-blue-600",
  submit_tenant_guard: "bg-blue-100 text-blue-600",
  reconcile_receipts: "bg-emerald-50 text-emerald-600",
  qr_scanned: "bg-green-100 text-green-600",
  change_password: "bg-orange-50 text-orange-600",
  reset_password: "bg-orange-50 text-orange-600",
  update_bank: "bg-orange-50 text-orange-600",
  update_billing_style: "bg-purple-100 text-purple-600",
  view_pin: "bg-indigo-100 text-indigo-600",
  view_auth: "bg-gray-100 text-gray-500",
  pin_enabled: "bg-green-100 text-green-600",
  pin_disabled: "bg-gray-100 text-gray-500",
  pin_login: "bg-blue-100 text-blue-600",
};

const APP_SOURCE_CLASSES: Record<string, { label: string; cls: string }> = {
  landlord_app: { label: "Landlord", cls: "bg-blue-100 text-blue-600" },
  admin_app: { label: "Admin", cls: "bg-purple-100 text-purple-600" },
  tenant_portal: { label: "Tenant", cls: "bg-green-100 text-green-600" },
};

function ActionBadge({ action }: { action: string }) {
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${
        ACTION_CLASSES[action] ?? "bg-gray-100 text-gray-700"
      }`}
      title={action}
    >
      {action.replace(/_/g, " ")}
    </span>
  );
}

function AppBadge({ source }: { source: string }) {
  const info = APP_SOURCE_CLASSES[source];
  if (!info) {
    return <span className="rounded-md bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-500">{source}</span>;
  }
  return (
    <span className={`inline-block rounded-md px-2 py-0.5 text-xs font-semibold ${info.cls}`}>{info.label}</span>
  );
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [limit] = useState(20);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [exporting, setExporting] = useState(false);

  const [appFilter, setAppFilter] = useState("all");
  const [actionFilter, setActionFilter] = useState("all");
  const [searchFilter, setSearchFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const params = () => {
    const p = new URLSearchParams();
    if (appFilter !== "all") p.set("app_source", appFilter);
    if (actionFilter !== "all") p.set("action", actionFilter);
    if (searchFilter) p.set("search", searchFilter);
    if (dateFrom) p.set("from", dateFrom);
    if (dateTo) p.set("to", dateTo);
    p.set("limit", String(limit));
    p.set("offset", String(offset));
    return p;
  };

  const fetchLogs = async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const res = await fetchApi(`/audit-logs?${params()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setLogs(data.items || []);
      setTotal(data.total || 0);
    } catch {
      setLoadError(true);
      setLogs([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLogs(); }, [offset, limit, appFilter, actionFilter, searchFilter, dateFrom, dateTo]);

  const resetFilters = () => {
    setAppFilter("all");
    setActionFilter("all");
    setSearchFilter("");
    setDateFrom("");
    setDateTo("");
    setOffset(0);
  };

  const hasFilters =
    appFilter !== "all" || actionFilter !== "all" || searchFilter !== "" || dateFrom !== "" || dateTo !== "";

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await fetchApi("/audit-logs/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          app_source: appFilter !== "all" ? appFilter : null,
          action: actionFilter !== "all" ? actionFilter : null,
          search: searchFilter || null,
          from: dateFrom || null,
          to: dateTo || null,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.jsonl`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Export failed. Check the console for details.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <Layout>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-[26px] font-bold text-[#1a1d2e]">Audit Logs</h1>
        <Button variant="outline" onClick={handleExport} disabled={exporting || logs.length === 0} className="font-semibold">
          {exporting ? "Exporting…" : "Export JSONL"}
        </Button>
      </div>

      <div className="mb-5 flex flex-wrap items-center gap-2 rounded-xl border border-gray-200 bg-white p-4">
        <Select value={appFilter} onValueChange={setAppFilter}>
          <SelectTrigger className="w-[130px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All apps</SelectItem>
            <SelectItem value="landlord_app">Landlord</SelectItem>
            <SelectItem value="admin_app">Admin</SelectItem>
            <SelectItem value="tenant_portal">Tenant</SelectItem>
          </SelectContent>
        </Select>
        <Select value={actionFilter} onValueChange={setActionFilter}>
          <SelectTrigger className="w-auto">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All actions</SelectItem>
            {Object.keys(ACTION_CLASSES).map((a) => (
              <SelectItem key={a} value={a}>{a.replace(/_/g, " ")}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          type="text"
          value={searchFilter}
          onChange={(e) => setSearchFilter(e.target.value)}
          placeholder="Search actor / target…"
          className="min-w-[180px] flex-1"
        />
        <div className="flex items-center gap-2">
          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="w-[150px]" />
          <span className="text-gray-400">→</span>
          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-[150px]" />
        </div>
        <Button variant="outline" size="sm" onClick={resetFilters} disabled={!hasFilters}>
          Reset
        </Button>
      </div>

      <Card className="overflow-hidden rounded-xl border border-gray-200">
        {loadError && (
          <div className="flex items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-[13px] text-amber-700">Couldn't load audit logs. Check the connection and try again.</p>
            <Button variant="outline" size="sm" onClick={fetchLogs} className="shrink-0">Retry</Button>
          </div>
        )}
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-[#f9fafb]">
              {["Timestamp", "App", "Actor", "Action", "Target", "IP Address", "Details"].map((h) => (
                <TableHead key={h} className="bg-[#f9fafb] text-[12px] font-semibold uppercase tracking-wide text-gray-700">
                  {h}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="p-10 text-center text-gray-400">Loading…</TableCell>
              </TableRow>
            ) : logs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="p-10 text-center text-gray-400">No audit logs found.</TableCell>
              </TableRow>
            ) : (
              logs.map((log) => (
                <TableRow key={`${log.app_source}-${log.id}`} className="border-b border-gray-100">
                  <TableCell className="whitespace-nowrap text-gray-500" title={log.created_at}>
                    {formatTs(log.created_at)}
                  </TableCell>
                  <TableCell><AppBadge source={log.app_source} /></TableCell>
                  <TableCell>
                    <div className="font-semibold text-[#1a1d2e]">{log.actor_name || log.username || log.email || "—"}</div>
                    {log.email && <div className="text-xs text-gray-400">{log.email}</div>}
                  </TableCell>
                  <TableCell><ActionBadge action={log.action} /></TableCell>
                  <TableCell className="text-gray-500">
                    {log.target_type ? `${log.target_type}${log.target_id ? ` #${log.target_id}` : ""}` : "—"}
                  </TableCell>
                  <TableCell className="whitespace-nowrap font-mono text-xs text-gray-500">{log.ip_address || "—"}</TableCell>
                  <TableCell className="max-w-[220px] whitespace-normal break-words">
                    {log.meta && Object.keys(log.meta).length > 0 ? (
                      <span
                        className="text-xs text-gray-500"
                        title={JSON.stringify(log.meta, null, 2)}
                      >
                        {Object.entries(log.meta).map(([k, v]) => `${k}=${String(v)}`).join(", ")}
                      </span>
                    ) : "—"}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Card>

      {total > limit && (
        <div className="mt-4 flex items-center justify-center gap-3">
          <Button variant="outline" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - limit))}>
            Previous
          </Button>
          <span className="text-[13px] text-gray-500">
            {offset + 1}–{Math.min(offset + limit, total)} of {total}
          </span>
          <Button variant="outline" disabled={offset + limit >= total} onClick={() => setOffset((o) => o + limit)}>
            Next
          </Button>
        </div>
      )}
    </Layout>
  );
}