import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app import create_app


@pytest.fixture
def app():
    app = create_app(testing=True)
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def make_reading(station_id="station-1", timestamp="2026-01-15T12:00:00+00:00",
                  temperature=20.0, humidity=50.0, pressure=1013.0,
                  wind_speed=3.0, wind_direction=180.0, lat=None, lon=None):
    reading = {
        "station_id": station_id,
        "timestamp": timestamp,
        "temperature": temperature,
        "humidity": humidity,
        "pressure": pressure,
        "wind_speed": wind_speed,
        "wind_direction": wind_direction,
    }
    if lat is not None:
        reading["lat"] = lat
    if lon is not None:
        reading["lon"] = lon
    return reading
