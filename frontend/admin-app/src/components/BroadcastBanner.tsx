import { useState, useEffect, useCallback } from "react";
import { getApiUrl } from "@shared/api-config";
import { cn } from "../lib/utils";

interface BroadcastConfig {
  enabled: boolean;
  message: string;
  type: "info" | "warning" | "maintenance";
  dismissible: boolean;
}

interface BroadcastBannerProps {
  healthUrl?: string;
}

const typeClasses: Record<string, string> = {
  info: "bg-blue-800 text-white",
  warning: "bg-amber-800 text-white",
  maintenance: "bg-red-800 text-white",
};

export default function BroadcastBanner({ healthUrl }: BroadcastBannerProps) {
  const [broadcast, setBroadcast] = useState<BroadcastConfig | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const url = healthUrl || getApiUrl("/health");

  const fetchBroadcast = useCallback(async () => {
    try {
      const res = await fetch(url, { credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        if (data.broadcast?.enabled && data.broadcast.message) {
          setBroadcast(data.broadcast);
        } else {
          setBroadcast(null);
        }
      }
    } catch {
      // Silently ignore — broadcast is non-critical
    }
  }, [url]);

  useEffect(() => {
    fetchBroadcast();
    const interval = setInterval(fetchBroadcast, 30000);
    return () => clearInterval(interval);
  }, [fetchBroadcast]);

  if (!broadcast || dismissed) return null;

  const typeClass = broadcast.type || "info";

  return (
    <div className={cn(
      "sticky top-0 z-[9999] flex items-center justify-between px-4 py-2.5 text-sm font-medium leading-[1.4]",
      "animate-[broadcast-slide-in_0.3s_ease-out]",
      typeClasses[typeClass]
    )}>
      <div className="flex flex-1 items-center gap-2.5">
        <span className="shrink-0 text-base">
          {typeClass === "maintenance" ? "🔧" : typeClass === "warning" ? "⚠️" : "ℹ️"}
        </span>
        <span className="flex-1">{broadcast.message}</span>
      </div>
      {broadcast.dismissible && (
        <button
          className="shrink-0 cursor-pointer border-none bg-transparent p-0 text-[22px] font-bold leading-none text-inherit opacity-70 transition-opacity hover:opacity-100"
          onClick={() => setDismissed(true)}
          aria-label="Dismiss"
        >
          ×
        </button>
      )}
    </div>
  );
}