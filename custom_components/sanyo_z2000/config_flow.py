"""Config flow for Sanyo PLV-Z2000 integration."""
from __future__ import annotations

import logging
from typing import Any

import serialx
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_DEVICE
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.selector import SerialPortSelector

from .const import DOMAIN
from .coordinator import SanyoCoordinator

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE): SerialPortSelector(),
    }
)


class SanyoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sanyo PLV-Z2000."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            device = user_input[CONF_DEVICE]
            await self.async_set_unique_id(device)
            self._abort_if_unique_id_configured()

            coordinator = SanyoCoordinator(self.hass, device=device)
            try:
                await coordinator.async_connect()
            except ConfigEntryNotReady:
                # ESPHome integration registered the stub handler but the real one
                # isn't loaded yet (the picked port belongs to an ESPHome device
                # whose entry hasn't finished setting up). Treat as cannot_connect.
                _LOGGER.warning("ESPHome handler not ready for %s", device)
                errors["base"] = "cannot_connect"
            except (
                ValueError,
                ConnectionError,
                OSError,
                TimeoutError,
                serialx.SerialException,
            ) as err:
                _LOGGER.warning("Cannot open serial port %s: %s", device, err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception opening %s", device)
                errors["base"] = "unknown"
            else:
                await coordinator.async_disconnect()
                return self.async_create_entry(
                    title="Sanyo PLV-Z2000",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
