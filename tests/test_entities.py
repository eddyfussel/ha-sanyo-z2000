"""Entity-level integration tests using the MockConfigEntry pattern."""
from __future__ import annotations

import pytest
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from .conftest import MOCK_PROJECTOR_DATA


async def test_power_switch_state(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    state = hass.states.get("switch.sanyo_plv_z2000_power")
    assert state is not None
    assert state.state == STATE_ON


async def test_projector_mode_sensor(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    state = hass.states.get("sensor.sanyo_plv_z2000_projector_mode")
    assert state is not None
    assert state.state == MOCK_PROJECTOR_DATA.status_label


async def test_lamp_hours_sensor(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    state = hass.states.get("sensor.sanyo_plv_z2000_lamp_hours")
    assert state is not None
    assert state.state == str(MOCK_PROJECTOR_DATA.lamp_hours)


@pytest.mark.parametrize(
    ("entity_id", "expected"),
    [
        ("sensor.sanyo_plv_z2000_temperature_sensor_1", MOCK_PROJECTOR_DATA.temp1),
        ("sensor.sanyo_plv_z2000_temperature_sensor_2", MOCK_PROJECTOR_DATA.temp2),
        ("sensor.sanyo_plv_z2000_temperature_sensor_3", MOCK_PROJECTOR_DATA.temp3),
    ],
)
async def test_temperature_sensors(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    entity_id: str,
    expected: float,
) -> None:
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == expected


async def test_input_select_current_option(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    state = hass.states.get("select.sanyo_plv_z2000_input_source")
    assert state is not None
    assert state.state == MOCK_PROJECTOR_DATA.input_label


async def test_select_option_counts(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    image = hass.states.get("select.sanyo_plv_z2000_image_mode")
    screen = hass.states.get("select.sanyo_plv_z2000_screen_mode")
    assert image is not None and len(image.attributes["options"]) == 14
    assert screen is not None and len(screen.attributes["options"]) == 8


async def test_all_entities_match_snapshot(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Snapshot full state of every entity under our domain.

    Catches accidental changes to entity IDs, attributes, units, icons,
    state values, options lists, etc.
    """
    domain_states = sorted(
        (s for s in hass.states.async_all() if s.domain in ("switch", "sensor", "select")
         and s.entity_id.startswith(("switch.sanyo_plv_z2000_",
                                     "sensor.sanyo_plv_z2000_",
                                     "select.sanyo_plv_z2000_"))),
        key=lambda s: s.entity_id,
    )
    serialised = [
        {
            "entity_id": s.entity_id,
            "state": s.state,
            "attributes": {
                k: v for k, v in s.attributes.items()
                # Skip volatile attrs that would make snapshots brittle
                if k not in ("supported_features",)
            },
        }
        for s in domain_states
    ]
    assert serialised == snapshot
