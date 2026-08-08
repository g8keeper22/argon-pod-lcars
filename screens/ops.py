import lcars_theme as t

PCT_COL_W = 42  # fixed width for "XX.X%" at the end of each bar


def _row(surface, rect, label, pct, detail_str=None, detail_color=None, bar_color=None):
    """Two-line gauge: label + expanded descriptive text on the top line
    (e.g. 'MEMORY' / '2.1/4.0GB'), then a long bar with its precise
    percentage at the trailing end on the line below. detail_str is
    optional -- skip it when there's nothing to add above the bar.
    bar_color overrides the default 60/85 coloring, for gauges (like
    storage) that need their own thresholds."""
    x, y, w, h = rect
    label_h = t.Fonts.small.get_height()

    t.text(surface, label, t.Fonts.small, t.WHITE, (x, y))
    if detail_str:
        t.text(surface, detail_str, t.Fonts.small, detail_color or t.PEACH, (x + w - 4, y), align="right")

    bar_y = y + label_h + 3
    bar_h = 11
    pct = pct or 0
    pct_str = f"{pct:.1f}%"
    gap = 6
    bar_w = w - PCT_COL_W - gap
    color = bar_color or t.bar_color_for_pct(pct)
    t.hbar(surface, (x, bar_y, bar_w, bar_h), pct, color)
    t.text(surface, pct_str, t.Fonts.tiny, t.PEACH,
           (x + w - 2, bar_y + (bar_h - t.Fonts.tiny.get_height()) // 2), align="right")


def _color_for(pct, warn, crit):
    """Same green/yellow/red logic as lcars_theme.bar_color_for_pct, but
    with thresholds that can be tuned per metric instead of one fixed
    60/85 pair for everything."""
    if pct >= crit:
        return t.STATUS_BAD
    if pct >= warn:
        return t.STATUS_WARN
    return t.STATUS_OK


def _mini_bar(surface, x, y, w, label, pct, value_str):
    """Compact labeled bar for the 5/15-min trend readouts -- same visual
    language as the main gauges, just half-width and shorter."""
    t.text(surface, f"{label} {value_str}", t.Fonts.tiny, t.GREY, (x, y))
    bar_y = y + t.Fonts.tiny.get_height() + 2
    t.hbar(surface, (x, bar_y, w, 7), pct, t.bar_color_for_pct(pct))


def _overall_status(items):
    """items: list of (pct, warn_threshold, crit_threshold). Storage
    gets much higher thresholds than CPU/RAM/temp/load: a disk sitting
    at 60-70% full is completely normal for a working Pi-hole setup
    (OS + gravity DB + growing logs) and isn't a sign of active stress
    the way high CPU/temp/load is -- it shouldn't read as 'elevated'
    until space is actually starting to run out."""
    worst_level = 0  # 0=nominal, 1=elevated, 2=critical
    for pct, warn, crit in items:
        if pct is None:
            continue
        if pct >= crit:
            worst_level = max(worst_level, 2)
        elif pct >= warn:
            worst_level = max(worst_level, 1)
    if worst_level == 2:
        return "CRITICAL", t.STATUS_BAD
    if worst_level == 1:
        return "ELEVATED", t.STATUS_WARN
    return "NOMINAL", t.STATUS_OK


def draw(surface, content_rect, hub_state):
    sysd = hub_state.get("system")
    x, y, w, h = content_rect

    if not sysd:
        t.text(surface, "SYSTEM DATA UNAVAILABLE", t.Fonts.med, t.STATUS_BAD, (x, y))
        return

    # Precompute every gauge's percentage up front so the CPU LOAD row
    # can show an overall status summary before the other rows are drawn.
    cpu_pct = sysd["cpu_pct"]
    ram_pct = sysd["ram_pct"]
    disk_pct = sysd["disk_pct"]

    temp_c = sysd.get("temp_c")
    temp_pct = min(100, max(0, (temp_c - 30) / (80 - 30) * 100)) if temp_c is not None else None

    load = sysd.get("load_avg")
    cores = sysd.get("cpu_count") or 1
    load_pct = min(100, (load[0] / cores) * 100) if load else None

    status_label, status_color = _overall_status([
        (cpu_pct, 60, 85),
        (ram_pct, 60, 85),
        (disk_pct, 90, 97),   # capacity fact, not active stress -- don't flag until nearly full
        (temp_pct, 60, 85),
        (load_pct, 60, 85),
    ])

    row_h = 30
    _row(surface, (x, y, w, row_h), "CPU LOAD", cpu_pct,
         detail_str=f"SYSTEM: {status_label}", detail_color=status_color)

    ram_gb_used = sysd["ram_used"] / (1024 ** 3)
    ram_gb_total = sysd["ram_total"] / (1024 ** 3)
    _row(surface, (x, y + row_h, w, row_h), "MEMORY",
         ram_pct, f"{ram_gb_used:.1f}/{ram_gb_total:.1f}GB")

    disk_gb_used = sysd["disk_used"] / (1024 ** 3)
    disk_gb_total = sysd["disk_total"] / (1024 ** 3)
    _row(surface, (x, y + row_h * 2, w, row_h), "STORAGE",
         disk_pct, f"{disk_gb_used:.1f}/{disk_gb_total:.1f}GB",
         bar_color=_color_for(disk_pct, 90, 97))

    if temp_pct is not None:
        _row(surface, (x, y + row_h * 3, w, row_h), "CORE TEMP",
             temp_pct, f"{sysd['temp_f']:.0f}\u00b0F")

    if load:
        # Trend arrow comparing right-now (1min) to the 15min baseline --
        # answers "is this getting worse?" at a glance instead of making
        # you do the math on three raw decimals yourself.
        if load[0] > load[2] * 1.15:
            arrow, arrow_color = "\u25b2", t.STATUS_BAD
        elif load[0] < load[2] * 0.85:
            arrow, arrow_color = "\u25bc", t.STATUS_OK
        else:
            arrow, arrow_color = "\u25ac", t.PEACH
        _row(surface, (x, y + row_h * 4, w, row_h), "SYSTEM LOAD",
             load_pct, f"{load[0]:.2f}/{cores} CORES {arrow}", detail_color=arrow_color)
    else:
        t.text(surface, "SYSTEM LOAD: N/A", t.Fonts.small, t.WHITE, (x, y + row_h * 4))

    # ---- Process count, as a colored LCARS readout rather than plain text ----
    pill_y = y + row_h * 5 + 4
    pill_h = 20
    proc = sysd.get("proc_count")
    proc_str = str(proc) if proc is not None else "N/A"

    t.pill(surface, (x, pill_y, w, pill_h), t.ORANGE)
    t.text(surface, "PROCESSES", t.Fonts.tiny, t.BLACK,
           (x + 14, pill_y + (pill_h - t.Fonts.tiny.get_height()) // 2))
    t.text(surface, proc_str, t.Fonts.small, t.BLACK,
           (x + w - 14, pill_y + (pill_h - t.Fonts.small.get_height()) // 2), align="right")

    # ---- Network throughput, as two mini-bars (replaces the old 5/15-min
    # load readout -- that trend is still visible via the arrow on the
    # SYSTEM LOAD row above, and there's no spare room for both) ----
    net = sysd.get("network")
    trend_y = pill_y + pill_h + 3
    half_w = (w - 10) // 2
    if net:
        up_pct = min(100, (net["up_mbps"] / 100) * 100)   # 100Mbps treated as full-scale for the bar
        down_pct = min(100, (net["down_mbps"] / 100) * 100)
        _mini_bar(surface, x, trend_y, half_w, "UP", up_pct, f"{net['up_mbps']:.1f}Mb/s")
        _mini_bar(surface, x + half_w + 10, trend_y, half_w, "DOWN", down_pct, f"{net['down_mbps']:.1f}Mb/s")
    else:
        # First snapshot after boot has no prior reading to diff against yet
        t.text(surface, "NETWORK: MEASURING\u2026", t.Fonts.tiny, t.GREY, (x, trend_y))
