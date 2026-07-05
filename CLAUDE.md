# CLAUDE.md

HA custom integration for the Sanyo PLV-Z2000 projector over RS232. The projector speaks an ASCII command protocol (commands in [`docs/commands.yaml`](docs/commands.yaml)) and we talk to it through `serialx`, which transparently handles physical USB-serial adapters and ESPHome `serial_proxy` URLs. Architecture mirrors the official `denon_rs232` integration.

## Layout

```
custom_components/sanyo_z2000/   The integration
docs/commands.yaml               Source of truth for the RS232 protocol
esphome/                         ESPHome configs
tests/                           pytest suite (no hardware needed)
```

## Dev workflow

macOS prereqs: `brew install python@3.14 uv go-task`.

```
task setup              venv + symlink integration into config/
task run                Local HA at :8123
task test               pytest
task cov                pytest + coverage
task lint               ruff
task clean              Wipe runtime state — keeps venv
task snapshot-update    Regenerate Syrupy snapshots
```

`task run` needs `CPATH=...MacOSX.sdk/usr/include/c++/v1` on macOS for runtime C-extension builds; the Taskfile sets it.

## Things to know

**The `serial_proxy` URI handler only registers when the `usb` component is loaded.** That's why `manifest.json` lists `usb` as a hard dependency. Without it, physical ports still appear in the dropdown but ESPHome proxies don't.

**`hassil` and `home-assistant-intents` are in dev deps explicitly.** HA pip-installs them lazily for the `conversation` integration, but the WS `get_services` handler imports every base component eagerly. Skip them and you get `ModuleNotFoundError` on first UI interaction.

**The power switch sends `C01` (Quick Power Off).** `C02` shows a confirmation OSD and needs to be sent twice. If you want to expose both, add custom services rather than touching the switch.

**`is_on=True` for both status `00` (on) and `40` (warmup).** Treating `40` as off makes the switch visibly flip back for 20–30s after the user turns it on.

**User-intent grace window (12s).** After a user command, ignore coordinator state for a few seconds. The projector reports the *old* value for a few seconds after an input switch (§4.11), which otherwise causes a HDMI1 → HDMI2 → HDMI1 → HDMI2 flicker.

**Image/Screen mode have no status-read.** They use `RestoreEntity` for persistence; the last user pick survives restarts. Input does have CR1 readback so it eventually matches the projector.

**Setup never raises `ConfigEntryNotReady`.** The RS232 bridge usually shares power with the projector (energy-saving smart plug), so it's offline whenever the projector is unplugged. If `async_setup_entry` failed in that state, the entry would land in `setup_retry` whose backoff grows exponentially to minutes — so it wouldn't recover promptly when power returns and would need a manual reload (the exact symptom users reported). Instead setup always succeeds; `async_setup_entry` calls the non-raising `coordinator.async_refresh()` and the fixed 10s poll restores entities within seconds of the device returning. Validation of a bad device still happens at config-flow time, not at runtime.

**Unreachable projector = `UpdateFailed` = all entities unavailable.** No silent stale data. On failure we force-close via `abort()` (not awaited `close()`, which can hang on a dead ESPHome-proxy TCP socket and block the next poll); the next poll opens a fresh transport.

**All device I/O catches `CONNECTION_ERRORS`, not just `OSError`.** When the ESP is on the network but its ESPHome API isn't connected yet, serialx's esphome transport raises `aioesphomeapi.APIConnectionError` (e.g. "Not connected to <name>@<ip>"), which inherits from `Exception`, not `OSError`. Catch it via the `CONNECTION_ERRORS` tuple at every I/O boundary (open, send, drain, close) so it becomes a clean `UpdateFailed` instead of a coordinator "Unexpected error" traceback on every 10s poll. The import is guarded so the integration still loads if serialx is ever installed without the `[esphome]` extra.

**Buffer-dirty flag.** A timed-out `readuntil` doesn't stop the projector from eventually sending its response — those bytes land in serialx's buffer and would be misread as the next command's reply (the classic symptom: `Projector Mode: Unknown (----  ----  ----)` because a stale CR6 reply leaked into a CR0 read). After any timeout we set `_buffer_might_be_dirty`; the next `_send_command` drains pending bytes before writing.

**`serialx` flipped `write()` from sync to async between 1.7.x and 1.8.x.** HA pulls whichever version matches its core; that may not match what `uv.lock` resolves to. We call I/O methods through `_maybe_await(...)` which awaits only if the return value is a coroutine. Don't "simplify" this — getting it wrong silently drops the write (`RuntimeWarning: coroutine '...' was never awaited`), CR0 times out, and the integration ends up in `setup_retry` for weeks before anyone notices.

## Adding a command

`const.py` (bytes + map dict) → `docs/commands.yaml` (docs) → wire up in `switch.py` / `sensor.py` / `select.py`.

## Changing the entry schema

Bump `ConfigFlow.VERSION`, add a branch in `async_migrate_entry`, add a test in `tests/test_init.py`. The stub already refuses downgrades.

## Tests

Use the official HA pattern: `MockConfigEntry` + `add_to_hass` + `async_setup`, not the config-flow path. Patch `SanyoCoordinator` at both `config_flow.SanyoCoordinator` and `sanyo_z2000.SanyoCoordinator` — HA hits both. Snapshots in `tests/__snapshots__/` are checked in.

## Don't

- Commit `esphome/secrets.yaml`.
- Edit `esphome/local-config.yaml` — legacy uartex config, kept as reference only.
- Put projector logic into ESPHome; this integration is ESPHome-agnostic.
