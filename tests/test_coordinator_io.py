"""Tests for the coordinator's serial I/O — guards against await-vs-sync bugs."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.sanyo_z2000.coordinator import SanyoCoordinator


@pytest.fixture
def coordinator(hass: HomeAssistant) -> SanyoCoordinator:
    return SanyoCoordinator(hass, device="/dev/fake")


async def test_send_command_uses_sync_write_async_drain(
    coordinator: SanyoCoordinator,
) -> None:
    """Regression: AsyncSerial.write() is synchronous; only drain()/readuntil() await.

    The signature in serialx mirrors asyncio.StreamWriter — calling `await
    serial.write(...)` returned None and crashed with 'NoneType' object can't
    be awaited' during async_setup_entry.
    """
    fake = MagicMock()
    fake.is_open = True
    fake.write = MagicMock(return_value=None)      # sync method
    fake.drain = AsyncMock()                        # coroutine
    fake.readuntil = AsyncMock(return_value=b"00\r")
    coordinator._serial = fake

    result = await coordinator._send_command(b"CR0\r")

    assert result == "00"
    fake.write.assert_called_once_with(b"CR0\r")
    fake.drain.assert_awaited_once()
    fake.readuntil.assert_awaited_once_with(b"\r")


async def test_send_command_handles_timeout(coordinator: SanyoCoordinator) -> None:
    """If the projector doesn't respond, _send_command returns None — never raises."""
    fake = MagicMock()
    fake.is_open = True
    fake.write = MagicMock()
    fake.drain = AsyncMock()
    fake.readuntil = AsyncMock(side_effect=asyncio.TimeoutError)
    coordinator._serial = fake

    result = await coordinator._send_command(b"CR0\r")
    assert result is None
