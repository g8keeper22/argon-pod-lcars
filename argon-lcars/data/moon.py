"""Offline moon-phase calculation -- no network call needed."""
import datetime

SYNODIC_MONTH = 29.53058867
# A known new moon reference (2000-01-06 18:14 UTC)
_REF_NEW_MOON = datetime.datetime(2000, 1, 6, 18, 14, tzinfo=datetime.timezone.utc)

PHASE_NAMES = [
    (0.0, "New Moon"),
    (0.03, "Waxing Crescent"),
    (0.22, "First Quarter"),
    (0.28, "Waxing Gibbous"),
    (0.47, "Full Moon"),
    (0.53, "Waning Gibbous"),
    (0.72, "Third Quarter"),
    (0.78, "Waning Crescent"),
    (0.97, "New Moon"),
]


def get_phase():
    now = datetime.datetime.now(datetime.timezone.utc)
    days_since = (now - _REF_NEW_MOON).total_seconds() / 86400.0
    age = days_since % SYNODIC_MONTH
    frac = age / SYNODIC_MONTH  # 0..1 through the cycle

    name = "New Moon"
    for threshold, label in PHASE_NAMES:
        if frac >= threshold:
            name = label
    illum = (1 - abs(frac - 0.5) / 0.5) * 100  # rough illumination %
    waxing = frac < 0.5

    half_month = SYNODIC_MONTH / 2
    days_to_full = (half_month - age) % SYNODIC_MONTH
    days_to_new = (SYNODIC_MONTH - age) % SYNODIC_MONTH

    return {
        "name": name, "age_days": age, "illumination_pct": illum, "waxing": waxing,
        "days_to_full": days_to_full, "days_to_new": days_to_new,
    }
