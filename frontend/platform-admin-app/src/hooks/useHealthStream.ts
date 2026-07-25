import { useEffect, useRef, useState } from "react";
import { API_BASE } from "../lib/runtime";

export interface HealthSnapshot {
  type: string;
  status: string;
  database: string;
  active_connections: number;
  uptime: string;
  timestamp: string;
}

/**
 * Subscribe to real-time system health via WebSocket.
 * Connects to /ws/health and receives periodic health snapshots (every 15s).
 * Automatically reconnects on disconnect.
 *
 * @param enabled - Whether to enable the stream (default: true)
 */
export function useHealthStream(enabled = true) {
  const [health, setHealth] = useState<HealthSnapshot | null>(null);
  const healthRef = useRef(health);
  healthRef.current = health;

  useEffect(() => {
    if (!enabled) return;

    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let unmounted = false;

    function connect() {
      if (unmounted) return;

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}${API_BASE}/ws/health`;

      ws = new WebSocket(wsUrl);

      ws.onmessage = (e) => {
        try {
          const snapshot = JSON.parse(e.data);
          if (snapshot.type === "HEALTH_UPDATE") {
            setHealth(snapshot);
          }
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (!unmounted) {
          reconnectTimer = setTimeout(connect, 5000);
        }
      };

      ws.onerror = () => {
        ws?.close();
      };
    }

    connect();

    return () => {
      unmounted = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [enabled]);

  return health;
}
