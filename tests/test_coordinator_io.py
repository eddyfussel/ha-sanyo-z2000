"""Tests for the coordinator's serial I/O — both serialx API generations."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.sanyo_z2000.coordinator import SanyoCoordinator


@pytest.fixture
def coordinator(hass: HomeAssistant) -> SanyoCoordinator:
    return SanyoCoordinator(hass, device="/dev/fake")


async def test_send_command_with_async_write(
    coordinator: SanyoCoordinator,
) -> None:
    """serialx 1.8+ (HA 2026.6+): write() is a coroutine and must be awaited.

    Regression for the production bug where setup_retry kept firing because
    every write was a non-awaited coroutine — projector never saw the bytes,
    CR0 timed out, ConfigEntryNotReady, repeat.
    """
    fake = MagicMock()
    fake.is_open = True
    fake.write = AsyncMock(return_value=None)            # coroutine in 1.8+
    fake.drain = AsyncMock()
    fake.readuntil = AsyncMock(return_value=b"00\r")
    coordinator._serial = fake

    result = await coordinator._send_command(b"CR0\r")

    assert result == "00"
    fake.write.assert_awaited_once_with(b"CR0\r")
    fake.drain.assert_awaited_once()


async def test_send_command_with_sync_write(
    coordinator: SanyoCoordinator,
) -> None:
    """serialx 1.7.x: write() is sync. The defensive code path still works."""
    fake = MagicMock()
    fake.is_open = True
    fake.write = MagicMock(return_value=None)            # sync in 1.7.x
    fake.drain = AsyncMock()
    fake.readuntil = AsyncMock(return_value=b"00\r")
    coordinator._serial = fake

    result = await coordinator._send_command(b"CR0\r")

    assert result == "00"
    fake.write.assert_called_once_with(b"CR0\r")


async def test_send_command_handles_timeout(coordinator: SanyoCoordinator) -> None:
    """If the projector doesn't respond, _send_command returns None — never raises."""
    fake = MagicMock()
    fake.is_open = True
    fake.write = AsyncMock()
    fake.drain = AsyncMock()
    fake.readuntil = AsyncMock(side_effect=asyncio.TimeoutError)
    coordinator._serial = fake

    result = await coordinator._send_command(b"CR0\r")
    assert result is None
