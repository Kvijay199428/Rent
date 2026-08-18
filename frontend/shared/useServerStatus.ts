import { useEffect, useRef, useState } from "react";
import { getApiBaseUrl } from "./api-config";

export type ServerStatus = "online" | "degraded" | "offline";

export interface ServerState {
  status: ServerStatus;
  message: string | null;
  type: "info" | "warning" | "maintenance";
  dismissible: boolean;
}

const HEALTH_INTERVAL = 15000;
const FAIL_THRESHOLD = 3;
const MAX_BACKOFF = 60000;
const OFFLINE_MESSAGE =
  "Server is unreachable or under maintenance — we'll resume shortly. Your data is safe.";

function deriveWsUrl(httpBase: string): string {
  if (httpBase) {
    return httpBase.replace(/^https/, "wss").replace(/^http/, "ws");
  }
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}`;
}

export function useServerStatus(enabled = true): ServerState {
  const [state, setState] = useState<ServerState>({
    status: "online",
    message: null,
    type: "info",
    dismissible: true,
  });
  const failCount = useRef(0);
  const interval = useRef(HEALTH_INTERVAL);

  useEffect(() => {
    if (!enabled) return;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let unmounted = false;
    let ws: WebSocket | null = null;

    const base = getApiBaseUrl();
    const healthUrl = `${base || ""}/health`;

    async function checkHealth() {
      try {
        const res = await fetch(healthUrl, {
          credentials: "include",
          signal: AbortSignal.timeout(5000),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        failCount.current = 0;
        interval.current = HEALTH_INTERVAL;
        const bc = data?.broadcast;
        setState({
          status: "online",
          message: bc?.enabled && bc?.message ? bc.message : null,
          type: bc?.type ?? "info",
          dismissible: bc?.dismissible ?? true,
        });
      } catch {
        failCount.current += 1;
        if (failCount.current >= FAIL_THRESHOLD) {
          setState({
            status: "offline",
            message: OFFLINE_MESSAGE,
            type: "maintenance",
            dismissible: false,
          });
        } else {
          setState((s) => ({ ...s, status: "degraded" }));
        }
        interval.current = Math.min(interval.current * 2, MAX_BACKOFF);
      }
      if (!unmounted) timer = setTimeout(checkHealth, interval.current);
    }

    function connectWs() {
      const wsBase = deriveWsUrl(base);
      try {
        ws = new WebSocket(`${wsBase}/ws/sync?channel=global`);
      } catch {
        if (!unmounted) setTimeout(connectWs, 5000);
        return;
      }
      ws.onmessage = (e) => {
        try {
          const evt = JSON.parse(e.data);
          if (evt.type === "BROADCAST_UPDATED" && evt.broadcast) {
            const bc = evt.broadcast;
            setState((s) => ({
              ...s,
              message: bc.enabled && bc.message ? bc.message : null,
              type: bc.type ?? "info",
              dismissible: bc.dismissible ?? true,
            }));
          }
        } catch { /* ignore malformed */ }
      };
      ws.onclose = () => {
        if (!unmounted) setTimeout(connectWs, 5000);
      };
      ws.onerror = () => {
        ws?.close();
      };
    }

    function onVisible() {
      if (document.visibilityState === "visible") checkHealth();
    }

    checkHealth();
    connectWs();
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      unmounted = true;
      if (timer) clearTimeout(timer);
      ws?.close();
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [enabled]);

  return state;
}
