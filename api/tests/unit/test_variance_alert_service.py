"""Unit tests for Variance Alert to Jira Issue creation service.

Tests the VarianceAlertService with mocked repositories and Jira client.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.services.jira_client import JiraSyncError
from src.services.jira_variance_alert import (
    VARIANCE_ISSUE_TYPES,
    VARIANCE_PRIORITY_THRESHOLDS,
    BatchCreateResult,
    IntegrationNotFoundError,
    SyncDisabledError,
    VarianceAlertError,
    VarianceAlertService,
    VarianceIssueResult,
)


class TestVarianceIssueResult:
    """Tests for VarianceIssueResult dataclass."""

    def test_default_values(self):
        """VarianceIssueResult should have sensible defaults."""
        result = VarianceIssueResult(success=True)
        assert result.success is True
        assert result.jira_issue_key is None
        assert result.jira_issue_id is None
        assert result.mapping_id is None
        assert result.error_message is None
        assert result.duration_ms == 0

    def test_with_values(self):
        """VarianceIssueResult should store all values."""
        mapping_id = uuid4()
        result = VarianceIssueResult(
            success=True,
            jira_issue_key="PROJ-123",
            jira_issue_id="10123",
            mapping_id=mapping_id,
            error_message=None,
            duration_ms=500,
        )
        assert result.success is True
        assert result.jira_issue_key == "PROJ-123"
        assert result.jira_issue_id == "10123"
        assert result.mapping_id == mapping_id
        assert result.duration_ms == 500

    def test_failure_result(self):
        """VarianceIssueResult should store failure details."""
        result = VarianceIssueResult(
            success=False,
            error_message="API rate limit exceeded",
            duration_ms=100,
        )
        assert result.success is False
        assert result.jira_issue_key is None
        assert result.error_message == "API rate limit exceeded"


class TestBatchCreateResult:
    """Tests for BatchCreateResult dataclass."""

    def test_default_values(self):
        """BatchCreateResult should have sensible defaults."""
        result = BatchCreateResult(success=True, issues_created=0, issues_failed=0)
        assert result.success is True
        assert result.issues_created == 0
        assert result.issues_failed == 0
        assert result.errors == []
        assert result.created_issues == []
        assert result.duration_ms == 0

    def test_with_values(self):
        """BatchCreateResult should store all values."""
        issue_result = VarianceIssueResult(success=True, jira_issue_key="PROJ-1")
        result = BatchCreateResult(
            success=True,
            issues_created=5,
            issues_failed=2,
            errors=["Error 1", "Error 2"],
            created_issues=[issue_result],
            duration_ms=2500,
        )
        assert result.issues_created == 5
        assert result.issues_failed == 2
        assert len(result.errors) == 2
        assert len(result.created_issues) == 1


class TestVarianceAlertExceptions:
    """Tests for custom variance alert exceptions."""

    def test_variance_alert_error(self):
        """VarianceAlertError should store message and details."""
        error = VarianceAlertError("Creation failed", {"reason": "invalid project"})
        assert str(error) == "Creation failed"
        assert error.message == "Creation failed"
        assert error.details == {"reason": "invalid project"}

    def test_variance_alert_error_default_details(self):
        """VarianceAlertError should default to empty details."""
        error = VarianceAlertError("Error")
        assert error.details == {}

    def test_integration_not_found_error(self):
        """IntegrationNotFoundError should inherit from VarianceAlertError."""
        error = IntegrationNotFoundError("Not found")
        assert isinstance(error, VarianceAlertError)

    def test_sync_disabled_error(self):
        """SyncDisabledError should inherit from VarianceAlertError."""
        error = SyncDisabledError("Disabled")
        assert isinstance(error, VarianceAlertError)


class TestVarianceAlertConstants:
    """Tests for variance alert constants."""

    def test_priority_thresholds_ordering(self):
        """Priority thresholds should be in descending order."""
        thresholds = [t[0] for t in VARIANCE_PRIORITY_THRESHOLDS]
        assert thresholds == sorted(thresholds, reverse=True)

    def test_priority_thresholds_coverage(self):
        """Priority thresholds should cover critical levels."""
        priorities = [t[1] for t in VARIANCE_PRIORITY_THRESHOLDS]
        assert "Highest" in priorities
        assert "High" in priorities
        assert "Medium" in priorities
        assert "Low" in priorities
        assert "Lowest" in priorities

    def test_issue_types_mapping(self):
        """Issue types should map variance types correctly."""
        assert VARIANCE_ISSUE_TYPES["cost"] == "Bug"
        assert VARIANCE_ISSUE_TYPES["schedule"] == "Task"


class TestVarianceAlertServiceInit:
    """Tests for VarianceAlertService initialization."""

    def test_init_stores_dependencies(self):
        """Service should store all dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = MagicMock()
        mock_mapping_repo = MagicMock()
        mock_sync_log_repo = MagicMock()

        service = VarianceAlertService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
        )

        assert service.jira_client is mock_jira
        assert service.integration_repo is mock_integration_repo
        assert service.mapping_repo is mock_mapping_repo
        assert service.sync_log_repo is mock_sync_log_repo


class TestVarianceAlertServiceGetIntegration:
    """Tests for _get_integration method."""

    @pytest.fixture
    def service(self):
        """Create a VarianceAlertService with mocked dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()

        return VarianceAlertService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
        )

    @pytest.mark.asyncio
    async def test_get_integration_success(self, service):
        """Should return integration when found and enabled."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.sync_enabled = True
        service.integration_repo.get_by_id.return_value = mock_integration

        result = await service._get_integration(integration_id)

        assert result is mock_integration
        service.integration_repo.get_by_id.assert_called_once_with(integration_id)

    @pytest.mark.asyncio
    async def test_get_integration_not_found(self, service):
        """Should raise IntegrationNotFoundError when not found."""
        integration_id = uuid4()
        service.integration_repo.get_by_id.return_value = None

        with pytest.raises(IntegrationNotFoundError) as exc:
            await service._get_integration(integration_id)

        assert str(integration_id) in str(exc.value)

    @pytest.mark.asyncio
    async def test_get_integration_disabled(self, service):
        """Should raise SyncDisabledError when sync disabled."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.sync_enabled = False
        service.integration_repo.get_by_id.return_value = mock_integration

        with pytest.raises(SyncDisabledError) as exc:
            await service._get_integration(integration_id)

        assert "disabled" in str(exc.value).lower()


class TestVarianceAlertServiceBuildIssueSummary:
    """Tests for _build_issue_summary method."""

    @pytest.fixture
    def service(self):
        """Create a VarianceAlertService with mocked dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()

        return VarianceAlertService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
        )

    def test_cost_variance_over_budget(self, service):
        """Should format cost variance over budget correctly."""
        variance = MagicMock()
        variance.variance_type = "cost"
        variance.variance_percent = Decimal("15.50")
        variance.variance_amount = Decimal("50000.00")

        result = service._build_issue_summary(variance, "Design Phase")

        assert "[VARIANCE]" in result
        assert "COST" in result
        assert "over" in result
        assert "15.50%" in result
        assert "Design Phase" in result

    def test_cost_variance_under_budget(self, service):
        """Should format cost variance under budget correctly."""
        variance = MagicMock()
        variance.variance_type = "cost"
        variance.variance_percent = Decimal("-10.00")
        variance.variance_amount = Decimal("-25000.00")

        result = service._build_issue_summary(variance)

        assert "under" in result
        assert "10.00%" in result
        assert "Program Level" in result

    def test_schedule_variance(self, service):
        """Should format schedule variance correctly."""
        variance = MagicMock()
        variance.variance_type = "schedule"
        variance.variance_percent = Decimal("20.00")
        variance.variance_amount = Decimal("100000.00")

        result = service._build_issue_summary(variance, "Build Phase")

        assert "SCHEDULE" in result
        assert "Build Phase" in result

    def test_program_level_when_no_wbs(self, service):
        """Should use 'Program Level' when no WBS name provided."""
        variance = MagicMock()
        variance.variance_type = "cost"
        variance.variance_percent = Decimal("12.00")
        variance.variance_amount = Decimal("30000.00")

        result = service._build_issue_summary(variance, None)

        assert "Program Level" in result


class TestVarianceAlertServiceBuildIssueDescription:
    """Tests for _build_issue_description method."""

    @pytest.fixture
    def service(self):
        """Create a VarianceAlertService with mocked dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()

        return VarianceAlertService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
        )

    def test_includes_variance_details(self, service):
        """Description should include all variance details."""
        variance = MagicMock()
        variance.variance_type = "cost"
        variance.variance_amount = Decimal("50000.00")
        variance.variance_percent = Decimal("15.50")
        variance.explanation = "Material costs exceeded estimates due to supply chain issues."
        variance.corrective_action = None
        variance.expected_resolution = None

        result = service._build_issue_description(variance)

        assert "COST" in result
        assert "$50,000.00" in result
        assert "15.50%" in result
        assert "Material costs exceeded estimates" in result

    def test_includes_wbs_name(self, service):
        """Description should include WBS name when provided."""
        variance = MagicMock()
        variance.variance_type = "schedule"
        variance.variance_amount = Decimal("10000.00")
        variance.variance_percent = Decimal("12.00")
        variance.explanation = "Delay in procurement."
        variance.corrective_action = None
        variance.expected_resolution = None

        result = service._build_issue_description(variance, "Subsystem Integration")

        assert "Subsystem Integration" in result

    def test_includes_corrective_action(self, service):
        """Description should include corrective action when provided."""
        variance = MagicMock()
        variance.variance_type = "cost"
        variance.variance_amount = Decimal("75000.00")
        variance.variance_percent = Decimal("22.00")
        variance.explanation = "Labor overruns."
        variance.corrective_action = "Hire additional contractors to accelerate schedule."
        variance.expected_resolution = None

        result = service._build_issue_description(variance)

        assert "Corrective Action" in result
        assert "Hire additional contractors" in result

    def test_includes_expected_resolution(self, service):
        """Description should include expected resolution date when provided."""
        variance = MagicMock()
        variance.variance_type = "schedule"
        variance.variance_amount = Decimal("-5000.00")
        variance.variance_percent = Decimal("-8.00")
        variance.explanation = "Minor schedule slip."
        variance.corrective_action = None
        variance.expected_resolution = date(2026, 3, 15)

        result = service._build_issue_description(variance)

        assert "Expected Resolution" in result
        assert "2026-03-15" in result

    def test_includes_attribution(self, service):
        """Description should include Defense PM Tool attribution."""
        variance = MagicMock()
        variance.variance_type = "cost"
        variance.variance_amount = Decimal("1000.00")
        variance.variance_percent = Decimal("5.00")
        variance.explanation = "Minor cost variance."
        variance.corrective_action = None
        variance.expected_resolution = None

        result = service._build_issue_description(variance)

        assert "Defense PM Tool" in result


class TestVarianceAlertServiceGetPriority:
    """Tests for _get_priority_for_variance method."""

    @pytest.fixture
    def service(self):
        """Create a VarianceAlertService with mocked dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()

        return VarianceAlertService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
        )

    def test_highest_priority_for_25_percent_plus(self, service):
        """Should return Highest for >= 25% variance."""
        assert service._get_priority_for_variance(Decimal("25.0")) == "Highest"
        assert service._get_priority_for_variance(Decimal("30.0")) == "Highest"
        assert service._get_priority_for_variance(Decimal("-25.0")) == "Highest"

    def test_high_priority_for_20_to_25_percent(self, service):
        """Should return High for 20-24.99% variance."""
        assert service._get_priority_for_variance(Decimal("20.0")) == "High"
        assert service._get_priority_for_variance(Decimal("24.99")) == "High"
        assert service._get_priority_for_variance(Decimal("-22.0")) == "High"

    def test_medium_priority_for_15_to_20_percent(self, service):
        """Should return Medium for 15-19.99% variance."""
        assert service._get_priority_for_variance(Decimal("15.0")) == "Medium"
        assert service._get_priority_for_variance(Decimal("19.99")) == "Medium"
        assert service._get_priority_for_variance(Decimal("-17.5")) == "Medium"

    def test_low_priority_for_10_to_15_percent(self, service):
        """Should return Low for 10-14.99% variance."""
        assert service._get_priority_for_variance(Decimal("10.0")) == "Low"
        assert service._get_priority_for_variance(Decimal("14.99")) == "Low"
        assert service._get_priority_for_variance(Decimal("-12.0")) == "Low"

    def test_lowest_priority_for_under_10_percent(self, service):
        """Should return Lowest for < 10% variance."""
        assert service._get_priority_for_variance(Decimal("9.99")) == "Lowest"
        assert service._get_priority_for_variance(Decimal("5.0")) == "Lowest"
        assert service._get_priority_for_variance(Decimal("-3.0")) == "Lowest"
        assert service._get_priority_for_variance(Decimal("0.0")) == "Lowest"


class TestVarianceAlertServiceBuildLabels:
    """Tests for _build_labels method."""

    @pytest.fixture
    def service(self):
        """Create a VarianceAlertService with mocked dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()

        return VarianceAlertService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
        )

    def test_includes_standard_labels(self, service):
        """Should include standard labels for all variances."""
        variance = MagicMock()
        variance.variance_type = "cost"
        variance.variance_percent = Decimal("15.0")

        labels = service._build_labels(variance)

        assert "defense-pm-tool" in labels
        assert "variance-alert" in labels

    def test_includes_variance_type_label(self, service):
        """Should include variance type label."""
        variance = MagicMock()
        variance.variance_type = "schedule"
        variance.variance_percent = Decimal("12.0")

        labels = service._build_labels(variance)

        assert "variance-schedule" in labels

    def test_severity_critical_for_25_plus(self, service):
        """Should label as critical for >= 25% variance."""
        variance = MagicMock()
        variance.variance_type = "cost"
        variance.variance_percent = Decimal("28.0")

        labels = service._build_labels(variance)

        assert "severity-critical" in labels

    def test_severity_high_for_20_to_25(self, service):
        """Should label as high for 20-24.99% variance."""
        variance = MagicMock()
        variance.variance_type = "cost"
        variance.variance_percent = Decimal("22.0")

        labels = service._build_labels(variance)

        assert "severity-high" in labels

    def test_severity_medium_for_15_to_20(self, service):
        """Should label as medium for 15-19.99% variance."""
        variance = MagicMock()
        variance.variance_type = "schedule"
        variance.variance_percent = Decimal("-17.0")

        labels = service._build_labels(variance)

        assert "severity-medium" in labels

    def test_severity_low_for_under_15(self, service):
        """Should label as low for < 15% variance."""
        variance = MagicMock()
        variance.variance_type = "cost"
        variance.variance_percent = Decimal("12.0")

        labels = service._build_labels(variance)

        assert "severity-low" in labels


class TestVarianceAlertServiceShouldCreateIssue:
    """Tests for should_create_issue method."""

    @pytest.fixture
    def service(self):
        """Create a VarianceAlertService with mocked dependencies."""
        mock_jira = MagicMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()

        return VarianceAlertService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
        )

    @pytest.mark.asyncio
    async def test_true_when_exceeds_threshold(self, service):
        """Should return True when variance exceeds threshold."""
        variance = MagicMock()
        variance.variance_percent = Decimal("12.0")
        variance.corrective_action = None
        variance.expected_resolution = None

        result = await service.should_create_issue(variance, Decimal("10.0"))

        assert result is True

    @pytest.mark.asyncio
    async def test_true_when_has_corrective_action(self, service):
        """Should return True when corrective action is defined."""
        variance = MagicMock()
        variance.variance_percent = Decimal("5.0")  # Below threshold
        variance.corrective_action = "Add resources"
        variance.expected_resolution = None

        result = await service.should_create_issue(variance, Decimal("10.0"))

        assert result is True

    @pytest.mark.asyncio
    async def test_true_when_has_resolution_date(self, service):
        """Should return True when expected resolution is set."""
        variance = MagicMock()
        variance.variance_percent = Decimal("5.0")  # Below threshold
        variance.corrective_action = None
        variance.expected_resolution = date(2026, 3, 1)

        result = await service.should_create_issue(variance, Decimal("10.0"))

        assert result is True

    @pytest.mark.asyncio
    async def test_false_when_no_conditions_met(self, service):
        """Should return False when no conditions met."""
        variance = MagicMock()
        variance.variance_percent = Decimal("5.0")  # Below threshold
        variance.corrective_action = None
        variance.expected_resolution = None

        result = await service.should_create_issue(variance, Decimal("10.0"))

        assert result is False

    @pytest.mark.asyncio
    async def test_negative_variance_uses_absolute_value(self, service):
        """Should use absolute value for negative variances."""
        variance = MagicMock()
        variance.variance_percent = Decimal("-15.0")  # Negative but above 10%
        variance.corrective_action = None
        variance.expected_resolution = None

        result = await service.should_create_issue(variance, Decimal("10.0"))

        assert result is True


class TestVarianceAlertServiceCreateVarianceIssue:
    """Tests for create_variance_issue method."""

    @pytest.fixture
    def service(self):
        """Create a VarianceAlertService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()

        return VarianceAlertService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
        )

    @pytest.mark.asyncio
    async def test_raises_for_missing_integration(self, service):
        """Should raise IntegrationNotFoundError."""
        integration_id = uuid4()
        service.integration_repo.get_by_id.return_value = None

        variance = MagicMock()
        variance.id = uuid4()

        with pytest.raises(IntegrationNotFoundError):
            await service.create_variance_issue(integration_id, variance)

    @pytest.mark.asyncio
    async def test_raises_for_disabled_sync(self, service):
        """Should raise SyncDisabledError."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.sync_enabled = False
        service.integration_repo.get_by_id.return_value = mock_integration

        variance = MagicMock()
        variance.id = uuid4()

        with pytest.raises(SyncDisabledError):
            await service.create_variance_issue(integration_id, variance)

    @pytest.mark.asyncio
    async def test_creates_issue_successfully(self, service):
        """Should create issue and return success result."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.project_key = "PROJ"
        service.integration_repo.get_by_id.return_value = mock_integration

        variance = MagicMock()
        variance.id = uuid4()
        variance.wbs_id = None
        variance.variance_type = "cost"
        variance.variance_amount = Decimal("50000.00")
        variance.variance_percent = Decimal("15.0")
        variance.explanation = "Cost overrun due to material price increase."
        variance.corrective_action = None
        variance.expected_resolution = None

        mock_issue = MagicMock()
        mock_issue.key = "PROJ-42"
        mock_issue.id = "10042"
        service.jira_client.create_issue.return_value = mock_issue
        service.mapping_repo.get_by_wbs.return_value = None

        result = await service.create_variance_issue(integration_id, variance)

        assert result.success is True
        assert result.jira_issue_key == "PROJ-42"
        assert result.jira_issue_id == "10042"

    @pytest.mark.asyncio
    async def test_uses_correct_issue_type_for_cost(self, service):
        """Should use Bug issue type for cost variance."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.project_key = "PROJ"
        service.integration_repo.get_by_id.return_value = mock_integration

        variance = MagicMock()
        variance.id = uuid4()
        variance.wbs_id = None
        variance.variance_type = "cost"
        variance.variance_amount = Decimal("50000.00")
        variance.variance_percent = Decimal("15.0")
        variance.explanation = "Cost overrun."
        variance.corrective_action = None
        variance.expected_resolution = None

        mock_issue = MagicMock()
        mock_issue.key = "PROJ-42"
        mock_issue.id = "10042"
        service.jira_client.create_issue.return_value = mock_issue

        await service.create_variance_issue(integration_id, variance)

        call_kwargs = service.jira_client.create_issue.call_args[1]
        assert call_kwargs["issue_type"] == "Bug"

    @pytest.mark.asyncio
    async def test_uses_correct_issue_type_for_schedule(self, service):
        """Should use Task issue type for schedule variance."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.project_key = "PROJ"
        service.integration_repo.get_by_id.return_value = mock_integration

        variance = MagicMock()
        variance.id = uuid4()
        variance.wbs_id = None
        variance.variance_type = "schedule"
        variance.variance_amount = Decimal("20000.00")
        variance.variance_percent = Decimal("10.0")
        variance.explanation = "Schedule slip."
        variance.corrective_action = None
        variance.expected_resolution = None

        mock_issue = MagicMock()
        mock_issue.key = "PROJ-43"
        mock_issue.id = "10043"
        service.jira_client.create_issue.return_value = mock_issue

        await service.create_variance_issue(integration_id, variance)

        call_kwargs = service.jira_client.create_issue.call_args[1]
        assert call_kwargs["issue_type"] == "Task"

    @pytest.mark.asyncio
    async def test_links_to_wbs_epic(self, service):
        """Should link to WBS Epic when mapping exists."""
        integration_id = uuid4()
        wbs_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.project_key = "PROJ"
        service.integration_repo.get_by_id.return_value = mock_integration

        variance = MagicMock()
        variance.id = uuid4()
        variance.wbs_id = wbs_id
        variance.variance_type = "cost"
        variance.variance_amount = Decimal("30000.00")
        variance.variance_percent = Decimal("12.0")
        variance.explanation = "Cost variance on subsystem."
        variance.corrective_action = None
        variance.expected_resolution = None

        wbs_mapping = MagicMock()
        wbs_mapping.jira_issue_key = "PROJ-10"
        service.mapping_repo.get_by_wbs.return_value = wbs_mapping

        mock_issue = MagicMock()
        mock_issue.key = "PROJ-44"
        mock_issue.id = "10044"
        service.jira_client.create_issue.return_value = mock_issue

        await service.create_variance_issue(integration_id, variance, "Design Phase")

        call_kwargs = service.jira_client.create_issue.call_args[1]
        assert call_kwargs["epic_key"] == "PROJ-10"

    @pytest.mark.asyncio
    async def test_logs_sync_on_success(self, service):
        """Should create sync log entry on success."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.project_key = "PROJ"
        service.integration_repo.get_by_id.return_value = mock_integration

        variance = MagicMock()
        variance.id = uuid4()
        variance.wbs_id = None
        variance.variance_type = "cost"
        variance.variance_amount = Decimal("10000.00")
        variance.variance_percent = Decimal("8.0")
        variance.explanation = "Minor cost variance."
        variance.corrective_action = None
        variance.expected_resolution = None

        mock_issue = MagicMock()
        mock_issue.key = "PROJ-45"
        mock_issue.id = "10045"
        service.jira_client.create_issue.return_value = mock_issue

        await service.create_variance_issue(integration_id, variance)

        service.sync_log_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_jira_error(self, service):
        """Should return failure result on Jira error."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.project_key = "PROJ"
        service.integration_repo.get_by_id.return_value = mock_integration

        variance = MagicMock()
        variance.id = uuid4()
        variance.wbs_id = None
        variance.variance_type = "cost"
        variance.variance_amount = Decimal("10000.00")
        variance.variance_percent = Decimal("8.0")
        variance.explanation = "Cost variance."
        variance.corrective_action = None
        variance.expected_resolution = None

        service.jira_client.create_issue.side_effect = JiraSyncError("API error")

        result = await service.create_variance_issue(integration_id, variance)

        assert result.success is False
        assert "API error" in result.error_message

    @pytest.mark.asyncio
    async def test_logs_sync_on_failure(self, service):
        """Should create sync log entry on failure."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.project_key = "PROJ"
        service.integration_repo.get_by_id.return_value = mock_integration

        variance = MagicMock()
        variance.id = uuid4()
        variance.wbs_id = None
        variance.variance_type = "cost"
        variance.variance_amount = Decimal("10000.00")
        variance.variance_percent = Decimal("8.0")
        variance.explanation = "Cost variance."
        variance.corrective_action = None
        variance.expected_resolution = None

        service.jira_client.create_issue.side_effect = JiraSyncError("API error")

        await service.create_variance_issue(integration_id, variance)

        service.sync_log_repo.create.assert_called_once()
        call_args = service.sync_log_repo.create.call_args[0][0]
        assert call_args["status"] == "failed"


class TestVarianceAlertServiceBatchCreate:
    """Tests for create_variance_issues_batch method."""

    @pytest.fixture
    def service(self):
        """Create a VarianceAlertService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()

        return VarianceAlertService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
        )

    @pytest.mark.asyncio
    async def test_raises_for_missing_integration(self, service):
        """Should raise IntegrationNotFoundError."""
        integration_id = uuid4()
        service.integration_repo.get_by_id.return_value = None

        with pytest.raises(IntegrationNotFoundError):
            await service.create_variance_issues_batch(integration_id, [])

    @pytest.mark.asyncio
    async def test_creates_multiple_issues(self, service):
        """Should create multiple issues in batch."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.project_key = "PROJ"
        service.integration_repo.get_by_id.return_value = mock_integration

        variances = []
        for i in range(3):
            variance = MagicMock()
            variance.id = uuid4()
            variance.wbs_id = None
            variance.variance_type = "cost"
            variance.variance_amount = Decimal(f"{10000 * (i + 1)}.00")
            variance.variance_percent = Decimal(f"{10 + i}.0")
            variance.explanation = f"Variance {i + 1}"
            variance.corrective_action = None
            variance.expected_resolution = None
            variances.append((variance, f"WBS {i + 1}"))

        mock_issues = []
        for i in range(3):
            mock_issue = MagicMock()
            mock_issue.key = f"PROJ-{50 + i}"
            mock_issue.id = f"100{50 + i}"
            mock_issues.append(mock_issue)

        service.jira_client.create_issue.side_effect = mock_issues

        result = await service.create_variance_issues_batch(integration_id, variances)

        assert result.success is True
        assert result.issues_created == 3
        assert result.issues_failed == 0
        assert len(result.created_issues) == 3

    @pytest.mark.asyncio
    async def test_handles_partial_failure(self, service):
        """Should report partial success when some fail."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.project_key = "PROJ"
        service.integration_repo.get_by_id.return_value = mock_integration

        variances = []
        for i in range(3):
            variance = MagicMock()
            variance.id = uuid4()
            variance.wbs_id = None
            variance.variance_type = "cost"
            variance.variance_amount = Decimal(f"{10000 * (i + 1)}.00")
            variance.variance_percent = Decimal(f"{10 + i}.0")
            variance.explanation = f"Variance {i + 1}"
            variance.corrective_action = None
            variance.expected_resolution = None
            variances.append((variance, None))

        mock_issue = MagicMock()
        mock_issue.key = "PROJ-50"
        mock_issue.id = "10050"

        # First succeeds, second fails, third succeeds
        service.jira_client.create_issue.side_effect = [
            mock_issue,
            JiraSyncError("Rate limit"),
            mock_issue,
        ]

        result = await service.create_variance_issues_batch(integration_id, variances)

        assert result.success is True  # Partial success
        assert result.issues_created == 2
        assert result.issues_failed == 1
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_reports_total_failure(self, service):
        """Should report failure when all fail."""
        integration_id = uuid4()
        mock_integration = MagicMock()
        mock_integration.id = integration_id
        mock_integration.sync_enabled = True
        mock_integration.project_key = "PROJ"
        service.integration_repo.get_by_id.return_value = mock_integration

        variance = MagicMock()
        variance.id = uuid4()
        variance.wbs_id = None
        variance.variance_type = "cost"
        variance.variance_amount = Decimal("10000.00")
        variance.variance_percent = Decimal("10.0")
        variance.explanation = "Variance"
        variance.corrective_action = None
        variance.expected_resolution = None

        service.jira_client.create_issue.side_effect = JiraSyncError("API down")

        result = await service.create_variance_issues_batch(integration_id, [(variance, None)])

        assert result.success is False
        assert result.issues_created == 0
        assert result.issues_failed == 1


class TestVarianceAlertServiceLogSync:
    """Tests for _log_sync method."""

    @pytest.fixture
    def service(self):
        """Create a VarianceAlertService with mocked dependencies."""
        mock_jira = AsyncMock()
        mock_integration_repo = AsyncMock()
        mock_mapping_repo = AsyncMock()
        mock_sync_log_repo = AsyncMock()

        return VarianceAlertService(
            jira_client=mock_jira,
            integration_repo=mock_integration_repo,
            mapping_repo=mock_mapping_repo,
            sync_log_repo=mock_sync_log_repo,
        )

    @pytest.mark.asyncio
    async def test_creates_sync_log_entry(self, service):
        """Should create sync log with all parameters."""
        integration_id = uuid4()

        await service._log_sync(
            integration_id=integration_id,
            sync_type="push",
            status="success",
            items_synced=1,
            error_message=None,
            duration_ms=500,
        )

        service.sync_log_repo.create.assert_called_once()
        call_args = service.sync_log_repo.create.call_args[0][0]
        assert call_args["integration_id"] == integration_id
        assert call_args["sync_type"] == "push"
        assert call_args["status"] == "success"
        assert call_args["items_synced"] == 1
        assert call_args["duration_ms"] == 500

    @pytest.mark.asyncio
    async def test_creates_sync_log_with_error(self, service):
        """Should include error message in sync log."""
        integration_id = uuid4()

        await service._log_sync(
            integration_id=integration_id,
            sync_type="push",
            status="failed",
            items_synced=0,
            error_message="Connection timeout",
            duration_ms=30000,
        )

        call_args = service.sync_log_repo.create.call_args[0][0]
        assert call_args["status"] == "failed"
        assert call_args["error_message"] == "Connection timeout"
