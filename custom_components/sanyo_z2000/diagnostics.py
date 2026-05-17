"""Diagnostics support for Sanyo PLV-Z2000."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import SanyoConfigEntry

# `device` may contain an ESPHome entry_id or a host path — not strictly secret,
# but redacting on principle (HA convention for any user-provided identifiers).
TO_REDACT = {"device"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SanyoConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    projector_data = asdict(coordinator.data) if coordinator.data else None

    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "unique_id_redacted": entry.unique_id is not None,
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "data": projector_data,
        },
    }
