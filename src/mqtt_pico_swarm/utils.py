

def _current_timestamp_string():
    """Return current time formatted as YYYY-MM-DD HH:MM:SS.mmm."""
    milliseconds = 0
    epoch_seconds = None

    try:
        now = time.time()
        epoch_seconds = int(now)
        milliseconds = int((now - epoch_seconds) * 1000)
    except Exception:
        epoch_seconds = None
        milliseconds = 0

    try:
        if epoch_seconds is not None:
            tm = time.localtime(epoch_seconds)
        else:
            tm = time.localtime()
    except Exception:
        tm = time.gmtime()

    # Fallback till ticks_ms när time.time saknar sub-sekunds upplösning (MicroPython)
    if milliseconds == 0 and hasattr(time, "ticks_ms"):
        try:
            milliseconds = time.ticks_ms() % 1000
        except Exception:
            milliseconds = 0

    year_short = tm[0] % 100
    return "{:02d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}.{:03d}".format(
        year_short, tm[1], tm[2], tm[3], tm[4], tm[5], milliseconds
    )
"""Shared utility helpers for the MQTT Pico Swarm client.

These helpers must remain MicroPython-friendly (no datetime module, no
format strings). Only import standard modules available on the Pico W.
"""

import json
import time

try:
    import gc
except ImportError:  # pragma: no cover - desktop mocks might not provide gc
    gc = None

try:
    import network  # type: ignore
except ImportError:  # pragma: no cover - network module unavailable on host
    network = None


RFC3339_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def current_timestamp():
    """Return the current UTC timestamp in RFC3339 format.

    MicroPython's ``time.gmtime`` returns a tuple with UTC values. We avoid
    allocating large strings by building the timestamp manually.
    """
    gmt = time.gmtime()
    return (
        _pad(gmt[0], 4)
        + "-"
        + _pad(gmt[1])
        + "-"
        + _pad(gmt[2])
        + "T"
        + _pad(gmt[3])
        + ":"
        + _pad(gmt[4])
        + ":"
        + _pad(gmt[5])
        + "Z"
    )


def _pad(value, width=2):
    string_value = str(value)
    if len(string_value) >= width:
        return string_value
    return ("0" * (width - len(string_value))) + string_value


def json_dumps(data):
    """Serialize to JSON using MicroPython's json module.

    We ensure separators are compact to minimise payload size.
    """
    return json.dumps(data, separators=(",", ":"))


def json_loads(payload):
    """Parse JSON payloads and return python objects."""
    return json.loads(payload)


def trigger_gc(threshold=10240):
    """Invoke garbage collection if free heap is below threshold.

    Args:
        threshold: Byte threshold to trigger ``gc.collect`` when available.
    """
    if gc is None:
        return
    if hasattr(gc, "mem_free"):
        free_bytes = gc.mem_free()
        if free_bytes is not None and free_bytes < threshold:
            gc.collect()
    else:
        gc.collect()


def log(debug_enabled, message, prefix="[PicoSwarm]"):
    """Print message when debugging is enabled."""
    if not debug_enabled:
        return

    timestamp = _current_timestamp_string()
    print("{} {} {}".format(timestamp, prefix, message))


def is_network_available():
    """Return True if WiFi interface is active and connected.

    Desktop testmiljö kan sakna ``network``-modulen; i dessa fall antar vi att
    nätverket är tillgängligt för att inte blockera enhetstester.
    """
    if network is None:
        return True

    try:
        if hasattr(network, "WLAN") and hasattr(network, "STA_IF"):
            wlan = network.WLAN(network.STA_IF)
            if hasattr(wlan, "isconnected"):
                return bool(wlan.isconnected())
    except Exception:
        # Om nätverksmodulen existerar men rapporterar fel, betraktar vi
        # gränssnittet som otillgängligt.
        return False

    return True
