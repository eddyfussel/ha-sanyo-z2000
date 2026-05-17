"""Smoke tests against the real (unmocked) integration code path."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


async def test_form_can_render(hass: HomeAssistant) -> None:
    """Form must render without raising."""
    result = await hass.config_entries.flow.async_init(
        "sanyo_z2000", context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_real_submit_with_invalid_port(hass: HomeAssistant) -> None:
    """Submit a bogus port path — should surface as cannot_connect, NOT raise."""
    result = await hass.config_entries.flow.async_init(
        "sanyo_z2000", context={"source": "user"}
    )
    # No mocks here — real SanyoCoordinator tries to open the port and fails
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device": "/dev/nonexistent-fake-port"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_real_submit_esphome_url_without_esphome_loaded(hass: HomeAssistant) -> None:
    """Without the ESPHome integration loaded, esphome-hass:// URLs cannot resolve.

    This is what likely happens when the user submits the form: the test catches
    whether we surface the UnknownUriScheme error gracefully.
    """
    result = await hass.config_entries.flow.async_init(
        "sanyo_z2000", context={"source": "user"}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device": "esphome-hass://esphome/abc?port_name=uart_bus"}
    )
    assert result2["type"] == FlowResultType.FORM
    assert "base" in result2["errors"]
