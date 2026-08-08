"""
ISS next-pass prediction.
Uses the free, keyless g7vrd satellite-passes API. This is a small
community-run service rather than an official NASA endpoint, so treat it
as best-effort -- if it's unreachable the Astrometrics screen will just
show 'ISS DATA UNAVAILABLE' instead of crashing.
"""

import datetime as dt
import requests
import config

ISS_NORAD_ID = 25544
API_BASE = "https://api.g7vrd.co.uk/v1/satellite-passes"


def _parse_utc(value):
    if value is None:
        return None
    try:
        # Accept either ISO-8601 strings or epoch-like numbers.
        if isinstance(value, (int, float)):
            return dt.datetime.fromtimestamp(float(value), tz=dt.timezone.utc)
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = dt.datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except Exception:
        return None


def fetch_next_pass():
    try:
        # IMPORTANT: no altitude in the path.
        url = (
            f"{API_BASE}/{ISS_NORAD_ID}/"
            f"{config.LATITUDE}/{config.LONGITUDE}.json"
        )
        params = {
            "minelevation": 10,
            "hours": 48,
        }
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        passes = data.get("passes") or []
        if not passes:
            return None
        p = passes[0]
        start = _parse_utc(p.get("start") or p.get("startUTC"))
        tca = _parse_utc(p.get("tca"))
        end = _parse_utc(p.get("end"))
        duration = p.get("duration")
        if duration is None and start and end:
            duration = int((end - start).total_seconds())
        max_elevation = p.get("max_elevation")
        if max_elevation is None:
            max_elevation = p.get("maxElevation")
        return {
            "start_local": start.astimezone() if start else None,
            "tca_local": tca.astimezone() if tca else None,
            "end_local": end.astimezone() if end else None,
            "duration_sec": int(duration) if duration is not None else None,
            "max_elevation": max_elevation,
        }
    except Exception:
        return None
