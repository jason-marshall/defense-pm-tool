#!/usr/bin/env python
"""Run load tests and generate report."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_load_test(
    host: str = "http://localhost:8000",
    users: int = 50,
    spawn_rate: int = 5,
    run_time: str = "5m",
) -> None:
    """Run Locust load test with specified parameters.

    Args:
        host: Target API host URL
        users: Number of concurrent users to simulate
        spawn_rate: Users to spawn per second
        run_time: Duration of the test (e.g., "5m", "1h")
    """
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_report = report_dir / f"load_test_{timestamp}.html"
    csv_prefix = report_dir / f"load_test_{timestamp}"

    locustfile = Path(__file__).parent / "locustfile.py"

    cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        str(locustfile),
        "--host",
        host,
        "--users",
        str(users),
        "--spawn-rate",
        str(spawn_rate),
        "--run-time",
        run_time,
        "--headless",
        "--html",
        str(html_report),
        "--csv",
        str(csv_prefix),
    ]

    print(f"Running load test: {users} users, {run_time} duration")
    print(f"Target host: {host}")
    print(f"Report will be saved to: {html_report}")
    print("-" * 60)

    result = subprocess.run(cmd, check=False)

    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("Load test completed successfully!")
        print(f"  HTML Report: {html_report}")
        print(f"  CSV Stats: {csv_prefix}_stats.csv")
        print("=" * 60)
    else:
        print(f"\nLoad test failed with code {result.returncode}")
        sys.exit(1)


def main() -> None:
    """Parse arguments and run load test."""
    import argparse

    parser = argparse.ArgumentParser(description="Run load tests for Defense PM Tool API")
    parser.add_argument(
        "--host",
        default="http://localhost:8000",
        help="Target API host URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=50,
        help="Number of concurrent users (default: 50)",
    )
    parser.add_argument(
        "--spawn-rate",
        type=int,
        default=5,
        help="Users to spawn per second (default: 5)",
    )
    parser.add_argument(
        "--run-time",
        default="5m",
        help="Test duration, e.g., 5m, 1h (default: 5m)",
    )

    args = parser.parse_args()
    run_load_test(args.host, args.users, args.spawn_rate, args.run_time)


if __name__ == "__main__":
    main()
