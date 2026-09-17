"""Simulated IoT weather sensor client.

IMPORTANT: This module does not talk to any real hardware. It generates
realistic-ish synthetic readings in software:

- temperature follows a daily sinusoidal pattern (warmer in the afternoon,
  cooler at night) plus Gaussian noise.
- humidity is inversely correlated with temperature (drier when hotter)
  plus its own noise, clamped to [0, 100].
- barometric pressure follows a slow random-walk drift around a station's
  baseline, which is what makes the "rapid pressure drop" storm-alert
  heuristic meaningful to test against.
- wind speed/direction are generated independently per reading.

The client can either generate a single reading, a batch of history, or
run a simple polling loop that POSTs readings to a running backend over
HTTP (used by `scripts/run_simulator.py`, not by the test suite).
"""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class Station:
    station_id: str
    lat: float
    lon: float
    baseline_pressure: float = 1013.25
    mean_temperature: float = 18.0
    temperature_amplitude: float = 8.0
    # internal random-walk state for pressure drift
    _pressure_state: float = field(default=None, repr=False)

    def __post_init__(self):
        if self._pressure_state is None:
            self._pressure_state = self.baseline_pressure


DEFAULT_STATIONS = [
    Station(station_id="station-1", lat=37.7749, lon=-122.4194,
            mean_temperature=16.0, temperature_amplitude=6.0),
    Station(station_id="station-2", lat=40.7128, lon=-74.0060,
            mean_temperature=13.0, temperature_amplitude=10.0),
    Station(station_id="station-3", lat=25.7617, lon=-80.1918,
            mean_temperature=26.0, temperature_amplitude=4.0),
]


class SensorSimulator:
    """Generates simulated readings for one or more stations."""

    def __init__(self, stations=None, rng=None):
        self.stations = stations if stations is not None else DEFAULT_STATIONS
        self.rng = rng or random.Random()

    def _daily_temperature(self, station, at_time):
        # Peak temperature at 15:00 local-equivalent, trough at 03:00.
        seconds_in_day = 24 * 3600
        seconds = (
            at_time.hour * 3600 + at_time.minute * 60 + at_time.second
        )
        phase = 2 * math.pi * ((seconds / seconds_in_day) - 15 / 24)
        base = station.mean_temperature + station.temperature_amplitude * math.cos(
            phase
        )
        noise = self.rng.gauss(0, 0.6)
        return base + noise

    def _humidity_from_temperature(self, station, temperature):
        # Roughly: warmer air -> lower relative humidity, centered near 55%.
        deviation = temperature - station.mean_temperature
        humidity = 55.0 - deviation * 1.8 + self.rng.gauss(0, 3.0)
        return max(0.0, min(100.0, humidity))

    def _next_pressure(self, station):
        # Slow bounded random walk so pressure drifts realistically instead
        # of jumping around, but still occasionally produces a rapid drop
        # that the storm-alert rule should catch.
        step = self.rng.gauss(0, 0.4)
        new_pressure = station._pressure_state + step
        # Gently pull back toward baseline so it doesn't wander forever.
        pull = (station.baseline_pressure - new_pressure) * 0.02
        new_pressure += pull
        new_pressure = max(950.0, min(1050.0, new_pressure))
        station._pressure_state = new_pressure
        return new_pressure

    def _wind(self):
        speed = max(0.0, self.rng.gauss(4.5, 2.5))
        direction = self.rng.uniform(0, 360)
        return speed, direction

    def generate_reading(self, station, at_time=None):
        """Generate one simulated reading dict for the given station."""
        at_time = at_time or datetime.now(timezone.utc)
        temperature = self._daily_temperature(station, at_time)
        humidity = self._humidity_from_temperature(station, temperature)
        pressure = self._next_pressure(station)
        wind_speed, wind_direction = self._wind()
        return {
            "station_id": station.station_id,
            "lat": station.lat,
            "lon": station.lon,
            "timestamp": at_time.isoformat(),
            "temperature": round(temperature, 2),
            "humidity": round(humidity, 2),
            "pressure": round(pressure, 2),
            "wind_speed": round(wind_speed, 2),
            "wind_direction": round(wind_direction, 1),
        }

    def generate_batch(self, count_per_station=1, start_time=None,
                        interval_seconds=300):
        """Generate a batch of readings for all stations.

        Produces `count_per_station` readings per station, spaced
        `interval_seconds` apart starting at `start_time` (default: now).
        """
        start_time = start_time or datetime.now(timezone.utc)
        readings = []
        for station in self.stations:
            for i in range(count_per_station):
                at_time = start_time + timedelta(seconds=i * interval_seconds)
                readings.append(self.generate_reading(station, at_time))
        return readings

    def run_forever(self, post_fn, interval_seconds=5, iterations=None):
        """Continuously generate and hand off readings via `post_fn`.

        `post_fn` receives a list of reading dicts (one per station) each
        tick. `iterations`, if given, limits the loop for testability;
        otherwise it runs until interrupted.
        """
        import time

        count = 0
        while iterations is None or count < iterations:
            batch = [self.generate_reading(s) for s in self.stations]
            post_fn(batch)
            count += 1
            if iterations is None or count < iterations:
                time.sleep(interval_seconds)
