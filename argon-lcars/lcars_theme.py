"""
LCARS drawing toolkit -- colors, fonts, and the reusable frame every
screen is drawn inside of (corner bracket + broken header bar + sidebar
nav + content area), styled after the Galaxy-class (TNG-era) Okuda
interface.
"""
import os
import math
import pygame

# ---------------------------------------------------------------------------
# Palette (classic LCARS)
# ---------------------------------------------------------------------------
BLACK = (0, 0, 0)
BG = (0, 0, 0)

ORANGE = (255, 153, 0)
PEACH = (255, 204, 153)
TAN = (249, 200, 138)
GOLD = (255, 204, 0)
RED = (204, 51, 0)
ALERT_RED = (255, 40, 40)
BLUE = (153, 153, 204)
PALE_BLUE = (153, 204, 255)
LAVENDER = (204, 153, 255)
PURPLE = (153, 102, 204)
PINK = (255, 153, 153)
TEAL = (0, 204, 184)
WHITE = (255, 255, 255)
GREY = (100, 100, 100)
DARK_GREY = (40, 40, 40)

STATUS_OK = (102, 255, 102)
STATUS_WARN = (255, 204, 0)
STATUS_BAD = (255, 51, 51)

SIDEBAR_W = 66
BAND_THICKNESS = 26    # uniform width of the LCARS band -- same for the
                         # top bar and the vertical border, so the curve
                         # connecting them is a constant-width sweep
HEADER_H = BAND_THICKNESS
BORDER_W = BAND_THICKNESS
OUTER_R = 32              # outer curve radius -- the curve's influence is
                            # confined to y < OUTER_R (see draw_lcars_corner's
                            # clip), so this also sets how soon the sidebar
                            # buttons can start without sitting on the sweep
INNER_R = OUTER_R - BAND_THICKNESS  # inner curve radius, same center as outer
NAV_TOP_GAP = 12

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
]


def _load_font(size):
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.SysFont("sans", size, bold=True)


class Fonts:
    huge = None
    big = None
    med = None
    small = None
    tiny = None

    @classmethod
    def init(cls):
        cls.huge = _load_font(26)
        cls.big = _load_font(18)
        cls.med = _load_font(14)
        cls.small = _load_font(11)
        cls.tiny = _load_font(9)


def text(surface, s, font, color, pos, align="left"):
    img = font.render(s, True, color)
    rect = img.get_rect()
    if align == "left":
        rect.topleft = pos
    elif align == "right":
        rect.topright = pos
    elif align == "center":
        rect.midtop = pos
    surface.blit(img, rect)
    return rect


def pill(surface, rect, color):
    """Fully rounded 'capsule' rectangle."""
    x, y, w, h = rect
    radius = h // 2
    pygame.draw.rect(surface, color, rect, border_radius=radius)


def elbow(surface, x, y, w, h, color, corner="tl"):
    """A single rounded corner block (used by the red alert border, which
    needs simple matching corners rather than the tapered bracket)."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    radius = min(w, h)
    rect = pygame.Rect(0, 0, w * 2, h * 2)
    if corner == "tl":
        rect.topleft = (0, 0)
    elif corner == "tr":
        rect.topright = (w, 0)
    elif corner == "bl":
        rect.bottomleft = (0, h)
    elif corner == "br":
        rect.bottomright = (w, h)
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    clipped = pygame.Surface((w, h), pygame.SRCALPHA)
    clipped.blit(surf, (0, 0))
    surface.blit(clipped, (x, y))


def draw_lcars_corner(surface, accent, top_w, thickness, screen_h, outer_r, inner_r):
    """
    An LCARS corner bracket, matching the reference: a uniform-width band
    that sweeps from a horizontal bar into a vertical bar around ONE
    shared center point. The outer edge is an arc of radius outer_r, the
    inner edge is a concentric arc of radius inner_r = outer_r -
    thickness, so the band width stays constant all the way through the
    bend instead of two mismatched curves stitched together.
    """
    cx = cy = outer_r

    # Straight extensions: top bar (right of the bend) and side bar
    # (below the bend)
    pygame.draw.rect(surface, accent, (0, 0, top_w, thickness))
    pygame.draw.rect(surface, accent, (0, 0, thickness, screen_h))

    # Everything below only affects the top-left corner square -- clip to
    # it so the far side of these circles can't bleed out into the
    # sidebar/content area as a stray ring.
    old_clip = surface.get_clip()
    surface.set_clip(pygame.Rect(0, 0, outer_r, outer_r))

    pygame.draw.rect(surface, BLACK, (0, 0, outer_r, outer_r))
    pygame.draw.circle(surface, accent, (cx, cy), outer_r)
    if inner_r > 0:
        pygame.draw.circle(surface, BLACK, (cx, cy), inner_r)

    surface.set_clip(old_clip)


def hbar(surface, rect, pct, color, bg=DARK_GREY):
    """Horizontal LCARS-style meter bar. pct is 0-100."""
    x, y, w, h = rect
    pill(surface, rect, bg)
    fill_w = max(int(w * max(0, min(100, pct)) / 100), h)
    if pct > 0:
        pill(surface, (x, y, fill_w, h), color)


def bar_color_for_pct(pct):
    if pct < 60:
        return STATUS_OK
    if pct < 85:
        return STATUS_WARN
    return STATUS_BAD


def nav_button(surface, rect, color, label, active):
    """Sidebar nav button: a short rounded rectangle, black text on
    colored fill, inverted (colored text on white) when the screen it
    points to is the one currently showing."""
    x, y, w, h = rect
    fill = WHITE if active else color
    txt_color = color if active else BLACK
    pygame.draw.rect(surface, fill, rect, border_radius=10)
    img = Fonts.tiny.render(label, True, txt_color)
    img_rect = img.get_rect(center=(x + w // 2, y + h // 2))
    surface.blit(img, img_rect)


def segmented_strip(surface, x, y, w, h, colors, gap=3):
    """Decorative row of small color blocks -- handy for section dividers
    within a screen body (not used in the header)."""
    if not colors:
        return
    seg_w = (w - gap * (len(colors) - 1)) // len(colors)
    cx = x
    for c in colors:
        pygame.draw.rect(surface, c, (cx, y, seg_w, h), border_radius=h // 3)
        cx += seg_w + gap


def draw_moon_icon(surface, cx, cy, r, illum_pct, waxing,
                    light=(230, 230, 210), dark=(35, 35, 45)):
    """Simple but legible lunar-phase disc: dark base + a lit half +
    a terminator ellipse whose width encodes illumination fraction."""
    frac = max(0.0, min(1.0, (illum_pct or 0) / 100.0))
    pygame.draw.circle(surface, dark, (cx, cy), r)
    if frac <= 0.01:
        pygame.draw.circle(surface, GREY, (cx, cy), r, 1)
        return

    old_clip = surface.get_clip()
    if frac >= 0.99:
        pygame.draw.circle(surface, light, (cx, cy), r)
    else:
        half_rect = pygame.Rect(cx, cy - r, r, r * 2) if waxing else pygame.Rect(cx - r, cy - r, r, r * 2)
        surface.set_clip(half_rect)
        pygame.draw.circle(surface, light, (cx, cy), r)
        surface.set_clip(old_clip)

        term_w = int(r * abs(1 - 2 * frac))
        if term_w > 0:
            color = light if frac > 0.5 else dark
            ellipse_rect = pygame.Rect(cx - term_w, cy - r, term_w * 2, r * 2)
            surface.set_clip(pygame.Rect(cx - r, cy - r, r * 2, r * 2))
            pygame.draw.ellipse(surface, color, ellipse_rect)
            surface.set_clip(old_clip)
    pygame.draw.circle(surface, GREY, (cx, cy), r, 1)


def draw_gear_icon(surface, cx, cy, radius, fg_color, hole_color, teeth=8):
    """Simple gear glyph: a body circle with small circular teeth bumped
    around the edge, and a punched-out center hole (drawn in hole_color,
    which should match whatever's behind the icon -- e.g. the button's
    own fill -- so it reads as an actual hole rather than a dot)."""
    tooth_r = max(2, radius // 3)
    pygame.draw.circle(surface, fg_color, (cx, cy), radius)
    for i in range(teeth):
        angle = (2 * math.pi / teeth) * i
        tx = cx + int(math.cos(angle) * radius)
        ty = cy + int(math.sin(angle) * radius)
        pygame.draw.circle(surface, fg_color, (tx, ty), tooth_r)
    hole_r = max(2, radius // 2)
    pygame.draw.circle(surface, hole_color, (cx, cy), hole_r)


def draw_sparkline(surface, rect, values, color, fill_color=None, baseline_values=None, baseline_color=None):
    """
    LCARS-style sparkline: values scaled to fit rect, drawn as a filled
    area + line. If baseline_values is given (same length as values),
    it's drawn as a second line on top -- used on Engineering to show
    blocked queries against total query volume.
    """
    x, y, w, h = rect
    pygame.draw.rect(surface, DARK_GREY, rect, border_radius=3)
    if not values or len(values) < 2:
        text(surface, "NO HISTORY DATA", Fonts.tiny, GREY, (x + 6, y + h // 2 - 5))
        return

    vmax = max(values) or 1
    n = len(values)
    step = w / (n - 1)

    def point(i, v):
        px = x + int(i * step)
        py = y + h - int((v / vmax) * (h - 4)) - 2
        return px, py

    pts = [point(i, v) for i, v in enumerate(values)]

    if fill_color:
        poly = [(x, y + h)] + pts + [(x + w, y + h)]
        pygame.draw.polygon(surface, fill_color, poly)

    pygame.draw.lines(surface, color, False, pts, 2)

    if baseline_values and len(baseline_values) == n:
        bpts = [point(i, v) for i, v in enumerate(baseline_values)]
        pygame.draw.lines(surface, baseline_color or STATUS_BAD, False, bpts, 2)


def fmt_clock(dt, twelve_hour, seconds=False):
    """Formats a datetime as a time-of-day string honoring the
    Settings panel's 12hr/24hr toggle -- the one place every screen
    that shows a clock time (sunrise/sunset, ISS pass, query log,
    Ship's Log boot time) should route through, so flipping the
    toggle actually changes all of them consistently."""
    if twelve_hour:
        fmt = "%I:%M:%S %p" if seconds else "%I:%M%p"
        return dt.strftime(fmt).lstrip("0")
    fmt = "%H:%M:%S" if seconds else "%H:%M"
    return dt.strftime(fmt)


def fit_text(font, s, max_w):
    """Truncates s with a trailing ellipsis so its rendered width fits
    max_w, measured against actual font metrics rather than a fixed
    character count -- used anywhere a value (like a domain name) could
    be long enough to run into whatever's next to it."""
    if font.size(s)[0] <= max_w:
        return s
    ellipsis = "\u2026"
    lo, hi = 0, len(s)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.size(s[:mid] + ellipsis)[0] <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return (s[:lo] + ellipsis) if lo > 0 else ellipsis


def fit_text_left(font, s, max_w):
    """Like fit_text(), but drops characters from the START and puts the
    ellipsis in front -- preserving the END of the string. For values
    where the tail carries the identifying information (an IP's last
    octet, say), trailing truncation throws away exactly the part you
    need: '192.168.86.3' becoming '192.168.86...' tells you nothing,
    while '...86.3' still identifies the device."""
    if font.size(s)[0] <= max_w:
        return s
    ellipsis = "\u2026"
    lo, hi = 0, len(s)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        # keep the LAST `mid` characters
        if font.size(ellipsis + s[-mid:])[0] <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return (ellipsis + s[-lo:]) if lo > 0 else ellipsis


# Compound words that have no space/slash to break at but should still
# wrap as real words rather than an arbitrary character cut.
WORD_BREAK_HINTS = {
    "THUNDERSTORM": "THUNDER STORM",
}


def wrap_two_lines(font, s, max_w):
    """Wraps s onto up to two lines that each fit max_w, preferring to
    break at a space or slash. Compound words with no natural break
    point (like 'Thunderstorm') use WORD_BREAK_HINTS to split as real
    words instead of falling back to a mid-word character cut."""
    if font.size(s)[0] <= max_w:
        return s, ""

    hinted = s
    for word, replacement in WORD_BREAK_HINTS.items():
        hinted = hinted.replace(word, replacement)

    break_points = [i + 1 for i, ch in enumerate(hinted) if ch in (" ", "/")]
    best = None
    for b in break_points:
        candidate = hinted[:b].rstrip()
        if font.size(candidate)[0] <= max_w:
            best = b
        else:
            break

    if best:
        line1 = hinted[:best].rstrip()
        rest = hinted[best:].lstrip()
        return line1, fit_text(font, rest, max_w)

    # No word/slash break fits -- last-resort character split (only hit
    # for a genuinely unbroken long word with no hint registered)
    for i in range(len(hinted) - 1, 0, -1):
        if font.size(hinted[:i])[0] <= max_w:
            return hinted[:i], fit_text(font, hinted[i:], max_w)
    return hinted, ""


# ---------------------------------------------------------------------------
# Shared frame: corner bracket + broken header bar + sidebar nav. Returns
# the content rect a screen module should draw its data into.
# ---------------------------------------------------------------------------
SCREENS = ["OPS", "ENGINEERING", "TACTICAL", "COMMS", "ASTROMETRICS", "SHIP'S LOG"]
SCREEN_LABELS = {
    "OPS": "OPS",
    "ENGINEERING": "ENG",
    "TACTICAL": "TAC",
    "COMMS": "COM",
    "ASTROMETRICS": "AST",
    "SHIP'S LOG": "LOG",
}
SCREEN_COLORS = {
    "OPS": ORANGE,
    "ENGINEERING": GOLD,
    "TACTICAL": PALE_BLUE,
    "COMMS": PURPLE,
    "ASTROMETRICS": LAVENDER,
    "SHIP'S LOG": PEACH,
    "SETTINGS": TEAL,   # not part of the normal SCREENS rotation, but
                          # draw_frame looks up accent color by name --
                          # this keys it to teal specifically.
}

# The curve's visual influence is confined to y < OUTER_R (see the clip
# in draw_lcars_corner), so buttons can start as soon as that clears --
# aligned with CONTENT_TOP so the sidebar and the text line up.
NAV_START_Y = CONTENT_TOP = HEADER_H + 8
NAV_X = BORDER_W + 6          # clear of the vertical border, no overlap
NAV_W = SIDEBAR_W - NAV_X - 4


def nav_button_rects(screen_w, screen_h):
    """Returns [(screen_name, pygame.Rect), ...] for the 5 sidebar nav
    buttons using the exact geometry draw_frame() paints them with --
    shared so touchscreen hit-testing always matches what's on screen."""
    y = NAV_START_Y
    gap = 4
    slot_h = (screen_h - y - 4 - gap * (len(SCREENS) - 1)) // len(SCREENS)
    rects = []
    for name in SCREENS:
        rects.append((name, pygame.Rect(NAV_X, y, NAV_W, slot_h)))
        y += slot_h + gap
    return rects


def _fit_title_font(label, max_w):
    """Largest of the standard fonts whose rendered width fits max_w, so
    a long screen name can never run into the clock."""
    for font in (Fonts.big, Fonts.med, Fonts.small):
        if font.size(label)[0] <= max_w:
            return font
    return Fonts.small


def content_rect_for(screen_w, screen_h):
    """Same content rect geometry draw_frame() computes, exposed
    standalone so main.py can hit-test screen-specific touch targets
    (like Tactical's action button) without needing to draw first."""
    sb_w = SIDEBAR_W
    content_top = CONTENT_TOP
    return pygame.Rect(sb_w + 6, content_top, screen_w - sb_w - 16, screen_h - content_top - 6)


def draw_frame(surface, screen_w, screen_h, active_name, clock_str, alert=False):
    surface.fill(BLACK)
    accent = ALERT_RED if alert else SCREEN_COLORS.get(active_name, ORANGE)
    sb_w = SIDEBAR_W

    # --- Corner bracket: one continuous shape, outer curve rounding the
    # true top-left corner, inner curve smoothing the bar-width change ---
    draw_lcars_corner(surface, accent, sb_w, HEADER_H, screen_h, OUTER_R, INNER_R)

    # --- Header bar, broken around the title, flat all the way to the
    # right edge of the screen (no end cap) ---
    header_x = sb_w
    header_right = screen_w
    pad = 10
    label = "RED ALERT" if alert else active_name

    clock_surf = Fonts.small.render(clock_str, True, BLACK)
    clock_w = clock_surf.get_width()

    max_title_w = header_right - header_x - pad * 2 - clock_w - 16
    title_font = _fit_title_font(label, max(max_title_w, 10))
    title_surf = title_font.render(label, True, accent)
    title_w = title_surf.get_width()

    # Title sits directly on black, in the bar's own accent color
    title_x = header_x + pad
    surface.blit(title_surf, (title_x, (HEADER_H - title_surf.get_height()) // 2))

    # Bar resumes after the title -- flat rectangle, no rounded cap,
    # running straight to the screen edge
    resume_x = title_x + title_w + pad
    resume_w = header_right - resume_x
    if resume_w > 4:
        pygame.draw.rect(surface, accent, (resume_x, 0, resume_w, HEADER_H))
        text(surface, clock_str, Fonts.small, BLACK,
             (header_right - 8, (HEADER_H - Fonts.small.get_height()) // 2), align="right")

    # --- Sidebar nav buttons (also the touch targets) ---
    for name, rect in nav_button_rects(screen_w, screen_h):
        color = SCREEN_COLORS[name]
        is_active = name == active_name and not alert
        nav_button(surface, rect, color, SCREEN_LABELS[name], is_active)

    content_rect = content_rect_for(screen_w, screen_h)
    return content_rect, accent
