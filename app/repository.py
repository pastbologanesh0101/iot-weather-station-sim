"""Query helpers that sit between the Flask routes and raw SQL."""

from .db import get_db


def insert_reading(reading):
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO readings
            (station_id, lat, lon, timestamp, temperature, humidity,
             pressure, wind_speed, wind_direction)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reading["station_id"],
            reading["lat"],
            reading["lon"],
            reading["timestamp"],
            reading["temperature"],
            reading["humidity"],
            reading["pressure"],
            reading["wind_speed"],
            reading["wind_direction"],
        ),
    )
    db.commit()
    return cursor.lastrowid


def insert_readings(readings):
    return [insert_reading(r) for r in readings]


def _row_to_dict(row):
    return dict(row)


def get_latest_reading_per_station():
    db = get_db()
    rows = db.execute(
        """
        SELECT r.* FROM readings r
        INNER JOIN (
            SELECT station_id, MAX(timestamp) AS max_ts
            FROM readings
            GROUP BY station_id
        ) latest
        ON r.station_id = latest.station_id AND r.timestamp = latest.max_ts
        ORDER BY r.station_id
        """
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_readings_in_range(station_id, start, end):
    db = get_db()
    rows = db.execute(
        """
        SELECT * FROM readings
        WHERE station_id = ? AND timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp ASC
        """,
        (station_id, start, end),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_all_readings_for_station(station_id, limit=None):
    db = get_db()
    query = (
        "SELECT * FROM readings WHERE station_id = ? ORDER BY timestamp ASC"
    )
    params = [station_id]
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    rows = db.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_recent_readings_for_station(station_id, count=20):
    db = get_db()
    rows = db.execute(
        """
        SELECT * FROM readings WHERE station_id = ?
        ORDER BY timestamp DESC LIMIT ?
        """,
        (station_id, count),
    ).fetchall()
    return [_row_to_dict(r) for r in reversed(rows)]


def get_all_station_ids():
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT station_id FROM readings ORDER BY station_id"
    ).fetchall()
    return [r["station_id"] for r in rows]


def get_daily_aggregation(station_id, day):
    """Return min/max/avg temperature for a station on a given day.

    `day` is an ISO date string, e.g. "2026-01-15". Matches any reading
    whose timestamp starts with that date prefix.
    """
    db = get_db()
    row = db.execute(
        """
        SELECT MIN(temperature) AS min_temp,
               MAX(temperature) AS max_temp,
               AVG(temperature) AS avg_temp,
               COUNT(*) AS count
        FROM readings
        WHERE station_id = ? AND timestamp LIKE ?
        """,
        (station_id, f"{day}%"),
    ).fetchone()
    if row is None or row["count"] == 0:
        return None
    return {
        "station_id": station_id,
        "day": day,
        "min_temperature": row["min_temp"],
        "max_temperature": row["max_temp"],
        "avg_temperature": round(row["avg_temp"], 2),
        "sample_count": row["count"],
    }
