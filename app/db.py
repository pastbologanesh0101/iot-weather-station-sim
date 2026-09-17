"""SQLite storage layer for the IoT Weather Station backend.

Uses the standard library sqlite3 module directly (no ORM) so the schema
and queries are easy to read and reason about. Each Flask app gets its own
connection stored on `flask.g`, opened/closed per-request via
`init_app(app)`.
"""

import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT NOT NULL,
    lat REAL,
    lon REAL,
    timestamp TEXT NOT NULL,
    temperature REAL NOT NULL,
    humidity REAL NOT NULL,
    pressure REAL NOT NULL,
    wind_speed REAL,
    wind_direction REAL
);

CREATE INDEX IF NOT EXISTS idx_readings_station_ts
    ON readings (station_id, timestamp);
"""


def get_db():
    """Return the request-scoped SQLite connection, opening it if needed."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create tables if they do not already exist, for the given app."""
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
