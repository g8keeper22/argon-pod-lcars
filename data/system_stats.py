"""System telemetry for the local Pi (the POD's own Pi Zero 2W)."""
import datetime
import os
import socket
import time

try:
    import psutil
except ImportError:
    psutil = None


def get_cpu_percent():
    if psutil:
        return psutil.cpu_percent(interval=None)
    return 0.0


def get_ram():
    if psutil:
        vm = psutil.virtual_memory()
        return vm.percent, vm.used, vm.total
    return 0.0, 0, 0


def get_disk():
    if psutil:
        du = psutil.disk_usage("/")
        return du.percent, du.used, du.total
    return 0.0, 0, 0


def get_cpu_temp_f():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            milli_c = int(f.read().strip())
        c = milli_c / 1000.0
        return c, (c * 9 / 5) + 32
    except Exception:
        return None, None


def get_uptime_str():
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
    except Exception:
        return "N/A"
    days, rem = divmod(int(secs), 86400)
    hours, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours:02d}h {mins:02d}m"
    return f"{hours:02d}h {mins:02d}m"


def get_boot_time():
    """Returns a datetime, or None -- deliberately not pre-formatted to
    a string here, since the display format (12hr/24hr) is a render-time
    choice from the Settings panel, not a data-collection concern."""
    try:
        with open("/proc/stat") as f:
            for line in f:
                if line.startswith("btime"):
                    ts = int(line.split()[1])
                    return datetime.datetime.fromtimestamp(ts)
    except Exception:
        pass
    if psutil:
        try:
            return datetime.datetime.fromtimestamp(psutil.boot_time())
        except Exception:
            pass
    return None


def get_pi_model():
    try:
        with open("/proc/device-tree/model") as f:
            return f.read().strip("\x00").strip()
    except Exception:
        pass
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("Model"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return "N/A"


def get_load_avg():
    try:
        return os.getloadavg()  # (1min, 5min, 15min)
    except Exception:
        return None


def get_process_count():
    if psutil:
        try:
            return len(psutil.pids())
        except Exception:
            pass
    return None


def get_cpu_count():
    try:
        return os.cpu_count() or 1
    except Exception:
        return 1


_last_net = {"time": None, "bytes_sent": None, "bytes_recv": None}


def get_network_throughput():
    """Up/down throughput in Mbps, computed from the delta between this
    call and the last one (psutil only exposes cumulative byte counters,
    not a rate). Returns None on the very first call, since there's no
    prior reading yet to diff against."""
    if not psutil:
        return None
    try:
        io = psutil.net_io_counters()
        now = time.time()
        result = None
        if _last_net["time"] is not None:
            dt = now - _last_net["time"]
            if dt > 0:
                up = max(0.0, (io.bytes_sent - _last_net["bytes_sent"]) * 8 / dt / 1_000_000)
                down = max(0.0, (io.bytes_recv - _last_net["bytes_recv"]) * 8 / dt / 1_000_000)
                result = {"up_mbps": up, "down_mbps": down}
        _last_net["time"] = now
        _last_net["bytes_sent"] = io.bytes_sent
        _last_net["bytes_recv"] = io.bytes_recv
        return result
    except Exception:
        return None


def get_local_ip():
    """Best-effort local IP without needing external connectivity."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "N/A"
    finally:
        s.close()


def get_hostname():
    return socket.gethostname()


# These never change while the process is running -- read once, not
# every REFRESH_SYSTEM cycle. (boot_time and pi_model come from /proc,
# hostname and cpu_count from the OS; none of them can change without a
# reboot or a restart of this app.)
_STATIC = {}


def _static():
    if not _STATIC:
        _STATIC.update({
            "boot_time": get_boot_time(),
            "pi_model": get_pi_model(),
            "cpu_count": get_cpu_count(),
            "hostname": get_hostname(),
        })
    return _STATIC


def snapshot():
    cpu = get_cpu_percent()
    ram_pct, ram_used, ram_total = get_ram()
    disk_pct, disk_used, disk_total = get_disk()
    temp_c, temp_f = get_cpu_temp_f()
    static = _static()
    return {
        "cpu_pct": cpu,
        "ram_pct": ram_pct,
        "ram_used": ram_used,
        "ram_total": ram_total,
        "disk_pct": disk_pct,
        "disk_used": disk_used,
        "disk_total": disk_total,
        "temp_c": temp_c,
        "temp_f": temp_f,
        "uptime": get_uptime_str(),
        "boot_time": static["boot_time"],
        "pi_model": static["pi_model"],
        "load_avg": get_load_avg(),
        "proc_count": get_process_count(),
        "cpu_count": static["cpu_count"],
        "network": get_network_throughput(),
        "ip": get_local_ip(),
        "hostname": static["hostname"],
        "ts": time.time(),
    }
