from app.alerts import (
    check_rapid_pressure_drop,
    check_temperature_threshold,
    evaluate_alerts,
)
from conftest import make_reading


def test_rapid_pressure_drop_fires_on_sharp_decline():
    readings = [
        make_reading(timestamp="2026-01-15T00:00:00+00:00", pressure=1015.0),
        make_reading(timestamp="2026-01-15T01:00:00+00:00", pressure=1013.0),
        make_reading(timestamp="2026-01-15T02:00:00+00:00", pressure=1010.0),
        make_reading(timestamp="2026-01-15T03:00:00+00:00", pressure=1005.0),
    ]
    alerts = check_rapid_pressure_drop(
        readings, window_hours=3, drop_threshold_hpa=3.0
    )
    assert len(alerts) >= 1
    assert alerts[-1]["type"] == "rapid_pressure_drop"
    assert alerts[-1]["drop_hpa"] >= 3.0


def test_rapid_pressure_drop_does_not_fire_on_stable_pressure():
    readings = [
        make_reading(timestamp="2026-01-15T00:00:00+00:00", pressure=1013.0),
        make_reading(timestamp="2026-01-15T01:00:00+00:00", pressure=1013.2),
        make_reading(timestamp="2026-01-15T02:00:00+00:00", pressure=1012.8),
        make_reading(timestamp="2026-01-15T03:00:00+00:00", pressure=1013.1),
    ]
    alerts = check_rapid_pressure_drop(
        readings, window_hours=3, drop_threshold_hpa=3.0
    )
    assert alerts == []


def test_temperature_threshold_fires_when_above_threshold():
    readings = [
        make_reading(timestamp="2026-01-15T12:00:00+00:00", temperature=37.5),
    ]
    alerts = check_temperature_threshold(readings, high_threshold_c=35.0)
    assert len(alerts) == 1
    assert alerts[0]["type"] == "high_temperature"
    assert alerts[0]["temperature"] == 37.5


def test_temperature_threshold_does_not_fire_when_below_threshold():
    readings = [
        make_reading(timestamp="2026-01-15T12:00:00+00:00", temperature=22.0),
    ]
    alerts = check_temperature_threshold(readings, high_threshold_c=35.0)
    assert alerts == []


def test_temperature_threshold_low_freeze_warning():
    readings = [
        make_reading(timestamp="2026-01-15T04:00:00+00:00", temperature=-3.0),
    ]
    alerts = check_temperature_threshold(
        readings, high_threshold_c=35.0, low_threshold_c=0.0
    )
    assert len(alerts) == 1
    assert alerts[0]["type"] == "low_temperature"


def test_evaluate_alerts_combines_and_sorts_both_rule_types():
    readings = [
        make_reading(timestamp="2026-01-15T00:00:00+00:00", pressure=1015.0, temperature=10.0),
        make_reading(timestamp="2026-01-15T01:00:00+00:00", pressure=1010.0, temperature=36.0),
    ]
    alerts = evaluate_alerts(
        readings, window_hours=3, drop_threshold_hpa=3.0, high_threshold_c=35.0
    )
    types = {a["type"] for a in alerts}
    assert "rapid_pressure_drop" in types
    assert "high_temperature" in types
    # sorted chronologically
    timestamps = [a["timestamp"] for a in alerts]
    assert timestamps == sorted(timestamps)
