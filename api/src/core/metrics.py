"""Prometheus metrics for observability."""

from __future__ import annotations

import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from functools import wraps
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, Info

# Application info
app_info = Info("defense_pm_tool", "Defense Program Management Tool")
app_info.info({"version": "1.0.0", "python_version": "3.11"})

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Database metrics
db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections",
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

# Business metrics
programs_total = Gauge("programs_total", "Total number of programs")
activities_total = Gauge("activities_total", "Total number of activities")
simulations_total = Counter("simulations_total", "Total Monte Carlo simulations run")
reports_generated_total = Counter(
    "reports_generated_total",
    "Total reports generated",
    ["format"],
)

# CPM metrics
cpm_calculation_duration_seconds = Histogram(
    "cpm_calculation_duration_seconds",
    "CPM calculation duration in seconds",
    ["activity_count_bucket"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)

# Cache metrics
cache_hits_total = Counter("cache_hits_total", "Total cache hits", ["cache_name"])
cache_misses_total = Counter("cache_misses_total", "Total cache misses", ["cache_name"])

# EVMS metrics
evms_calculations_total = Counter(
    "evms_calculations_total",
    "Total EVMS calculations performed",
)

evms_calculation_duration_seconds = Histogram(
    "evms_calculation_duration_seconds",
    "EVMS calculation duration in seconds",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5],
)


@contextmanager
def track_time(
    histogram: Histogram, labels: dict[str, str] | None = None
) -> Generator[None, None, None]:
    """Context manager to track operation duration."""
    labels = labels or {}
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        histogram.labels(**labels).observe(duration)


def get_activity_count_bucket(activity_count: int) -> str:
    """Get bucket label for activity count."""
    if activity_count < 100:
        return "0-99"
    elif activity_count < 500:
        return "100-499"
    elif activity_count < 1000:
        return "500-999"
    elif activity_count < 5000:
        return "1000-4999"
    else:
        return "5000+"


def track_cpm_calculation(activity_count: int) -> Callable[..., Any]:
    """Decorator to track CPM calculation duration."""
    bucket = get_activity_count_bucket(activity_count)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with track_time(cpm_calculation_duration_seconds, {"activity_count_bucket": bucket}):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def record_cpm_duration(activity_count: int, duration_seconds: float) -> None:
    """Record CPM calculation duration."""
    bucket = get_activity_count_bucket(activity_count)
    cpm_calculation_duration_seconds.labels(activity_count_bucket=bucket).observe(duration_seconds)


def record_cache_hit(cache_name: str) -> None:
    """Record a cache hit."""
    cache_hits_total.labels(cache_name=cache_name).inc()


def record_cache_miss(cache_name: str) -> None:
    """Record a cache miss."""
    cache_misses_total.labels(cache_name=cache_name).inc()


def record_report_generated(format_type: str) -> None:
    """Record a report generation."""
    reports_generated_total.labels(format=format_type).inc()


def record_simulation_run() -> None:
    """Record a Monte Carlo simulation run."""
    simulations_total.inc()
