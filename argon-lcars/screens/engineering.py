import datetime
import lcars_theme as t


def _kv(surface, x, y, w, label, value, value_color=None):
    t.text(surface, label, t.Fonts.small, t.GREY, (x, y))
    t.text(surface, str(value), t.Fonts.med, value_color or t.WHITE, (x + w - 4, y - 2), align="right")


def _relative_time(ts):
    if not ts:
        return "N/A"
    try:
        dt = datetime.datetime.fromtimestamp(float(ts))
        seconds = (datetime.datetime.now() - dt).total_seconds()
        if seconds < 3600:
            return f"{max(1, int(seconds // 60))}m ago"
        if seconds < 172800:
            return f"{int(seconds // 3600)}h ago"
        return f"{int(seconds // 86400)}d ago"
    except Exception:
        return "N/A"


def draw(surface, content_rect, hub_state):
    x, y, w, h = content_rect
    summary = hub_state.get("pihole_summary")
    blocking = hub_state.get("pihole_blocking")

    status_color = t.STATUS_OK if blocking else (t.STATUS_BAD if blocking is False else t.GREY)
    status_text = "ENABLED" if blocking else ("DISABLED" if blocking is False else "UNKNOWN")

    t.pill(surface, (x, y, w, 22), status_color)
    t.text(surface, f"GRAVITY: {status_text}", t.Fonts.med, t.BLACK, (x + 10, y + 2))

    if not summary:
        t.text(surface, "PI-HOLE UNREACHABLE", t.Fonts.med, t.STATUS_BAD, (x, y + 34))
        t.text(surface, "check config.py PIHOLE_HOST / PASSWORD", t.Fonts.tiny, t.GREY, (x, y + 54))
        return

    row_y = y + 28
    row_h = 18
    _kv(surface, x, row_y, w, "QUERIES TODAY", summary.get("total", "N/A"))
    _kv(surface, x, row_y + row_h, w, "BLOCKED TODAY", summary.get("blocked", "N/A"), t.STATUS_WARN)
    pct = summary.get("percent_blocked")
    pct_str = f"{pct:.1f}%" if isinstance(pct, (int, float)) else "N/A"
    _kv(surface, x, row_y + row_h * 2, w, "PERCENT BLOCKED", pct_str, t.STATUS_WARN)
    _kv(surface, x, row_y + row_h * 3, w, "DOMAINS ON LIST", summary.get("domains_blocked", "N/A"))
    _kv(surface, x, row_y + row_h * 4, w, "ACTIVE CLIENTS",
        f"{summary.get('clients_active', 'N/A')}/{summary.get('clients_total', 'N/A')}")

    gravity_ts = hub_state.get("pihole_gravity_last_update")
    _kv(surface, x, row_y + row_h * 5, w, "GRAVITY UPDATED", _relative_time(gravity_ts), t.GOLD)

    # ---- 24h query volume sparkline ----
    spark_y = row_y + row_h * 6 + 4
    t.text(surface, "QUERY VOLUME (24H)", t.Fonts.tiny, t.GREY, (x, spark_y))
    t.text(surface, "TOTAL", t.Fonts.tiny, t.GOLD, (x + w - 90, spark_y), align="left")
    t.text(surface, "BLOCKED", t.Fonts.tiny, t.STATUS_BAD, (x + w - 46, spark_y), align="left")

    history = hub_state.get("pihole_history")
    spark_rect = (x, spark_y + 12, w, max(h - (spark_y + 12 - y), 20))
    if history:
        totals = [p["total"] for p in history]
        blocked = [p["blocked"] for p in history]
        t.draw_sparkline(surface, spark_rect, totals, t.GOLD,
                          fill_color=(60, 48, 0), baseline_values=blocked, baseline_color=t.STATUS_BAD)
    else:
        t.draw_sparkline(surface, spark_rect, None, t.GOLD)
