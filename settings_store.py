"""
Small persisted-settings store for values adjustable live via the
on-screen Settings panel (sleep/wake time, default brightness, carousel
interval). Stored as JSON next to the app so changes survive reboots
and app restarts. config.py's values are the fallback defaults the
first time this runs, or if the file's ever missing/corrupted.
"""
import json
import os

import config

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_settings.json")


def _defaults():
    return {
        "quiet_hours_start_min": config.QUIET_HOURS_START * 60,
        "quiet_hours_end_min": config.QUIET_HOURS_END * 60,
        "brightness_default": config.BRIGHTNESS_DEFAULT,
        "carousel_interval_sec": config.CAROUSEL_INTERVAL_SEC,
        "time_format_12h": config.CLOCK_12_HOUR,
    }


def load():
    settings = _defaults()
    try:
        if os.path.exists(_PATH):
            with open(_PATH) as f:
                saved = json.load(f)
            for key in settings:
                if key in saved:
                    settings[key] = saved[key]
    except Exception:
        pass
    return settings


def save(settings):
    try:
        with open(_PATH, "w") as f:
            json.dump(settings, f)
        return True
    except Exception:
        return False
