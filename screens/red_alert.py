import time
import pygame
import lcars_theme as t
import config


def draw(surface, screen_w, screen_h, hub_state):
    """LCARS-framed red alert: black field, a red elbow-cornered border
    (the border pulses, the text stays steady and readable), with
    'RED ALERT' / 'Network Unreachable' centered in the middle. This is
    the more severe of the two alerts -- Pi-hole can't be reached at
    all, versus Yellow Alert where it answered and told us blocking is
    off."""
    pulse_on = int(time.time() * config.RED_ALERT_FLASH_HZ) % 2 == 0
    border_color = t.ALERT_RED if pulse_on else (50, 5, 5)

    surface.fill(t.BLACK)

    margin = 10
    corner = 30
    bar_t = 14

    # Corner elbows
    t.elbow(surface, margin, margin, corner, corner, border_color, corner="tl")
    t.elbow(surface, screen_w - margin - corner, margin, corner, corner, border_color, corner="tr")
    t.elbow(surface, margin, screen_h - margin - corner, corner, corner, border_color, corner="bl")
    t.elbow(surface, screen_w - margin - corner, screen_h - margin - corner, corner, corner,
            border_color, corner="br")

    # Straight bars connecting the elbows along each edge
    top_bar = (margin + corner + 4, margin, screen_w - 2 * (margin + corner + 4), bar_t)
    bottom_bar = (margin + corner + 4, screen_h - margin - bar_t,
                  screen_w - 2 * (margin + corner + 4), bar_t)
    left_bar = (margin, margin + corner + 4, bar_t, screen_h - 2 * (margin + corner + 4))
    right_bar = (screen_w - margin - bar_t, margin + corner + 4, bar_t,
                 screen_h - 2 * (margin + corner + 4))
    for bar in (top_bar, bottom_bar, left_bar, right_bar):
        pygame.draw.rect(surface, border_color, bar, border_radius=4)

    # Centered text
    cx, cy = screen_w // 2, screen_h // 2
    t.text(surface, "RED ALERT", t.Fonts.huge, t.ALERT_RED, (cx, cy - 26), align="center")
    t.text(surface, "Network Unreachable", t.Fonts.med, t.WHITE, (cx, cy + 10), align="center")
