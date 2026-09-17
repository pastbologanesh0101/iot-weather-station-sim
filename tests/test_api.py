from conftest import make_reading


def test_valid_reading_ingestion_and_retrieval(client):
    reading = make_reading(station_id="station-1", timestamp="2026-01-15T08:00:00+00:00")
    resp = client.post("/readings", json=reading)
    assert resp.status_code == 201
    assert resp.get_json()["inserted"] == 1

    history = client.get("/readings/station-1")
    assert history.status_code == 200
    data = history.get_json()
    assert len(data) == 1
    assert data[0]["station_id"] == "station-1"
    assert data[0]["temperature"] == 20.0


def test_invalid_humidity_rejected_with_400(client):
    reading = make_reading(humidity=150.0)
    resp = client.post("/readings", json=reading)
    assert resp.status_code == 400
    body = resp.get_json()
    assert "humidity" in body["detail"]

    # confirm nothing was stored
    history = client.get("/readings/station-1")
    assert history.get_json() == []


def test_invalid_temperature_rejected_with_400(client):
    reading = make_reading(temperature=999.0)
    resp = client.post("/readings", json=reading)
    assert resp.status_code == 400
    body = resp.get_json()
    assert "temperature" in body["detail"]

    history = client.get("/readings/station-1")
    assert history.get_json() == []


def test_missing_required_field_rejected(client):
    reading = make_reading()
    del reading["pressure"]
    resp = client.post("/readings", json=reading)
    assert resp.status_code == 400


def test_latest_reading_per_station_multiple_stations(client):
    client.post("/readings", json=make_reading(
        station_id="station-1", timestamp="2026-01-15T08:00:00+00:00",
        temperature=10.0,
    ))
    client.post("/readings", json=make_reading(
        station_id="station-1", timestamp="2026-01-15T09:00:00+00:00",
        temperature=12.0,
    ))
    client.post("/readings", json=make_reading(
        station_id="station-2", timestamp="2026-01-15T08:30:00+00:00",
        temperature=30.0,
    ))

    resp = client.get("/readings/latest")
    assert resp.status_code == 200
    latest = {r["station_id"]: r for r in resp.get_json()}

    assert set(latest.keys()) == {"station-1", "station-2"}
    assert latest["station-1"]["temperature"] == 12.0
    assert latest["station-1"]["timestamp"] == "2026-01-15T09:00:00+00:00"
    assert latest["station-2"]["temperature"] == 30.0


def test_historical_time_range_query_filters_correctly(client):
    for hour, temp in [(6, 10.0), (9, 12.0), (12, 15.0), (15, 18.0), (18, 14.0)]:
        client.post("/readings", json=make_reading(
            station_id="station-1",
            timestamp=f"2026-01-15T{hour:02d}:00:00+00:00",
            temperature=temp,
        ))

    resp = client.get(
        "/readings/station-1",
        query_string={
            "start": "2026-01-15T09:00:00+00:00",
            "end": "2026-01-15T15:00:00+00:00",
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    temps = [r["temperature"] for r in data]
    assert temps == [12.0, 15.0, 18.0]


def test_daily_aggregation_min_max_avg(client):
    readings = [
        make_reading(station_id="station-1", timestamp="2026-01-15T00:00:00+00:00", temperature=10.0),
        make_reading(station_id="station-1", timestamp="2026-01-15T06:00:00+00:00", temperature=5.0),
        make_reading(station_id="station-1", timestamp="2026-01-15T12:00:00+00:00", temperature=20.0),
        make_reading(station_id="station-1", timestamp="2026-01-15T18:00:00+00:00", temperature=15.0),
    ]
    for r in readings:
        client.post("/readings", json=r)
    # different day, should be excluded from the 2026-01-15 aggregation
    client.post("/readings", json=make_reading(
        station_id="station-1", timestamp="2026-01-16T12:00:00+00:00", temperature=50.0,
    ))

    resp = client.get("/readings/station-1/daily", query_string={"day": "2026-01-15"})
    assert resp.status_code == 200
    agg = resp.get_json()
    assert agg["min_temperature"] == 5.0
    assert agg["max_temperature"] == 20.0
    assert agg["avg_temperature"] == 12.5
    assert agg["sample_count"] == 4


def test_daily_aggregation_no_data_returns_404(client):
    resp = client.get("/readings/station-1/daily", query_string={"day": "2026-01-01"})
    assert resp.status_code == 404


def test_batch_ingestion_multiple_readings(client):
    batch = {
        "readings": [
            make_reading(station_id="station-1", timestamp="2026-01-15T08:00:00+00:00", temperature=10.0),
            make_reading(station_id="station-1", timestamp="2026-01-15T09:00:00+00:00", temperature=11.0),
            make_reading(station_id="station-2", timestamp="2026-01-15T08:00:00+00:00", temperature=25.0),
        ]
    }
    resp = client.post("/readings", json=batch)
    assert resp.status_code == 201
    assert resp.get_json()["inserted"] == 3

    s1 = client.get("/readings/station-1").get_json()
    s2 = client.get("/readings/station-2").get_json()
    assert len(s1) == 2
    assert len(s2) == 1


def test_batch_ingestion_rejects_whole_batch_on_one_bad_reading(client):
    batch = {
        "readings": [
            make_reading(station_id="station-1", temperature=10.0),
            make_reading(station_id="station-1", humidity=200.0),
        ]
    }
    resp = client.post("/readings", json=batch)
    assert resp.status_code == 400
    # nothing should have been committed
    assert client.get("/readings/station-1").get_json() == []


def test_dashboard_page_renders(client):
    client.post("/readings", json=make_reading())
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Weather Station" in resp.data
    assert b"simulated" in resp.data.lower()
