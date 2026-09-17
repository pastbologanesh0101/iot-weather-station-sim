# IoT Weather Station (Simulated)

A small, fully working IoT weather-station project: a real Flask ingestion
backend, real SQLite storage, real aggregation/alert logic, and a
**simulated** sensor client that stands in for physical hardware.

## Honesty about what's real and what's simulated

- **Simulated:** temperature, humidity, pressure, and wind readings. There
  is no physical thermometer, hygrometer, barometer, or anemometer
  anywhere in this repo. `app/sensor_simulator.py` generates synthetic
  values in software (daily sinusoidal temperature curve + noise, humidity
  inversely correlated with temperature, a slow random-walk pressure
  drift, and independently generated wind speed/direction).
- **Real:** the Flask HTTP ingestion API, request validation, SQLite
  storage, the time-range/aggregation queries, the storm/temperature
  alert rule engine, and the dashboard. All of that is genuine working
  code you can run, hit with `curl`, and test.

If you plugged in real sensors and pointed them at `POST /readings` with
the same JSON shape, this backend would work unchanged.

## Architecture

```
app/
  factory.py           create_app() app factory (supports testing=True)
  db.py                 SQLite connection + schema management
  validation.py         plausibility checks on incoming readings
  repository.py         SQL query helpers (insert, latest, range, daily agg)
  alerts.py             rapid-pressure-drop + temperature-threshold rules
  sensor_simulator.py    simulated sensor client (no hardware)
  routes.py             Flask blueprint: ingestion API, query API, dashboard
  templates/dashboard.html
scripts/run_simulator.py  standalone script that POSTs simulated readings
                            to a running backend over HTTP
tests/                    pytest test suite (Flask test client)
```

## Running it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python wsgi.py
# -> http://127.0.0.1:5000/  (dashboard)
```

In a second terminal, feed it simulated data:

```bash
python scripts/run_simulator.py --url http://127.0.0.1:5000 --interval 5
```

This posts a fresh batch of simulated readings (one per configured
station) every 5 seconds. Refresh the dashboard to see it update.

## API

### `POST /readings`

Accepts either a single reading object, `{"readings": [...]}`, or a bare
JSON array of reading objects.

```json
{
  "station_id": "station-1",
  "timestamp": "2026-01-15T12:00:00+00:00",
  "temperature": 21.4,
  "humidity": 48.2,
  "pressure": 1012.6,
  "wind_speed": 3.1,
  "wind_direction": 210.0,
  "lat": 37.7749,
  "lon": -122.4194
}
```

`station_id`, `temperature`, `humidity`, and `pressure` are required.
`timestamp` defaults to "now" (UTC) if omitted. Readings outside
physically plausible bounds are rejected with `400` and a JSON error body
explaining exactly which field failed and why, e.g. humidity outside
`[0, 100]`, temperature outside `[-90, 65]` C, pressure outside
`[850, 1085]` hPa. On success: `201` with `{"inserted": N, "ids": [...]}`.
A batch is rejected as a whole (no partial writes) if any reading in it
fails validation.

### `GET /readings/latest`

Latest reading per station.

### `GET /readings/<station_id>?start=...&end=...`

Historical readings for a station. With `start`/`end` (ISO-8601), filters
to that time range inclusive. Without them, returns full history
(optionally capped with `?limit=N`).

### `GET /readings/<station_id>/daily?day=YYYY-MM-DD`

Min/max/avg temperature and sample count for that station on that day.

### `GET /alerts?station_id=...&window_hours=3&drop_threshold_hpa=3&high_threshold_c=35&low_threshold_c=0`

Runs the alert rule engine (see below) over stored history and returns
matching alerts, sorted chronologically. Omit `station_id` to check all
stations.

### `GET /`

HTML dashboard: latest reading per station, plus a per-station table and
ASCII/unicode sparkline of recent temperature history.

## Alert rules

- **Rapid pressure drop** (storm-warning heuristic): fires when pressure
  falls by more than `drop_threshold_hpa` (default 3.0 hPa) within any
  `window_hours` window (default 3h) — a real meteorological rule of
  thumb for an approaching low-pressure system.
- **Temperature threshold**: fires when a reading is at/above
  `high_threshold_c` (default 35C), and optionally at/below
  `low_threshold_c` for freeze warnings.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

The suite (in `tests/`) uses Flask's test client against
`create_app(testing=True)`, which spins up a fresh temp-file SQLite
database per test app so tests never interfere with each other or with
any real database file. It covers ingestion (valid + invalid data,
batches), the query endpoints (latest, time-range, daily aggregation),
both alert rules (fires / doesn't fire), and the sensor simulator's
output bounds.

CI (`.github/workflows/tests.yml`) runs the same suite on Python 3.11 and
3.12 on every push and pull request.

## License

MIT — see `LICENSE`.
