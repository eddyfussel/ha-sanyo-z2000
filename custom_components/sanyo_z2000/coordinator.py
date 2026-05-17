"""DataUpdateCoordinator for Sanyo PLV-Z2000 via serial port (physical or ESPHome proxy)."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta

import serialx
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BAUD_RATE,
    BYTE_SIZE,
    CMD_READ_INPUT,
    CMD_READ_LAMP_TIME,
    CMD_READ_STATUS,
    CMD_READ_TEMPERATURE,
    COMMAND_DELAY_SECONDS,
    DOMAIN,
    INPUT_MAP,
    PARITY,
    POLL_INTERVAL_SECONDS,
    POWER_ON_STATUS_CODES,
    RESPONSE_TIMEOUT_SECONDS,
    STATUS_MAP,
    STOP_BITS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ProjectorData:
    """Snapshot of projector state after one poll cycle."""

    status_code: str = ""
    status_label: str = "Unknown"
    is_on: bool = False
    input_label: str | None = None
    lamp_hours: int | None = None
    temp1: float | None = None
    temp2: float | None = None
    temp3: float | None = None


class SanyoCoordinator(DataUpdateCoordinator[ProjectorData]):
    """Manages the serial connection and RS232 polling.

    The `device` value is whatever HA's SerialPortSelector returns — either a
    physical path (e.g. /dev/ttyUSB0) or an ESPHome proxy URL
    (e.g. esphome-hass://entry_id?port_name=...). `serialx` resolves both
    transparently.
    """

    def __init__(self, hass: HomeAssistant, device: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=POLL_INTERVAL_SECONDS),
        )
        self._device = device
        self._serial: serialx.AsyncSerial | None = None
        self._lock = asyncio.Lock()
        # Set after a read times out: the projector may still send a late
        # response, which would otherwise leak into the next command.
        self._buffer_might_be_dirty = False

    # ── Connection lifecycle ───────────────────────────────────────────────────

    async def async_connect(self) -> None:
        """Open the serial port."""
        self._serial = serialx.async_serial_for_url(
            self._device,
            baudrate=BAUD_RATE,
            byte_size=BYTE_SIZE,
            parity=PARITY,
            stopbits=STOP_BITS,
        )
        await self._serial.open()

    async def async_disconnect(self) -> None:
        """Close the serial port gracefully (entry unload path).

        Uses an awaited close() with a timeout. If the underlying connection
        is dead it would otherwise hang HA's unload — fall through to abort.
        """
        if self._serial is None:
            return
        try:
            await asyncio.wait_for(self._serial.close(), timeout=2.0)
        except (TimeoutError, OSError, serialx.SerialException):
            try:
                self._serial.abort()
            except (OSError, serialx.SerialException):
                pass
        self._serial = None
        self._buffer_might_be_dirty = False

    # ── Serial I/O ─────────────────────────────────────────────────────────────

    async def _send_command(self, command: bytes) -> str | None:
        """Send an RS232 command and return the CR-terminated response."""
        if self._serial is None or not self._serial.is_open:
            return None

        async with self._lock:
            if self._buffer_might_be_dirty:
                await self._drain_pending_bytes()
                self._buffer_might_be_dirty = False

            try:
                # write() is synchronous (mirrors asyncio.StreamWriter); only drain() awaits.
                self._serial.write(command)
                await self._serial.drain()
                raw = await asyncio.wait_for(
                    self._serial.readuntil(b"\r"),
                    timeout=RESPONSE_TIMEOUT_SECONDS,
                )
            except (TimeoutError, OSError, serialx.SerialException) as err:
                # A late response may still arrive after we time out and
                # would be misread as the next command's reply. Flag the
                # buffer dirty so we drain before the next write.
                self._buffer_might_be_dirty = True
                _LOGGER.debug("No response to %r: %s", command, err)
                return None

            # Strip trailing CR and decode
            response = raw.rstrip(b"\r").decode("ascii", errors="replace").strip()
            await asyncio.sleep(COMMAND_DELAY_SECONDS)
            return response

    async def _drain_pending_bytes(self) -> None:
        """Discard bytes left in the read buffer from a cancelled previous read.

        Without this, a delayed temperature response (`---- ---- ----`) from
        a previous poll's CR6 surfaces as the next poll's CR0 reply and the
        Projector Mode entity reports `Unknown (---- ---- ----)`.
        """
        if self._serial is None or not self._serial.is_open:
            return
        try:
            while True:
                stale = await asyncio.wait_for(
                    self._serial.read(1024), timeout=0.1
                )
                if not stale:
                    return
        except (TimeoutError, OSError, serialx.SerialException):
            return

    # ── Polling ────────────────────────────────────────────────────────────────

    async def _async_update_data(self) -> ProjectorData:
        """Poll all status read commands and return a ProjectorData snapshot.

        If a previous poll closed the serial port (after a failure), we
        reopen it transparently here so the integration recovers as soon
        as the projector comes back.
        """
        if self._serial is None or not self._serial.is_open:
            try:
                await self.async_connect()
            except (OSError, serialx.SerialException) as err:
                raise UpdateFailed(f"Cannot open serial port: {err}") from err

        data = ProjectorData()

        try:
            status_raw = await self._send_command(CMD_READ_STATUS)
            if not status_raw:
                # No response to the most basic status-read command means the
                # projector is unreachable (e.g. unplugged from mains — the
                # ESP32 still sends bytes but nothing answers on the bus).
                # Close the port so the next poll reopens cleanly — this
                # discards any stale bytes from cancelled reads and recovers
                # if the ESPHome proxy connection itself was dropped.
                await self._safe_close()
                raise UpdateFailed("Projector not responding to status read")

            data.status_code = status_raw
            data.status_label = STATUS_MAP.get(status_raw, f"Unknown ({status_raw})")
            # "On" covers normal projection (00) AND the warmup countdown (40),
            # otherwise the switch flips back to "off" for 20–30s after the
            # user turns it on, which feels broken.
            data.is_on = status_raw in POWER_ON_STATUS_CODES

            if data.is_on:
                input_raw = await self._send_command(CMD_READ_INPUT)
                if input_raw:
                    data.input_label = INPUT_MAP.get(input_raw)

            lamp_raw = await self._send_command(CMD_READ_LAMP_TIME)
            if lamp_raw and lamp_raw.isdigit():
                data.lamp_hours = int(lamp_raw)

            temp_raw = await self._send_command(CMD_READ_TEMPERATURE)
            if temp_raw:
                parts = temp_raw.split()
                if len(parts) >= 3:
                    # During Standby / Power Save the projector reports a
                    # placeholder per sensor — '----' or 'I--' (spec §8.7).
                    # We leave that field as None instead of logging on every
                    # poll cycle.
                    data.temp1 = _parse_temp(parts[0])
                    data.temp2 = _parse_temp(parts[1])
                    data.temp3 = _parse_temp(parts[2])

        except (OSError, serialx.SerialException) as err:
            await self._safe_close()
            raise UpdateFailed(f"Serial error: {err}") from err

        return data

    async def _safe_close(self) -> None:
        """Force-close the serial port (recovery path). Synchronous + non-blocking.

        Uses `abort()` rather than awaiting `close()` because the underlying
        TCP connection to an ESPHome proxy may be dead — `close()` would
        hang waiting for a half-closed handshake that never finishes, and
        the next poll would never run. With `abort()` we drop the transport
        immediately and let the next poll open a fresh one.
        """
        if self._serial is None:
            return
        try:
            self._serial.abort()
        except (OSError, serialx.SerialException):
            pass
        self._serial = None
        self._buffer_might_be_dirty = False

    async def async_send_command(self, command: bytes) -> None:
        """Send a fire-and-forget functional command; refresh state afterwards."""
        await self._send_command(command)
        await self.async_request_refresh()


def _parse_temp(value: str) -> float | None:
    """Parse one temperature sensor reading, returning None for placeholders.

    The projector reports placeholders like '----' (Power Save) or 'I--'
    (Standby / 10s after Power On) when a sensor isn't producing real data.
    """
    try:
        return float(value)
    except ValueError:
        return None
