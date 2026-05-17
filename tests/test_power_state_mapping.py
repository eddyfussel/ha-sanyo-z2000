"""Tests for the projector status → is_on mapping."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.sanyo_z2000.coordinator import SanyoCoordinator


@pytest.mark.parametrize(
    ("status_code", "expected_is_on", "expected_label_contains"),
    [
        ("00", True, "Power ON"),
        ("40", True, "Countdown"),     # the bug fix: warmup must read as "on"
        ("80", False, "Standby"),
        ("20", False, "Cooling Down"),
        ("04", False, "Power Save"),
        ("88", False, "Standby"),
        ("21", False, "Cooling Down"),
        ("10", False, "Power Failure"),
    ],
)
async def test_is_on_mapping_covers_warmup(
    hass: HomeAssistant,
    status_code: str,
    expected_is_on: bool,
    expected_label_contains: str,
) -> None:
    """The switch's is_on must reflect the user's intent during warmup.

    Without code 40 mapping to is_on=True, the switch visually flips back
    to 'off' for the 20–30 seconds the projector spends in countdown.
    """
    coord = SanyoCoordinator(hass, device="/dev/fake")
    coord._serial = _fake_serial_returning({
        b"CR0\r": status_code,
        b"CR1\r": "4",                    # HDMI 1
        b"CR3\r": "00410",                # 410 hours
        b"CR6\r": " 31.5  35.2  32.8",
    })

    data = await coord._async_update_data()
    assert data.is_on is expected_is_on
    assert expected_label_contains in data.status_label


async def test_unreachable_projector_raises_update_failed(hass) -> None:
    """When the projector is unplugged the serial port still opens (the ESP32
    is independent), but CR0 times out. The coordinator must raise
    UpdateFailed so HA marks all entities as 'unavailable' — like other
    integrations do when their device is unreachable.
    """
    from homeassistant.helpers.update_coordinator import UpdateFailed

    coord = SanyoCoordinator(hass, device="/dev/fake")
    coord._serial = _fake_serial_returning({})  # any command → no response

    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


async def test_send_command_drains_buffer_after_previous_timeout(hass) -> None:
    """After a timed-out read, the next command must drain stale bytes first.

    Concrete scenario: previous CR6 timed out. A late '----  ----  ----'
    response then arrives in the read buffer. Without draining, the next
    CR0 read would return that string and the Projector Mode entity would
    surface 'Unknown (----  ----  ----)' — exactly the bug the user reported.
    """
    coord = SanyoCoordinator(hass, device="/dev/fake")
    fake = _fake_serial_returning({b"CR0\r": "00"})
    coord._serial = fake

    # Simulate the previous poll having timed out — buffer is "dirty"
    coord._buffer_might_be_dirty = True

    result = await coord._send_command(b"CR0\r")
    assert result == "00"
    # Drain was attempted
    assert fake.read.await_count >= 1
    # Flag is cleared after drain
    assert coord._buffer_might_be_dirty is False


async def test_failed_poll_closes_port_so_next_poll_can_recover(hass) -> None:
    """A failed poll must drop the serial port so the *next* poll opens a
    fresh one. Otherwise stale bytes from cancelled reads (or a dead
    ESPHome-proxy connection) leave entities stuck on 'unavailable'
    forever, even after the projector comes back online.
    """
    from homeassistant.helpers.update_coordinator import UpdateFailed

    coord = SanyoCoordinator(hass, device="/dev/fake")
    coord._serial = _fake_serial_returning({})  # CR0 times out

    with pytest.raises(UpdateFailed):
        await coord._async_update_data()

    # After the failed poll, _serial must be None so the next call
    # reopens via async_connect().
    assert coord._serial is None


async def test_temperature_placeholders_yield_none_silently(
    hass, caplog
) -> None:
    """When the projector is in Standby/Power Save it returns placeholders
    like '----' or 'I--' instead of real temperature values. These must:
      (a) not raise / not crash
      (b) leave the field as None
      (c) NOT spam the log on every poll
    """
    import logging
    coord = SanyoCoordinator(hass, device="/dev/fake")
    coord._serial = _fake_serial_returning({
        b"CR0\r": "04",                    # Power Save
        b"CR3\r": "00410",
        b"CR6\r": "----  ----  ----",      # placeholder seen in Power Save
    })

    with caplog.at_level(logging.DEBUG, logger="custom_components.sanyo_z2000"):
        data = await coord._async_update_data()

    assert data.temp1 is None
    assert data.temp2 is None
    assert data.temp3 is None
    assert "Could not parse temperature" not in caplog.text


def _fake_serial_returning(responses: dict[bytes, str]):
    """Build a MagicMock AsyncSerial that replies to known commands.

    Unknown commands raise asyncio.TimeoutError to simulate the projector
    being unplugged / unreachable.
    """
    import asyncio

    fake = MagicMock()
    fake.is_open = True

    pending: list[bytes] = []

    def write(data: bytes) -> None:
        pending.append(data)

    async def drain() -> None:
        return None

    async def readuntil(_sep: bytes) -> bytes:
        cmd = pending.pop(0)
        if cmd not in responses:
            raise asyncio.TimeoutError
        return responses[cmd].encode("ascii") + b"\r"

    fake.write = write
    fake.drain = AsyncMock(side_effect=drain)
    fake.readuntil = AsyncMock(side_effect=readuntil)
    fake.read = AsyncMock(return_value=b"")  # drain reads → "nothing pending"
    fake.close = AsyncMock()
    fake.abort = MagicMock()  # sync, force-close
    return fake
