import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { tenantApi } from "@/lib/api";
import { BrandWave } from "@shared/loading/BrandWave";
import { Shield } from "lucide-react";

const ACTION_COLORS: Record<string, { bg: string; fg: string }> = {
  "Login Success":            { bg: "bg-emerald-100 dark:bg-emerald-900/30", fg: "text-emerald-700 dark:text-emerald-400" },
  "Login Failed - Wrong PIN": { bg: "bg-red-100 dark:bg-red-900/30", fg: "text-red-700 dark:text-red-400" },
  "Logout Success":           { bg: "bg-gray-100 dark:bg-gray-800/30", fg: "text-gray-600 dark:text-gray-400" },
  "Token Refreshed":          { bg: "bg-gray-100 dark:bg-gray-800/30", fg: "text-gray-600 dark:text-gray-400" },
  "Logout All Devices":       { bg: "bg-red-100 dark:bg-red-900/30", fg: "text-red-700 dark:text-red-400" },
};

function actionBadge(action: string) {
  const c = ACTION_COLORS[action] || { bg: "bg-gray-100 dark:bg-gray-800/30", fg: "text-gray-700 dark:text-gray-300" };
  return (
    <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${c.bg} ${c.fg}`}>
      {action.replace(/_/g, " ")}
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

export default function ActivityLog() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    tenantApi.audit.getLogs({ limit: 50 })
      .then((res) => setLogs(res.data.items || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <BrandWave stacked label="Loading…" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold flex items-center gap-2">
          <Shield className="h-5 w-5" /> Activity
        </h2>
        <p className="text-sm text-muted-foreground">Your login and portal activity</p>
      </div>

      {logs.length === 0 ? (
        <p className="text-sm text-muted-foreground py-8 text-center">No activity recorded yet.</p>
      ) : (
        <ScrollArea className="h-[400px]">
          <div className="space-y-2 pr-4">
            {logs.map((log) => (
              <Card key={log.id} className="border-border/50">
                <CardContent className="p-3 flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      {actionBadge(log.action)}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 font-mono">
                      {log.ip_address || "\u2014"}
                    </p>
                  </div>
                  <span className="text-xs text-muted-foreground whitespace-nowrap" title={log.created_at}>
                    {formatTs(log.created_at)}
                  </span>
                </CardContent>
              </Card>
            ))}
          </div>
        </ScrollArea>
      )}
    </div>
  );
}
