import pygame
import datetime
import lcars_theme as t
import config

SETTINGS_BTN_SIZE = 36


def _stardate():
    # Cosmetic-only pseudo-stardate: year fraction + day-of-year
    now = datetime.datetime.now()
    year_frac = (now.timetuple().tm_yday / 365.0) * 1000
    return f"{now.year - 1000}.{year_frac:05.1f}"


def _position_str():
    lat = config.LATITUDE
    lon = config.LONGITUDE
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"{abs(lat):.4f}\u00b0{ns} {abs(lon):.4f}\u00b0{ew}"


def settings_button_rect(content_rect):
    """Geometry for the bottom-right SETTINGS button -- shared between
    drawing and main.py's touch hit-testing, same pattern as Tactical's
    action button."""
    x, y, w, h = content_rect
    return pygame.Rect(x + w - SETTINGS_BTN_SIZE, y + h - SETTINGS_BTN_SIZE,
                        SETTINGS_BTN_SIZE, SETTINGS_BTN_SIZE)


def draw(surface, content_rect, hub_state):
    x, y, w, h = content_rect
    sysd = hub_state.get("system") or {}
    versions = hub_state.get("pihole_versions")
    twelve_hour = hub_state.get("time_format_12h", True)

    earth_date = datetime.datetime.now().strftime("%b %d, %Y")

    boot_dt = sysd.get("boot_time")
    if boot_dt:
        boot_str = f"{boot_dt.strftime('%b %d, %Y')} {t.fmt_clock(boot_dt, twelve_hour)}"
    else:
        boot_str = "N/A"

    t.text(surface, f"STARDATE {_stardate()}", t.Fonts.small, t.PEACH, (x, y))
    t.text(surface, f"EARTH DATE {earth_date}", t.Fonts.small, t.PEACH, (x, y + 16))
    t.text(surface, f"POSITION {_position_str()}", t.Fonts.small, t.PEACH, (x, y + 32))

    max_w = w - 4
    vessel = t.fit_text(t.Fonts.small, f"VESSEL: {sysd.get('hostname', 'N/A')}", max_w)
    vessel_class = t.fit_text(t.Fonts.small, f"CLASS: {sysd.get('pi_model', 'N/A')}", max_w)
    commissioned = t.fit_text(t.Fonts.small, f"COMMISSIONED {boot_str}", max_w)

    t.text(surface, vessel, t.Fonts.small, t.WHITE, (x, y + 52))
    t.text(surface, vessel_class, t.Fonts.small, t.WHITE, (x, y + 68))
    t.text(surface, commissioned, t.Fonts.small, t.WHITE, (x, y + 84))
    t.text(surface, f"UPTIME: {sysd.get('uptime', 'N/A')}", t.Fonts.small, t.WHITE, (x, y + 100))

    t.text(surface, "PI-HOLE VERSIONS", t.Fonts.tiny, t.GREY, (x, y + 124))
    if versions:
        t.text(surface, f"CORE {versions.get('core', 'N/A')}", t.Fonts.small, t.GOLD, (x, y + 136))
        t.text(surface, f"FTL  {versions.get('ftl', 'N/A')}", t.Fonts.small, t.GOLD, (x, y + 150))
        t.text(surface, f"WEB  {versions.get('web', 'N/A')}", t.Fonts.small, t.GOLD, (x, y + 164))
    else:
        t.text(surface, "UNAVAILABLE", t.Fonts.small, t.STATUS_BAD, (x, y + 136))

    # ---- Settings button, bottom-right: teal rounded square + gear glyph ----
    btn = settings_button_rect(content_rect)
    pygame.draw.rect(surface, t.TEAL, btn, border_radius=10)
    t.draw_gear_icon(surface, btn.centerx, btn.centery, radius=10, fg_color=t.BLACK, hole_color=t.TEAL)
