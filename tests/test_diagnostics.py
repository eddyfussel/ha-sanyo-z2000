"""Tests for the diagnostics endpoint."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from custom_components.sanyo_z2000.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_redacts_device_and_includes_state(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Diagnostics dump must redact `device` and include coordinator data."""
    diagnostics = await async_get_config_entry_diagnostics(hass, init_integration)

    # Sanity: device must be redacted, not the raw path
    assert diagnostics["entry"]["data"]["device"] == "**REDACTED**"
    assert diagnostics["coordinator"]["data"]["lamp_hours"] == 410

    # Full shape snapshot
    assert diagnostics == snapshot
