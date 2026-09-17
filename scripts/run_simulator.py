#!/usr/bin/env python3
"""Run the simulated sensor client against a live backend over HTTP.

Usage:
    python scripts/run_simulator.py --url http://127.0.0.1:5000 --interval 5

This posts a fresh batch of simulated readings (one per configured
station) to the backend's POST /readings endpoint every `interval`
seconds. It does not read from any real hardware -- everything is
generated synthetically by app.sensor_simulator.SensorSimulator.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])

from app.sensor_simulator import SensorSimulator  # noqa: E402


def post_batch(url, batch):
    data = json.dumps({"readings": batch}).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/readings",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"posted {len(batch)} readings -> {resp.status}")
    except urllib.error.HTTPError as exc:
        print(f"error posting batch: {exc.code} {exc.read().decode()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:5000")
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument(
        "--iterations", type=int, default=None,
        help="Number of batches to send before stopping (default: forever)",
    )
    args = parser.parse_args()

    simulator = SensorSimulator()
    simulator.run_forever(
        post_fn=lambda batch: post_batch(args.url, batch),
        interval_seconds=args.interval,
        iterations=args.iterations,
    )


if __name__ == "__main__":
    main()
