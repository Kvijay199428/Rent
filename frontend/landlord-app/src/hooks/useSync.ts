import { useEffect, useRef, useCallback } from "react";
import { API_BASE } from "@/lib/runtime";

export interface SyncEvent {
  type: string;
  [key: string]: any;
}

type EventHandler = (event: SyncEvent) => void;

/**
 * Subscribe to real-time sync events via WebSocket.
 * Automatically reconnects on disconnect.
 *
 * @param channel - Channel to subscribe to (e.g., "landlord:{uuid}", "platform_admin", "global")
 * @param onEvent - Callback invoked when an event is received
 * @param enabled - Whether to enable the connection (default: true)
 */
export function useSync(channel: string, onEvent: EventHandler, enabled = true) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!enabled || !channel) return;

    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let pingTimer: ReturnType<typeof setInterval> | null = null;
    let unmounted = false;

    function connect() {
      if (unmounted) return;

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}${API_BASE}/ws/sync?channel=${encodeURIComponent(channel)}`;

      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        // Send periodic pings to keep alive
        pingTimer = setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send("ping");
          }
        }, 30000);
      };

      ws.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data);
          if (event.type !== "pong") {
            onEventRef.current(event);
          }
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (pingTimer) clearInterval(pingTimer);
        if (!unmounted) {
          reconnectTimer = setTimeout(connect, 3000);
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
      if (pingTimer) clearInterval(pingTimer);
      ws?.close();
    };
  }, [channel, enabled]);
}
