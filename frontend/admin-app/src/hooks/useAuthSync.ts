import { useEffect, useRef } from "react";
import { getApiBaseUrl } from "@shared/api-config";

export interface AuthSyncEvent {
  type: string;
  [key: string]: any;
}

type AuthEventHandler = (event: AuthSyncEvent) => void;

/**
 * Subscribe to real-time auth state changes via WebSocket.
 * Connects to /ws/auth and listens for AUTH_STATE_CHANGED, TOTP_STATE_CHANGED, PASSWORD_RESET.
 * Automatically reconnects on disconnect.
 *
 * @param channel - Auth channel (e.g., "landlord:{uuid}")
 * @param onEvent - Callback invoked when an auth event is received
 * @param enabled - Whether to enable the connection (default: true)
 */
export function useAuthSync(channel: string, onEvent: AuthEventHandler, enabled = true) {
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

      const apiBase = getApiBaseUrl();
      let wsUrl: string;

      if (apiBase) {
        const wsBase = apiBase.replace(/^https?/, "ws");
        wsUrl = `${wsBase}/ws/auth?channel=${encodeURIComponent(channel)}`;
      } else {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        wsUrl = `${protocol}//${window.location.host}/rent/ws/auth?channel=${encodeURIComponent(channel)}`;
      }

      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
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
