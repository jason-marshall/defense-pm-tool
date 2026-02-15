"""Unit tests for variance explanation management endpoints."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.variance_explanations import (
    create_variance_explanation,
    delete_variance_explanation,
    get_significant_variances,
    get_variance_explanation,
    list_variance_explanations,
    list_variance_explanations_by_period,
    list_variance_explanations_by_wbs,
    restore_variance_explanation,
    update_variance_explanation,
)
from src.core.exceptions import NotFoundError, ValidationError


def _make_explanation_mock(
    *,
    program_id=None,
    wbs_id=None,
    period_id=None,
    variance_type="cost",
    variance_amount=Decimal("-5000.00"),
    variance_percent=Decimal("12.50"),
    explanation_text="Budget overrun due to supply chain delays affecting material costs",
    corrective_action="Negotiate new supplier contracts",
    expected_resolution=None,
):
    """Create a mock variance explanation model instance."""
    now = datetime.now(UTC)
    mock = MagicMock()
    mock.id = uuid4()
    mock.program_id = program_id or uuid4()
    mock.wbs_id = wbs_id
    mock.period_id = period_id
    mock.created_by = uuid4()
    mock.variance_type = variance_type
    mock.variance_amount = variance_amount
    mock.variance_percent = variance_percent
    mock.explanation = explanation_text
    mock.corrective_action = corrective_action
    mock.expected_resolution = expected_resolution
    mock.created_at = now
    mock.updated_at = now
    mock.deleted_at = None
    return mock


class TestListVarianceExplanations:
    """Tests for list_variance_explanations endpoint."""

    @pytest.mark.asyncio
    async def test_list_explanations_success(self):
        """Should return paginated list of variance explanations for a program."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        exp1 = _make_explanation_mock(program_id=program_id, expected_resolution=None)
        exp2 = _make_explanation_mock(program_id=program_id, expected_resolution=None)

        with (
            patch(
                "src.api.v1.endpoints.variance_explanations.ProgramRepository"
            ) as mock_prog_repo_cls,
            patch(
                "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
            ) as mock_ve_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_ve_repo = MagicMock()
            mock_ve_repo.get_by_program = AsyncMock(return_value=[exp1, exp2])
            mock_ve_repo_cls.return_value = mock_ve_repo

            result = await list_variance_explanations(
                db=mock_db,
                current_user=mock_user,
                program_id=program_id,
                variance_type=None,
                threshold_percent=Decimal("0"),
                include_resolved=True,
                page=1,
                per_page=20,
            )

            assert result.total == 2
            assert len(result.items) == 2
            assert result.page == 1
            assert result.per_page == 20
            mock_prog_repo.get.assert_called_once_with(program_id)

    @pytest.mark.asyncio
    async def test_list_explanations_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()

        with patch(
            "src.api.v1.endpoints.variance_explanations.ProgramRepository"
        ) as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await list_variance_explanations(
                    db=mock_db,
                    current_user=mock_user,
                    program_id=program_id,
                    variance_type=None,
                    threshold_percent=Decimal("0"),
                    include_resolved=False,
                    page=1,
                    per_page=20,
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_list_explanations_with_threshold(self):
        """Should use get_significant_variances when threshold > 0."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        exp1 = _make_explanation_mock(
            program_id=program_id,
            variance_percent=Decimal("15.00"),
            expected_resolution=None,
        )

        with (
            patch(
                "src.api.v1.endpoints.variance_explanations.ProgramRepository"
            ) as mock_prog_repo_cls,
            patch(
                "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
            ) as mock_ve_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_ve_repo = MagicMock()
            mock_ve_repo.get_significant_variances = AsyncMock(return_value=[exp1])
            mock_ve_repo_cls.return_value = mock_ve_repo

            result = await list_variance_explanations(
                db=mock_db,
                current_user=mock_user,
                program_id=program_id,
                variance_type=None,
                threshold_percent=Decimal("10"),
                include_resolved=True,
                page=1,
                per_page=20,
            )

            assert result.total == 1
            mock_ve_repo.get_significant_variances.assert_called_once_with(
                program_id=program_id,
                threshold_percent=Decimal("10"),
                include_deleted=False,
            )

    @pytest.mark.asyncio
    async def test_list_explanations_filters_resolved(self):
        """Should filter out resolved explanations when include_resolved=False."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        # One unresolved (future date), one resolved (past date)
        exp_unresolved = _make_explanation_mock(
            program_id=program_id,
            expected_resolution=date(2099, 12, 31),
        )
        exp_resolved = _make_explanation_mock(
            program_id=program_id,
            expected_resolution=date(2020, 1, 1),
        )

        with (
            patch(
                "src.api.v1.endpoints.variance_explanations.ProgramRepository"
            ) as mock_prog_repo_cls,
            patch(
                "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
            ) as mock_ve_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_ve_repo = MagicMock()
            mock_ve_repo.get_by_program = AsyncMock(return_value=[exp_unresolved, exp_resolved])
            mock_ve_repo_cls.return_value = mock_ve_repo

            result = await list_variance_explanations(
                db=mock_db,
                current_user=mock_user,
                program_id=program_id,
                variance_type=None,
                threshold_percent=Decimal("0"),
                include_resolved=False,
                page=1,
                per_page=20,
            )

            # Only the unresolved explanation should remain
            assert result.total == 1

    @pytest.mark.asyncio
    async def test_list_explanations_pagination(self):
        """Should correctly paginate results."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        # 3 items, page 2 with per_page=2 should return 1 item
        explanations = [
            _make_explanation_mock(program_id=program_id, expected_resolution=None)
            for _ in range(3)
        ]

        with (
            patch(
                "src.api.v1.endpoints.variance_explanations.ProgramRepository"
            ) as mock_prog_repo_cls,
            patch(
                "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
            ) as mock_ve_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_ve_repo = MagicMock()
            mock_ve_repo.get_by_program = AsyncMock(return_value=explanations)
            mock_ve_repo_cls.return_value = mock_ve_repo

            result = await list_variance_explanations(
                db=mock_db,
                current_user=mock_user,
                program_id=program_id,
                variance_type=None,
                threshold_percent=Decimal("0"),
                include_resolved=True,
                page=2,
                per_page=2,
            )

            assert result.total == 3
            assert len(result.items) == 1
            assert result.page == 2
            assert result.pages == 2


class TestListVarianceExplanationsByPeriod:
    """Tests for list_variance_explanations_by_period endpoint."""

    @pytest.mark.asyncio
    async def test_list_by_period_success(self):
        """Should return explanations for a given period."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        period_id = uuid4()
        mock_period = MagicMock()
        mock_period.id = period_id

        exp1 = _make_explanation_mock(period_id=period_id)

        with (
            patch(
                "src.api.v1.endpoints.variance_explanations.EVMSPeriodRepository"
            ) as mock_period_repo_cls,
            patch(
                "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
            ) as mock_ve_repo_cls,
        ):
            mock_period_repo = MagicMock()
            mock_period_repo.get = AsyncMock(return_value=mock_period)
            mock_period_repo_cls.return_value = mock_period_repo

            mock_ve_repo = MagicMock()
            mock_ve_repo.get_by_period = AsyncMock(return_value=[exp1])
            mock_ve_repo_cls.return_value = mock_ve_repo

            result = await list_variance_explanations_by_period(
                db=mock_db,
                current_user=mock_user,
                period_id=period_id,
            )

            assert len(result) == 1
            mock_ve_repo.get_by_period.assert_called_once_with(period_id)

    @pytest.mark.asyncio
    async def test_list_by_period_not_found(self):
        """Should raise NotFoundError when period does not exist."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        period_id = uuid4()

        with patch(
            "src.api.v1.endpoints.variance_explanations.EVMSPeriodRepository"
        ) as mock_period_repo_cls:
            mock_period_repo = MagicMock()
            mock_period_repo.get = AsyncMock(return_value=None)
            mock_period_repo_cls.return_value = mock_period_repo

            with pytest.raises(NotFoundError) as exc_info:
                await list_variance_explanations_by_period(
                    db=mock_db,
                    current_user=mock_user,
                    period_id=period_id,
                )

            assert exc_info.value.code == "PERIOD_NOT_FOUND"


class TestListVarianceExplanationsByWBS:
    """Tests for list_variance_explanations_by_wbs endpoint."""

    @pytest.mark.asyncio
    async def test_list_by_wbs_success(self):
        """Should return explanations for a given WBS element."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        wbs_id = uuid4()
        mock_wbs = MagicMock()
        mock_wbs.id = wbs_id

        exp1 = _make_explanation_mock(wbs_id=wbs_id)

        with (
            patch(
                "src.api.v1.endpoints.variance_explanations.WBSElementRepository"
            ) as mock_wbs_repo_cls,
            patch(
                "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
            ) as mock_ve_repo_cls,
        ):
            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get = AsyncMock(return_value=mock_wbs)
            mock_wbs_repo_cls.return_value = mock_wbs_repo

            mock_ve_repo = MagicMock()
            mock_ve_repo.get_by_wbs = AsyncMock(return_value=[exp1])
            mock_ve_repo_cls.return_value = mock_ve_repo

            result = await list_variance_explanations_by_wbs(
                db=mock_db,
                current_user=mock_user,
                wbs_id=wbs_id,
            )

            assert len(result) == 1
            mock_ve_repo.get_by_wbs.assert_called_once_with(wbs_id)

    @pytest.mark.asyncio
    async def test_list_by_wbs_not_found(self):
        """Should raise NotFoundError when WBS element does not exist."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        wbs_id = uuid4()

        with patch(
            "src.api.v1.endpoints.variance_explanations.WBSElementRepository"
        ) as mock_wbs_repo_cls:
            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get = AsyncMock(return_value=None)
            mock_wbs_repo_cls.return_value = mock_wbs_repo

            with pytest.raises(NotFoundError) as exc_info:
                await list_variance_explanations_by_wbs(
                    db=mock_db,
                    current_user=mock_user,
                    wbs_id=wbs_id,
                )

            assert exc_info.value.code == "WBS_NOT_FOUND"


class TestCreateVarianceExplanation:
    """Tests for create_variance_explanation endpoint."""

    @pytest.mark.asyncio
    async def test_create_explanation_success(self):
        """Should create a variance explanation successfully."""
        from src.schemas.variance_explanation import (
            VarianceExplanationCreate,
            VarianceType,
        )

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        explanation_mock = _make_explanation_mock(program_id=program_id)

        data = VarianceExplanationCreate(
            program_id=program_id,
            variance_type=VarianceType.COST,
            variance_amount=Decimal("-5000.00"),
            variance_percent=Decimal("12.50"),
            explanation="Budget overrun due to supply chain delays affecting material costs",
            corrective_action="Negotiate new supplier contracts",
            create_jira_issue=False,
        )

        with (
            patch(
                "src.api.v1.endpoints.variance_explanations.ProgramRepository"
            ) as mock_prog_repo_cls,
            patch(
                "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
            ) as mock_ve_repo_cls,
            patch(
                "src.api.v1.endpoints.variance_explanations.VarianceExplanationWithJiraResponse"
            ) as mock_response_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_ve_repo = MagicMock()
            mock_ve_repo.create = AsyncMock(return_value=explanation_mock)
            mock_ve_repo_cls.return_value = mock_ve_repo

            mock_response = MagicMock()
            mock_response.id = explanation_mock.id
            mock_response.jira_issue_key = None
            mock_response.jira_issue_created = False
            mock_response_cls.model_validate.return_value = mock_response

            result = await create_variance_explanation(
                db=mock_db,
                current_user=mock_user,
                explanation_data=data,
            )

            assert result.id == explanation_mock.id
            assert result.jira_issue_created is False
            assert result.jira_issue_key is None
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(explanation_mock)

    @pytest.mark.asyncio
    async def test_create_explanation_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        from src.schemas.variance_explanation import (
            VarianceExplanationCreate,
            VarianceType,
        )

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()

        data = VarianceExplanationCreate(
            program_id=program_id,
            variance_type=VarianceType.SCHEDULE,
            variance_amount=Decimal("-3000.00"),
            variance_percent=Decimal("8.00"),
            explanation="Schedule slip due to resource unavailability in Phase 2",
            create_jira_issue=False,
        )

        with patch(
            "src.api.v1.endpoints.variance_explanations.ProgramRepository"
        ) as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_variance_explanation(
                    db=mock_db,
                    current_user=mock_user,
                    explanation_data=data,
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_explanation_wbs_not_found(self):
        """Should raise NotFoundError when WBS element does not exist."""
        from src.schemas.variance_explanation import (
            VarianceExplanationCreate,
            VarianceType,
        )

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        wbs_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        data = VarianceExplanationCreate(
            program_id=program_id,
            wbs_id=wbs_id,
            variance_type=VarianceType.COST,
            variance_amount=Decimal("-2000.00"),
            variance_percent=Decimal("5.00"),
            explanation="Cost variance on WBS element due to rework requirements",
            create_jira_issue=False,
        )

        with (
            patch(
                "src.api.v1.endpoints.variance_explanations.ProgramRepository"
            ) as mock_prog_repo_cls,
            patch(
                "src.api.v1.endpoints.variance_explanations.WBSElementRepository"
            ) as mock_wbs_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get = AsyncMock(return_value=None)
            mock_wbs_repo_cls.return_value = mock_wbs_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_variance_explanation(
                    db=mock_db,
                    current_user=mock_user,
                    explanation_data=data,
                )

            assert exc_info.value.code == "WBS_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_explanation_wbs_program_mismatch(self):
        """Should raise ValidationError when WBS does not belong to the program."""
        from src.schemas.variance_explanation import (
            VarianceExplanationCreate,
            VarianceType,
        )

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        wbs_id = uuid4()
        other_program_id = uuid4()

        mock_program = MagicMock()
        mock_program.id = program_id

        mock_wbs = MagicMock()
        mock_wbs.id = wbs_id
        mock_wbs.program_id = other_program_id  # Different program
        mock_wbs.name = "WBS Element 1.1"

        data = VarianceExplanationCreate(
            program_id=program_id,
            wbs_id=wbs_id,
            variance_type=VarianceType.COST,
            variance_amount=Decimal("-1000.00"),
            variance_percent=Decimal("3.00"),
            explanation="Cost variance on mismatched WBS element for testing",
            create_jira_issue=False,
        )

        with (
            patch(
                "src.api.v1.endpoints.variance_explanations.ProgramRepository"
            ) as mock_prog_repo_cls,
            patch(
                "src.api.v1.endpoints.variance_explanations.WBSElementRepository"
            ) as mock_wbs_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_wbs_repo = MagicMock()
            mock_wbs_repo.get = AsyncMock(return_value=mock_wbs)
            mock_wbs_repo_cls.return_value = mock_wbs_repo

            with pytest.raises(ValidationError) as exc_info:
                await create_variance_explanation(
                    db=mock_db,
                    current_user=mock_user,
                    explanation_data=data,
                )

            assert exc_info.value.code == "WBS_PROGRAM_MISMATCH"

    @pytest.mark.asyncio
    async def test_create_explanation_period_not_found(self):
        """Should raise NotFoundError when period does not exist."""
        from src.schemas.variance_explanation import (
            VarianceExplanationCreate,
            VarianceType,
        )

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        period_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        data = VarianceExplanationCreate(
            program_id=program_id,
            period_id=period_id,
            variance_type=VarianceType.SCHEDULE,
            variance_amount=Decimal("-4000.00"),
            variance_percent=Decimal("11.00"),
            explanation="Schedule variance in reporting period due to testing delays",
            create_jira_issue=False,
        )

        with (
            patch(
                "src.api.v1.endpoints.variance_explanations.ProgramRepository"
            ) as mock_prog_repo_cls,
            patch(
                "src.api.v1.endpoints.variance_explanations.EVMSPeriodRepository"
            ) as mock_period_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_period_repo = MagicMock()
            mock_period_repo.get = AsyncMock(return_value=None)
            mock_period_repo_cls.return_value = mock_period_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_variance_explanation(
                    db=mock_db,
                    current_user=mock_user,
                    explanation_data=data,
                )

            assert exc_info.value.code == "PERIOD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_explanation_period_program_mismatch(self):
        """Should raise ValidationError when period does not belong to the program."""
        from src.schemas.variance_explanation import (
            VarianceExplanationCreate,
            VarianceType,
        )

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        period_id = uuid4()
        other_program_id = uuid4()

        mock_program = MagicMock()
        mock_program.id = program_id

        mock_period = MagicMock()
        mock_period.id = period_id
        mock_period.program_id = other_program_id  # Different program

        data = VarianceExplanationCreate(
            program_id=program_id,
            period_id=period_id,
            variance_type=VarianceType.COST,
            variance_amount=Decimal("-6000.00"),
            variance_percent=Decimal("14.00"),
            explanation="Cost variance in mismatched period for testing purposes",
            create_jira_issue=False,
        )

        with (
            patch(
                "src.api.v1.endpoints.variance_explanations.ProgramRepository"
            ) as mock_prog_repo_cls,
            patch(
                "src.api.v1.endpoints.variance_explanations.EVMSPeriodRepository"
            ) as mock_period_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_period_repo = MagicMock()
            mock_period_repo.get = AsyncMock(return_value=mock_period)
            mock_period_repo_cls.return_value = mock_period_repo

            with pytest.raises(ValidationError) as exc_info:
                await create_variance_explanation(
                    db=mock_db,
                    current_user=mock_user,
                    explanation_data=data,
                )

            assert exc_info.value.code == "PERIOD_PROGRAM_MISMATCH"

    @pytest.mark.asyncio
    async def test_create_explanation_with_jira_issue(self):
        """Should create explanation and attempt Jira issue creation when requested."""
        from src.schemas.variance_explanation import (
            VarianceExplanationCreate,
            VarianceType,
        )

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        explanation_mock = _make_explanation_mock(program_id=program_id)

        data = VarianceExplanationCreate(
            program_id=program_id,
            variance_type=VarianceType.COST,
            variance_amount=Decimal("-8000.00"),
            variance_percent=Decimal("20.00"),
            explanation="Significant cost overrun requiring Jira tracking for corrective actions",
            create_jira_issue=True,
        )

        with (
            patch(
                "src.api.v1.endpoints.variance_explanations.ProgramRepository"
            ) as mock_prog_repo_cls,
            patch(
                "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
            ) as mock_ve_repo_cls,
            patch("src.api.v1.endpoints.variance_explanations._try_create_jira_issue") as mock_jira,
            patch(
                "src.api.v1.endpoints.variance_explanations.VarianceExplanationWithJiraResponse"
            ) as mock_response_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_ve_repo = MagicMock()
            mock_ve_repo.create = AsyncMock(return_value=explanation_mock)
            mock_ve_repo_cls.return_value = mock_ve_repo

            mock_jira.return_value = ("PROJ-42", True)

            mock_response = MagicMock()
            mock_response.jira_issue_key = None
            mock_response.jira_issue_created = False
            mock_response_cls.model_validate.return_value = mock_response

            result = await create_variance_explanation(
                db=mock_db,
                current_user=mock_user,
                explanation_data=data,
            )

            # The endpoint sets these after model_validate
            assert result.jira_issue_key == "PROJ-42"
            assert result.jira_issue_created is True
            mock_jira.assert_called_once()


class TestGetVarianceExplanation:
    """Tests for get_variance_explanation endpoint."""

    @pytest.mark.asyncio
    async def test_get_explanation_success(self):
        """Should return a specific variance explanation by ID."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        explanation_id = uuid4()
        explanation_mock = _make_explanation_mock()
        explanation_mock.id = explanation_id

        with patch(
            "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
        ) as mock_ve_repo_cls:
            mock_ve_repo = MagicMock()
            mock_ve_repo.get = AsyncMock(return_value=explanation_mock)
            mock_ve_repo_cls.return_value = mock_ve_repo

            result = await get_variance_explanation(
                db=mock_db,
                current_user=mock_user,
                explanation_id=explanation_id,
            )

            assert result.id == explanation_id
            mock_ve_repo.get.assert_called_once_with(explanation_id)

    @pytest.mark.asyncio
    async def test_get_explanation_not_found(self):
        """Should raise NotFoundError when explanation does not exist."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        explanation_id = uuid4()

        with patch(
            "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
        ) as mock_ve_repo_cls:
            mock_ve_repo = MagicMock()
            mock_ve_repo.get = AsyncMock(return_value=None)
            mock_ve_repo_cls.return_value = mock_ve_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_variance_explanation(
                    db=mock_db,
                    current_user=mock_user,
                    explanation_id=explanation_id,
                )

            assert exc_info.value.code == "VARIANCE_EXPLANATION_NOT_FOUND"


class TestUpdateVarianceExplanation:
    """Tests for update_variance_explanation endpoint."""

    @pytest.mark.asyncio
    async def test_update_explanation_success(self):
        """Should update a variance explanation with provided fields."""
        from src.schemas.variance_explanation import VarianceExplanationUpdate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        explanation_id = uuid4()
        explanation_mock = _make_explanation_mock()
        explanation_mock.id = explanation_id

        updated_mock = _make_explanation_mock()
        updated_mock.id = explanation_id
        updated_mock.explanation = "Updated explanation text with more detail about the root cause"
        updated_mock.corrective_action = "Updated corrective action plan"

        update_data = VarianceExplanationUpdate(
            explanation="Updated explanation text with more detail about the root cause",
            corrective_action="Updated corrective action plan",
        )

        with patch(
            "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
        ) as mock_ve_repo_cls:
            mock_ve_repo = MagicMock()
            mock_ve_repo.get = AsyncMock(return_value=explanation_mock)
            mock_ve_repo.update = AsyncMock(return_value=updated_mock)
            mock_ve_repo_cls.return_value = mock_ve_repo

            # After commit and refresh, the refreshed object is used for response
            mock_db.refresh = AsyncMock()

            result = await update_variance_explanation(
                db=mock_db,
                current_user=mock_user,
                explanation_id=explanation_id,
                update_data=update_data,
            )

            mock_ve_repo.update.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_explanation_not_found(self):
        """Should raise NotFoundError when explanation does not exist."""
        from src.schemas.variance_explanation import VarianceExplanationUpdate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        explanation_id = uuid4()

        update_data = VarianceExplanationUpdate(
            explanation="Attempting to update a non-existent explanation record",
        )

        with patch(
            "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
        ) as mock_ve_repo_cls:
            mock_ve_repo = MagicMock()
            mock_ve_repo.get = AsyncMock(return_value=None)
            mock_ve_repo_cls.return_value = mock_ve_repo

            with pytest.raises(NotFoundError) as exc_info:
                await update_variance_explanation(
                    db=mock_db,
                    current_user=mock_user,
                    explanation_id=explanation_id,
                    update_data=update_data,
                )

            assert exc_info.value.code == "VARIANCE_EXPLANATION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_explanation_no_changes(self):
        """Should commit even when no fields are provided (empty update)."""
        from src.schemas.variance_explanation import VarianceExplanationUpdate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        explanation_id = uuid4()
        explanation_mock = _make_explanation_mock()
        explanation_mock.id = explanation_id

        update_data = VarianceExplanationUpdate()

        with patch(
            "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
        ) as mock_ve_repo_cls:
            mock_ve_repo = MagicMock()
            mock_ve_repo.get = AsyncMock(return_value=explanation_mock)
            mock_ve_repo_cls.return_value = mock_ve_repo

            result = await update_variance_explanation(
                db=mock_db,
                current_user=mock_user,
                explanation_id=explanation_id,
                update_data=update_data,
            )

            # update should NOT be called when there's nothing to update
            mock_ve_repo.update.assert_not_called()
            mock_db.commit.assert_called_once()


class TestDeleteVarianceExplanation:
    """Tests for delete_variance_explanation endpoint."""

    @pytest.mark.asyncio
    async def test_delete_explanation_success(self):
        """Should soft delete a variance explanation."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        explanation_id = uuid4()
        explanation_mock = _make_explanation_mock()
        explanation_mock.id = explanation_id

        with patch(
            "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
        ) as mock_ve_repo_cls:
            mock_ve_repo = MagicMock()
            mock_ve_repo.get = AsyncMock(return_value=explanation_mock)
            mock_ve_repo.delete = AsyncMock(return_value=None)
            mock_ve_repo_cls.return_value = mock_ve_repo

            result = await delete_variance_explanation(
                db=mock_db,
                current_user=mock_user,
                explanation_id=explanation_id,
            )

            assert result is None
            mock_ve_repo.delete.assert_called_once_with(explanation_id)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_explanation_not_found(self):
        """Should raise NotFoundError when explanation does not exist."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        explanation_id = uuid4()

        with patch(
            "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
        ) as mock_ve_repo_cls:
            mock_ve_repo = MagicMock()
            mock_ve_repo.get = AsyncMock(return_value=None)
            mock_ve_repo_cls.return_value = mock_ve_repo

            with pytest.raises(NotFoundError) as exc_info:
                await delete_variance_explanation(
                    db=mock_db,
                    current_user=mock_user,
                    explanation_id=explanation_id,
                )

            assert exc_info.value.code == "VARIANCE_EXPLANATION_NOT_FOUND"


class TestRestoreVarianceExplanation:
    """Tests for restore_variance_explanation endpoint."""

    @pytest.mark.asyncio
    async def test_restore_explanation_success(self):
        """Should restore a soft-deleted variance explanation."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        explanation_id = uuid4()
        explanation_mock = _make_explanation_mock()
        explanation_mock.id = explanation_id
        explanation_mock.deleted_at = None  # restored

        with patch(
            "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
        ) as mock_ve_repo_cls:
            mock_ve_repo = MagicMock()
            mock_ve_repo.restore = AsyncMock(return_value=explanation_mock)
            mock_ve_repo_cls.return_value = mock_ve_repo

            result = await restore_variance_explanation(
                db=mock_db,
                current_user=mock_user,
                explanation_id=explanation_id,
            )

            assert result.id == explanation_id
            mock_ve_repo.restore.assert_called_once_with(explanation_id)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(explanation_mock)

    @pytest.mark.asyncio
    async def test_restore_explanation_not_found(self):
        """Should raise NotFoundError when explanation does not exist."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        explanation_id = uuid4()

        with patch(
            "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
        ) as mock_ve_repo_cls:
            mock_ve_repo = MagicMock()
            mock_ve_repo.restore = AsyncMock(return_value=None)
            mock_ve_repo_cls.return_value = mock_ve_repo

            with pytest.raises(NotFoundError) as exc_info:
                await restore_variance_explanation(
                    db=mock_db,
                    current_user=mock_user,
                    explanation_id=explanation_id,
                )

            assert exc_info.value.code == "VARIANCE_EXPLANATION_NOT_FOUND"


class TestGetSignificantVariances:
    """Tests for get_significant_variances endpoint."""

    @pytest.mark.asyncio
    async def test_get_significant_variances_success(self):
        """Should return explanations above the threshold."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        exp1 = _make_explanation_mock(program_id=program_id, variance_percent=Decimal("15.00"))
        exp2 = _make_explanation_mock(program_id=program_id, variance_percent=Decimal("22.50"))

        with (
            patch(
                "src.api.v1.endpoints.variance_explanations.ProgramRepository"
            ) as mock_prog_repo_cls,
            patch(
                "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
            ) as mock_ve_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_ve_repo = MagicMock()
            mock_ve_repo.get_significant_variances = AsyncMock(return_value=[exp1, exp2])
            mock_ve_repo_cls.return_value = mock_ve_repo

            result = await get_significant_variances(
                db=mock_db,
                current_user=mock_user,
                program_id=program_id,
                threshold_percent=Decimal("10.0"),
            )

            assert len(result) == 2
            mock_ve_repo.get_significant_variances.assert_called_once_with(
                program_id=program_id,
                threshold_percent=Decimal("10.0"),
            )

    @pytest.mark.asyncio
    async def test_get_significant_variances_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        program_id = uuid4()

        with patch(
            "src.api.v1.endpoints.variance_explanations.ProgramRepository"
        ) as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_significant_variances(
                    db=mock_db,
                    current_user=mock_user,
                    program_id=program_id,
                    threshold_percent=Decimal("10.0"),
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_significant_variances_empty(self):
        """Should return empty list when no variances exceed threshold."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        program_id = uuid4()
        mock_program = MagicMock()
        mock_program.id = program_id

        with (
            patch(
                "src.api.v1.endpoints.variance_explanations.ProgramRepository"
            ) as mock_prog_repo_cls,
            patch(
                "src.api.v1.endpoints.variance_explanations.VarianceExplanationRepository"
            ) as mock_ve_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_ve_repo = MagicMock()
            mock_ve_repo.get_significant_variances = AsyncMock(return_value=[])
            mock_ve_repo_cls.return_value = mock_ve_repo

            result = await get_significant_variances(
                db=mock_db,
                current_user=mock_user,
                program_id=program_id,
                threshold_percent=Decimal("50.0"),
            )

            assert len(result) == 0
