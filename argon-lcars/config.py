"""
Argon POD LCARS Display - Configuration
========================================
Edit the values below for your setup. Nothing else in the project
should need to change for a normal install.
"""

# ---------------------------------------------------------------------------
# Pi-hole -- this instance runs locally on this same Pi Zero 2W (it's a
# second, independent Pi-hole -- not linked to any other Pi-hole you may
# have elsewhere). "127.0.0.1" talks to it over loopback; change this
# only if you ever point the app at a different Pi-hole instead.
# ---------------------------------------------------------------------------
PIHOLE_HOST = "127.0.0.1"        # Pi-hole on this same Pi (loopback).
                                  # Change to an IP/hostname if your Pi-hole
                                  # runs on another box on the network.
PIHOLE_PORT = 80                  # 443 if PIHOLE_USE_HTTPS = True
PIHOLE_USE_HTTPS = False
PIHOLE_VERIFY_TLS = True
PIHOLE_PASSWORD = "CHANGE_ME"     # Pi-hole v6 admin password (app-password
                                   # from Settings > API works too)

# Pi-hole v6 changed API paths from earlier versions. If a data screen shows
# "N/A" across the board, open http://<PIHOLE_HOST>/api/docs on your Pi-hole
# and compare against data/pihole.py -- endpoint names occasionally shift
# between point releases.

# ---------------------------------------------------------------------------
# Location (used for weather / sunrise-sunset / moon / ISS passes)
# Set these to your own coordinates -- decimal degrees, negative longitude
# for the western hemisphere. The defaults below are New York City.
# ---------------------------------------------------------------------------
LATITUDE = 40.7128
LONGITUDE = -74.0060
ALTITUDE_M = 20
TIMEZONE = "America/New_York"

# ---------------------------------------------------------------------------
# Weather -- Open-Meteo, free, no API key required
# ---------------------------------------------------------------------------
WEATHER_UNITS = "imperial"     # "imperial" or "metric"

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
FRAMEBUFFER = "/dev/fb0"        # confirmed on Trixie -- the POD display
                                  # overlay lands here, not /dev/fb1
SCREEN_W = 320
SCREEN_H = 240
FPS = 20                         # Touch events are only drained once per
                                  # frame, so this directly caps input
                                  # latency (worst case = 1 frame = 50ms
                                  # at 20fps, vs 125ms at 8fps). 8 was
                                  # necessary in 1.0 when the framebuffer
                                  # conversion cost ~33ms/frame; the numpy
                                  # path made that ~1ms, so there's headroom
                                  # now. Lower it again if OPS shows the
                                  # CPU gauge running hot.
ROTATE_DEGREES = 0               # Leave at 0. The kernel overlay
                                  # (dtoverlay=tft9341:rotate=270,swapxy=1)
                                  # already produces the correct
                                  # buttons-on-top orientation. Setting this
                                  # to 180 rotates the image but NOT the
                                  # touch coordinates, which flips the
                                  # display and makes taps register on the
                                  # opposite corner.

# Set True to run in a normal desktop window instead of the framebuffer,
# for testing on a laptop/dev Pi before deploying to the POD.
WINDOWED_DEV_MODE = False

# ---------------------------------------------------------------------------
# Refresh intervals (seconds) -- how often background threads poll each
# data source. Keep Pi-hole/system frequent, weather/ISS/moon infrequent.
# ---------------------------------------------------------------------------
REFRESH_SYSTEM = 3
REFRESH_PIHOLE = 5
REFRESH_TOPS = 30        # top blocked/allowed domain + top client -- daily
                          # aggregates, barely move minute to minute
REFRESH_WEATHER = 600
REFRESH_ISS = 300
REFRESH_MOON_SUN = 3600
REFRESH_HISTORY = 300   # query-volume sparkline data, doesn't need to be frequent
REFRESH_CONFIG = 600     # upstream DNS, gravity update time -- changes rarely
REFRESH_CONFIG_RETRY = 15  # but retry fast if the fetch failed (e.g. Pi-hole
                            # not ready yet on a cold boot)
REFRESH_QUERIES = 4       # recent query feed for COMMS -- frequent, for a "live" feel

# ---------------------------------------------------------------------------
# Yellow Alert -- shown when Pi-hole hasn't answered at all in this many
# seconds (distinct from Red Alert, which needs a *confirmed* "blocking
# is off" response -- if the network's down we can't confirm that).
# ---------------------------------------------------------------------------
NETWORK_TIMEOUT_SEC = 30

# ---------------------------------------------------------------------------
# Idle carousel -- auto-cycle through screens when nothing's touched the
# panel for a while. Any button press or touch resets the idle timer.
# CAROUSEL_INTERVAL_SEC is only the first-run default -- once the app has
# started once, the live value lives in user_settings.json (adjustable
# from the on-screen Settings panel, in 5s steps) and this is ignored.
# ---------------------------------------------------------------------------
CAROUSEL_ENABLED = True
CAROUSEL_INTERVAL_SEC = 30

# ---------------------------------------------------------------------------
# Tactical screen's "disable blocking" button
# ---------------------------------------------------------------------------
TACTICAL_DISABLE_SECONDS = 300  # 5 minutes

# ---------------------------------------------------------------------------
# Red Alert
# ---------------------------------------------------------------------------
RED_ALERT_ON_BLOCKING_DISABLED = True
RED_ALERT_FLASH_HZ = 2

# ---------------------------------------------------------------------------
# Buttons (BCM GPIO numbers -- matches the Argon POD Display wiring diagram)
# ---------------------------------------------------------------------------
# 1: previous screen (cycles left)   2: dim   3: brighten   4: next screen (cycles right)
BTN_1 = 16   # -> previous screen
BTN_2 = 20   # -> decrease brightness
BTN_3 = 21   # -> increase brightness
BTN_4 = 26   # -> next screen
DEBOUNCE_SEC = 0.05

# Any button also acknowledges/silences an active Red Alert for this many
# seconds before it can re-trigger (it will still come back if blocking is
# still disabled after this window).
RED_ALERT_SNOOZE_SEC = 30

# ---------------------------------------------------------------------------
# Touchscreen
# ---------------------------------------------------------------------------
# The POD display is RESISTIVE touch (ADS7846 controller), not capacitive.
# Tapping the five LCARS nav pills on the left switches screens directly.
# Touch input is read directly from evdev (see TouchInputManager in
# main.py) with Argon's own factory calibration constants baked in --
# no tslib, no ts_calibrate step, no SDL touch driver involved. If touch
# ever needs re-tuning, the constants live in main.py's _transform().
TOUCH_ENABLED = True

# ---------------------------------------------------------------------------
# Brightness (software dimming -- the POD display module has no documented
# backlight PWM pin, so "brightness" is simulated with a black overlay of
# variable opacity rather than true backlight control). BRIGHTNESS_DEFAULT
# is only the first-run default -- adjustable afterward from the on-screen
# Settings panel (Ship's Log > Settings), persisted in user_settings.json,
# and reapplied automatically every time the display wakes from quiet hours.
# ---------------------------------------------------------------------------
BRIGHTNESS_DEFAULT = 1.0
BRIGHTNESS_MIN = 0.15
BRIGHTNESS_MAX = 1.0
BRIGHTNESS_STEP = 0.15

# ---------------------------------------------------------------------------
# Quiet hours -- screen blanks to black outside this window (data threads
# keep running in the background so it's instantly current again at wake
# time). QUIET_HOURS_START/END are only the first-run defaults (whole
# hours here for readability) -- the live values live in
# user_settings.json as minutes-since-midnight, adjustable in 15-minute
# steps from the on-screen Settings panel. This is a software blank, not
# a hardware backlight-off, since the display doesn't expose one.
# ---------------------------------------------------------------------------
QUIET_HOURS_ENABLED = True
QUIET_HOURS_START = 23   # 11pm
QUIET_HOURS_END = 6      # 6am

# Any touch or button press during quiet hours wakes the display for
# this many seconds (like a phone screen), then it blanks again
# automatically if there's no further interaction.
QUIET_HOURS_WAKE_PEEK_SEC = 20

# ---------------------------------------------------------------------------
# Clock format -- 12-hour with AM/PM by default. Adjustable from the on-
# screen Settings panel (affects the header clock and the Sleep/Wake
# time displays); this is only the first-run default.
# ---------------------------------------------------------------------------
CLOCK_12_HOUR = True

# ---------------------------------------------------------------------------
# App version -- shown in the bottom-right corner of the Settings screen.
# ---------------------------------------------------------------------------
APP_VERSION = "2.6"
