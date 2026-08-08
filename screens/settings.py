import pygame
import lcars_theme as t
import config

ROW_H = 32
BTN_W = 40
BTN_H = 24
BACK_W = 100
BACK_H = 28

ROW_LABELS = ["SLEEP TIME", "WAKE TIME", "BRIGHTNESS", "CYCLE TIME", "TIME FORMAT"]


def _row_rect(content_rect, i):
    x, y, w, h = content_rect
    return pygame.Rect(x, y + i * ROW_H, w, ROW_H)


def minus_button_rect(content_rect, i):
    row = _row_rect(content_rect, i)
    return pygame.Rect(row.x, row.y + (ROW_H - BTN_H) // 2, BTN_W, BTN_H)


def plus_button_rect(content_rect, i):
    row = _row_rect(content_rect, i)
    return pygame.Rect(row.right - BTN_W, row.y + (ROW_H - BTN_H) // 2, BTN_W, BTN_H)


def back_button_rect(content_rect):
    x, y, w, h = content_rect
    return pygame.Rect(x + (w - BACK_W) // 2, y + ROW_H * len(ROW_LABELS) + 6, BACK_W, BACK_H)


def fmt_clock(total_min, twelve_hour=True):
    hh, mm = divmod(int(total_min) % 1440, 60)
    if twelve_hour:
        period = "AM" if hh < 12 else "PM"
        h12 = hh % 12 or 12
        return f"{h12}:{mm:02d} {period}"
    return f"{hh:02d}:{mm:02d}"


def _pm_button(surface, rect, label):
    pygame.draw.rect(surface, t.TEAL, rect, border_radius=6)
    img = t.Fonts.med.render(label, True, t.BLACK)
    img_rect = img.get_rect(center=rect.center)
    surface.blit(img, img_rect)


def draw(surface, content_rect, user_settings):
    x, y, w, h = content_rect

    twelve = user_settings.get("time_format_12h", True)
    values = [
        fmt_clock(user_settings["quiet_hours_start_min"], twelve),
        fmt_clock(user_settings["quiet_hours_end_min"], twelve),
        f"{int(round(user_settings['brightness_default'] * 100))}%",
        f"{user_settings['carousel_interval_sec']}s",
        "12-HOUR" if twelve else "24-HOUR",
    ]

    for i, label in enumerate(ROW_LABELS):
        row = _row_rect(content_rect, i)
        t.text(surface, label, t.Fonts.tiny, t.GREY, (row.x + BTN_W + 8, row.y + 2))
        t.text(surface, values[i], t.Fonts.small, t.GOLD,
               (row.centerx, row.y + 2 + t.Fonts.tiny.get_height() + 1), align="center")

        _pm_button(surface, minus_button_rect(content_rect, i), "-")
        _pm_button(surface, plus_button_rect(content_rect, i), "+")

        if i < len(ROW_LABELS) - 1:
            pygame.draw.line(surface, t.DARK_GREY, (row.x, row.bottom - 1), (row.right, row.bottom - 1), 1)

    back = back_button_rect(content_rect)
    pygame.draw.rect(surface, t.TEAL, back, border_radius=12)
    t.text(surface, "BACK", t.Fonts.small, t.BLACK,
           (back.centerx, back.centery - t.Fonts.small.get_height() // 2), align="center")

    version_str = f"v{config.APP_VERSION}"
    t.text(surface, version_str, t.Fonts.tiny, t.GREY,
           (x + w - 4, y + h - t.Fonts.tiny.get_height() - 4), align="right")
