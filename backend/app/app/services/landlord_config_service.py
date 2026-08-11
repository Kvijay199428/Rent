"""
app/services/landlord_config_service.py

Effective per-landlord configuration resolution for the "landlord" config
section (used by the Settings page and the PDF generator).

Precedence: per-landlord profile (landlord_profiles) overrides the global
landlord.json defaults. Landlords that never touched Settings keep the
global section via the fallback — so existing behaviour and PDF layout
are unchanged.
"""
from typing import Any, Dict

from app.core.config_service import config
from app.database.property_repository import get_landlord_profile, save_landlord_profile


def get_effective_landlord_config(landlord_id: int) -> Dict[str, Any]:
    """Global landlord section merged with the per-landlord profile."""
    global_section = dict(config.get("landlord", {}) or {})
    profile = get_landlord_profile(landlord_id) or {}
    global_section.update(profile)
    return global_section


def save_effective_landlord_config(landlord_id: int, section: Dict[str, Any]) -> None:
    """Persist the per-landlord override of the landlord section."""
    save_landlord_profile(landlord_id, dict(section or {}))
    config.reload("landlord")
