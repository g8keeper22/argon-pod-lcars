import pygame
import lcars_theme as t
import config

ACTION_COL_W = 64  # narrower than before, leaves more room for domain text

# Common public DNS resolvers, so "1.1.1.1" reads as "Cloudflare (1.1.1.1)"
# instead of a bare IP. Not exhaustive -- unrecognized IPs just show as-is.
DNS_PROVIDERS = {
    "1.1.1.1": "Cloudflare", "1.0.0.1": "Cloudflare",
    "8.8.8.8": "Google", "8.8.4.4": "Google",
    "9.9.9.9": "Quad9", "149.112.112.112": "Quad9",
    "208.67.222.222": "OpenDNS", "208.67.220.220": "OpenDNS",
    "94.140.14.14": "AdGuard", "94.140.15.15": "AdGuard",
    "76.76.2.0": "Control D", "76.76.10.0": "Control D",
    "64.6.64.6": "Verisign", "64.6.65.6": "Verisign",
    "84.200.69.80": "DNS.WATCH", "84.200.70.40": "DNS.WATCH",
    "198.101.242.72": "Alternate DNS", "23.253.163.53": "Alternate DNS",
    "4.2.2.1": "Level3", "4.2.2.2": "Level3",
}


def _friendly_dns(value):
    if not value:
        return None
    ip = value.split("#")[0].strip()
    name = DNS_PROVIDERS.get(ip)
    return f"{name} ({ip})" if name else ip


def action_button_rect(content_rect):
    """Geometry for the 'disable blocking' button -- shared between
    drawing and main.py's touch hit-testing, same pattern as the sidebar
    nav buttons."""
    x, y, w, h = content_rect
    return pygame.Rect(x + w - ACTION_COL_W, y, ACTION_COL_W, h)


def _entry(surface, x, y, w, label, value, color):
    t.pill(surface, (x, y, 10, 14), color)
    t.text(surface, label, t.Fonts.tiny, t.GREY, (x + 14, y))
    val = str(value) if value else "N/A"
    # Measured against the actual available width (not a fixed char
    # count), so long domain names truncate safely and can never run
    # into the action button regardless of column width.
    val = t.fit_text(t.Fonts.small, val, w - 14)
    t.text(surface, val, t.Fonts.small, t.WHITE, (x + 14, y + 11))


def draw(surface, content_rect, hub_state):
    x, y, w, h = content_rect

    data_w = w - ACTION_COL_W - 10

    row_h = 32
    _entry(surface, x, y, data_w, "PI-HOLE HOST", config.PIHOLE_HOST, t.PALE_BLUE)

    latency = hub_state.get("pihole_latency_ms")
    if latency is not None:
        latency_color = t.STATUS_OK if latency < 150 else (t.STATUS_WARN if latency < 400 else t.STATUS_BAD)
        _entry(surface, x, y + row_h, data_w, "RESPONSE TIME", f"{latency:.0f}ms", latency_color)
    else:
        _entry(surface, x, y + row_h, data_w, "RESPONSE TIME", None, t.GREY)

    _entry(surface, x, y + row_h * 2, data_w, "UPSTREAM DNS",
           _friendly_dns(hub_state.get("pihole_upstream_dns")), t.BLUE)
    _entry(surface, x, y + row_h * 3, data_w, "TOP BLOCKED DOMAIN",
           hub_state.get("pihole_top_blocked"), t.STATUS_BAD)
    _entry(surface, x, y + row_h * 4, data_w, "TOP ALLOWED DOMAIN",
           hub_state.get("pihole_top_allowed"), t.STATUS_OK)
    _entry(surface, x, y + row_h * 5, data_w, "TOP CLIENT",
           hub_state.get("pihole_top_client"), t.GOLD)

    # ---- Action button: disable blocking for N minutes ----
    # Colored to match Yellow Alert now, since pressing this legitimately
    # triggers that alert (confirmed blocking-off), not Red.
    btn_rect = action_button_rect(content_rect)
    blocking = hub_state.get("pihole_blocking")
    if blocking is False:
        pygame.draw.rect(surface, t.DARK_GREY, btn_rect, border_radius=12)
        pygame.draw.rect(surface, t.GOLD, btn_rect, width=2, border_radius=12)
        t.text(surface, "BLOCK", t.Fonts.tiny, t.GOLD,
               (btn_rect.centerx, btn_rect.centery - 18), align="center")
        t.text(surface, "PAUSED", t.Fonts.tiny, t.GOLD,
               (btn_rect.centerx, btn_rect.centery - 4), align="center")
    else:
        pygame.draw.rect(surface, t.GOLD, btn_rect, border_radius=12)
        mins = config.TACTICAL_DISABLE_SECONDS // 60
        t.text(surface, "DISABLE", t.Fonts.tiny, t.BLACK,
               (btn_rect.centerx, btn_rect.centery - 24), align="center")
        t.text(surface, "BLOCKING", t.Fonts.tiny, t.BLACK,
               (btn_rect.centerx, btn_rect.centery - 10), align="center")
        t.text(surface, f"{mins} MIN", t.Fonts.tiny, t.BLACK,
               (btn_rect.centerx, btn_rect.centery + 6), align="center")
