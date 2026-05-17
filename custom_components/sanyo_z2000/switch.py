"""Power switch entity for Sanyo PLV-Z2000."""
from __future__ import annotations

import time

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SanyoConfigEntry
from .const import (
    CMD_POWER_OFF_QUICK,
    CMD_POWER_ON,
    DOMAIN,
    USER_INTENT_GRACE_SECONDS,
)
from .coordinator import SanyoCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SanyoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([SanyoPowerSwitch(entry.runtime_data, entry)])


class SanyoPowerSwitch(CoordinatorEntity[SanyoCoordinator], SwitchEntity):
    """Power switch with grace-window optimistic state.

    The Sanyo PLV-Z2000 takes several seconds to transition between standby
    and the Countdown / Cooling-Down phases (spec §4.9 mentions a 7s window).
    During that time, status reads still return the *old* state. Without
    a grace window, the switch would flip back to the old value on the
    next poll, then back to the new value, then back again — visibly
    flickering.
    """

    _attr_name = "Power"
    _attr_icon = "mdi:projector"

    _user_intent_is_on: bool | None = None
    _user_intent_until: float = 0.0

    def __init__(self, coordinator: SanyoCoordinator, entry: SanyoConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_power"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Sanyo PLV-Z2000",
            manufacturer="Sanyo",
            model="PLV-Z2000",
        )

    @property
    def is_on(self) -> bool:
        # Within the grace window, prefer the user's expressed intent so the
        # UI doesn't flicker while the projector is still transitioning.
        if (
            self._user_intent_is_on is not None
            and time.monotonic() < self._user_intent_until
        ):
            return self._user_intent_is_on
        return self.coordinator.data.is_on if self.coordinator.data else False

    async def async_turn_on(self, **kwargs: object) -> None:
        self._set_user_intent(True)
        await self.coordinator.async_send_command(CMD_POWER_ON)

    async def async_turn_off(self, **kwargs: object) -> None:
        # Use Quick Power Off (C01) — the regular Power Off (C02) shows an OSD
        # confirmation and only powers down on the *second* invocation, which
        # makes the switch feel broken when toggled from the HA frontend.
        self._set_user_intent(False)
        await self.coordinator.async_send_command(CMD_POWER_OFF_QUICK)

    def _set_user_intent(self, is_on: bool) -> None:
        """Record the user's last expressed intent and refresh HA's state."""
        self._user_intent_is_on = is_on
        self._user_intent_until = time.monotonic() + USER_INTENT_GRACE_SECONDS
        self.async_write_ha_state()
