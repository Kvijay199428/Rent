"""
app/core/websocket_manager.py

WebSocket connection manager for real-time sync across all frontend apps.
Supports per-channel subscriptions with automatic cleanup on disconnect.
"""

import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections organized by channel."""

    def __init__(self):
        self._channels: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        """Accept a WebSocket connection and add it to a channel."""
        await websocket.accept()
        if channel not in self._channels:
            self._channels[channel] = []
        self._channels[channel].append(websocket)
        logger.info(f"WS connect: channel={channel}, total={len(self._channels[channel])}")

    def disconnect(self, websocket: WebSocket, channel: str):
        """Remove a WebSocket connection from a channel."""
        if channel in self._channels:
            self._channels[channel] = [ws for ws in self._channels[channel] if ws != websocket]
            if not self._channels[channel]:
                del self._channels[channel]
            else:
                logger.info(f"WS disconnect: channel={channel}, remaining={len(self._channels[channel])}")

    async def broadcast(self, channel: str, event: dict):
        """Send an event to all connections in a channel."""
        if channel not in self._channels:
            return

        message = json.dumps(event)
        dead: List[WebSocket] = []

        for ws in self._channels[channel]:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        # Clean up dead connections
        for ws in dead:
            self.disconnect(ws, channel)

    async def broadcast_all(self, event: dict):
        """Send an event to all connections across all channels."""
        for channel in list(self._channels.keys()):
            await self.broadcast(channel, event)

    def get_channel_count(self, channel: str) -> int:
        """Return the number of active connections in a channel."""
        return len(self._channels.get(channel, []))

    def get_total_count(self) -> int:
        """Return the total number of active connections."""
        return sum(len(ws_list) for ws_list in self._channels.values())


# Global singleton
sync_manager = ConnectionManager()
