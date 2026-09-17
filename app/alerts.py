"""Weather alert rule engine.

Two simple, explainable heuristics operate over a time-ordered list of
readings (dicts with at least `timestamp`, `temperature`, `pressure`):

1. Rapid pressure drop: if pressure falls by more than
   `drop_threshold_hpa` within any `window_hours` window, that's a classic
   storm-approaching signal (a real, widely used heuristic -- meteorologists
   watch for ~3+ hPa/3h drops as a sign of an approaching low-pressure
   system).
2. Temperature threshold: fires when the latest reading's temperature is
   at or above (or, for cold alerts, at or below) a configured threshold.
"""

from datetime import datetime


def _parse_ts(ts):
    if isinstance(ts, datetime):
        return ts
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def check_rapid_pressure_drop(readings, window_hours=3, drop_threshold_hpa=3.0):
    """Return a list of alert dicts for rapid pressure drops.

    For each reading, look back up to `window_hours` and see if pressure
    has dropped by more than `drop_threshold_hpa` hPa within that window.
    Readings must be provided in chronological order (oldest first).
    """
    alerts = []
    parsed = [(r, _parse_ts(r["timestamp"])) for r in readings]

    for i, (reading, ts) in enumerate(parsed):
        window_start = ts.timestamp() - window_hours * 3600
        # Find the earliest reading within the window (inclusive).
        candidates = [
            r for r, t in parsed[: i + 1] if t.timestamp() >= window_start
        ]
        if len(candidates) < 2:
            continue
        window_max_pressure = max(r["pressure"] for r in candidates)
        drop = window_max_pressure - reading["pressure"]
        if drop >= drop_threshold_hpa:
            alerts.append(
                {
                    "type": "rapid_pressure_drop",
                    "station_id": reading.get("station_id"),
                    "timestamp": reading["timestamp"],
                    "drop_hpa": round(drop, 2),
                    "window_hours": window_hours,
                    "message": (
                        f"Pressure dropped {drop:.2f} hPa within "
                        f"{window_hours}h window - possible approaching storm"
                    ),
                }
            )
    return alerts


def check_temperature_threshold(readings, high_threshold_c=35.0,
                                 low_threshold_c=None):
    """Return alert dicts for readings crossing a temperature threshold.

    `high_threshold_c`: fires when temperature >= this value.
    `low_threshold_c`: if provided, also fires when temperature <= this
    value (e.g. a freeze warning).
    """
    alerts = []
    for reading in readings:
        temperature = reading["temperature"]
        if high_threshold_c is not None and temperature >= high_threshold_c:
            alerts.append(
                {
                    "type": "high_temperature",
                    "station_id": reading.get("station_id"),
                    "timestamp": reading["timestamp"],
                    "temperature": temperature,
                    "threshold": high_threshold_c,
                    "message": (
                        f"Temperature {temperature:.1f}C at/above threshold "
                        f"{high_threshold_c:.1f}C"
                    ),
                }
            )
        if low_threshold_c is not None and temperature <= low_threshold_c:
            alerts.append(
                {
                    "type": "low_temperature",
                    "station_id": reading.get("station_id"),
                    "timestamp": reading["timestamp"],
                    "temperature": temperature,
                    "threshold": low_threshold_c,
                    "message": (
                        f"Temperature {temperature:.1f}C at/below threshold "
                        f"{low_threshold_c:.1f}C"
                    ),
                }
            )
    return alerts


def evaluate_alerts(readings, window_hours=3, drop_threshold_hpa=3.0,
                     high_threshold_c=35.0, low_threshold_c=None):
    """Run all alert rules and return a combined, timestamp-sorted list."""
    ordered = sorted(readings, key=lambda r: _parse_ts(r["timestamp"]))
    alerts = []
    alerts.extend(
        check_rapid_pressure_drop(
            ordered, window_hours=window_hours,
            drop_threshold_hpa=drop_threshold_hpa,
        )
    )
    alerts.extend(
        check_temperature_threshold(
            ordered, high_threshold_c=high_threshold_c,
            low_threshold_c=low_threshold_c,
        )
    )
    alerts.sort(key=lambda a: _parse_ts(a["timestamp"]))
    return alerts
