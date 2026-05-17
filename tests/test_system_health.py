"""Tests for the system_health endpoint."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    get_system_health_info,
)

from custom_components.sanyo_z2000.const import DOMAIN

from .conftest import PATCH_COORD_INIT, VALID_ENTRY_DATA


async def test_system_health(
    hass: HomeAssistant, mock_coordinator: MagicMock
) -> None:
    """System health surfaces projector count and polling state.

    system_health must be set up *before* our integration so that its
    auto-discovery picks up our callback registration when we load.
    """
    assert await async_setup_component(hass, "system_health", {})

    entry = MockConfigEntry(
        domain=DOMAIN, data=VALID_ENTRY_DATA, unique_id="/dev/ttyUSB0"
    )
    entry.add_to_hass(hass)
    with patch(PATCH_COORD_INIT, return_value=mock_coordinator):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    info = await get_system_health_info(hass, DOMAIN)
    assert info == {
        "configured_projectors": 1,
        "all_polling_successful": True,
    }
