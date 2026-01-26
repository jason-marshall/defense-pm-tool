"""Unit tests for metrics module."""

from src.core.metrics import (
    cpm_calculation_duration_seconds,
    http_request_duration_seconds,
    track_time,
)


class TestMetrics:
    """Test metrics tracking."""

    def test_track_time_context_manager(self) -> None:
        """Test time tracking context manager."""
        with track_time(http_request_duration_seconds, {"method": "GET", "endpoint": "/test"}):
            pass  # Simulate work

    def test_cpm_calculation_buckets(self) -> None:
        """Test CPM calculation time tracking."""
        # Just verify metrics are recorded without errors
        cpm_calculation_duration_seconds.labels(activity_count_bucket="0-99").observe(0.01)
        cpm_calculation_duration_seconds.labels(activity_count_bucket="100-499").observe(0.05)
