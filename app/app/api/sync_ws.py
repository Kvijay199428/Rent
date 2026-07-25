"""
app/api/sync_ws.py

WebSocket endpoint for real-time sync across all frontend apps.
Clients subscribe to a channel and receive events when data changes.
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.websocket_manager import sync_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/sync")
async def sync_websocket(
    websocket: WebSocket,
    channel: str = Query(...),
):
    """
    WebSocket endpoint for real-time sync.
    
    Query params:
      channel: The channel to subscribe to (e.g., "landlord:123", "platform_admin", "global")
    
    Events received:
      { type: "TOTP_STATE_CHANGED", enabled: bool }
      { type: "PASSWORD_RESET", landlordId: int }
      { type: "TENANT_CREATED", tenantId: int }
      { type: "TENANT_UPDATED", tenantId: int }
      { type: "TENANT_DELETED", tenantId: int }
      { type: "RECEIPT_CREATED", billNo: str, tenantId: int }
      { type: "RECEIPT_UPDATED", billNo: str, tenantId: int }
      { type: "KYC_UPLOADED", occupantUuid: str }
      { type: "SETTINGS_UPDATED", domain: str }
    """
    # Validate channel format
    allowed_prefixes = ("landlord:", "tenant:", "platform_admin", "global")
    if not any(channel.startswith(p) for p in allowed_prefixes):
        await websocket.close(code=4003, reason="Invalid channel")
        return

    await sync_manager.connect(websocket, channel)
    try:
        while True:
            # Keep connection alive; client may send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        sync_manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WS error on channel={channel}: {e}")
        sync_manager.disconnect(websocket, channel)
