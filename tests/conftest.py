"""Shared test fixtures for the Sanyo Z2000 integration.

Follows Home Assistant's developer-testing conventions:
https://developers.home-assistant.io/docs/development_testing
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sanyo_z2000.const import DOMAIN
from custom_components.sanyo_z2000.coordinator import ProjectorData

MOCK_PROJECTOR_DATA = ProjectorData(
    status_code="00",
    status_label="Power ON",
    is_on=True,
    input_label="HDMI 1",
    lamp_hours=410,
    temp1=31.5,
    temp2=35.2,
    temp3=32.8,
)

VALID_ENTRY_DATA = {"device": "/dev/ttyUSB0"}
ESPHOME_PROXY_ENTRY_DATA = {"device": "esphome-hass://esphome/abc123?port_name=uart_bus"}

# Patch locations for the SanyoCoordinator class (config flow + entry setup)
PATCH_COORD_FLOW = "custom_components.sanyo_z2000.config_flow.SanyoCoordinator"
PATCH_COORD_INIT = "custom_components.sanyo_z2000.SanyoCoordinator"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: HomeAssistant,
) -> None:
    """Enable the sanyo_z2000 custom component for every test."""


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """SanyoCoordinator double with preset projector data and async methods.

    Returns a fresh `ProjectorData` per test so that tests which mutate
    `coordinator.data.*` do not leak state into later tests.
    """
    from dataclasses import replace
    from datetime import timedelta

    coord = MagicMock()
    coord.async_connect = AsyncMock()
    coord.async_disconnect = AsyncMock()
    coord.async_config_entry_first_refresh = AsyncMock()
    coord.async_request_refresh = AsyncMock()
    coord.async_send_command = AsyncMock()
    coord.data = replace(MOCK_PROJECTOR_DATA)  # fresh copy per test
    coord.last_update_success = True
    coord.update_interval = timedelta(seconds=10)
    return coord


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """A ready-to-add MockConfigEntry for the integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Sanyo PLV-Z2000",
        data=VALID_ENTRY_DATA,
        unique_id=VALID_ENTRY_DATA["device"],
    )


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_coordinator: MagicMock,
) -> AsyncGenerator[MockConfigEntry]:
    """Fully set up the integration with a mocked coordinator.

    Uses the official `MockConfigEntry → add_to_hass → async_setup` pattern
    instead of going through the config flow. This exercises the same code
    path HA takes when restoring entries on boot.
    """
    mock_config_entry.add_to_hass(hass)
    with patch(PATCH_COORD_INIT, return_value=mock_coordinator):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    yield mock_config_entry
