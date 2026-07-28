import { useState, useEffect, useCallback } from "react";
import { getApiUrl } from "@shared/api-config";
import "./BroadcastBanner.css";

interface BroadcastConfig {
  enabled: boolean;
  message: string;
  type: "info" | "warning" | "maintenance";
  dismissible: boolean;
}

interface BroadcastBannerProps {
  healthUrl?: string;
}

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
    <div className={`broadcast-banner broadcast-${typeClass}`}>
      <div className="broadcast-banner-content">
        <span className="broadcast-banner-icon">
          {typeClass === "maintenance" ? "🔧" : typeClass === "warning" ? "⚠️" : "ℹ️"}
        </span>
        <span className="broadcast-banner-message">{broadcast.message}</span>
      </div>
      {broadcast.dismissible && (
        <button
          className="broadcast-banner-close"
          onClick={() => setDismissed(true)}
          aria-label="Dismiss"
        >
          ×
        </button>
      )}
    </div>
  );
}
