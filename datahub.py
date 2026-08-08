"""
Polls every data source on its own interval, in background threads, and
keeps a thread-safe snapshot that the render loop reads from. Nothing in
the pygame loop ever blocks on a network call.
"""
import threading
import time

import config
from data import system_stats, weather, iss, moon
from data.pihole import PiHoleClient


class DataHub:
    def __init__(self):
        self._lock = threading.Lock()
        self.pihole_client = PiHoleClient()
        self._state = {
            "system": None,
            "pihole_summary": None,
            "pihole_blocking": None,   # True/False/None(unknown/unreachable)
            "pihole_blocking_timer_sec": None,   # seconds remaining when last polled, or None (indefinite)
            "pihole_blocking_timer_polled_ts": None,  # when that reading was taken, for a live countdown
            "pihole_top_blocked": None,
            "pihole_top_allowed": None,
            "pihole_top_client": None,
            "pihole_versions": None,
            "pihole_history": None,
            "pihole_last_contact_ts": None,  # last time Pi-hole answered at all
            "pihole_upstream_dns": None,
            "pihole_latency_ms": None,
            "pihole_gravity_last_update": None,
            "pihole_recent_queries": None,
            "weather": None,
            "iss": None,
            "moon": None,
        }
        self._stop = False
        self._version = 0

    def get(self):
        with self._lock:
            return dict(self._state)

    def version(self):
        """Monotonic counter bumped on every data write. Lets the render
        loop detect 'did any data change since last frame?' without
        deep-comparing the whole state dict."""
        with self._lock:
            return self._version

    def _set(self, key, value):
        with self._lock:
            if self._state.get(key) != value:
                self._state[key] = value
                self._version += 1

    def start(self):
        threading.Thread(target=self._loop_system, daemon=True).start()
        threading.Thread(target=self._loop_pihole, daemon=True).start()
        threading.Thread(target=self._loop_pihole_tops, daemon=True).start()
        threading.Thread(target=self._loop_history, daemon=True).start()
        threading.Thread(target=self._loop_config, daemon=True).start()
        threading.Thread(target=self._loop_queries, daemon=True).start()
        threading.Thread(target=self._loop_weather, daemon=True).start()
        threading.Thread(target=self._loop_iss, daemon=True).start()
        threading.Thread(target=self._loop_moon, daemon=True).start()

    def stop(self):
        self._stop = True

    def disable_blocking_async(self, seconds):
        """Fire-and-forget: disable Pi-hole blocking for `seconds`,
        called from the Tactical screen's touch button. Runs in its own
        thread so a slow network call never stalls the render loop."""
        def _do():
            self.pihole_client.set_blocking(False, timer=seconds)
        threading.Thread(target=_do, daemon=True).start()

    def _loop_system(self):
        while not self._stop:
            try:
                self._set("system", system_stats.snapshot())
            except Exception:
                pass
            time.sleep(config.REFRESH_SYSTEM)

    def _loop_pihole(self):
        """Fast loop -- only the two calls that genuinely need 5s cadence.
        summary() drives the live query counters; blocking_status() drives
        Yellow Alert responsiveness. Everything else moved to slower
        loops below, since polling version strings and daily aggregates
        every 5 seconds was ~4x the API traffic for no visible benefit."""
        while not self._stop:
            try:
                summary = self.pihole_client.summary()
                blocking, timer_sec = self.pihole_client.blocking_status()
                self._set("pihole_summary", summary)
                self._set("pihole_blocking", blocking)
                self._set("pihole_blocking_timer_sec", timer_sec)
                self._set("pihole_blocking_timer_polled_ts", time.time() if timer_sec is not None else None)
                # Any of these succeeding means we were actually able to
                # talk to Pi-hole -- that's what "network is fine" means
                # here, distinct from "blocking happens to be off".
                if summary is not None or blocking is not None:
                    self._set("pihole_last_contact_ts", time.time())
                    self._set("pihole_latency_ms", self.pihole_client.last_latency_ms)
            except Exception:
                pass
            time.sleep(config.REFRESH_PIHOLE)

    def _loop_pihole_tops(self):
        """Top blocked/allowed domain and top client -- daily aggregates
        that barely move minute to minute."""
        while not self._stop:
            try:
                self._set("pihole_top_blocked", self.pihole_client.top_blocked())
                self._set("pihole_top_allowed", self.pihole_client.top_allowed())
                self._set("pihole_top_client", self.pihole_client.top_client())
            except Exception:
                pass
            time.sleep(config.REFRESH_TOPS)

    def _loop_history(self):
        while not self._stop:
            try:
                self._set("pihole_history", self.pihole_client.history())
            except Exception:
                pass
            time.sleep(config.REFRESH_HISTORY)

    def _loop_config(self):
        while not self._stop:
            ok = False
            try:
                self._set("pihole_upstream_dns", self.pihole_client.upstream_dns())
                self._set("pihole_gravity_last_update", self.pihole_client.gravity_last_update())
                # Core/FTL/Web version strings change on the order of
                # months -- no reason to ask every 5 seconds.
                versions = self.pihole_client.versions()
                self._set("pihole_versions", versions)
                # Not just "did we get a dict?" -- on a cold boot Pi-hole
                # can answer successfully while its own version cache is
                # still filling in, returning e.g. core and ftl populated
                # but web null. That's a valid dict, so a plain None check
                # would back off for the full interval and leave one field
                # showing N/A for 10 minutes. Only accept it as settled
                # once every component has a real value.
                ok = bool(versions) and all(
                    versions.get(k) not in (None, "N/A") for k in ("core", "ftl", "web")
                )
            except Exception:
                pass
            # Only back off to the slow interval once we've actually got
            # data. On a cold boot the LCARS app can easily win the race
            # against pihole-FTL becoming ready to serve requests -- and
            # systemd's After= only guarantees FTL was *started*, not that
            # it's accepting API calls yet. Without this, one early failure
            # would leave Ship's Log showing UNAVAILABLE for a full
            # REFRESH_CONFIG period with nothing actually wrong.
            time.sleep(config.REFRESH_CONFIG if ok else config.REFRESH_CONFIG_RETRY)

    def _loop_queries(self):
        while not self._stop:
            try:
                self._set("pihole_recent_queries", self.pihole_client.recent_queries())
            except Exception:
                pass
            time.sleep(config.REFRESH_QUERIES)

    def _loop_weather(self):
        while not self._stop:
            try:
                self._set("weather", weather.fetch())
            except Exception:
                pass
            time.sleep(config.REFRESH_WEATHER)

    def _loop_iss(self):
        while not self._stop:
            try:
                self._set("iss", iss.fetch_next_pass())
            except Exception:
                pass
            time.sleep(config.REFRESH_ISS)

    def _loop_moon(self):
        while not self._stop:
            try:
                self._set("moon", moon.get_phase())
            except Exception:
                pass
            time.sleep(config.REFRESH_MOON_SUN)
