import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api } from "@/services/api";
import { useToast } from "@/hooks/useToast";
import { useAuth } from "@/contexts/AuthContext";
import { Shield, Search, ChevronLeft, ChevronRight, Filter, X } from "lucide-react";
import { BrandWave } from '@shared/loading/BrandWave';

const ACTION_COLORS: Record<string, { bg: string; fg: string }> = {
  "Login Success":            { bg: "bg-emerald-100 dark:bg-emerald-900/30", fg: "text-emerald-700 dark:text-emerald-400" },
  "Login Failed - Wrong PIN": { bg: "bg-red-100 dark:bg-red-900/30", fg: "text-red-700 dark:text-red-400" },
  "Logout Success":           { bg: "bg-gray-100 dark:bg-gray-800/30", fg: "text-gray-600 dark:text-gray-400" },
  "Token Refreshed":          { bg: "bg-gray-100 dark:bg-gray-800/30", fg: "text-gray-600 dark:text-gray-400" },
  "Logout All Devices":       { bg: "bg-red-100 dark:bg-red-900/30", fg: "text-red-700 dark:text-red-400" },
  logout:                     { bg: "bg-gray-100 dark:bg-gray-800/30", fg: "text-gray-600 dark:text-gray-400" },
  totp_enabled:               { bg: "bg-emerald-100 dark:bg-emerald-900/30", fg: "text-emerald-700 dark:text-emerald-400" },
  totp_disabled:              { bg: "bg-red-100 dark:bg-red-900/30", fg: "text-red-700 dark:text-red-400" },
  totp_regenerated:           { bg: "bg-violet-100 dark:bg-violet-900/30", fg: "text-violet-700 dark:text-violet-400" },
  password_changed:           { bg: "bg-blue-100 dark:bg-blue-900/30", fg: "text-blue-700 dark:text-blue-400" },
  login_success:              { bg: "bg-emerald-100 dark:bg-emerald-900/30", fg: "text-emerald-700 dark:text-emerald-400" },
  login_failed:               { bg: "bg-red-100 dark:bg-red-900/30", fg: "text-red-700 dark:text-red-400" },
};

const APP_SOURCE_BADGE: Record<string, { label: string; cls: string }> = {
  landlord: { label: "You", cls: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" },
  tenant:   { label: "Tenant", cls: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" },
};

function actionBadge(action: string) {
  const c = ACTION_COLORS[action] || { bg: "bg-gray-100 dark:bg-gray-800/30", fg: "text-gray-700 dark:text-gray-300" };
  return (
    <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${c.bg} ${c.fg}`}>
      {action.replace(/_/g, " ")}
    </span>
  );
}

function appBadge(source: string) {
  const c = APP_SOURCE_BADGE[source] || { label: source, cls: "bg-gray-100 text-gray-600" };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${c.cls}`}>
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

export default function ActivityPage() {
  const { landlordUuid } = useAuth();
  const toast = useToast();
  const [logs, setLogs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const limit = 25;

  const [actionFilter, setActionFilter] = useState("");
  const [searchFilter, setSearchFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [actionTypes, setActionTypes] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  const fetchLogs = useCallback(async () => {
    if (!landlordUuid) return;
    setLoading(true);
    try {
      const data = await api.getActivityLogs(landlordUuid, {
        action_type: actionFilter || undefined,
        search: searchFilter || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        limit,
        offset,
      });
      setLogs(data.items);
      setTotal(data.total);
    } catch {
      toast.error("Failed to load activity logs");
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [landlordUuid, actionFilter, searchFilter, dateFrom, dateTo, offset]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  useEffect(() => {
    if (!landlordUuid) return;
    api.getActivityActionTypes(landlordUuid)
      .then((d) => setActionTypes(Array.isArray(d) ? d : []))
      .catch(() => {});
  }, [landlordUuid]);

  const hasFilters = actionFilter || searchFilter || dateFrom || dateTo;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="h-6 w-6" /> Activity
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Your actions and tenant activity across the portal
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowFilters(!showFilters)}
          className={hasFilters ? "border-primary text-primary" : ""}
        >
          <Filter className="h-4 w-4 mr-1" />
          Filters
          {hasFilters && (
            <span className="ml-1 h-5 w-5 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center">
              {[actionFilter, searchFilter, dateFrom, dateTo].filter(Boolean).length}
            </span>
          )}
        </Button>
      </div>

      {showFilters && (
        <Card>
          <CardContent className="pt-4">
            <div className="flex flex-wrap gap-3 items-end">
              <div className="flex-1 min-w-[150px]">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1 block">Action Type</label>
                <select
                  value={actionFilter}
                  onChange={(e) => { setActionFilter(e.target.value); setOffset(0); }}
                  className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value="">All Actions</option>
                  {actionTypes.map((a) => (
                    <option key={a} value={a}>{a.replace(/_/g, " ")}</option>
                  ))}
                </select>
              </div>
              <div className="flex-1 min-w-[180px]">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1 block">Search</label>
                <div className="relative">
                  <Search className="absolute left-2.5 top-2 h-4 w-4 text-muted-foreground" />
                  <Input
                    value={searchFilter}
                    onChange={(e) => setSearchFilter(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") { setOffset(0); fetchLogs(); } }}
                    placeholder="Action, IP, actor\u2026"
                    className="pl-8"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1 block">From</label>
                <Input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => { setDateFrom(e.target.value); setOffset(0); }}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1 block">To</label>
                <Input
                  type="date"
                  value={dateTo}
                  onChange={(e) => { setDateTo(e.target.value); setOffset(0); }}
                />
              </div>
              {hasFilters && (
                <Button variant="ghost" size="sm" onClick={() => { setActionFilter(""); setSearchFilter(""); setDateFrom(""); setDateTo(""); setOffset(0); }}>
                  <X className="h-4 w-4 mr-1" /> Clear
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <p className="text-sm text-muted-foreground">
        {total} total entries{hasFilters ? " (filtered)" : ""}
      </p>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground text-xs uppercase tracking-wide">Timestamp</th>
                  <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground text-xs uppercase tracking-wide">Actor</th>
                  <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground text-xs uppercase tracking-wide">Action</th>
                  <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground text-xs uppercase tracking-wide">IP Address</th>
                  <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground text-xs uppercase tracking-wide">Details</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-12 text-center text-muted-foreground">
                      <div className="flex items-center justify-center">
                        <BrandWave size="sm" label="Loading…" />
                      </div>
                    </td>
                  </tr>
                ) : logs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-12 text-center text-muted-foreground">No activity logs found</td>
                  </tr>
                ) : logs.map((log) => (
                  <tr key={`${log.app_source}-${log.id}`} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="px-4 py-2.5 whitespace-nowrap text-muted-foreground" title={log.created_at}>{formatTs(log.created_at)}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        {appBadge(log.app_source)}
                        <span className="font-medium">{log.actor_name || "\u2014"}</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5">{actionBadge(log.action)}</td>
                    <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground">{log.ip_address || "\u2014"}</td>
                    <td className="px-4 py-2.5 max-w-[200px]">
                      {log.meta && Object.keys(log.meta).length > 0 ? (
                        <span className="text-xs text-muted-foreground" title={JSON.stringify(log.meta, null, 2)}>
                          {Object.entries(log.meta).map(([k, v]) => `${k}=${String(v)}`).join(", ")}
                        </span>
                      ) : "\u2014"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
          >
            <ChevronLeft className="h-4 w-4 mr-1" /> Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {Math.floor(offset / limit) + 1} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setOffset(offset + limit)}
            disabled={offset + limit >= total}
          >
            Next <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      )}
    </div>
  );
}
