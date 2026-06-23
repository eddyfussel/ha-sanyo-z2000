"""Sanyo PLV-Z2000 RS232 integration via serial port (physical or ESPHome proxy)."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE, Platform
from homeassistant.core import HomeAssistant

from .coordinator import SanyoCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SWITCH, Platform.SENSOR, Platform.SELECT]

# Type alias for config entries carrying the coordinator as runtime_data.
type SanyoConfigEntry = ConfigEntry[SanyoCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SanyoConfigEntry) -> bool:
    """Set up Sanyo Z2000 from a config entry.

    We deliberately never raise ConfigEntryNotReady here, even when the
    projector (or the ESP bridging RS232) is unreachable. The bridge usually
    shares power with the projector itself — e.g. on an energy-saving smart
    plug — so it is offline whenever the projector is unplugged. Raising
    ConfigEntryNotReady would drop the entry into HA's setup_retry state,
    whose backoff grows exponentially to minutes; the integration would then
    fail to come back promptly when power returns and would need a manual
    reload (exactly the symptom users hit). Instead we always finish setup
    and let the DataUpdateCoordinator's fixed 10s poll mark entities
    unavailable while offline and restore them within seconds of the
    projector returning — no reload required.
    """
    coordinator = SanyoCoordinator(hass, device=entry.data[CONF_DEVICE])
    entry.runtime_data = coordinator

    # Non-raising first poll: populates state if the projector is reachable,
    # otherwise leaves the coordinator marked unsuccessful (entities
    # unavailable) without aborting setup.
    await coordinator.async_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SanyoConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_disconnect()
    return unloaded


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries to the current schema.

    Called by HA when `entry.version` is lower than `ConfigFlow.VERSION`.
    Currently we are on version 1 and have no migrations — this is a stub
    that keeps future schema changes (e.g. additional fields, options flow)
    upgradable instead of requiring users to delete and re-add the entry.
    """
    if entry.version > 1:
        # User downgraded the integration; cannot safely handle.
        return False

    # No migration steps for v1 yet.
    return True
