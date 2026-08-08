#!/usr/bin/env python3
"""
Argon POD LCARS Display -- main application.

Renders straight to the POD's framebuffer (/dev/fb0) with pygame, no X11
required. Screens can be switched by tapping the LCARS nav pills on the
resistive touchscreen, by cycling with buttons 1 (left) and 4 (right),
or automatically via the idle carousel; buttons 2/3 dim/brighten. The
display blanks during quiet hours. A flashing RED ALERT frame overrides
everything if Pi-hole blocking is confirmed disabled; a slower YELLOW
ALERT frame overrides everything if Pi-hole can't be reached at all.
A SETTINGS button on SHIP'S LOG opens a touch panel for adjusting
sleep/wake time, default brightness, and carousel interval -- changes
persist across restarts via settings_store.py.
"""
import datetime
import glob
import os
import sys
import time
import threading
import traceback
from array import array
from queue import Queue

try:
    import numpy as np
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False

import config
import settings_store

# Must be set before pygame.init()
if not config.WINDOWED_DEV_MODE:
    # Use a headless SDL driver for event handling only. The app renders
    # directly to the POD framebuffer (/dev/fb0) below.
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("SDL_TOUCH_MOUSE_EVENTS", "1")

try:
    from evdev import InputDevice, ecodes, list_devices
    HAVE_EVDEV = True
except Exception:  # pragma: no cover - optional dependency
    InputDevice = None
    ecodes = None
    list_devices = None
    HAVE_EVDEV = False

import pygame  # noqa: E402

import lcars_theme as t  # noqa: E402
from datahub import DataHub  # noqa: E402
from buttons import ButtonManager, EVT_ANY, EVT_PREV, EVT_NEXT, EVT_DIM, EVT_BRIGHT  # noqa: E402
from screens import (  # noqa: E402
    ops, engineering, tactical, comms, astrometrics, ships_log,
    red_alert, yellow_alert, settings as settings_screen,
)

SCREEN_DRAW = {
    "OPS": ops.draw,
    "ENGINEERING": engineering.draw,
    "TACTICAL": tactical.draw,
    "COMMS": comms.draw,
    "ASTROMETRICS": astrometrics.draw,
    "SHIP'S LOG": ships_log.draw,
}

BRIGHTNESS_ADJUST_STEP = 0.05
CYCLE_ADJUST_STEP = 5
CYCLE_MIN_SEC = 5
CLOCK_STEP_MIN = 15


def is_quiet_hours(now, start_min, end_min):
    """True if now (a datetime) falls in [start_min, end_min) measured
    in minutes-since-midnight, wrapping past midnight."""
    cur_min = now.hour * 60 + now.minute
    if start_min == end_min:
        return False
    if start_min < end_min:
        return start_min <= cur_min < end_min
    return cur_min >= start_min or cur_min < end_min


def format_clock(now, twelve_hour):
    """Header clock text -- 12-hour with AM/PM (no leading zero) or
    24-hour, per the Settings panel's TIME FORMAT toggle."""
    if twelve_hour:
        return now.strftime("%I:%M:%S %p").lstrip("0")
    return now.strftime("%H:%M:%S")


def to_logical_pos(pos):
    return pos


class TouchInputManager:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.events = Queue()
        self._stop = False
        self._device_path = None
        # Pressure floor for accepting a sample. This was 25, which
        # silently dropped light taps -- evtest on real hardware showed
        # legitimate taps landing as low as 43, leaving almost no margin.
        # A value this low only needs to reject genuine noise; the panel
        # reports 0 on release, so anything above a few counts is a real
        # finger.
        self._pressure_threshold = 8
        self._max_samples = 8

    def _find_device(self):
        if not HAVE_EVDEV:
            return None

        candidates = []
        for path in glob.glob('/dev/input/event*'):
            if path not in candidates:
                candidates.append(path)
        for path in glob.glob('/dev/input/by-path/*'):
            real = os.path.realpath(path)
            if real not in candidates:
                candidates.append(real)
        for path in list_devices() or []:
            if path not in candidates:
                candidates.append(path)

        for path in candidates:
            try:
                dev = InputDevice(path)
                name = (dev.name or '').lower()
                abs_caps = dev.capabilities().get(ecodes.EV_ABS, [])
                key_caps = dev.capabilities().get(ecodes.EV_KEY, [])
                dev.close()
                if (
                    ('touch' in name)
                    or ('ads7846' in name)
                    or (ecodes.BTN_TOUCH in key_caps)
                    or (ecodes.ABS_X in abs_caps and ecodes.ABS_Y in abs_caps)
                ):
                    return path
            except Exception:
                continue
        return None

    def start(self):
        threading.Thread(target=self._watch_loop, daemon=True).start()

    def stop(self):
        self._stop = True

    def _clamp(self, value, limit):
        return max(0, min(limit - 1, int(round(value))))

    def _transform(self, raw_x, raw_y):
        # Argon POD fixed calibration for the 270-degree-mounted touchscreen.
        # Based on the official installer: SwapAxes=1 and calibration values
        # 115 3700 3865 155.
        x_raw = raw_y
        y_raw = raw_x

        x = (x_raw - 115.0) / (3700.0 - 115.0) * (self.width - 1)
        y = (3865.0 - y_raw) / (3865.0 - 155.0) * (self.height - 1)

        return (
            self._clamp(x, self.width),
            self._clamp(y, self.height),
        )

    def _watch_loop(self):
        while not self._stop:
            if self._device_path is None:
                self._device_path = self._find_device()
                if self._device_path:
                    print(f"Touch device found: {self._device_path}", flush=True)
                else:
                    time.sleep(1)
                    continue

            try:
                self._poll_loop(self._device_path)
            except Exception:
                traceback.print_exc()
            self._device_path = None
            time.sleep(1)

    def _emit_samples(self, samples):
        if not samples:
            return
        xs = sorted(s[0] for s in samples)
        ys = sorted(s[1] for s in samples)
        mid = len(samples) // 2
        raw_x = xs[mid]
        raw_y = ys[mid]
        self.events.put(self._transform(raw_x, raw_y))

    def _poll_loop(self, device_path):
        dev = InputDevice(device_path)
        try:
            cur_x = 0
            cur_y = 0
            pressure = 0
            touching = False
            samples = []
            fallback = None

            for event in dev.read_loop():
                if self._stop:
                    break

                if event.type == ecodes.EV_ABS:
                    if event.code == ecodes.ABS_X:
                        cur_x = event.value
                    elif event.code == ecodes.ABS_Y:
                        cur_y = event.value
                    elif event.code == ecodes.ABS_PRESSURE:
                        pressure = event.value

                elif event.type == ecodes.EV_KEY and event.code in (ecodes.BTN_TOUCH, ecodes.BTN_LEFT):
                    touching = bool(event.value)
                    if touching:
                        samples = []
                        fallback = None
                    else:
                        if samples:
                            self._emit_samples(samples)
                        elif fallback is not None:
                            # No sample cleared the pressure filter, but the
                            # panel did report a real touch (BTN_TOUCH went
                            # 1 then 0). Emit the last known position rather
                            # than silently dropping the tap -- a slightly
                            # noisier coordinate beats no response at all,
                            # which is what made light taps feel ignored.
                            self._emit_samples([fallback])
                        samples = []
                        fallback = None

                elif event.type == ecodes.EV_SYN and event.code == ecodes.SYN_REPORT:
                    if touching:
                        fallback = (cur_x, cur_y)
                        if pressure >= self._pressure_threshold:
                            samples.append((cur_x, cur_y))
                            if len(samples) > self._max_samples:
                                samples.pop(0)
        finally:
            dev.close()

    def poll(self):
        out = []
        try:
            while True:
                out.append(self.events.get_nowait())
        except Exception:
            pass
        return out


class FramebufferWriter:
    def __init__(self, device, width, height):
        self.width = width
        self.height = height
        self._fh = open(device, "r+b", buffering=0)
        self._pixels = array("H", [0]) * (width * height)

    def present(self, surface):
        if surface.get_size() != (self.width, self.height):
            surface = pygame.transform.scale(surface, (self.width, self.height))

        raw = pygame.image.tostring(surface, "RGB")

        if HAVE_NUMPY:
            # Vectorized RGB888 -> RGB565 pack. On a Pi Zero 2W this is
            # dramatically cheaper than the pure-Python per-pixel loop
            # below (76,800 iterations/frame) -- same bit-packing math,
            # just done as array ops instead of a Python-level loop.
            arr = np.frombuffer(raw, dtype=np.uint8).reshape((self.height, self.width, 3))
            r = arr[:, :, 0].astype(np.uint16)
            g = arr[:, :, 1].astype(np.uint16)
            b = arr[:, :, 2].astype(np.uint16)
            rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
            self._fh.seek(0)
            self._fh.write(rgb565.astype(np.uint16).tobytes())
            return

        # Fallback if numpy isn't installed -- same output, just slower.
        pixels = self._pixels
        j = 0
        for i in range(self.width * self.height):
            r = raw[j]
            g = raw[j + 1]
            b = raw[j + 2]
            j += 3
            pixels[i] = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)

        self._fh.seek(0)
        self._fh.write(pixels.tobytes())


def rect_hit(rect, pos, pad=18):
    if pad <= 0:
        return rect.collidepoint(pos)
    return rect.inflate(pad * 2, pad * 2).collidepoint(pos)

def main():
    pygame.init()
    t.Fonts.init()

    if config.WINDOWED_DEV_MODE:
        display = pygame.display.set_mode((config.SCREEN_W, config.SCREEN_H))
        pygame.display.set_caption("Argon POD LCARS")
        render_surface = display
    else:
        # SDL only exists here to keep pygame's event loop alive. The real
        # visible output is written directly to /dev/fb0.
        pygame.display.set_mode((1, 1))
        pygame.display.set_caption("Argon POD LCARS")
        render_surface = pygame.Surface((config.SCREEN_W, config.SCREEN_H))

    fb = FramebufferWriter(config.FRAMEBUFFER, config.SCREEN_W, config.SCREEN_H)
    touch = TouchInputManager(config.SCREEN_W, config.SCREEN_H)

    hub = DataHub()
    hub.start()

    buttons = ButtonManager()
    buttons.start()
    touch.start()

    user_settings = settings_store.load()

    content_rect = t.content_rect_for(config.SCREEN_W, config.SCREEN_H)
    tactical_btn_rect = tactical.action_button_rect(content_rect)
    ships_log_btn_rect = ships_log.settings_button_rect(content_rect)

    screen_index = 0
    settings_open = False
    brightness = user_settings["brightness_default"]
    was_quiet = False
    quiet_peek_until = 0
    red_alert_snoozed_until = 0
    now_ts = time.time()
    last_interaction_ts = now_ts
    last_carousel_advance_ts = now_ts
    clock = pygame.time.Clock()

    # ---- Render throttling state ----
    # The event loop runs at FPS (for touch responsiveness), but the
    # draw+present pipeline only runs when something actually changed.
    # At 20fps with a seconds-resolution clock, that's ~1 render/sec
    # instead of 20 -- the other 19 frames were producing a
    # pixel-identical image and writing it to the framebuffer anyway.
    last_render_key = None
    _overlay_cache = {"surface": None, "brightness": None}

    def get_overlay(b):
        """Cached dim overlay -- only reallocated when brightness moves."""
        if _overlay_cache["brightness"] != b:
            surf = pygame.Surface((config.SCREEN_W, config.SCREEN_H), pygame.SRCALPHA)
            surf.fill((0, 0, 0, int((1 - b) * 255)))
            _overlay_cache["surface"] = surf
            _overlay_cache["brightness"] = b
        return _overlay_cache["surface"]

    def handle_touch(touch_pos, currently_blanked, now_ts):
        nonlocal screen_index, settings_open, brightness, quiet_peek_until, red_alert_snoozed_until

        if currently_blanked:
            quiet_peek_until = now_ts + config.QUIET_HOURS_WAKE_PEEK_SEC
            return True

        hit_nav = False
        touch_pos = to_logical_pos(touch_pos)
        for name, rect in t.nav_button_rects(config.SCREEN_W, config.SCREEN_H):
            if rect_hit(rect, touch_pos, pad=2):
                screen_index = t.SCREENS.index(name)
                settings_open = False
                red_alert_snoozed_until = time.time() + config.RED_ALERT_SNOOZE_SEC
                hit_nav = True
                break

        if not hit_nav:
            if settings_open:
                if rect_hit(settings_screen.back_button_rect(content_rect), touch_pos, pad=22):
                    settings_open = False
                else:
                    for i in range(len(settings_screen.ROW_LABELS)):
                        minus_hit = rect_hit(settings_screen.minus_button_rect(content_rect, i), touch_pos, pad=18)
                        plus_hit = rect_hit(settings_screen.plus_button_rect(content_rect, i), touch_pos, pad=18)
                        if not (minus_hit or plus_hit):
                            continue
                        d = -1 if minus_hit else 1
                        if i == 0:
                            user_settings["quiet_hours_start_min"] = (
                                user_settings["quiet_hours_start_min"] + d * CLOCK_STEP_MIN
                            ) % 1440
                        elif i == 1:
                            user_settings["quiet_hours_end_min"] = (
                                user_settings["quiet_hours_end_min"] + d * CLOCK_STEP_MIN
                            ) % 1440
                        elif i == 2:
                            user_settings["brightness_default"] = round(min(
                                config.BRIGHTNESS_MAX,
                                max(config.BRIGHTNESS_MIN,
                                    user_settings["brightness_default"] + d * BRIGHTNESS_ADJUST_STEP),
                            ), 2)
                            brightness = user_settings["brightness_default"]
                        elif i == 3:
                            user_settings["carousel_interval_sec"] = max(
                                CYCLE_MIN_SEC,
                                user_settings["carousel_interval_sec"] + d * CYCLE_ADJUST_STEP,
                            )
                        elif i == 4:
                            user_settings["time_format_12h"] = not user_settings["time_format_12h"]
                        settings_store.save(user_settings)
                        break
            elif t.SCREENS[screen_index] == "TACTICAL":
                if rect_hit(tactical_btn_rect, touch_pos, pad=28):
                    hub.disable_blocking_async(config.TACTICAL_DISABLE_SECONDS)
            elif t.SCREENS[screen_index] == "SHIP'S LOG":
                if rect_hit(ships_log_btn_rect, touch_pos, pad=24):
                    settings_open = True
        return True

    running = True
    while running:
        interacted = False
        now_ts = time.time()
        now = datetime.datetime.now()

        quiet_raw = config.QUIET_HOURS_ENABLED and is_quiet_hours(
            now, user_settings["quiet_hours_start_min"], user_settings["quiet_hours_end_min"]
        )
        currently_blanked = quiet_raw and now_ts > quiet_peek_until

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                buttons.feed_key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and config.TOUCH_ENABLED:
                interacted = handle_touch(event.pos, currently_blanked, now_ts)

        for touch_pos in touch.poll():
            interacted = handle_touch(touch_pos, currently_blanked, now_ts)

        for evt in buttons.poll():
            interacted = True
            if currently_blanked:
                quiet_peek_until = now_ts + config.QUIET_HOURS_WAKE_PEEK_SEC
                continue
            if evt == EVT_ANY:
                red_alert_snoozed_until = time.time() + config.RED_ALERT_SNOOZE_SEC
            elif evt == EVT_PREV:
                screen_index = (screen_index - 1) % len(t.SCREENS)
                settings_open = False
            elif evt == EVT_NEXT:
                screen_index = (screen_index + 1) % len(t.SCREENS)
                settings_open = False
            elif evt == EVT_DIM:
                brightness = max(config.BRIGHTNESS_MIN, brightness - config.BRIGHTNESS_STEP)
            elif evt == EVT_BRIGHT:
                brightness = min(config.BRIGHTNESS_MAX, brightness + config.BRIGHTNESS_STEP)

        now_ts = time.time()
        if interacted:
            last_interaction_ts = now_ts
            last_carousel_advance_ts = now_ts
        elif (
            config.CAROUSEL_ENABLED
            and not settings_open
            and now_ts - last_interaction_ts >= user_settings["carousel_interval_sec"]
            and now_ts - last_carousel_advance_ts >= user_settings["carousel_interval_sec"]
        ):
            screen_index = (screen_index + 1) % len(t.SCREENS)
            last_carousel_advance_ts = now_ts

        current_screen = t.SCREENS[screen_index]
        state = hub.get()
        state["time_format_12h"] = user_settings["time_format_12h"]

        quiet = quiet_raw and now_ts > quiet_peek_until
        if was_quiet and not quiet:
            brightness = user_settings["brightness_default"]
        was_quiet = quiet

        # ---- Determine what would be drawn, before drawing it ----
        blocking = state.get("pihole_blocking")
        last_contact = state.get("pihole_last_contact_ts")
        network_down = last_contact is None or (now_ts - last_contact) > config.NETWORK_TIMEOUT_SEC

        red_alert_active = (not quiet) and network_down and now_ts > red_alert_snoozed_until
        yellow_alert_active = (
            (not quiet)
            and config.RED_ALERT_ON_BLOCKING_DISABLED
            and blocking is False
            and not network_down
            and now_ts > red_alert_snoozed_until
        )

        now_str = format_clock(now, user_settings["time_format_12h"])

        # Alert screens animate (pulsing border, live countdown), so their
        # pulse phase and the current second have to be part of the key or
        # they'd freeze. Everything else is static between data updates.
        if red_alert_active:
            anim = (int(now_ts * config.RED_ALERT_FLASH_HZ) % 2, int(now_ts))
        elif yellow_alert_active:
            anim = (int(now_ts) % 2, int(now_ts))
        else:
            anim = None

        render_key = (
            quiet,
            current_screen,
            settings_open,
            round(brightness, 3),
            red_alert_active,
            yellow_alert_active,
            anim,
            None if quiet else now_str,
            hub.version(),
            tuple(sorted(user_settings.items())),
        )

        if render_key != last_render_key:
            last_render_key = render_key

            if quiet:
                render_surface.fill(t.BLACK)
            else:
                if red_alert_active:
                    red_alert.draw(render_surface, config.SCREEN_W, config.SCREEN_H, state)
                elif yellow_alert_active:
                    yellow_alert.draw(render_surface, config.SCREEN_W, config.SCREEN_H, state)
                elif settings_open:
                    content_rect, _accent = t.draw_frame(
                        render_surface, config.SCREEN_W, config.SCREEN_H,
                        "SETTINGS", now_str, alert=False,
                    )
                    settings_screen.draw(render_surface, content_rect, user_settings)
                else:
                    content_rect, _accent = t.draw_frame(
                        render_surface, config.SCREEN_W, config.SCREEN_H,
                        current_screen, now_str, alert=False,
                    )
                    SCREEN_DRAW[current_screen](render_surface, content_rect, state)

                if brightness < 1.0:
                    render_surface.blit(get_overlay(brightness), (0, 0))

            if config.ROTATE_DEGREES:
                fb.present(pygame.transform.rotate(render_surface, config.ROTATE_DEGREES))
            else:
                fb.present(render_surface)

        clock.tick(config.FPS)

    hub.stop()
    buttons.stop()
    touch.stop()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
