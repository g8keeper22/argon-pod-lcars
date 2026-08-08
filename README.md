# Argon POD LCARS Display

A Star Trek: TNG LCARS-styled Pi-hole and system dashboard for the Argon
POD case's 2.8" display, running on a Raspberry Pi Zero 2 W. Six screens
of live telemetry — network stats, system health, a real-time DNS query
feed, weather and ISS passes — rendered straight to the framebuffer with
pygame. No X11, no desktop, starts on boot as a systemd service.

**v2.6 — built for Raspberry Pi OS Trixie and Pi-hole v6.**

## Why this exists


Most small-SPI-display guides assume Raspberry Pi OS Bookworm, and on
Trixie a lot of that toolchain quietly stops working:

- **SDL's `fbcon` driver** no longer reliably grabs the framebuffer.
- **`tslib` / `ts_calibrate`** behave erratically.
- **FBCP won't build at all** — it depends on the DispmanX API that
  Trixie's DRM/KMS-only graphics stack removed.

This project sidesteps all three by going lower-level: it writes RGB565
bytes directly to `/dev/fb0` and reads touch input straight from `evdev`.
The Trixie-specific gotchas found along the way are documented throughout
this README — the `config.txt` truncation bug in the vendor installer and
the ADS7846 pressure-ceiling issue in particular cost real debugging time
and aren't written down anywhere else I could find.

## Hardware


- Raspberry Pi Zero 2 W
- Argon POD case + POD Display Module (2.8", 320×240, **resistive** touch
  via ADS7846 on SPI)
- A Pi-hole v6 instance, either on this same Pi or elsewhere on the network

**The touch panel is resistive — use a stylus.** See the touchscreen
section below; this is the single most common source of confusion with
this hardware.

## Screens


**OPS** (CPU/RAM/disk/temp/system load bars with an overall status
summary, network up/down throughput, process count) · **ENGINEERING**
(full Pi-hole stats, gravity/blocklist last-updated time, 24h
query-volume sparkline) · **TACTICAL** (Pi-hole host, API response
time, upstream DNS with provider name lookup, top blocked/allowed, top
client, plus a touch button to pause blocking for 5 minutes) ·
**COMMS** (live-scrolling feed of the most recent DNS queries, color-
coded allowed/blocked) · **ASTROMETRICS** (weather with icon and day
length, sunrise/sunset, moon phase with next full/new moon countdown,
next ISS pass) · **SHIP'S LOG** (Pi-hole versions, hostname, uptime,
stardate + Earth date).

## Alerts


- **RED ALERT** -- Pi-hole hasn't answered *at all* in
  `NETWORK_TIMEOUT_SEC` (config.py, default 30s). This is the more
  severe case: we can't even confirm the blocking state. Since Pi-hole
  runs locally on this same Pi (127.0.0.1), this specifically means
  Pi-hole's own service (FTL/web) has stopped responding -- not a
  general network/internet outage the way it would if the app were
  talking to a remote Pi-hole instead.
- **YELLOW ALERT** -- Pi-hole answered and *confirmed* blocking is off.
  Less severe than Red, since it's a known, specific state rather than
  "no idea what's going on." Shows a live countdown to when blocking
  auto-resumes if a timer is running (e.g. from Tactical's 5-minute
  button), or "disabled indefinitely" if blocking was turned off with no
  timer (such as from Pi-hole's own admin UI).

Either alert can be silenced for 30s by any button press or touch.

## Idle Carousel


If nothing's touched the panel for the configured cycle time (default
30s), it auto-advances through the screens on that same interval --
like a real bridge display cycling status boards. Any button press or
touch resets the idle timer and pauses the carousel for a fresh
interval. Adjustable from the Settings panel (see below), or set
`CAROUSEL_ENABLED = False` in config.py to turn it off entirely.

## Settings Panel


Tap the **SETTINGS** button in the bottom-right corner of SHIP'S LOG to
open a touch panel with four adjustable values, each with **-** / **+**
buttons:

- **Sleep time** and **Wake time** -- the quiet-hours window, in
  15-minute steps
- **Brightness** -- the default the display resets to whenever it wakes
  from quiet hours (adjusting it here also live-previews the change
  immediately)
- **Cycle time** -- the idle carousel interval, in 5-second steps
- **Time format** -- 12-hour (default) or 24-hour, affecting the header
  clock and the Sleep/Wake time displays; either **-** or **+** just
  flips it, since it's a two-state toggle rather than a range

Tap **BACK** to return to Ship's Log, or tap any sidebar nav pill to
jump straight to a screen (also exits Settings). Changes save
immediately to `user_settings.json` (next to the app) and persist
across restarts -- config.py's values are only the first-run defaults.

## Controls


**Touch** (the POD display is RESISTIVE touch, ADS7846 controller --
not capacitive, but tapping still works fine, and needs no manual
calibration in 2.0 -- see "What changed in 2.0" above): tap any of the
6 colored LCARS pills on the left sidebar to jump straight to that
screen. On Tactical, tap the yellow button on the right to pause
Pi-hole blocking for 5 minutes (colored to match Yellow Alert, since
that's exactly what pressing it will trigger -- expected, not a bug).
On Ship's Log, tap SETTINGS in the bottom-right to adjust sleep/wake
time, brightness, and carousel interval (see Settings Panel above).

**Buttons:**

| Button | GPIO | Action |
|---|---|---|
| 1 | 16 | Previous screen (cycle left) |
| 2 | 20 | Dim |
| 3 | 21 | Brighten |
| 4 | 26 | Next screen (cycle right) |

Any button or touch also acknowledges/silences an active alert for 30
seconds.

Brightness is software-simulated (a variable black overlay) since the
POD display module doesn't expose a documented backlight PWM pin. If you
later find yours does have one, `main.py`'s brightness block is the spot
to swap in real PWM control.

## Quiet Hours


The screen blanks to black from 11pm-6am (`QUIET_HOURS_START` /
`QUIET_HOURS_END` in config.py). Background data polling keeps running
so everything's current the instant it wakes back up. This is a
software blank, not a true backlight power-off -- same caveat as
brightness above.

## Prerequisites


1. Assemble the POD Case + Display Module per the Argon manual, with a
   Pi Zero 2 W and full Raspberry Pi OS (Trixie) installed.
2. Install Argon's own display driver:
   ```
   curl https://download.argon40.com/podsystem.sh | bash
   ```
   **Before you reboot, check `/boot/firmware/config.txt`.** This
   script has a real bug on Trixie: one of its `grep` cleanup steps
   reads and writes the same temp file in the same command, which
   truncates it before `grep` can read it -- the practical effect is
   your `config.txt` can end up containing *only* the newly-added Argon
   lines, with everything else (including `dtoverlay=vc4-kms-v3d`,
   which Trixie's DRM/KMS stack needs) silently dropped. Confirmed
   working `config.txt` contents on Trixie:
   ```
   dtoverlay=vc4-kms-v3d
   hdmi_force_hotplug=1
   dtparam=i2c_arm=on
   dtparam=spi=on
   enable_uart=1
   dtoverlay=tft9341:rotate=270,swapxy=1
   hdmi_group=2
   hdmi_mode=1
   hdmi_mode=87
   hdmi_cvt 320 240 60 6 0 0 0
   hdmi_drive=2
   dtoverlay=gpio-ir,gpio_pin=23
   ```
   The `swapxy=1` on the tft9341 overlay line matters -- it's part of
   what makes the display orientation correct on this panel. Compare
   your file against this and fix it manually if anything's missing,
   *then* reboot.
3. A working Pi-hole v6 instance the app can reach. It can run on this
   same Pi (the default, `PIHOLE_HOST = "127.0.0.1"`) or on another box
   on your network -- set `PIHOLE_HOST` accordingly in `config.py`.

## Install


```bash
sudo ./install.sh
```

This copies the app to `/opt/argon-lcars`, installs pygame/psutil/
requests/RPi.GPIO/evdev/numpy, stops Argon's own `argonpodd` button daemon (it
would otherwise fight this app for the same GPIO lines), and installs/
starts `argon-lcars.service` so it runs on every boot.

Then edit the config and restart:

```bash
sudo nano /opt/argon-lcars/config.py
sudo systemctl restart argon-lcars
```

At minimum set `PIHOLE_PASSWORD`, and `LATITUDE`/`LONGITUDE` to your own
location (the defaults are New York City). `PIHOLE_HOST` defaults to
`127.0.0.1` for a Pi-hole running on this same Pi -- change it to the
IP or hostname of your Pi-hole box if it lives elsewhere on the network.

### Touchscreen: use a stylus

**The POD panel is RESISTIVE, not capacitive** -- despite what some
product listings say. Verified on-device: it enumerates as `ti,ads7846`
(a resistive ADC) on SPI, the overlay carries `ti,x-plate-ohms`, and
`i2cdetect` finds no touch controller on any I2C bus. A plastic pen cap
registers touches, which is only possible on a resistive panel.

Practical consequence: it responds to **concentrated pressure**, not
skin contact. A fingertip pad spreads force too widely to reliably press
the two conductive layers together, so most fingertip taps register
nothing at all. Use a plastic stylus, pen cap, or fingernail edge.

### Touch overlay patch (`patch-touch-overlay.sh`)

`install.sh` runs this automatically; it's also safe to run standalone
and to re-run (it detects an already-patched overlay).

Argon's stock overlay sets `ti,pressure-max = [00 ff]` (255). The
`ads7846` driver computes touch *resistance* and **silently discards**
any sample above that ceiling -- the touch never becomes an input event,
so no application-side tuning can recover it. A large share of normal
taps on this panel exceed 255 and vanish. The script decompiles the
overlay, raises the ceiling to 1500, and recompiles it, keeping a backup
at `/boot/overlays/tft9341.dtbo.orig`.

Requires a reboot. Verify with `sudo evtest /dev/input/event3` -- the
`ABS_PRESSURE` Max should read 1500. To revert:

```bash
sudo cp /boot/overlays/tft9341.dtbo.orig /boot/overlays/tft9341.dtbo
sudo reboot
```

### Touchscreen calibration

Nothing to do here in 2.0 -- touch input is read directly via `evdev`
with Argon's own factory calibration constants (`115, 3700, 3865, 155`,
matching the values in Argon's own xorg calibration block) hardcoded
into `TouchInputManager._transform()` in `main.py`. No `ts_calibrate`,
no `pointercal` file, no environment variables to set.

If touch ever feels off on your specific panel, the constants to adjust
are right there in `_transform()` -- `evtest` against the raw
`/dev/input/eventN` device (see Troubleshooting below) is the fastest
way to see what raw values your taps are actually producing before
tweaking them.

## Backing Up Your SD Card First


Before making any changes (uninstalling a previous display driver,
disabling WiFi, etc.), it's worth cloning the SD card so you can always
get back to exactly where you started. This clones it remotely over
SSH from another computer on your network -- no need to pull the card.

**1. Connect the Pi via Ethernet if you can** (not required, but faster
than WiFi for a clone that can be tens of GB).

**2. Confirm the SD card's device name on the Pi:**

```bash
ssh pi@<pi-ip-address>
lsblk
```

It's almost always `/dev/mmcblk0` for the onboard SD slot. Confirm by
capacity before proceeding.

**3. Run the clone from your other computer** (not the Pi):

```bash
ssh pi@<pi-ip-address> "sudo dd if=/dev/mmcblk0 bs=4M status=progress | gzip -1 -" > pi_zero_backup_$(date +%Y%m%d).img.gz
```

This reads the card byte-for-byte on the Pi, compresses it on the fly
before it crosses the network, and lands it in a single `.img.gz` file
locally. Expect anywhere from ~15 minutes to over an hour depending on
card size and connection speed. It'll prompt for the Pi's sudo password
interactively.

**4. Verify the backup isn't corrupted:**

```bash
gzip -t pi_zero_backup_20260717.img.gz
```

No output means the file transferred cleanly.

**Note:** this clones a live, running system, so it's a
"crash-consistent" snapshot rather than a perfectly atomic one -- like
pulling power mid-operation. In practice this is fine for ext4's
journaling to handle on restore, and not worth worrying about for a
personal backup before a case migration.

**To restore**, on a machine with a physical SD card reader:

```bash
gunzip -c pi_zero_backup_20260717.img.gz | sudo dd of=/dev/diskN bs=4M status=progress
```

Replace `/dev/diskN` with the *new* card's actual device identifier
(`diskutil list` on Mac, `lsblk` on Linux) -- double-check this before
running it, since `dd` will overwrite whatever device you point it at.

## Troubleshooting


- **Blank/garbled screen**: try flipping `ROTATE_DEGREES` between `0`
  and `180` in config.py, and confirm `/dev/fb0` exists (`ls -la
  /dev/fb*`) -- if not, check `/boot/firmware/config.txt` against the
  block in Prerequisites above; the Argon installer's known bug may
  have dropped `dtoverlay=vc4-kms-v3d` or the `swapxy=1` flag.
- **Touch doesn't register, or registers in the wrong place**: run
  `sudo evtest /dev/input/eventN` (find the right N via `cat
  /proc/bus/input/devices`, look for the ADS7846 entry) and touch a few
  known spots -- clean, consistent X/Y/pressure readings mean the
  hardware's fine and the issue is in `_transform()`'s calibration
  constants; garbled/flooding/phantom readings point at a hardware
  issue instead (reseat the header connection, check `dmesg | grep -i
  ads7846` for SPI errors).
- **Pi-hole screens all say N/A**: verify credentials with `curl -X POST
  http://<PIHOLE_HOST>/api/auth -d '{"password":"..."}'` and check
  `http://<PIHOLE_HOST>/api/docs` -- endpoint names have shifted slightly
  between Pi-hole v6 point releases; adjust `data/pihole.py` to match.
- **Engineering's sparkline says "NO HISTORY DATA"**: the `/api/history`
  endpoint's exact response shape can vary by Pi-hole version; check
  `/api/docs` and adjust `PiHoleClient.history()` if the field names
  don't match.
- **Tactical's disable button doesn't seem to do anything**: it calls
  `POST /api/dns/blocking` with `{"blocking": false, "timer": 300}` --
  same `/api/docs` caveat as above applies to `PiHoleClient.set_blocking()`.
- **Yellow Alert's countdown always says "disabled indefinitely," even
  right after using Tactical's button**: `blocking_status()` expects
  `GET /api/dns/blocking` to echo back a `timer` field with seconds
  remaining while a timer is running. If your Pi-hole version doesn't
  return that field, check `/api/docs` and adjust
  `PiHoleClient.blocking_status()` to match.
- **COMMS says "NO QUERY DATA"**: `recent_queries()` reads
  `GET /api/queries` -- same version-drift caveat as everything else
  here. Check `/api/docs` for the current query-log shape (field names
  for domain/client/status in particular) and adjust
  `PiHoleClient.recent_queries()`.
- **Engineering's "GRAVITY UPDATED" says N/A**: `gravity_last_update()`
  reads `GET /api/info/database` looking for a `gravity_last_updated`
  (or nested `gravity.last_update`) timestamp field. If your Pi-hole
  doesn't expose it under either name, check `/api/docs` and adjust.
- **Tactical's upstream DNS says N/A**: same caveat again --
  `PiHoleClient.upstream_dns()` reads `/api/config/dns`, whose exact
  nesting has moved around between Pi-hole v6 point releases.
- **Yellow Alert fires right at startup**: expected for the first ~30s
  before the first successful Pi-hole poll completes -- it genuinely
  hasn't confirmed reachability yet.
- **ISS pass says unavailable**: the free g7vrd API occasionally has
  downtime; it'll just retry on the next refresh cycle.
- **Logs**: `journalctl -u argon-lcars -f`

## Testing off-Pi


Set `WINDOWED_DEV_MODE = True` in config.py and run `python3 main.py` on
any desktop with pygame installed. Left/Right arrow keys stand in for
buttons 1/4 (screen cycling), Up/Down arrows for buttons 3/2
(brighten/dim), and mouse clicks on the sidebar pills simulate touch.

## File layout


```
main.py            entry point / pygame loop / alerts / touch / carousel /
                    settings / FramebufferWriter (raw /dev/fb0 writer,
                    numpy-accelerated) / TouchInputManager (evdev, with
                    Argon's factory calibration built in)
config.py           all user-editable first-run defaults
settings_store.py    persisted user_settings.json (sleep/wake, brightness, cycle time)
lcars_theme.py       colors, fonts, LCARS drawing primitives, sparkline, shared frame
weather_icons.py      geometric weather glyphs (sun/cloud/rain/snow/fog/thunder)
buttons.py           GPIO button polling (prev/dim/bright/next)
datahub.py           background refresh threads -> thread-safe snapshot
data/
  system_stats.py    CPU/RAM/disk/temp/uptime/IP/network throughput
  pihole.py          Pi-hole v6 REST API client (stats, history, queries,
                       blocking control, gravity update time)
  weather.py          Open-Meteo current conditions + sunrise/sunset
  iss.py              next ISS pass prediction
  moon.py              offline moon-phase calculation
screens/
  ops.py, engineering.py, tactical.py, comms.py, astrometrics.py,
  ships_log.py, settings.py, red_alert.py, yellow_alert.py
install.sh            installer
patch-touch-overlay.sh  raises ADS7846 pressure ceiling in Argon's overlay
argon-lcars.service   systemd unit
```

## Changelog

### v2.6


- **Touch reliability.** Lowered the app-side pressure threshold and added
  a fallback so a touch is never silently discarded when no sample clears
  the filter. Added `patch-touch-overlay.sh` to raise the ADS7846
  `pressure-max` ceiling, which was rejecting most taps at the kernel
  level before they ever became input events.
- **Pi-hole `versions()` null handling.** `.get(key, default)` only
  defaults on a *missing* key — a present-but-null value fell through and
  rendered as the literal string "None".
- **Cold-boot retry.** The config poll now retries every 15s until all
  version fields are populated, instead of caching a partial result for a
  full 10-minute cycle when Pi-hole isn't ready yet at startup.

### v2.5


Performance pass -- no behavior, screen, or visual changes. All of this
was measured, not guessed:

- **Render only when something changed.** The event loop still runs at
  `FPS` (20) so touch stays responsive, but the draw + framebuffer-write
  pipeline now only fires when the output would actually differ: a data
  update, an interaction, a screen switch, the clock's second rolling
  over, or an alert mid-pulse. Since content changes about once per
  second and the pipeline measured ~1.2ms/frame (likely 12-25ms on a
  Pi Zero 2W), this was the dominant cost. **Measured 95% fewer renders
  in normal operation, 90% during an active alert** (alerts still
  animate correctly -- pulse phase is part of the change key).
- **Pi-hole polling split by how fast things actually change.** The old
  loop fired six API calls every 5 seconds, including `versions()`
  (Core/FTL/Web strings that change monthly) and the top
  blocked/allowed/client aggregates. Now: `summary()` + `blocking_status()`
  stay at 5s (they drive the live counters and Yellow Alert), the top_*
  calls moved to a new 30s loop (`REFRESH_TOPS`), and `versions()` moved
  to the 600s config loop. **~72 API calls/minute down to ~26.**
- **Static system values cached.** `boot_time`, `pi_model`, `cpu_count`,
  and `hostname` were being re-read from `/proc` and the OS every 3
  seconds despite being fixed for the process lifetime. Read once now.
- **Brightness overlay cached.** A new 320x240 SRCALPHA surface was
  allocated and filled every frame whenever brightness was below 100%.
  Now allocated once and reused until brightness actually changes.
- **`DataHub` gained a version counter** so the render loop can detect
  "did any data change?" cheaply, without deep-comparing the state dict.
  It only increments on genuine value changes, so repeated identical
  writes don't trigger pointless redraws.

### v2.1


Field fixes found while running 2.0 on real hardware:

- **`ROTATE_DEGREES` now defaults to 0.** 2.0 shipped with 180, which
  rotated the image but not the touch coordinates -- the display came up
  upside-down and taps registered on the opposite corner. The kernel
  overlay (`rotate=270,swapxy=1`) already produces the correct
  buttons-on-top orientation on its own.
- **`FPS` raised from 8 to 20.** Touch events are only drained once per
  frame, so the frame rate directly capped input latency (125ms worst
  case at 8fps). The numpy framebuffer path added in 2.0 made the
  higher rate affordable. Measured on-device afterward: CPU ~10%,
  load ~2.3 on 4 cores.
- **`data/iss.py` rewritten.** The original built a request URL with an
  altitude segment the g7vrd API doesn't accept, so every ISS lookup
  failed silently and the screen permanently showed "NO PASS DATA".
  Also now tolerates both `start`/`startUTC` and
  `max_elevation`/`maxElevation` field spellings, and derives duration
  from start/end when the API omits it.
- **Astrometrics guards against partial ISS data.** The rewritten
  `iss.py` can return a pass dict with `start_local = None` (timestamp
  present but unparseable), which would have crashed the render loop on
  `.strftime()`. `max_elevation = None` now displays as `--` instead of
  the literal string "None".
- **COMMS client column truncates from the left.** For IP addresses the
  last octet is the identifying part, so cutting the tail
  (`192.168.86.…`) discarded exactly the useful information. Now shows
  `….168.86.103` instead. New `fit_text_left()` helper in
  `lcars_theme.py`.
- Default coordinates updated.

### v2.0


Getting this running on Trixie required replacing two pieces that
turned out to be broken on the newer OS/kernel:

- **Display output**: SDL's `fbcon` driver stopped reliably grabbing
  the framebuffer console on Trixie's kernel. 2.0 renders to an
  off-screen surface and writes raw RGB565 bytes directly to
  `/dev/fb0` instead (`FramebufferWriter` in `main.py`), bypassing SDL
  for actual display output entirely. Confirmed on Trixie: the POD
  display overlay lands on `/dev/fb0`, not `/dev/fb1` as earlier
  Bookworm-era testing assumed.
- **Touch input**: `SDL_MOUSEDRV=TSLIB` + `ts_calibrate` were similarly
  unreliable on Trixie. 2.0 reads the touchscreen directly via `evdev`
  (`TouchInputManager` in `main.py`) with Argon's own factory
  calibration constants built in -- no `tslib`, no manual calibration
  step required at all.
- **FBCP is not needed and won't build on Trixie** -- it depends on the
  deprecated DispmanX API, which Trixie's DRM/KMS-only graphics stack
  doesn't have. This app never used FBCP (it always wrote directly to
  the panel's own framebuffer), so this doesn't affect anything here,
  but if you go looking at Argon's own `argonpod-config` menu, skip
  that option.
- **PADD is not used or needed** -- this app talks to Pi-hole's REST
  API directly, not through Pi-hole's own terminal dashboard tool.

## Disclaimer


This is an unofficial, non-commercial fan project. LCARS and Star Trek
are trademarks of Paramount/CBS; this project is not affiliated with or
endorsed by them. All interface graphics are drawn programmatically from
geometric primitives in pygame — no assets from the show are included.

## License


MIT — see [LICENSE](LICENSE). The license covers this project's own code;
it does not grant any rights to the LCARS design language itself.

