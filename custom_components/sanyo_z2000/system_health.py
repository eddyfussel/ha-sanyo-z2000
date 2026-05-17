"""System health checks for Sanyo PLV-Z2000."""
from __future__ import annotations

from typing import Any

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN


@callback
def async_register(
    hass: HomeAssistant, register: system_health.SystemHealthRegistration
) -> None:
    """Register system health callbacks."""
    register.async_register_info(_async_system_health_info)


async def _async_system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Report aggregate state across all configured Sanyo entries."""
    entries = hass.config_entries.async_entries(DOMAIN)

    return {
        "configured_projectors": len(entries),
        "all_polling_successful": all(
            entry.runtime_data.last_update_success
            for entry in entries
            if entry.runtime_data is not None
        ),
    }
