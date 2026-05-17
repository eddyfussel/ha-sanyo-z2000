"""Sensor entities for Sanyo PLV-Z2000 (lamp hours, temperatures, status)."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SanyoConfigEntry
from .const import DOMAIN
from .coordinator import ProjectorData, SanyoCoordinator


@dataclass(frozen=True, kw_only=True)
class SanyoSensorDescription(SensorEntityDescription):
    value_fn: Callable[[ProjectorData], float | str | None]


SENSOR_DESCRIPTIONS: tuple[SanyoSensorDescription, ...] = (
    SanyoSensorDescription(
        key="projector_mode",
        name="Projector Mode",
        icon="mdi:information-outline",
        value_fn=lambda d: d.status_label,
    ),
    SanyoSensorDescription(
        key="lamp_hours",
        name="Lamp Hours",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:lightbulb-on-outline",
        value_fn=lambda d: d.lamp_hours,
    ),
    SanyoSensorDescription(
        key="temperature_1",
        name="Temperature Sensor 1",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.temp1,
    ),
    SanyoSensorDescription(
        key="temperature_2",
        name="Temperature Sensor 2",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.temp2,
    ),
    SanyoSensorDescription(
        key="temperature_3",
        name="Temperature Sensor 3",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.temp3,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SanyoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        SanyoSensor(entry.runtime_data, entry, desc) for desc in SENSOR_DESCRIPTIONS
    )


class SanyoSensor(CoordinatorEntity[SanyoCoordinator], SensorEntity):
    """Generic sensor backed by a ProjectorData field."""

    entity_description: SanyoSensorDescription

    def __init__(
        self,
        coordinator: SanyoCoordinator,
        entry: SanyoConfigEntry,
        description: SanyoSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Sanyo PLV-Z2000",
            manufacturer="Sanyo",
            model="PLV-Z2000",
        )

    @property
    def native_value(self) -> float | str | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
