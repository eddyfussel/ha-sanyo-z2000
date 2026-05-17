"""Tests for the Sanyo Z2000 config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sanyo_z2000.const import DOMAIN

from .conftest import (
    ESPHOME_PROXY_ENTRY_DATA,
    PATCH_COORD_FLOW,
    PATCH_COORD_INIT,
    VALID_ENTRY_DATA,
)


async def test_form_shows_on_init(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_successful_setup_physical_port(
    hass: HomeAssistant, mock_coordinator: MagicMock
) -> None:
    with patch(PATCH_COORD_FLOW, return_value=mock_coordinator), \
         patch(PATCH_COORD_INIT, return_value=mock_coordinator):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_ENTRY_DATA
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"] == VALID_ENTRY_DATA


async def test_successful_setup_esphome_proxy(
    hass: HomeAssistant, mock_coordinator: MagicMock
) -> None:
    with patch(PATCH_COORD_FLOW, return_value=mock_coordinator), \
         patch(PATCH_COORD_INIT, return_value=mock_coordinator):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], ESPHOME_PROXY_ENTRY_DATA
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"] == ESPHOME_PROXY_ENTRY_DATA


async def test_cannot_connect(hass: HomeAssistant) -> None:
    bad = MagicMock()
    bad.async_connect = AsyncMock(side_effect=OSError("port unavailable"))
    bad.async_disconnect = AsyncMock()

    with patch(PATCH_COORD_FLOW, return_value=bad):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_ENTRY_DATA
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_duplicate_entry_aborted(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """An already-configured device aborts the new flow."""
    mock_config_entry.add_to_hass(hass)

    with patch(PATCH_COORD_FLOW, return_value=mock_coordinator):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_ENTRY_DATA
        )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
