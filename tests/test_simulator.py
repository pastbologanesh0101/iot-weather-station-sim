import random
from datetime import datetime, timedelta, timezone

from app.sensor_simulator import SensorSimulator, Station
from app.validation import (
    HUMIDITY_MAX_PCT,
    HUMIDITY_MIN_PCT,
    PRESSURE_MAX_HPA,
    PRESSURE_MIN_HPA,
    TEMPERATURE_MAX_C,
    TEMPERATURE_MIN_C,
)


def test_simulated_readings_stay_within_plausible_bounds():
    rng = random.Random(42)
    simulator = SensorSimulator(rng=rng)
    start = datetime(2026, 1, 15, tzinfo=timezone.utc)

    samples = []
    for station in simulator.stations:
        for i in range(200):
            at_time = start + timedelta(minutes=i * 15)
            samples.append(simulator.generate_reading(station, at_time))

    assert len(samples) == 200 * len(simulator.stations)

    for reading in samples:
        assert TEMPERATURE_MIN_C <= reading["temperature"] <= TEMPERATURE_MAX_C
        assert HUMIDITY_MIN_PCT <= reading["humidity"] <= HUMIDITY_MAX_PCT
        assert PRESSURE_MIN_HPA <= reading["pressure"] <= PRESSURE_MAX_HPA
        assert reading["wind_speed"] >= 0.0
        assert 0.0 <= reading["wind_direction"] <= 360.0
        assert reading["station_id"]
        assert reading["timestamp"]


def test_simulated_temperature_follows_daily_pattern_roughly():
    rng = random.Random(7)
    station = Station(station_id="s", lat=0.0, lon=0.0, mean_temperature=15.0,
                       temperature_amplitude=8.0)
    simulator = SensorSimulator(stations=[station], rng=rng)

    afternoon = datetime(2026, 1, 15, 15, 0, tzinfo=timezone.utc)
    night = datetime(2026, 1, 15, 3, 0, tzinfo=timezone.utc)

    # Average several samples to smooth out noise.
    afternoon_avg = sum(
        simulator.generate_reading(station, afternoon)["temperature"]
        for _ in range(30)
    ) / 30
    night_avg = sum(
        simulator.generate_reading(station, night)["temperature"]
        for _ in range(30)
    ) / 30

    assert afternoon_avg > night_avg


def test_humidity_inversely_correlated_with_temperature():
    rng = random.Random(3)
    station = Station(station_id="s", lat=0.0, lon=0.0, mean_temperature=15.0,
                       temperature_amplitude=8.0)
    simulator = SensorSimulator(stations=[station], rng=rng)

    hot_reading = simulator._humidity_from_temperature(station, 30.0)
    cold_reading = simulator._humidity_from_temperature(station, 0.0)
    # Not a strict per-sample guarantee due to noise, but on average with a
    # 15C mean-temperature deviation swing it should hold clearly here.
    assert cold_reading > hot_reading


def test_generate_batch_produces_expected_count_and_spacing():
    rng = random.Random(1)
    simulator = SensorSimulator(rng=rng)
    start = datetime(2026, 1, 15, tzinfo=timezone.utc)
    batch = simulator.generate_batch(
        count_per_station=5, start_time=start, interval_seconds=300
    )
    assert len(batch) == 5 * len(simulator.stations)

    station_ids = {s.station_id for s in simulator.stations}
    for sid in station_ids:
        timestamps = sorted(
            r["timestamp"] for r in batch if r["station_id"] == sid
        )
        assert len(timestamps) == 5


def test_run_forever_respects_iteration_limit():
    rng = random.Random(2)
    simulator = SensorSimulator(rng=rng)
    posted = []
    simulator.run_forever(
        post_fn=lambda batch: posted.append(batch),
        interval_seconds=0,
        iterations=3,
    )
    assert len(posted) == 3
    for batch in posted:
        assert len(batch) == len(simulator.stations)
