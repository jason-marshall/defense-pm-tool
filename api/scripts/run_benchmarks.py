#!/usr/bin/env python
"""Run performance benchmarks and save results."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_benchmarks() -> bool:
    """Run pytest benchmarks and save results."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path("benchmark_results")
    results_dir.mkdir(exist_ok=True)

    output_file = results_dir / f"benchmark_{timestamp}.json"

    print("=" * 60)
    print("RUNNING PERFORMANCE BENCHMARKS")
    print("=" * 60)
    print()

    # Run benchmarks with verbose output
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/performance/",
            "-v",
            "-s",  # Show print statements
            "--tb=short",
        ],
        capture_output=False,
        text=True,
    )

    print()
    print("=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)

    return result.returncode == 0


def run_benchmarks_with_pytest_benchmark() -> bool:
    """Run benchmarks using pytest-benchmark if available."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path("benchmark_results")
    results_dir.mkdir(exist_ok=True)

    output_file = results_dir / f"benchmark_{timestamp}.json"

    print("=" * 60)
    print("RUNNING PERFORMANCE BENCHMARKS (pytest-benchmark)")
    print("=" * 60)
    print()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/performance/",
            "--benchmark-only",
            "--benchmark-json",
            str(output_file),
            "-v",
        ],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        return False

    # Load and summarize results
    if output_file.exists():
        with open(output_file) as f:
            data = json.load(f)

        print()
        print("=" * 60)
        print("PERFORMANCE BASELINE SUMMARY")
        print("=" * 60)

        for bench in data.get("benchmarks", []):
            name = bench["name"]
            mean = bench["stats"]["mean"] * 1000  # Convert to ms
            stddev = bench["stats"]["stddev"] * 1000
            print(f"{name}: {mean:.2f}ms (+/-{stddev:.2f}ms)")

    return True


if __name__ == "__main__":
    # Try simple benchmark first
    success = run_benchmarks()
    sys.exit(0 if success else 1)
