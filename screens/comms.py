import datetime
import lcars_theme as t

ROW_H = 17
CLIENT_COL_W = 74


def _time_col_width():
    """Time column width for the currently-active format: 24hr times
    are always exactly the same width (all digits, no AM/PM), so we can
    size it tightly; 12hr times vary (1-2 digit hour, plus AM/PM), so
    this reserves their worst case instead. Either way it's measured
    against real font metrics, not guessed, so the domain column gets
    back whatever room 24hr mode doesn't need."""
    return {
        True: max(t.Fonts.tiny.size(c)[0] for c in ("1:00:00 AM", "12:00:00 PM", "11:59:59 PM")) + 6,
        False: t.Fonts.tiny.size("00:00:00")[0] + 6,
    }


def _fmt_time(ts, twelve_hour):
    if not ts:
        return "--:--:--"
    try:
        return t.fmt_clock(datetime.datetime.fromtimestamp(float(ts)), twelve_hour, seconds=True)
    except Exception:
        return "--:--:--"


def draw(surface, content_rect, hub_state):
    x, y, w, h = content_rect
    queries = hub_state.get("pihole_recent_queries")
    twelve_hour = hub_state.get("time_format_12h", True)

    t.text(surface, "RECENT QUERIES", t.Fonts.tiny, t.GREY, (x, y))
    list_y = y + t.Fonts.tiny.get_height() + 4

    if not queries:
        t.text(surface, "NO QUERY DATA", t.Fonts.small, t.STATUS_BAD, (x, list_y))
        return

    time_col_w = _time_col_width()[twelve_hour]
    domain_x = x + 12 + time_col_w
    domain_max_w = w - 12 - time_col_w - CLIENT_COL_W - 8
    max_rows = min(len(queries), (h - (list_y - y)) // ROW_H)

    for i in range(max_rows):
        q = queries[i]
        row_y = list_y + i * ROW_H
        color = t.STATUS_BAD if q["blocked"] else t.STATUS_OK

        t.pill(surface, (x, row_y + 3, 8, 8), color)
        t.text(surface, _fmt_time(q["time"], twelve_hour), t.Fonts.tiny, t.GREY, (x + 12, row_y))

        domain = t.fit_text(t.Fonts.tiny, q["domain"], domain_max_w)
        t.text(surface, domain, t.Fonts.tiny, t.WHITE, (domain_x, row_y))

        # Left-truncate: for IPs the last octet is the identifying part,
        # so dropping the tail ("192.168.86...") loses exactly what you
        # need to tell devices apart.
        client = t.fit_text_left(t.Fonts.tiny, q["client"], CLIENT_COL_W - 6)
        t.text(surface, client, t.Fonts.tiny, t.PEACH, (x + w - 2, row_y), align="right")
