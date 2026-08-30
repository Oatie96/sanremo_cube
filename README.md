# Sanremo Cube — Home Assistant integration

A native Home Assistant custom integration for the **Sanremo Cube** espresso
machine controller (Net Software Srl), built by reverse-engineering the
machine's own local web panel (`cube.html` / `cube.js`). No cloud account,
no bridge — it talks straight to the machine over your LAN.

## What you get

- **Device page** for the machine (Settings → Devices & Services)
- **Switches**: power, eco mode, steam booster, scheduler on/off, and one
  switch per weekday to enable/disable that day's programming
- **Numbers**: boiler setpoint, eco boiler setpoint, eco-mode timer
- **Sensors**: boiler temperature, shot time, filter days remaining,
  coffees today/week/month/total, total water erogated
- **Binary sensors**: ready, tank empty, steam booster heating, alarm
  active, filter-change needed, boiler fault
- **Service** `sanremo_cube.set_schedule` — write up to three on/off windows
  for one weekday, with an option to copy the same windows onto other days
  in one call (mirrors the panel's own "copy to days")

## Install (HACS custom repository)

1. Push this folder to your own GitHub repo, e.g. `ha-sanremo-cube`.
2. In Home Assistant: HACS → the ⋮ menu → **Custom repositories** → add
   your repo URL, category **Integration**.
3. Install "Sanremo Cube" from HACS, restart Home Assistant.
4. Settings → Devices & Services → **Add Integration** → search
   "Sanremo Cube" → enter the machine's IP address.
5. Leave the PIN field empty unless your panel is configured to require a
   login PIN — plenty of Cube panels on a trusted home LAN have none, and
   this integration works without it in that case.

If you'd rather skip HACS: copy `custom_components/sanremo_cube` straight
into your `<config>/custom_components/` folder and restart.

## Notes and caveats — please read

This was built entirely from the machine's own client-side JavaScript, not
from official documentation (Sanremo doesn't publish one for this local
API), and verified live against one machine only as far as: reading state,
and turning the machine on from standby. Everything else — every sensor,
the setpoints, and the scheduler write path — follows the same code paths
the panel itself uses, but hasn't all been individually exercised. A few
specific things worth knowing before you lean on this for anything
time-critical:

- **No dedicated "standby" bit was found** in the reversed read-side code,
  so the `power` switch's on/off *state* is inferred from a `Ready` status
  bit rather than a confirmed standby flag. Turning it on/off (writing)
  uses the same calls confirmed working from the panel.
- **Scheduler day ordering**: the weekly on/off toggle (`reqCode 250`) is
  confirmed to use plain `Date.getDay()` numbering (0=Sunday..6=Saturday).
  The per-slot day index used when *saving* time windows (`reqCode 253`)
  is inferred to follow the panel's own Monday-first day-button order —
  worth a one-off sanity check against your panel before scripting all
  seven days unattended.
- **Auth**: this integration sends empty `key`/`mac` fields and skips
  login entirely unless you set a PIN, matching what worked live against
  a panel with no login configured. If your machine does require a PIN,
  set it in the config flow — the integration will call the login command
  before every poll if it isn't already logged in.
- Traffic to the machine is **plain HTTP, unencrypted, on your LAN** —
  same as the panel itself. Don't expose the machine's IP outside your
  home network.

If any entity ends up reading `unknown` or a setpoint doesn't take, the
most likely cause is a register mapping that doesn't quite match your
machine's firmware revision — open an issue (or just tell Claude) with
what you're seeing and it's a quick fix in `coordinator.py` / `const.py`.

## Full API reference

The complete `reqCode` / register map this integration is built on is
documented separately: see the Cube API Reference page from this
conversation (or `const.py`, which mirrors it 1:1).
