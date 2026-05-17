"""Tests for write-only select entities — image mode and screen mode.

These selects have no status-read command on the Sanyo protocol, so we
remember the user's last choice locally and persist it across restarts.
"""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
)

from custom_components.sanyo_z2000.const import DOMAIN

from .conftest import PATCH_COORD_INIT, VALID_ENTRY_DATA


async def test_image_mode_persists_selection_after_pick(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """After picking an option, the dropdown stays on that value — no flicker to 'unknown'."""
    entity = "select.sanyo_plv_z2000_image_mode"
    assert hass.states.get(entity).state == "unknown"  # initial — never picked

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity, "option": "Vivid"},
        blocking=True,
    )

    # Optimistic update wrote 'Vivid' immediately
    assert hass.states.get(entity).state == "Vivid"

    # Simulate the coordinator pushing a fresh data refresh — the select
    # should NOT revert to 'unknown' because we hold the last-selected value.
    init_integration.runtime_data.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(entity).state == "Vivid"


async def test_screen_mode_persists_selection_after_pick(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    entity = "select.sanyo_plv_z2000_screen_mode"
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity, "option": "Zoom"},
        blocking=True,
    )
    assert hass.states.get(entity).state == "Zoom"

    init_integration.runtime_data.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(entity).state == "Zoom"


async def test_image_mode_restores_after_ha_restart(
    hass: HomeAssistant, mock_coordinator
) -> None:
    """A previously-selected image mode is restored from the state cache."""
    mock_restore_cache(
        hass,
        [
            _restored("select.sanyo_plv_z2000_image_mode", "Pure Cinema"),
        ],
    )

    entry = MockConfigEntry(
        domain=DOMAIN, data=VALID_ENTRY_DATA, unique_id="/dev/ttyUSB0"
    )
    entry.add_to_hass(hass)
    with patch(PATCH_COORD_INIT, return_value=mock_coordinator):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get("select.sanyo_plv_z2000_image_mode").state == "Pure Cinema"


async def test_image_mode_ignores_invalid_restored_state(
    hass: HomeAssistant, mock_coordinator
) -> None:
    """If a previously-saved value isn't in the options list, ignore it."""
    mock_restore_cache(
        hass,
        [
            _restored("select.sanyo_plv_z2000_image_mode", "OldRenamedMode"),
        ],
    )
    entry = MockConfigEntry(
        domain=DOMAIN, data=VALID_ENTRY_DATA, unique_id="/dev/ttyUSB0"
    )
    entry.add_to_hass(hass)
    with patch(PATCH_COORD_INIT, return_value=mock_coordinator):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get("select.sanyo_plv_z2000_image_mode").state == "unknown"


async def test_input_select_grace_window_blocks_stale_state(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Within the grace window, coordinator updates must NOT flip the input
    back to the old value. Prevents the 'click HDMI 2 → flips back to HDMI 1
    → finally settles on HDMI 2' flicker that the user reported."""
    entity = "select.sanyo_plv_z2000_input_source"
    assert hass.states.get(entity).state == "HDMI 1"

    await hass.services.async_call(
        "select", "select_option",
        {"entity_id": entity, "option": "HDMI 2"},
        blocking=True,
    )
    assert hass.states.get(entity).state == "HDMI 2"

    # Projector hasn't switched yet — still reports HDMI 1 on next poll.
    # Within the grace window, our entity must keep showing HDMI 2.
    entity_obj = _entity_for(hass, entity)
    entity_obj._handle_coordinator_update()
    await hass.async_block_till_done()
    assert hass.states.get(entity).state == "HDMI 2"


async def test_input_select_accepts_projector_state_after_grace_window(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Once the grace window elapses, coordinator state takes over."""
    entity = "select.sanyo_plv_z2000_input_source"
    await hass.services.async_call(
        "select", "select_option",
        {"entity_id": entity, "option": "HDMI 2"},
        blocking=True,
    )
    assert hass.states.get(entity).state == "HDMI 2"

    entity_obj = _entity_for(hass, entity)
    # Force the grace window to have already expired
    with patch(
        "custom_components.sanyo_z2000.select.time.monotonic",
        return_value=entity_obj._pending_until + 1,
    ):
        entity_obj._handle_coordinator_update()
        await hass.async_block_till_done()
    assert hass.states.get(entity).state == "HDMI 1"


def _entity_for(hass, entity_id):
    """Resolve an Entity instance from its entity_id by walking the platforms."""
    from homeassistant.helpers import entity_platform
    for platform in entity_platform.async_get_platforms(hass, "sanyo_z2000"):
        for ent in platform.entities.values():
            if ent.entity_id == entity_id:
                return ent
    raise LookupError(entity_id)


# ── helpers ─────────────────────────────────────────────────────────────────


def _restored(entity_id: str, state: str) -> State:
    """Build a minimal restored State for mock_restore_cache."""
    return State(entity_id, state)
