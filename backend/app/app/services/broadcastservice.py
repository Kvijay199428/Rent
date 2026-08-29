"""Central helper to update the global broadcast and fan it out over WebSocket."""

import logging

log = logging.getLogger("broadcast")

DEFAULT_BROADCAST = {"enabled": False, "message": "", "type": "info", "dismissible": True}

MAINTENANCE_MESSAGE = (
    "PropAura is under maintenance — we'll resume shortly. "
    "Your data is safe. Please don't close this page."
)


def get_broadcast() -> dict:
    from app.core.config_service import ConfigService
    return ConfigService().get("broadcast", dict(DEFAULT_BROADCAST))


async def set_broadcast(enabled: bool, message: str = "", type: str = "info",
                        dismissible: bool = True) -> dict:
    """Save broadcast config and push it to every connected client instantly."""
    from app.core.config_service import ConfigService

    payload = {
        "enabled": enabled,
        "message": message,
        "type": type,
        "dismissible": dismissible,
    }
    ConfigService().save("broadcast", payload)

    try:
        from app.core.websocket_manager import sync_manager
        await sync_manager.broadcast("global", {
            "type": "BROADCAST_UPDATED",
            "broadcast": payload,
        })
    except Exception as e:
        log.debug("WS broadcast push failed (non-fatal): %s", e)

    return payload


async def maintenance_on() -> dict:
    return await set_broadcast(
        enabled=True, message=MAINTENANCE_MESSAGE,
        type="maintenance", dismissible=False,
    )


async def maintenance_off() -> dict:
    return await set_broadcast(enabled=False)
