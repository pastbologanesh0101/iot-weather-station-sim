"""Input validation for incoming sensor readings.

Readings that are physically implausible are rejected outright with a
clear error message rather than silently stored, since garbage-in here
would poison every downstream aggregation and alert.
"""

from datetime import datetime, timezone

# Generous but physically sane bounds. Earth's recorded surface extremes
# are roughly -90C to +57C; we pad a bit for simulation headroom.
TEMPERATURE_MIN_C = -90.0
TEMPERATURE_MAX_C = 65.0
HUMIDITY_MIN_PCT = 0.0
HUMIDITY_MAX_PCT = 100.0
# Sea-level-adjusted barometric pressure record range, padded slightly.
PRESSURE_MIN_HPA = 850.0
PRESSURE_MAX_HPA = 1085.0
WIND_SPEED_MIN_MS = 0.0
WIND_SPEED_MAX_MS = 120.0  # faster than any recorded surface gust
WIND_DIRECTION_MIN_DEG = 0.0
WIND_DIRECTION_MAX_DEG = 360.0

REQUIRED_FIELDS = ("station_id", "temperature", "humidity", "pressure")


class ValidationError(ValueError):
    """Raised when an incoming reading fails validation."""


def _require_number(payload, field, low, high):
    if field not in payload or payload[field] is None:
        raise ValidationError(f"missing required field: {field}")
    value = payload[field]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"field {field!r} must be a number")
    if not (low <= value <= high):
        raise ValidationError(
            f"field {field!r} value {value} is out of plausible range "
            f"[{low}, {high}]"
        )
    return float(value)


def validate_reading(payload):
    """Validate and normalize a single reading dict.

    Returns a normalized dict on success, or raises ValidationError with a
    human-readable message describing exactly what was wrong.
    """
    if not isinstance(payload, dict):
        raise ValidationError("reading must be a JSON object")

    for field in REQUIRED_FIELDS:
        if field not in payload:
            raise ValidationError(f"missing required field: {field}")

    station_id = payload.get("station_id")
    if not isinstance(station_id, str) or not station_id.strip():
        raise ValidationError("station_id must be a non-empty string")

    temperature = _require_number(
        payload, "temperature", TEMPERATURE_MIN_C, TEMPERATURE_MAX_C
    )
    humidity = _require_number(
        payload, "humidity", HUMIDITY_MIN_PCT, HUMIDITY_MAX_PCT
    )
    pressure = _require_number(
        payload, "pressure", PRESSURE_MIN_HPA, PRESSURE_MAX_HPA
    )

    wind_speed = None
    if payload.get("wind_speed") is not None:
        wind_speed = _require_number(
            payload, "wind_speed", WIND_SPEED_MIN_MS, WIND_SPEED_MAX_MS
        )

    wind_direction = None
    if payload.get("wind_direction") is not None:
        wind_direction = _require_number(
            payload,
            "wind_direction",
            WIND_DIRECTION_MIN_DEG,
            WIND_DIRECTION_MAX_DEG,
        )

    timestamp = payload.get("timestamp")
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()
    else:
        if not isinstance(timestamp, str):
            raise ValidationError("timestamp must be an ISO-8601 string")
        try:
            _parse_timestamp(timestamp)
        except ValueError as exc:
            raise ValidationError(f"invalid timestamp: {exc}") from exc

    lat = payload.get("lat")
    lon = payload.get("lon")
    if lat is not None and not (-90.0 <= float(lat) <= 90.0):
        raise ValidationError("lat must be between -90 and 90")
    if lon is not None and not (-180.0 <= float(lon) <= 180.0):
        raise ValidationError("lon must be between -180 and 180")

    return {
        "station_id": station_id,
        "lat": float(lat) if lat is not None else None,
        "lon": float(lon) if lon is not None else None,
        "timestamp": timestamp,
        "temperature": temperature,
        "humidity": humidity,
        "pressure": pressure,
        "wind_speed": wind_speed,
        "wind_direction": wind_direction,
    }


def _parse_timestamp(value):
    """Parse an ISO-8601 timestamp, accepting a trailing 'Z'."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
