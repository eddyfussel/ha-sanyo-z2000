"""Tests for the integration's setup, unload, and migration logic."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sanyo_z2000 import async_migrate_entry
from custom_components.sanyo_z2000.const import DOMAIN

from .conftest import PATCH_COORD_INIT, VALID_ENTRY_DATA


async def test_setup_and_unload(
    hass: HomeAssistant, mock_coordinator: MagicMock
) -> None:
    """A clean entry transitions to LOADED, then NOT_LOADED on unload."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=VALID_ENTRY_DATA,
        unique_id="/dev/ttyUSB0",
    )
    entry.add_to_hass(hass)

    with patch(PATCH_COORD_INIT, return_value=mock_coordinator):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    mock_coordinator.async_disconnect.assert_awaited_once()


async def test_setup_succeeds_when_projector_unreachable(hass: HomeAssistant) -> None:
    """Setup must NOT go to setup_retry when the projector/ESP is offline.

    The bridge often shares power with the projector (energy-saving plug), so
    it's unreachable whenever the projector is unplugged. Failing setup would
    drop into setup_retry's exponential backoff and require a manual reload to
    recover. Instead the entry stays LOADED and the coordinator's 10s poll
    restores entities when power returns.
    """
    from unittest.mock import AsyncMock

    unreachable = MagicMock()
    unreachable.async_connect = AsyncMock(side_effect=OSError("port unavailable"))
    unreachable.async_disconnect = AsyncMock()
    # A real DataUpdateCoordinator.async_refresh() swallows the failure and
    # leaves last_update_success False; emulate the non-raising contract here.
    unreachable.async_refresh = AsyncMock()

    entry = MockConfigEntry(domain=DOMAIN, data=VALID_ENTRY_DATA, unique_id="x")
    entry.add_to_hass(hass)

    with patch(PATCH_COORD_INIT, return_value=unreachable):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    unreachable.async_refresh.assert_awaited_once()


async def test_migrate_entry_v1_is_noop(hass: HomeAssistant) -> None:
    """v1 entries don't need migration — the function still returns True."""
    entry = MockConfigEntry(domain=DOMAIN, data=VALID_ENTRY_DATA, version=1)
    assert await async_migrate_entry(hass, entry) is True


async def test_migrate_entry_future_version_refuses(hass: HomeAssistant) -> None:
    """Downgrade scenario: integration on an older code version sees newer entry."""
    entry = MockConfigEntry(domain=DOMAIN, data=VALID_ENTRY_DATA, version=99)
    assert await async_migrate_entry(hass, entry) is False
