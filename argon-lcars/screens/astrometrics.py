import datetime
import lcars_theme as t
import weather_icons


def _fmt_time(iso_str, twelve_hour):
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.datetime.fromisoformat(iso_str)
        return t.fmt_clock(dt, twelve_hour)
    except Exception:
        return iso_str


def _centered_pill(surface, rect, color, label):
    x, y, w, h = rect
    t.pill(surface, rect, color)
    t.text(surface, label, t.Fonts.tiny, t.BLACK, (x + w // 2, y + (h - t.Fonts.tiny.get_height()) // 2),
           align="center")


def draw(surface, content_rect, hub_state):
    x, y, w, h = content_rect
    wx = hub_state.get("weather")
    moon = hub_state.get("moon")
    iss_pass = hub_state.get("iss")
    twelve_hour = hub_state.get("time_format_12h", True)

    cy = y

    # ---- Icon + temp + condition (no "WEATHER" label -- the icon and
    # big number already make it obvious what this section is) ----
    if wx:
        unit = "F" if wx["units"] == "imperial" else "C"
        temp_h = t.Fonts.huge.get_height()
        small_h = t.Fonts.small.get_height()

        icon_box = 50
        temp_str = f"{wx['temp']:.0f}\u00b0{unit}"
        temp_w = t.Fonts.huge.size(temp_str)[0]
        temp_x = (x + w) - temp_w - 4   # anchored to the far right edge

        cond_x = x + icon_box + 12
        cond_max_w = max(temp_x - 10 - cond_x, 10)
        cond_line1, cond_line2 = t.wrap_two_lines(t.Fonts.small, wx["condition"].upper(), cond_max_w)
        cond_block_h = (small_h * 2 + 2) if cond_line2 else small_h

        row_h = max(temp_h, icon_box, cond_block_h)

        icon_cx = x + icon_box // 2
        icon_cy = cy + row_h // 2
        weather_icons.draw_icon(surface, wx.get("code"), icon_cx, icon_cy, scale=36)

        temp_y = cy + (row_h - temp_h) // 2
        t.text(surface, temp_str, t.Fonts.huge, t.LAVENDER, (temp_x, temp_y))

        if cond_line2:
            cond_y = cy + (row_h - cond_block_h) // 2
            t.text(surface, cond_line1, t.Fonts.small, t.WHITE, (cond_x, cond_y))
            t.text(surface, cond_line2, t.Fonts.small, t.WHITE, (cond_x, cond_y + small_h + 2))
        else:
            cond_y = cy + (row_h - small_h) // 2
            t.text(surface, cond_line1, t.Fonts.small, t.WHITE, (cond_x, cond_y))

        cy += row_h + 4

        wind_unit = "MPH" if wx["units"] == "imperial" else "KMH"
        day_len_str = ""
        try:
            sunrise_dt = datetime.datetime.fromisoformat(wx["sunrise"])
            sunset_dt = datetime.datetime.fromisoformat(wx["sunset"])
            day_len = sunset_dt - sunrise_dt
            dh, rem = divmod(int(day_len.total_seconds()), 3600)
            dm = rem // 60
            day_len_str = f"   DAY {dh}H{dm:02d}M"
        except Exception:
            pass
        t.text(surface, f"HUMIDITY {wx['humidity']}%   WIND {wx['wind']:.0f}{wind_unit}{day_len_str}",
               t.Fonts.tiny, t.GREY, (x, cy))
        cy += t.Fonts.tiny.get_height() + 6
    else:
        t.text(surface, "UNAVAILABLE", t.Fonts.small, t.STATUS_BAD, (x, cy))
        cy += t.Fonts.small.get_height() + 8

    # ---- Sunrise / Sunset, and High / Low, as centered pill pairs ----
    if wx:
        pill_h = 16
        half_w = w // 2 - 4
        _centered_pill(surface, (x, cy, half_w, pill_h), t.GOLD,
                        f"SUNRISE {_fmt_time(wx['sunrise'], twelve_hour)}")
        _centered_pill(surface, (x + w // 2, cy, half_w, pill_h), t.ORANGE,
                        f"SUNSET {_fmt_time(wx['sunset'], twelve_hour)}")
        cy += pill_h + 4

        temp_high = wx.get("temp_high")
        temp_low = wx.get("temp_low")
        if temp_high is not None and temp_low is not None:
            _centered_pill(surface, (x, cy, half_w, pill_h), t.PEACH,
                            f"HIGH {temp_high:.0f}\u00b0{unit}")
            _centered_pill(surface, (x + w // 2, cy, half_w, pill_h), t.PALE_BLUE,
                            f"LOW {temp_low:.0f}\u00b0{unit}")
            cy += pill_h + 6
        else:
            cy += 2

    # ---- Divider (single solid bar, not a multicolor strip) ----
    t.pill(surface, (x, cy, w, 4), t.PURPLE)
    cy += 4 + 8

    # ---- Moon (left) / ISS (right) ----
    # Keep the moon column just wide enough for a wrapped two-line phase
    # name, and give the rest of the width to ISS so its time text (which
    # was previously running off the right edge) has room to breathe.
    col_split = int(w * 0.50)
    x2 = x + col_split + 8
    label_h = t.Fonts.tiny.get_height()
    t.text(surface, "LUNAR PHASE", t.Fonts.tiny, t.GREY, (x, cy))
    t.text(surface, "ISS NEXT PASS", t.Fonts.tiny, t.GREY, (x2, cy))
    row_top = cy + label_h + 4

    if moon:
        icon_r = 16
        icon_cx = x + icon_r + 2
        icon_cy = row_top + icon_r
        t.draw_moon_icon(surface, icon_cx, icon_cy, icon_r,
                          moon["illumination_pct"], moon["waxing"])

        label_x = icon_cx + icon_r + 8
        words = moon["name"].upper().split()
        line1 = words[0]
        line2 = " ".join(words[1:]) if len(words) > 1 else ""
        small_h = t.Fonts.small.get_height()
        t.text(surface, line1, t.Fonts.small, t.PALE_BLUE, (label_x, row_top - 2))
        if line2:
            t.text(surface, line2, t.Fonts.small, t.PALE_BLUE, (label_x, row_top - 2 + small_h))
        illum_y = row_top - 2 + small_h * (2 if line2 else 1) + 2
        t.text(surface, f"{moon['illumination_pct']:.0f}% LIT", t.Fonts.tiny, t.GREY, (label_x, illum_y))

        # Whichever lunar milestone is sooner -- more useful than always
        # showing both, and keeps this to one line in a narrow column
        days_to_full = moon.get("days_to_full")
        days_to_new = moon.get("days_to_new")
        if days_to_full is not None and days_to_new is not None:
            if days_to_full <= days_to_new:
                countdown_str = f"NEXT FULL {days_to_full:.0f}D"
            else:
                countdown_str = f"NEXT NEW {days_to_new:.0f}D"
            t.text(surface, countdown_str, t.Fonts.tiny, t.GOLD,
                   (label_x, illum_y + t.Fonts.tiny.get_height() + 2))
    else:
        t.text(surface, "UNAVAILABLE", t.Fonts.small, t.STATUS_BAD, (x, row_top))

    if iss_pass and iss_pass.get("start_local"):
        start_local = iss_pass["start_local"]
        time_part = t.fmt_clock(start_local, twelve_hour)
        when = f"{start_local.strftime('%a')} {time_part}"
        dur = iss_pass.get("duration_sec") or 0
        el = iss_pass.get("max_elevation")
        if el is None:
            el = "--"
        # Same font size as the moon phase name (small), not the bigger
        # med font that was pushing the time off the edge of the screen
        small_h = t.Fonts.small.get_height()
        t.text(surface, when, t.Fonts.small, t.PEACH, (x2, row_top))
        iy = row_top + small_h + 3
        t.text(surface, f"{dur // 60}m DUR", t.Fonts.tiny, t.GREY, (x2, iy))
        iy += t.Fonts.tiny.get_height() + 2
        t.text(surface, f"{el}\u00b0 MAX EL", t.Fonts.tiny, t.GREY, (x2, iy))
    else:
        t.text(surface, "NO PASS DATA", t.Fonts.small, t.STATUS_BAD, (x2, row_top))
