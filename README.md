# Sanremo Cube — Home Assistant integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/Oatie96/sanremo_cube/actions/workflows/validate.yml/badge.svg)](https://github.com/Oatie96/sanremo_cube/actions/workflows/validate.yml)
[![Test](https://github.com/Oatie96/sanremo_cube/actions/workflows/test.yml/badge.svg)](https://github.com/Oatie96/sanremo_cube/actions/workflows/test.yml)

A native [Home Assistant](https://www.home-assistant.io/) custom integration for the **Sanremo Cube** espresso machine. It communicates directly with the machine's local web panel over your LAN; no cloud account, bridge or custom dashboard widget is required.

## Features

- **Power control** — turn the machine on or put it into standby
- **Machine status** — boiler temperature, readiness, tank/filter/boiler alerts and shot time
- **Settings** — boiler setpoint, eco boiler setpoint and eco-mode timer
- **Counters** — coffee totals for today, week, month and lifetime, plus dispensed water
- **Scheduler control** — enable the weekly schedule and individual weekdays
- **Native weekly calendar** — create, edit and delete the Cube's scheduled on-time windows in Home Assistant's standard calendar UI

### Weekly schedule calendar

The integration creates a calendar entity named **Sanremo Cube**. A calendar event maps directly to a Cube on-time window:

```text
Event start → machine turns on
Event end   → machine turns off
```

The Cube supports up to **three windows per weekday**. The integration validates these machine limits before saving:

- up to three windows on a single weekday;
- 15-minute time increments;
- start and end on the same day; and
- an end time later than its start time.

The calendar is standard Home Assistant functionality. Add it through the normal dashboard editor if you want it on a dashboard; this integration intentionally does **not** install a custom Lovelace widget.

## Installation

### HACS custom repository

1. Open **HACS** in Home Assistant.
2. Open the ⋮ menu → **Custom repositories**.
3. Add `https://github.com/Oatie96/sanremo_cube` with category **Integration**.
4. Search for **Sanremo Cube** and install it.
5. Restart Home Assistant.
6. Go to **Settings → Devices & services → Add integration**.
7. Search for **Sanremo Cube** and enter the local hostname or IP address of the machine.
8. Enter a PIN only when the machine's own web panel requires one.

### Manual installation

Copy `custom_components/sanremo_cube` into `<config>/custom_components/`, restart Home Assistant, then add the integration through **Settings → Devices & services**.

## Entities

| Type | Provided functionality |
|---|---|
| Switches | Power, eco mode, steam booster, scheduler and individual scheduler weekdays |
| Numbers | Boiler setpoint, eco boiler setpoint and eco-mode timer |
| Sensors | Boiler temperature, shot time, filter days remaining, coffee counters and water total |
| Binary sensors | Ready, tank empty, steam-booster heating, alarm active, filter change needed and boiler fault |
| Calendar | `Sanremo Cube` weekly schedule calendar |

The `sanremo_cube.set_schedule` service remains available for automations or bulk changes. It writes up to three on/off windows for one weekday and can copy them to additional weekdays.

## Connectivity and security

The Cube web panel uses **unencrypted HTTP on the local network**. This integration follows the same local protocol.

- Keep the Cube on a trusted home LAN.
- Do not expose the machine's web panel or Home Assistant directly to the internet.
- Use a PIN in the Cube panel when available.
- The integration does not collect or send machine data to a cloud service.

## Protocol and compatibility

Sanremo does not publish an official API for the Cube web panel. This integration is based on the panel's local protocol and uses form-encoded requests to `/ajax/post`. It is maintained against observed Cube firmware behaviour and includes regression tests for the transport protocol, scheduler slot handling and calendar validation.

Machine firmware may differ. If an entity shows unexpected data or a control does not work, please open an issue with:

- Cube firmware version;
- the affected Home Assistant entity; and
- a description of the observed behaviour.

Never include your PIN, access tokens, private IP address or raw panel response in a public issue.

## Development checks

Before submitting a pull request, run:

```bash
python -m pytest tests -q
python -m compileall -q custom_components
python -m json.tool custom_components/sanremo_cube/manifest.json >/dev/null
git diff --check
```

GitHub Actions runs HACS validation, Home Assistant hassfest and the test suite for pushes and pull requests.

## License

This project is licensed under the [MIT License](LICENSE). It is provided **as is**, without warranty.
