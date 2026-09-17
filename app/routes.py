"""Flask routes: ingestion API, query API, and the HTML dashboard."""

from flask import Blueprint, jsonify, render_template, request

from . import repository
from .alerts import evaluate_alerts
from .validation import ValidationError, validate_reading

bp = Blueprint("weather", __name__)


@bp.post("/readings")
def post_readings():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "request body must be valid JSON"}), 400

    if isinstance(payload, list):
        raw_readings = payload
    elif isinstance(payload, dict) and isinstance(payload.get("readings"), list):
        raw_readings = payload["readings"]
    else:
        raw_readings = [payload]

    if not raw_readings:
        return jsonify({"error": "no readings provided"}), 400

    normalized = []
    for index, item in enumerate(raw_readings):
        try:
            normalized.append(validate_reading(item))
        except ValidationError as exc:
            return (
                jsonify(
                    {
                        "error": "validation failed",
                        "index": index,
                        "detail": str(exc),
                    }
                ),
                400,
            )

    ids = repository.insert_readings(normalized)
    return (
        jsonify({"inserted": len(ids), "ids": ids}),
        201,
    )


@bp.get("/readings/latest")
def get_latest():
    return jsonify(repository.get_latest_reading_per_station())


@bp.get("/readings/<station_id>")
def get_history(station_id):
    start = request.args.get("start")
    end = request.args.get("end")
    if start and end:
        readings = repository.get_readings_in_range(station_id, start, end)
    else:
        limit = request.args.get("limit", type=int)
        readings = repository.get_all_readings_for_station(
            station_id, limit=limit
        )
    return jsonify(readings)


@bp.get("/readings/<station_id>/daily")
def get_daily(station_id):
    day = request.args.get("day")
    if not day:
        return jsonify({"error": "query parameter 'day' is required (YYYY-MM-DD)"}), 400
    result = repository.get_daily_aggregation(station_id, day)
    if result is None:
        return jsonify({"error": "no readings for that station/day"}), 404
    return jsonify(result)


@bp.get("/alerts")
def get_alerts():
    station_id = request.args.get("station_id")
    window_hours = request.args.get("window_hours", default=3, type=float)
    drop_threshold_hpa = request.args.get(
        "drop_threshold_hpa", default=3.0, type=float
    )
    high_threshold_c = request.args.get(
        "high_threshold_c", default=35.0, type=float
    )
    low_threshold_c = request.args.get("low_threshold_c", type=float)

    if station_id:
        station_ids = [station_id]
    else:
        station_ids = repository.get_all_station_ids()

    all_alerts = []
    for sid in station_ids:
        readings = repository.get_all_readings_for_station(sid)
        all_alerts.extend(
            evaluate_alerts(
                readings,
                window_hours=window_hours,
                drop_threshold_hpa=drop_threshold_hpa,
                high_threshold_c=high_threshold_c,
                low_threshold_c=low_threshold_c,
            )
        )
    return jsonify(all_alerts)


def _sparkline(values):
    """Render a tiny ASCII/unicode sparkline for a list of numeric values."""
    if not values:
        return ""
    blocks = "▁▂▃▄▅▆▇█"
    lo, hi = min(values), max(values)
    span = hi - lo
    if span == 0:
        return blocks[0] * len(values)
    chars = []
    for v in values:
        idx = int((v - lo) / span * (len(blocks) - 1))
        chars.append(blocks[idx])
    return "".join(chars)


@bp.get("/")
def dashboard():
    latest = repository.get_latest_reading_per_station()
    station_histories = {}
    for reading in latest:
        sid = reading["station_id"]
        recent = repository.get_recent_readings_for_station(sid, count=20)
        station_histories[sid] = {
            "readings": recent,
            "sparkline": _sparkline([r["temperature"] for r in recent]),
        }
    return render_template(
        "dashboard.html",
        latest=latest,
        histories=station_histories,
    )
