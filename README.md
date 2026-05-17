# ha-sanyo-z2000

Home Assistant integration for the Sanyo PLV-Z2000 projector over RS232.

Works with either a USB-to-serial adapter plugged into your HA host, or — more usefully — an ESP32 running ESPHome's `serial_proxy` to bridge the projector to your network. HA's built-in serial port picker shows both.

## Hardware

You need an RS232 level shifter (MAX3232 based). A plain 3.3V TTL cable doesn't push enough voltage and the projector silently ignores it — that's where I lost the first day.

My setup is a [DTECH USB-RS232 adapter](https://www.amazon.de/dp/B0FJRX7N3T) wired to an ESP32. The 3D-printed housing for the adapter is in [`hardware/`](hardware/). The original wiring approach was a port of [SerialChiller](https://github.com/lasselukkari/SerialChiller); the current ESPHome config lives in [`esphome/`](esphome/).

Cable: projector's Mini-8-Pin control port to DB9. Pinout in the [Sanyo spec](docs/RS232C_Basic_PLV-Z2000.pdf).

## Install

Via HACS:

1. HACS → ⋮ → *Custom repositories* → add this repo's URL as type *Integration*.
2. Install, restart HA.
3. Set up the ESPHome device through the official ESPHome integration first — that's what registers the serial proxy.
4. *Settings → Devices & Services → Add Integration → Sanyo PLV-Z2000*.
5. Pick the proxy from the *Serial Proxies* group in the port dropdown.

Manual: copy `custom_components/sanyo_z2000/` into your HA config and restart.

## Entities

| Entity | Notes |
|---|---|
| Power | Switch. Uses Quick Power Off, one click is enough. |
| Projector Mode | Status text (Power ON, Standby, Cooling Down, ...). |
| Lamp Hours | Total runtime. |
| Temperature 1/2/3 | Internal sensors, °C. Unavailable while the projector is in Standby. |
| Input Source | HDMI 1/2, Component, ... Reads back from the projector. |
| Image Mode | 14 picture presets. Write-only — the last pick persists across restarts. |
| Screen Mode | Aspect / zoom modes. Write-only — the last pick persists across restarts. |

When the projector is unplugged, everything goes *unavailable* until it's back.

## RS232 reference

Machine-readable: [`docs/commands.yaml`](docs/commands.yaml).

19200 8N1, ASCII commands terminated by CR. Commands start with `C` (e.g. `C53\r` for HDMI 1); status reads start with `CR` (e.g. `CR0\r` for projector state).

## Disclaimer

Built with the help of Anthropic's Claude. Every change was reviewed, but AI can still get things wrong — especially around hardware behaviour it can't observe.

Provided as-is, no warranty. If something breaks your projector, your HA setup, or an automation, that's on you. Open an issue if you spot something off and I'll take a look.
