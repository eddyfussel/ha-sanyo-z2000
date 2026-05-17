"""Tests for the power switch's optimistic state behaviour."""
from __future__ import annotations

import time
from unittest.mock import patch

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sanyo_z2000.const import (
    CMD_POWER_OFF_QUICK,
    CMD_POWER_ON,
    USER_INTENT_GRACE_SECONDS,
)


async def test_turn_on_optimistically_updates_state(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """turn_on flips the entity to 'on' immediately, without waiting for a poll."""
    coordinator = init_integration.runtime_data
    coordinator.data.is_on = False
    hass.states.async_set("switch.sanyo_plv_z2000_power", STATE_OFF)
    assert hass.states.get("switch.sanyo_plv_z2000_power").state == STATE_OFF

    await hass.services.async_call(
        "switch", "turn_on",
        {"entity_id": "switch.sanyo_plv_z2000_power"}, blocking=True,
    )

    assert hass.states.get("switch.sanyo_plv_z2000_power").state == STATE_ON
    coordinator.async_send_command.assert_awaited_with(CMD_POWER_ON)


async def test_turn_off_optimistically_updates_state(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    coordinator = init_integration.runtime_data
    assert hass.states.get("switch.sanyo_plv_z2000_power").state == STATE_ON

    await hass.services.async_call(
        "switch", "turn_off",
        {"entity_id": "switch.sanyo_plv_z2000_power"}, blocking=True,
    )

    assert hass.states.get("switch.sanyo_plv_z2000_power").state == STATE_OFF
    coordinator.async_send_command.assert_awaited_with(CMD_POWER_OFF_QUICK)


async def test_grace_window_blocks_stale_coordinator_state(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """After turn_on, a coordinator update that says 'still off' must not
    flip the switch back. Within the grace window the user's intent wins."""
    coordinator = init_integration.runtime_data

    # User clicks ON
    await hass.services.async_call(
        "switch", "turn_on",
        {"entity_id": "switch.sanyo_plv_z2000_power"}, blocking=True,
    )
    assert hass.states.get("switch.sanyo_plv_z2000_power").state == STATE_ON

    # Projector still reports standby — coordinator update should NOT flip us back.
    coordinator.data.is_on = False
    entity = _entity_for(hass, "switch.sanyo_plv_z2000_power")
    entity._handle_coordinator_update()
    await hass.async_block_till_done()
    assert hass.states.get("switch.sanyo_plv_z2000_power").state == STATE_ON


async def test_grace_window_expires(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """After the grace window elapses, coordinator state takes over again."""
    coordinator = init_integration.runtime_data
    await hass.services.async_call(
        "switch", "turn_on",
        {"entity_id": "switch.sanyo_plv_z2000_power"}, blocking=True,
    )
    entity = _entity_for(hass, "switch.sanyo_plv_z2000_power")

    # Simulate the grace window having elapsed
    with patch(
        "custom_components.sanyo_z2000.switch.time.monotonic",
        return_value=entity._user_intent_until + 1,
    ):
        coordinator.data.is_on = False
        entity._handle_coordinator_update()
        await hass.async_block_till_done()
        assert hass.states.get("switch.sanyo_plv_z2000_power").state == STATE_OFF


def _entity_for(hass, entity_id):
    from homeassistant.helpers import entity_platform
    for platform in entity_platform.async_get_platforms(hass, "sanyo_z2000"):
        for ent in platform.entities.values():
            if ent.entity_id == entity_id:
                return ent
    raise LookupError(entity_id)


# Smoke test for the constant being a sensible default
def test_grace_default_is_at_least_spec_minimum() -> None:
    """The Sanyo spec mentions 5s for input switch and 7s for power on from
    standby. Our grace window must cover both."""
    assert USER_INTENT_GRACE_SECONDS >= 8.0
