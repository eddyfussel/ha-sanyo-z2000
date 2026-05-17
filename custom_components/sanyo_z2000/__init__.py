"""Sanyo PLV-Z2000 RS232 integration via serial port (physical or ESPHome proxy)."""
from __future__ import annotations

import logging

import serialx
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .coordinator import SanyoCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SWITCH, Platform.SENSOR, Platform.SELECT]

# Type alias for config entries carrying the coordinator as runtime_data.
type SanyoConfigEntry = ConfigEntry[SanyoCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SanyoConfigEntry) -> bool:
    """Set up Sanyo Z2000 from a config entry."""
    coordinator = SanyoCoordinator(hass, device=entry.data[CONF_DEVICE])

    try:
        await coordinator.async_connect()
    except ConfigEntryNotReady:
        # The ESPHome stub handler raises this directly — propagate to let HA retry.
        raise
    except (
        ValueError,
        ConnectionError,
        OSError,
        TimeoutError,
        serialx.SerialException,
    ) as err:
        raise ConfigEntryNotReady(f"Cannot open serial port: {err}") from err

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
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
