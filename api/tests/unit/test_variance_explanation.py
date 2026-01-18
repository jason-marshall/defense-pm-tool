"""Unit tests for VarianceExplanation model, repository, and schemas."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from src.models.variance_explanation import VarianceExplanation
from src.repositories.variance_explanation import VarianceExplanationRepository
from src.schemas.variance_explanation import (
    VarianceExplanationCreate,
    VarianceExplanationListResponse,
    VarianceExplanationResponse,
    VarianceExplanationSummary,
    VarianceExplanationUpdate,
    VarianceThresholdFilter,
    VarianceType,
)

# =============================================================================
# Schema Tests
# =============================================================================


class TestVarianceType:
    """Tests for VarianceType enum."""

    def test_schedule_type(self):
        """Should have schedule variance type."""
        assert VarianceType.SCHEDULE.value == "schedule"

    def test_cost_type(self):
        """Should have cost variance type."""
        assert VarianceType.COST.value == "cost"


class TestVarianceExplanationCreate:
    """Tests for VarianceExplanationCreate schema."""

    def test_valid_create_minimal(self):
        """Should create with minimal required fields."""
        data = VarianceExplanationCreate(
            program_id=uuid4(),
            variance_type=VarianceType.COST,
            variance_amount=Decimal("1000.00"),
            variance_percent=Decimal("15.5"),
            explanation="Cost overrun due to material price increases.",
        )
        assert data.variance_type == VarianceType.COST
        assert data.variance_amount == Decimal("1000.00")
        assert data.wbs_id is None
        assert data.period_id is None

    def test_valid_create_with_all_fields(self):
        """Should create with all optional fields."""
        wbs_id = uuid4()
        period_id = uuid4()
        resolution_date = date.today() + timedelta(days=30)

        data = VarianceExplanationCreate(
            program_id=uuid4(),
            wbs_id=wbs_id,
            period_id=period_id,
            variance_type=VarianceType.SCHEDULE,
            variance_amount=Decimal("-5000.00"),
            variance_percent=Decimal("-12.5"),
            explanation="Schedule delay due to resource constraints.",
            corrective_action="Adding additional resources to accelerate work.",
            expected_resolution=resolution_date,
        )
        assert data.wbs_id == wbs_id
        assert data.period_id == period_id
        assert data.corrective_action is not None
        assert data.expected_resolution == resolution_date

    def test_explanation_min_length(self):
        """Should reject explanation shorter than 10 characters."""
        with pytest.raises(PydanticValidationError) as exc_info:
            VarianceExplanationCreate(
                program_id=uuid4(),
                variance_type=VarianceType.COST,
                variance_amount=Decimal("1000.00"),
                variance_percent=Decimal("10.0"),
                explanation="Short",  # Too short
            )
        assert "explanation" in str(exc_info.value)

    def test_explanation_max_length(self):
        """Should reject explanation longer than 5000 characters."""
        with pytest.raises(PydanticValidationError) as exc_info:
            VarianceExplanationCreate(
                program_id=uuid4(),
                variance_type=VarianceType.COST,
                variance_amount=Decimal("1000.00"),
                variance_percent=Decimal("10.0"),
                explanation="x" * 5001,  # Too long
            )
        assert "explanation" in str(exc_info.value)

    def test_negative_variance_amount(self):
        """Should accept negative variance amounts."""
        data = VarianceExplanationCreate(
            program_id=uuid4(),
            variance_type=VarianceType.COST,
            variance_amount=Decimal("-5000.00"),
            variance_percent=Decimal("-15.0"),
            explanation="Under budget due to better than expected labor rates.",
        )
        assert data.variance_amount == Decimal("-5000.00")


class TestVarianceExplanationUpdate:
    """Tests for VarianceExplanationUpdate schema."""

    def test_update_explanation_only(self):
        """Should update only explanation field."""
        data = VarianceExplanationUpdate(
            explanation="Updated explanation text here.",
        )
        assert data.explanation == "Updated explanation text here."
        assert data.corrective_action is None
        assert data.expected_resolution is None

    def test_update_corrective_action(self):
        """Should update corrective action."""
        data = VarianceExplanationUpdate(
            corrective_action="New corrective action plan.",
        )
        assert data.corrective_action == "New corrective action plan."

    def test_update_expected_resolution(self):
        """Should update expected resolution date."""
        resolution = date.today() + timedelta(days=60)
        data = VarianceExplanationUpdate(
            expected_resolution=resolution,
        )
        assert data.expected_resolution == resolution

    def test_update_all_fields(self):
        """Should update all fields together."""
        data = VarianceExplanationUpdate(
            explanation="Updated explanation with more detail.",
            corrective_action="Revised corrective action.",
            expected_resolution=date.today() + timedelta(days=30),
            variance_amount=Decimal("2000.00"),
            variance_percent=Decimal("20.0"),
        )
        assert data.explanation is not None
        assert data.corrective_action is not None
        assert data.variance_amount == Decimal("2000.00")


class TestVarianceExplanationResponse:
    """Tests for VarianceExplanationResponse schema."""

    def test_from_model_attributes(self):
        """Should create from model attributes."""
        now = datetime.now()
        data = VarianceExplanationResponse(
            id=uuid4(),
            program_id=uuid4(),
            wbs_id=None,
            period_id=None,
            created_by=uuid4(),
            variance_type="cost",
            variance_amount=Decimal("1000.00"),
            variance_percent=Decimal("10.0"),
            explanation="Test explanation for the variance.",
            corrective_action=None,
            expected_resolution=None,
            created_at=now,
            updated_at=now,
        )
        assert data.variance_type == "cost"
        assert data.variance_amount == Decimal("1000.00")

    def test_with_deleted_at(self):
        """Should include deleted_at field."""
        now = datetime.now()
        data = VarianceExplanationResponse(
            id=uuid4(),
            program_id=uuid4(),
            wbs_id=None,
            period_id=None,
            created_by=None,
            variance_type="schedule",
            variance_amount=Decimal("500.00"),
            variance_percent=Decimal("5.0"),
            explanation="Schedule variance explanation.",
            corrective_action=None,
            expected_resolution=None,
            created_at=now,
            updated_at=now,
            deleted_at=now,
        )
        assert data.deleted_at is not None


class TestVarianceExplanationSummary:
    """Tests for VarianceExplanationSummary schema."""

    def test_summary_fields(self):
        """Should contain only summary fields."""
        data = VarianceExplanationSummary(
            id=uuid4(),
            variance_type="cost",
            variance_amount=Decimal("1500.00"),
            variance_percent=Decimal("12.5"),
            expected_resolution=date.today() + timedelta(days=14),
            created_at=datetime.now(),
        )
        assert data.variance_amount == Decimal("1500.00")
        assert data.expected_resolution is not None


class TestVarianceExplanationListResponse:
    """Tests for VarianceExplanationListResponse schema."""

    def test_empty_list(self):
        """Should handle empty list."""
        data = VarianceExplanationListResponse(
            items=[],
            total=0,
            page=1,
            per_page=20,
            pages=1,
        )
        assert len(data.items) == 0
        assert data.total == 0

    def test_with_items(self):
        """Should contain list of responses."""
        now = datetime.now()
        item = VarianceExplanationResponse(
            id=uuid4(),
            program_id=uuid4(),
            wbs_id=None,
            period_id=None,
            created_by=None,
            variance_type="cost",
            variance_amount=Decimal("1000.00"),
            variance_percent=Decimal("10.0"),
            explanation="Test variance explanation.",
            corrective_action=None,
            expected_resolution=None,
            created_at=now,
            updated_at=now,
        )
        data = VarianceExplanationListResponse(
            items=[item],
            total=1,
            page=1,
            per_page=20,
            pages=1,
        )
        assert len(data.items) == 1
        assert data.total == 1


class TestVarianceThresholdFilter:
    """Tests for VarianceThresholdFilter schema."""

    def test_default_values(self):
        """Should have correct default values."""
        data = VarianceThresholdFilter()
        assert data.threshold_percent == Decimal("10.0")
        assert data.variance_type is None
        assert data.include_resolved is False

    def test_custom_threshold(self):
        """Should accept custom threshold."""
        data = VarianceThresholdFilter(
            threshold_percent=Decimal("15.0"),
            variance_type=VarianceType.SCHEDULE,
            include_resolved=True,
        )
        assert data.threshold_percent == Decimal("15.0")
        assert data.variance_type == VarianceType.SCHEDULE
        assert data.include_resolved is True


# =============================================================================
# Repository Tests
# =============================================================================


class TestVarianceExplanationRepositoryGetByProgram:
    """Tests for get_by_program method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return VarianceExplanationRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_program_returns_list(self, repo, mock_session):
        """Should return list of variance explanations for a program."""
        program_id = uuid4()
        explanation = VarianceExplanation(
            id=uuid4(),
            program_id=program_id,
            variance_type="cost",
            variance_amount=Decimal("1000.00"),
            variance_percent=Decimal("10.0"),
            explanation="Test explanation.",
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [explanation]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_program(program_id)

        assert result == [explanation]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_program_with_variance_type(self, repo, mock_session):
        """Should filter by variance type."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_by_program(program_id, variance_type="schedule")

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_program_empty_result(self, repo, mock_session):
        """Should return empty list when no explanations."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_program(program_id)

        assert result == []


class TestVarianceExplanationRepositoryGetByPeriod:
    """Tests for get_by_period method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return VarianceExplanationRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_period_returns_list(self, repo, mock_session):
        """Should return explanations for a period."""
        period_id = uuid4()
        explanation = VarianceExplanation(
            id=uuid4(),
            program_id=uuid4(),
            period_id=period_id,
            variance_type="schedule",
            variance_amount=Decimal("500.00"),
            variance_percent=Decimal("5.0"),
            explanation="Period variance explanation.",
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [explanation]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_period(period_id)

        assert result == [explanation]

    @pytest.mark.asyncio
    async def test_get_by_period_ordered_by_percent(self, repo, mock_session):
        """Should order by variance percent descending."""
        period_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_by_period(period_id)

        mock_session.execute.assert_called_once()


class TestVarianceExplanationRepositoryGetByWBS:
    """Tests for get_by_wbs method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return VarianceExplanationRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_wbs_returns_list(self, repo, mock_session):
        """Should return explanations for a WBS element."""
        wbs_id = uuid4()
        explanation = VarianceExplanation(
            id=uuid4(),
            program_id=uuid4(),
            wbs_id=wbs_id,
            variance_type="cost",
            variance_amount=Decimal("2000.00"),
            variance_percent=Decimal("20.0"),
            explanation="WBS element variance.",
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [explanation]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_wbs(wbs_id)

        assert result == [explanation]


class TestVarianceExplanationRepositoryGetSignificantVariances:
    """Tests for get_significant_variances method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return VarianceExplanationRepository(mock_session)

    @pytest.mark.asyncio
    async def test_default_threshold(self, repo, mock_session):
        """Should use default 10% threshold."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_significant_variances(program_id)

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_threshold(self, repo, mock_session):
        """Should use custom threshold."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_significant_variances(program_id, threshold_percent=Decimal("15.0"))

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_only_significant(self, repo, mock_session):
        """Should return only variances above threshold."""
        program_id = uuid4()
        significant = VarianceExplanation(
            id=uuid4(),
            program_id=program_id,
            variance_type="cost",
            variance_amount=Decimal("5000.00"),
            variance_percent=Decimal("25.0"),
            explanation="Significant cost variance.",
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [significant]
        mock_session.execute.return_value = mock_result

        result = await repo.get_significant_variances(program_id)

        assert len(result) == 1
        assert result[0].variance_percent == Decimal("25.0")


# =============================================================================
# Model Tests
# =============================================================================


class TestVarianceExplanationModel:
    """Tests for VarianceExplanation model."""

    def test_create_model(self):
        """Should create model instance."""
        explanation = VarianceExplanation(
            id=uuid4(),
            program_id=uuid4(),
            variance_type="cost",
            variance_amount=Decimal("1000.00"),
            variance_percent=Decimal("10.0"),
            explanation="Test variance explanation.",
        )
        assert explanation.variance_type == "cost"
        assert explanation.variance_amount == Decimal("1000.00")

    def test_model_with_wbs(self):
        """Should create model with WBS reference."""
        explanation = VarianceExplanation(
            id=uuid4(),
            program_id=uuid4(),
            wbs_id=uuid4(),
            variance_type="schedule",
            variance_amount=Decimal("-500.00"),
            variance_percent=Decimal("-5.0"),
            explanation="WBS element variance explanation.",
        )
        assert explanation.wbs_id is not None

    def test_model_with_period(self):
        """Should create model with period reference."""
        explanation = VarianceExplanation(
            id=uuid4(),
            program_id=uuid4(),
            period_id=uuid4(),
            variance_type="cost",
            variance_amount=Decimal("2000.00"),
            variance_percent=Decimal("15.0"),
            explanation="Period variance explanation.",
        )
        assert explanation.period_id is not None

    def test_model_with_corrective_action(self):
        """Should create model with corrective action."""
        explanation = VarianceExplanation(
            id=uuid4(),
            program_id=uuid4(),
            variance_type="cost",
            variance_amount=Decimal("3000.00"),
            variance_percent=Decimal("20.0"),
            explanation="Significant cost variance.",
            corrective_action="Implement cost reduction measures.",
        )
        assert explanation.corrective_action is not None

    def test_model_repr(self):
        """Should have informative repr."""
        explanation = VarianceExplanation(
            id=uuid4(),
            program_id=uuid4(),
            variance_type="cost",
            variance_amount=Decimal("1000.00"),
            variance_percent=Decimal("10.5"),
            explanation="Test explanation.",
        )
        repr_str = repr(explanation)
        assert "VarianceExplanation" in repr_str
        assert "cost" in repr_str
        assert "10.5" in repr_str
