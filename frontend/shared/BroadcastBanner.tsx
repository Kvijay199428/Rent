import { useEffect, useState } from "react";
import { useServerStatus } from "./useServerStatus";
import "./BroadcastBanner.css";

export default function BroadcastBanner() {
  const { status, message, type, dismissible } = useServerStatus();
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    setDismissed(false);
  }, [message]);

  if (!message || (dismissible && dismissed)) return null;

  const typeClass =
    type === "maintenance" ? "maintenance" : type === "warning" ? "warning" : "info";

  return (
    <div className={`broadcast-banner broadcast-${typeClass}`} role="alert" aria-live="polite">
      <div className="broadcast-banner-content">
        <span className="broadcast-banner-icon">
          {type === "maintenance" ? "🔧" : type === "warning" ? "⚠️" : "ℹ️"}
        </span>
        <span className="broadcast-banner-message">{message}</span>
        {status === "offline" && (
          <span className="broadcast-banner-retry">Retrying automatically…</span>
        )}
      </div>
      {dismissible && (
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
