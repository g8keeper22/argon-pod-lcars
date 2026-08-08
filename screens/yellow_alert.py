import time
import pygame
import lcars_theme as t
import config


def draw(surface, screen_w, screen_h, hub_state):
    """LCARS-framed yellow alert: a slower, less urgent pulse than Red
    Alert (this is 'Pi-hole answered and confirmed blocking is off', not
    'we can't reach it at all' -- that's the more severe Red Alert) --
    black field, amber elbow-cornered border, centered text."""
    pulse_on = int(time.time() * 1) % 2 == 0  # slower pulse than red alert
    border_color = t.GOLD if pulse_on else (110, 90, 0)

    surface.fill(t.BLACK)

    margin = 10
    corner = 30
    bar_t = 14

    t.elbow(surface, margin, margin, corner, corner, border_color, corner="tl")
    t.elbow(surface, screen_w - margin - corner, margin, corner, corner, border_color, corner="tr")
    t.elbow(surface, margin, screen_h - margin - corner, corner, corner, border_color, corner="bl")
    t.elbow(surface, screen_w - margin - corner, screen_h - margin - corner, corner, corner,
            border_color, corner="br")

    top_bar = (margin + corner + 4, margin, screen_w - 2 * (margin + corner + 4), bar_t)
    bottom_bar = (margin + corner + 4, screen_h - margin - bar_t,
                  screen_w - 2 * (margin + corner + 4), bar_t)
    left_bar = (margin, margin + corner + 4, bar_t, screen_h - 2 * (margin + corner + 4))
    right_bar = (screen_w - margin - bar_t, margin + corner + 4, bar_t,
                 screen_h - 2 * (margin + corner + 4))
    for bar in (top_bar, bottom_bar, left_bar, right_bar):
        pygame.draw.rect(surface, border_color, bar, border_radius=4)

    cx, cy = screen_w // 2, screen_h // 2
    t.text(surface, "YELLOW ALERT", t.Fonts.huge, t.GOLD, (cx, cy - 26), align="center")
    t.text(surface, "Pi-Hole Blocking Disabled", t.Fonts.med, t.WHITE, (cx, cy + 10), align="center")

    # ---- Countdown to auto-resume, or a notice that none is set ----
    # Pi-hole reports a 'timer' (seconds remaining) when blocking was
    # disabled with a timer -- same field the Tactical button sends when
    # disabling. No timer in the response means it was disabled without
    # one (e.g. via Pi-hole's own admin UI) and won't resume on its own.
    timer_sec = hub_state.get("pihole_blocking_timer_sec")
    polled_ts = hub_state.get("pihole_blocking_timer_polled_ts")

    if timer_sec is not None and polled_ts is not None:
        elapsed = time.time() - polled_ts
        remaining = max(0, timer_sec - elapsed)
        mins, secs = divmod(int(remaining), 60)
        t.text(surface, f"Resuming in {mins:02d}:{secs:02d}", t.Fonts.med, t.GOLD,
               (cx, cy + 34), align="center")
    else:
        t.text(surface, "DISABLED INDEFINITELY", t.Fonts.small, t.STATUS_BAD,
               (cx, cy + 36), align="center")
