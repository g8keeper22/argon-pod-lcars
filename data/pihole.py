"""
Pi-hole v6 API client.

Pi-hole v6 replaced the old ?auth=<token> query-string scheme with a
session-based login: POST a password to /api/auth, get back a session id
(sid), then send that sid on every subsequent call (either as the
'sid' query param or the 'X-FTL-SID' header -- this client sends both,
which is harmless and covers both v6 point releases).

v6-only -- no v5 fallback. blocking_status() and gravity_last_update()
have been verified against a live v6 instance running on Trixie.
"""
import time
import requests
import config

_session_lock_msg = None


class PiHoleClient:
    def __init__(self):
        scheme = "https" if config.PIHOLE_USE_HTTPS else "http"
        self.base = f"{scheme}://{config.PIHOLE_HOST}:{config.PIHOLE_PORT}/api"
        self.sid = None
        self.sid_expires = 0
        self.verify = config.PIHOLE_VERIFY_TLS
        self.last_latency_ms = None

    def _login(self):
        try:
            r = requests.post(
                f"{self.base}/auth",
                json={"password": config.PIHOLE_PASSWORD},
                timeout=5,
                verify=self.verify,
            )
            r.raise_for_status()
            data = r.json()
            sess = data.get("session", {})
            if sess.get("valid"):
                self.sid = sess.get("sid")
                # sessions are typically short-lived (~30 min); re-login
                # well before that
                self.sid_expires = time.time() + sess.get("validity", 1200) - 60
                return True
        except Exception:
            pass
        self.sid = None
        return False

    def _get(self, path, params=None):
        if not self.sid or time.time() > self.sid_expires:
            if not self._login():
                return None
        params = dict(params or {})
        params["sid"] = self.sid
        try:
            start = time.time()
            r = requests.get(
                f"{self.base}{path}",
                params=params,
                headers={"X-FTL-SID": self.sid},
                timeout=5,
                verify=self.verify,
            )
            if r.status_code == 401:
                # session expired mid-flight, retry once
                if self._login():
                    params["sid"] = self.sid
                    start = time.time()
                    r = requests.get(
                        f"{self.base}{path}",
                        params=params,
                        headers={"X-FTL-SID": self.sid},
                        timeout=5,
                        verify=self.verify,
                    )
            r.raise_for_status()
            self.last_latency_ms = (time.time() - start) * 1000
            return r.json()
        except Exception:
            return None

    # -- Public data pulls -------------------------------------------------

    def summary(self):
        """Queries today, blocked today, % blocked, domains on blocklist, clients."""
        data = self._get("/stats/summary")
        if not data:
            return None
        try:
            queries = data.get("queries", {})
            gravity = data.get("gravity", {})
            clients = data.get("clients", {})
            return {
                "total": queries.get("total"),
                "blocked": queries.get("blocked"),
                "percent_blocked": queries.get("percent_blocked"),
                "domains_blocked": gravity.get("domains_being_blocked"),
                "clients_active": clients.get("active"),
                "clients_total": clients.get("total"),
            }
        except Exception:
            return None

    def blocking_status(self):
        """Returns (status, timer_seconds).
        status is True (enabled), False (disabled), or None (unknown).
        timer_seconds is how long until Pi-hole auto-re-enables blocking
        (mirrors the 'timer' field set_blocking() sends), or None if
        blocking is enabled, or if it's disabled with no timer running
        (i.e. disabled indefinitely)."""
        data = self._get("/dns/blocking")
        if not data:
            return None, None
        status = data.get("blocking")
        timer = data.get("timer")
        if isinstance(status, bool):
            return status, timer if status is False else None
        if isinstance(status, str):
            lowered = status.strip().lower()
            if lowered in ("enabled", "on", "true", "1"):
                return True, None
            if lowered in ("disabled", "off", "false", "0"):
                return False, timer
        return None, None

    def top_blocked(self, count=1):
        data = self._get("/stats/top_domains", params={"blocked": "true", "count": count})
        if not data:
            return None
        try:
            domains = data.get("domains", [])
            return domains[0]["domain"] if domains else "N/A"
        except Exception:
            return None

    def top_allowed(self, count=1):
        data = self._get("/stats/top_domains", params={"blocked": "false", "count": count})
        if not data:
            return None
        try:
            domains = data.get("domains", [])
            return domains[0]["domain"] if domains else "N/A"
        except Exception:
            return None

    def top_client(self, count=1):
        data = self._get("/stats/top_clients", params={"count": count})
        if not data:
            return None
        try:
            clients = data.get("clients", [])
            if not clients:
                return "N/A"
            c = clients[0]
            return c.get("name") or c.get("ip", "N/A")
        except Exception:
            return None

    def versions(self):
        data = self._get("/info/version")
        if not data:
            return None

        def _local_version(node):
            """Pi-hole can return a component as present-but-null (e.g.
            "web": {"local": {"version": null}}) rather than omitting it.
            A plain .get(key, "N/A") only defaults on a *missing* key, so
            null would fall straight through and render as the literal
            string "None". The `or` catches both cases."""
            try:
                return ((node or {}).get("local") or {}).get("version") or "N/A"
            except Exception:
                return "N/A"

        try:
            v = data.get("version") or {}
            return {
                "core": _local_version(v.get("core")),
                "ftl": _local_version(v.get("ftl")),
                "web": _local_version(v.get("web")),
            }
        except Exception:
            return None

    def gateway_ip(self):
        return config.PIHOLE_HOST

    def gravity_last_update(self):
        data = self._get("/stats/summary")
        if not data:
            return None
        try:
            gravity = data.get("gravity", {})
            ts = gravity.get("last_update")
            return float(ts) if ts is not None else None
        except Exception:
            return None

    def recent_queries(self, count=12):
        """Most recent DNS queries, newest first, for the COMMS screen.
        Pi-hole v6's query-log endpoint and status field names have
        shifted between point releases -- this makes a best effort and
        degrades to None (not a crash) if the shape doesn't match."""
        data = self._get("/queries", params={"length": count})
        if not data:
            return None
        try:
            raw = data.get("queries", [])
            out = []
            for q in raw[:count]:
                status = str(q.get("status", "")).upper()
                blocked = any(k in status for k in ("GRAVITY", "BLACK", "DENY", "REGEX", "BLOCK"))
                client = q.get("client")
                if isinstance(client, dict):
                    client_name = client.get("name") or client.get("ip") or "N/A"
                else:
                    client_name = client or "N/A"
                out.append({
                    "time": q.get("time"),
                    "domain": q.get("domain", "N/A"),
                    "client": client_name,
                    "type": q.get("type", ""),
                    "blocked": blocked,
                })
            return out
        except Exception:
            return None

    def upstream_dns(self):
        """The primary configured upstream DNS server, for Tactical.
        Pi-hole v6's config endpoint nesting has shifted between point
        releases, so this tries a couple of common shapes defensively."""
        data = self._get("/config/dns")
        if not data:
            return None
        try:
            cfg = data.get("config", data)
            dns_cfg = cfg.get("dns", cfg)
            upstreams = dns_cfg.get("upstreams")
            if isinstance(upstreams, list) and upstreams:
                return upstreams[0]
        except Exception:
            pass
        return None

    def history(self):
        """Query volume over the last 24h, for the Engineering sparkline.
        Returns a list of {"total": int, "blocked": int} points, oldest
        first, or None if unreachable."""
        data = self._get("/history")
        if not data:
            return None
        try:
            raw = data.get("history", [])
            points = []
            for entry in raw:
                total = entry.get("total")
                if total is None:
                    total = entry.get("queries", entry.get("count"))
                if total is None:
                    continue
                points.append({"total": total, "blocked": entry.get("blocked") or 0})
            return points or None
        except Exception:
            return None

    def set_blocking(self, enabled, timer=None):
        """Enable/disable blocking, optionally auto-re-enabling after
        `timer` seconds (Pi-hole handles the re-enable itself server
        side). Used by the Tactical screen's 5-minute disable button."""
        if not self.sid or time.time() > self.sid_expires:
            if not self._login():
                return False
        payload = {"blocking": enabled}
        if timer is not None:
            payload["timer"] = timer
        try:
            r = requests.post(
                f"{self.base}/dns/blocking",
                json=payload,
                params={"sid": self.sid},
                headers={"X-FTL-SID": self.sid},
                timeout=6,
                verify=self.verify,
            )
            r.raise_for_status()
            return True
        except Exception:
            return False
