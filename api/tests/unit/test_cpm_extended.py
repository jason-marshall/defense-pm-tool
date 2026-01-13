"""Extended unit tests for CPM Engine."""

from uuid import uuid4

from src.services.cpm import CPMEngine, ScheduleResult


class TestCPMEngineBasic:
    """Basic tests for CPM Engine initialization."""

    def test_create_engine_empty(self):
        """Test creating engine with no activities."""
        engine = CPMEngine(activities=[], dependencies=[])
        assert engine is not None


class TestScheduleResult:
    """Tests for ScheduleResult dataclass."""

    def test_create_result_critical(self):
        """Test creating a critical schedule result (zero float)."""
        result = ScheduleResult(
            activity_id=uuid4(),
            early_start=0,
            early_finish=5,
            late_start=0,
            late_finish=5,
            total_float=0,
            free_float=0,
        )
        assert result.early_start == 0
        assert result.early_finish == 5
        assert result.is_critical is True

    def test_result_with_float(self):
        """Test result with schedule float."""
        result = ScheduleResult(
            activity_id=uuid4(),
            early_start=0,
            early_finish=5,
            late_start=3,
            late_finish=8,
            total_float=3,
            free_float=0,
        )
        assert result.total_float == 3
        assert result.is_critical is False

    def test_result_negative_float(self):
        """Test result with negative float (schedule compression)."""
        result = ScheduleResult(
            activity_id=uuid4(),
            early_start=5,
            early_finish=10,
            late_start=3,
            late_finish=8,
            total_float=-2,
            free_float=-2,
        )
        assert result.total_float == -2
        assert result.is_critical is False  # Negative float is not critical
