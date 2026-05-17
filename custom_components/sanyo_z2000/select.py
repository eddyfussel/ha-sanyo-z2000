"""Select entities for Sanyo PLV-Z2000 (input, image mode, screen mode)."""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SanyoConfigEntry
from .const import (
    DOMAIN,
    IMAGE_MODE_CMD_MAP,
    IMAGE_MODE_OPTIONS,
    INPUT_CMD_MAP,
    INPUT_MAP,
    SCREEN_MODE_CMD_MAP,
    SCREEN_MODE_OPTIONS,
    USER_INTENT_GRACE_SECONDS,
)
from .coordinator import ProjectorData, SanyoCoordinator


@dataclass(frozen=True, kw_only=True)
class SanyoSelectDescription(SelectEntityDescription):
    options: list[str]
    # Read the current option from coordinator data, or None if the projector
    # does not expose a status-read command for this select.
    current_option_fn: Callable[[ProjectorData], str | None]
    cmd_map: dict[str, bytes]


SELECT_DESCRIPTIONS: tuple[SanyoSelectDescription, ...] = (
    SanyoSelectDescription(
        key="input",
        name="Input Source",
        icon="mdi:import",
        options=list(INPUT_MAP.values()),
        current_option_fn=lambda d: d.input_label,
        cmd_map=INPUT_CMD_MAP,
    ),
    SanyoSelectDescription(
        key="image_mode",
        name="Image Mode",
        icon="mdi:image-filter-hdr",
        options=IMAGE_MODE_OPTIONS,
        # The Sanyo PLV-Z2000 protocol has no status-read command for the
        # image mode — we can only write it. Falls back to the entity's
        # restored last-selected value (see SanyoSelect below).
        current_option_fn=lambda _: None,
        cmd_map=IMAGE_MODE_CMD_MAP,
    ),
    SanyoSelectDescription(
        key="screen_mode",
        name="Screen Mode",
        icon="mdi:aspect-ratio",
        options=SCREEN_MODE_OPTIONS,
        # Same as image mode — no status-read command exists.
        current_option_fn=lambda _: None,
        cmd_map=SCREEN_MODE_CMD_MAP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SanyoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        SanyoSelect(entry.runtime_data, entry, desc) for desc in SELECT_DESCRIPTIONS
    )


class SanyoSelect(CoordinatorEntity[SanyoCoordinator], SelectEntity, RestoreEntity):
    """Select entity that sends an RS232 command when changed.

    For selects whose value cannot be read back from the projector (image
    mode, screen mode), the last user-selected option is persisted via
    `RestoreEntity` so the dropdown does not flip to 'unknown' on the next
    coordinator update or after HA restarts.
    """

    entity_description: SanyoSelectDescription
    _last_selected: str | None = None
    _pending_until: float = 0.0  # monotonic deadline; coordinator overrides suppressed until then

    def __init__(
        self,
        coordinator: SanyoCoordinator,
        entry: SanyoConfigEntry,
        description: SanyoSelectDescription,
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
        self._attr_options = description.options

    async def async_added_to_hass(self) -> None:
        """Restore the last user-selected option after HA restart, then sync
        from the projector if a poll has already populated the coordinator."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in self._attr_options:
            self._last_selected = last_state.state
        # Pull authoritative state if the projector has already reported it
        self._refresh_from_coordinator()

    @property
    def current_option(self) -> str | None:
        return self._last_selected

    async def async_select_option(self, option: str) -> None:
        cmd = self.entity_description.cmd_map.get(option)
        if cmd is None:
            return
        # Optimistic update + grace window:
        # The projector keeps reporting the OLD value for up to 5s (spec §4.11)
        # after an input switch, so suppress coordinator overrides until the
        # device has had time to settle on the new state.
        self._last_selected = option
        self._pending_until = time.monotonic() + USER_INTENT_GRACE_SECONDS
        self.async_write_ha_state()
        await self.coordinator.async_send_command(cmd)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Sync the displayed value with whatever the projector reports.

        For Input (CR1 status-read), this normally overrides the optimistic
        value with the projector's truth — but only after the grace window
        elapses. For image_mode/screen_mode (no status-read command),
        `current_option_fn` returns None and the user's last selection
        persists indefinitely.
        """
        self._refresh_from_coordinator()
        super()._handle_coordinator_update()

    def _refresh_from_coordinator(self) -> None:
        # User just made a selection — trust them, the projector is still settling.
        if time.monotonic() < self._pending_until:
            return
        if self.coordinator.data is None:
            return
        from_projector = self.entity_description.current_option_fn(
            self.coordinator.data
        )
        if from_projector is not None:
            self._last_selected = from_projector
