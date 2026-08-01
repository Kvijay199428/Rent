"""
app/api/sync_ws.py

WebSocket endpoints for real-time sync across all frontend apps.
- /ws/sync  — general data sync (tenants, billing, settings)
- /ws/auth  — auth state sync (TOTP, password change, session)
- /ws/health — live system health stream
"""

import asyncio
import json
import logging
import time
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.websocket_manager import sync_manager

logger = logging.getLogger(__name__)

router = APIRouter()

_START_TIME = time.time()


# ─── /ws/sync — general data sync ───────────────────────────────────────────

@router.websocket("/ws/sync")
async def sync_websocket(
    websocket: WebSocket,
    channel: str = Query(...),
):
    """
    WebSocket endpoint for real-time data sync.

    Query params:
      channel: The channel to subscribe to (e.g., "landlord:123", "platform_admin", "global")

    Events received:
      { type: "TOTP_STATE_CHANGED", enabled: bool }
      { type: "PASSWORD_RESET", landlordId: int }
      { type: "AUTH_STATE_CHANGED", role: str, id: int }
      { type: "TENANT_CREATED", tenantId: int }
      { type: "TENANT_UPDATED", tenantId: int }
      { type: "TENANT_DELETED", tenantId: int }
      { type: "RECEIPT_CREATED", billNo: str, tenantId: int }
      { type: "RECEIPT_UPDATED", billNo: str, tenantId: int }
      { type: "KYC_UPLOADED", occupantUuid: str }
      { type: "SETTINGS_UPDATED", domain: str }
    """
    allowed_prefixes = ("landlord:", "tenant:", "platform_admin", "global")
    if not any(channel.startswith(p) for p in allowed_prefixes):
        await websocket.close(code=4003, reason="Invalid channel")
        return

    await sync_manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        sync_manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WS sync error on channel={channel}: {e}")
        sync_manager.disconnect(websocket, channel)


# ─── /ws/auth — auth state sync ─────────────────────────────────────────────

_AUTH_CHANNELS = ("landlord:", "platform_admin")

@router.websocket("/ws/auth")
async def auth_websocket(
    websocket: WebSocket,
    channel: str = Query(...),
):
    """
    WebSocket endpoint for real-time auth state sync.

    Query params:
      channel: Auth channel (e.g., "landlord:{uuid}", "platform_admin")

    Events received:
      { type: "AUTH_STATE_CHANGED", role: str, id: int }
      { type: "TOTP_STATE_CHANGED", enabled: bool, landlordId?: int }
      { type: "PASSWORD_RESET", landlordId: int }
    """
    if not any(channel.startswith(p) for p in _AUTH_CHANNELS):
        await websocket.close(code=4003, reason="Invalid auth channel")
        return

    await sync_manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        sync_manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WS auth error on channel={channel}: {e}")
        sync_manager.disconnect(websocket, channel)


# ─── /ws/health — live system health ────────────────────────────────────────

def _build_health_snapshot() -> dict:
    uptime_secs = int(time.time() - _START_TIME)
    hours, remainder = divmod(uptime_secs, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"

    return {
        "type": "HEALTH_UPDATE",
        "status": "ok",
        "database": "ok",
        "active_connections": sync_manager.get_total_count(),
        "uptime": uptime_str,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.websocket("/ws/health")
async def health_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for live system health stream.
    Pushes a health snapshot every 15 seconds.
    No authentication required — health is public.
    """
    await sync_manager.connect(websocket, "health")
    try:
        while True:
            snapshot = _build_health_snapshot()
            await websocket.send_text(json.dumps(snapshot))
            await asyncio.sleep(15)
    except WebSocketDisconnect:
        sync_manager.disconnect(websocket, "health")
    except Exception as e:
        logger.error(f"WS health error: {e}")
        sync_manager.disconnect(websocket, "health")
