"""Unit tests for simulation model properties and methods."""

from datetime import UTC, datetime
from uuid import uuid4

from src.models.simulation import SimulationConfig, SimulationResult, SimulationStatus


class TestSimulationConfigProperties:
    """Tests for SimulationConfig model properties."""

    def test_activity_count_with_distributions(self) -> None:
        """Should return count of activity distributions."""
        config = SimulationConfig(
            id=uuid4(),
            program_id=uuid4(),
            name="Test Config",
            iterations=1000,
            activity_distributions={
                "activity_1": {"min": 5, "mode": 10, "max": 15},
                "activity_2": {"min": 8, "mode": 12, "max": 20},
                "activity_3": {"min": 3, "mode": 5, "max": 8},
            },
        )
        assert config.activity_count == 3

    def test_activity_count_empty(self) -> None:
        """Should return 0 when no distributions."""
        config = SimulationConfig(
            id=uuid4(),
            program_id=uuid4(),
            name="Empty Config",
            iterations=1000,
            activity_distributions=None,
        )
        assert config.activity_count == 0

    def test_activity_count_empty_dict(self) -> None:
        """Should return 0 for empty dictionary."""
        config = SimulationConfig(
            id=uuid4(),
            program_id=uuid4(),
            name="Empty Config",
            iterations=1000,
            activity_distributions={},
        )
        assert config.activity_count == 0

    def test_has_cost_distributions_true(self) -> None:
        """Should return True when cost distributions exist."""
        config = SimulationConfig(
            id=uuid4(),
            program_id=uuid4(),
            name="Cost Config",
            iterations=1000,
            cost_distributions={"activity_1": {"min": 1000, "mode": 1500, "max": 2000}},
        )
        assert config.has_cost_distributions is True

    def test_has_cost_distributions_false(self) -> None:
        """Should return False when no cost distributions."""
        config = SimulationConfig(
            id=uuid4(),
            program_id=uuid4(),
            name="No Cost Config",
            iterations=1000,
            cost_distributions=None,
        )
        assert config.has_cost_distributions is False

    def test_repr(self) -> None:
        """Should return formatted string representation."""
        config = SimulationConfig(
            id=uuid4(),
            program_id=uuid4(),
            name="Test Config",
            iterations=5000,
        )
        repr_str = repr(config)
        assert "SimulationConfig" in repr_str
        assert "Test Config" in repr_str
        assert "5000" in repr_str


class TestSimulationResultProperties:
    """Tests for SimulationResult model properties."""

    def test_is_complete_true(self) -> None:
        """Should return True for completed simulation."""
        result = SimulationResult(
            id=uuid4(),
            config_id=uuid4(),
            status=SimulationStatus.COMPLETED,
            iterations_completed=1000,
        )
        assert result.is_complete is True

    def test_is_complete_false(self) -> None:
        """Should return False for non-completed simulation."""
        result = SimulationResult(
            id=uuid4(),
            config_id=uuid4(),
            status=SimulationStatus.RUNNING,
            iterations_completed=500,
        )
        assert result.is_complete is False

    def test_is_running_true(self) -> None:
        """Should return True for running simulation."""
        result = SimulationResult(
            id=uuid4(),
            config_id=uuid4(),
            status=SimulationStatus.RUNNING,
            iterations_completed=250,
        )
        assert result.is_running is True

    def test_is_running_false(self) -> None:
        """Should return False for non-running simulation."""
        result = SimulationResult(
            id=uuid4(),
            config_id=uuid4(),
            status=SimulationStatus.PENDING,
            iterations_completed=0,
        )
        assert result.is_running is False

    def test_duration_seconds_completed(self) -> None:
        """Should calculate duration for completed simulation."""
        start = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        end = datetime(2026, 1, 15, 10, 5, 30, tzinfo=UTC)
        result = SimulationResult(
            id=uuid4(),
            config_id=uuid4(),
            status=SimulationStatus.COMPLETED,
            started_at=start,
            completed_at=end,
            iterations_completed=1000,
        )
        assert result.duration_seconds == 330.0  # 5 minutes 30 seconds

    def test_duration_seconds_incomplete(self) -> None:
        """Should return None for incomplete simulation."""
        result = SimulationResult(
            id=uuid4(),
            config_id=uuid4(),
            status=SimulationStatus.RUNNING,
            started_at=datetime.now(UTC),
            completed_at=None,
            iterations_completed=500,
        )
        assert result.duration_seconds is None

    def test_duration_seconds_not_started(self) -> None:
        """Should return None for not started simulation."""
        result = SimulationResult(
            id=uuid4(),
            config_id=uuid4(),
            status=SimulationStatus.PENDING,
            started_at=None,
            completed_at=None,
            iterations_completed=0,
        )
        assert result.duration_seconds is None

    def test_progress_percent_with_config(self) -> None:
        """Should calculate progress percentage."""
        config = SimulationConfig(
            id=uuid4(),
            program_id=uuid4(),
            name="Test",
            iterations=1000,
        )
        result = SimulationResult(
            id=uuid4(),
            config_id=config.id,
            status=SimulationStatus.RUNNING,
            iterations_completed=500,
        )
        result.config = config
        assert result.progress_percent == 50.0

    def test_progress_percent_no_config(self) -> None:
        """Should return 0 when config not loaded."""
        result = SimulationResult(
            id=uuid4(),
            config_id=uuid4(),
            status=SimulationStatus.PENDING,
            iterations_completed=0,
        )
        result.config = None
        assert result.progress_percent == 0.0

    def test_repr(self) -> None:
        """Should return formatted string representation."""
        config_id = uuid4()
        result = SimulationResult(
            id=uuid4(),
            config_id=config_id,
            status=SimulationStatus.COMPLETED,
            iterations_completed=1000,
        )
        repr_str = repr(result)
        assert "SimulationResult" in repr_str
        assert str(config_id) in repr_str
        assert "completed" in repr_str.lower()
        assert "1000" in repr_str
