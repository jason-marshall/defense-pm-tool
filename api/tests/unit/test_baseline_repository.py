"""Unit tests for BaselineRepository methods using mocks."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.activity import Activity
from src.models.baseline import Baseline
from src.models.dependency import Dependency
from src.models.wbs import WBSElement
from src.repositories.baseline import BaselineRepository


class TestBaselineRepositoryGetByProgram:
    """Tests for get_by_program method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaselineRepository(Baseline, mock_session)

    @pytest.mark.asyncio
    async def test_get_by_program_returns_list(self, repo, mock_session):
        """Should return list of baselines for a program."""
        program_id = uuid4()
        baseline = Baseline(
            id=uuid4(),
            program_id=program_id,
            name="Test",
            version=1,
            is_approved=False,
            total_bac=Decimal("0"),
            activity_count=0,
            wbs_count=0,
            created_by_id=uuid4(),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [baseline]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_program(program_id)

        assert result == [baseline]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_program_with_pagination(self, repo, mock_session):
        """Should apply skip and limit parameters."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_by_program(program_id, skip=10, limit=50)

        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_program_include_deleted(self, repo, mock_session):
        """Should include deleted baselines when flag is set."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repo.get_by_program(program_id, include_deleted=True)

        mock_session.execute.assert_called_once()


class TestBaselineRepositoryCountByProgram:
    """Tests for count_by_program method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaselineRepository(Baseline, mock_session)

    @pytest.mark.asyncio
    async def test_count_by_program_returns_count(self, repo, mock_session):
        """Should return count of baselines."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        result = await repo.count_by_program(program_id)

        assert result == 5

    @pytest.mark.asyncio
    async def test_count_by_program_returns_zero(self, repo, mock_session):
        """Should return 0 when no baselines."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.count_by_program(program_id)

        assert result == 0

    @pytest.mark.asyncio
    async def test_count_by_program_include_deleted(self, repo, mock_session):
        """Should count deleted baselines when flag is set."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_session.execute.return_value = mock_result

        result = await repo.count_by_program(program_id, include_deleted=True)

        assert result == 10


class TestBaselineRepositoryGetLatestVersion:
    """Tests for get_latest_version method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaselineRepository(Baseline, mock_session)

    @pytest.mark.asyncio
    async def test_get_latest_version_returns_version(self, repo, mock_session):
        """Should return latest version number."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_session.execute.return_value = mock_result

        result = await repo.get_latest_version(program_id)

        assert result == 3

    @pytest.mark.asyncio
    async def test_get_latest_version_no_baselines(self, repo, mock_session):
        """Should return 0 when no baselines exist."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_latest_version(program_id)

        assert result == 0


class TestBaselineRepositoryGetApprovedBaseline:
    """Tests for get_approved_baseline method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaselineRepository(Baseline, mock_session)

    @pytest.mark.asyncio
    async def test_get_approved_baseline_returns_baseline(self, repo, mock_session):
        """Should return the approved baseline."""
        program_id = uuid4()
        baseline = Baseline(
            id=uuid4(),
            program_id=program_id,
            name="PMB",
            version=1,
            is_approved=True,
            total_bac=Decimal("100000"),
            activity_count=10,
            wbs_count=5,
            created_by_id=uuid4(),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = baseline
        mock_session.execute.return_value = mock_result

        result = await repo.get_approved_baseline(program_id)

        assert result == baseline
        assert result.is_approved is True

    @pytest.mark.asyncio
    async def test_get_approved_baseline_none(self, repo, mock_session):
        """Should return None when no approved baseline."""
        program_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_approved_baseline(program_id)

        assert result is None


class TestBaselineRepositoryApproveBaseline:
    """Tests for approve_baseline method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaselineRepository(Baseline, mock_session)

    @pytest.mark.asyncio
    async def test_approve_baseline_first(self, repo, mock_session):
        """Should approve baseline when no previous PMB."""
        baseline_id = uuid4()
        approver_id = uuid4()
        baseline = Baseline(
            id=baseline_id,
            program_id=uuid4(),
            name="Test",
            version=1,
            is_approved=False,
            total_bac=Decimal("0"),
            activity_count=0,
            wbs_count=0,
            created_by_id=uuid4(),
        )

        # Mock get to return the baseline
        with patch.object(repo, "get", new_callable=AsyncMock, return_value=baseline):
            with patch.object(repo, "get_approved_baseline", new_callable=AsyncMock, return_value=None):
                result = await repo.approve_baseline(baseline_id, approver_id)

        assert result.is_approved is True
        assert result.approved_by_id == approver_id
        assert result.approved_at is not None

    @pytest.mark.asyncio
    async def test_approve_baseline_replaces_previous(self, repo, mock_session):
        """Should unapprove existing PMB when approving new one."""
        baseline_id = uuid4()
        approver_id = uuid4()
        program_id = uuid4()

        new_baseline = Baseline(
            id=baseline_id,
            program_id=program_id,
            name="New PMB",
            version=2,
            is_approved=False,
            total_bac=Decimal("0"),
            activity_count=0,
            wbs_count=0,
            created_by_id=uuid4(),
        )

        old_baseline = Baseline(
            id=uuid4(),
            program_id=program_id,
            name="Old PMB",
            version=1,
            is_approved=True,
            approved_at=datetime.now(),
            approved_by_id=uuid4(),
            total_bac=Decimal("0"),
            activity_count=0,
            wbs_count=0,
            created_by_id=uuid4(),
        )

        with patch.object(repo, "get", new_callable=AsyncMock, return_value=new_baseline):
            with patch.object(repo, "get_approved_baseline", new_callable=AsyncMock, return_value=old_baseline):
                result = await repo.approve_baseline(baseline_id, approver_id)

        assert result.is_approved is True
        assert old_baseline.is_approved is False
        assert old_baseline.approved_at is None

    @pytest.mark.asyncio
    async def test_approve_baseline_not_found(self, repo, mock_session):
        """Should return None when baseline not found."""
        baseline_id = uuid4()
        approver_id = uuid4()

        with patch.object(repo, "get", new_callable=AsyncMock, return_value=None):
            result = await repo.approve_baseline(baseline_id, approver_id)

        assert result is None


class TestBaselineRepositoryCreateSnapshot:
    """Tests for create_snapshot method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaselineRepository(Baseline, mock_session)

    @pytest.mark.asyncio
    async def test_create_snapshot_with_schedule(self, repo, mock_session):
        """Should create snapshot with schedule data."""
        program_id = uuid4()
        user_id = uuid4()

        # Mock the helper methods
        with patch.object(repo, "get_latest_version", return_value=0):
            with patch.object(
                repo,
                "_build_schedule_snapshot",
                return_value=({"activities": []}, 5, date(2026, 6, 30)),
            ):
                with patch.object(
                    repo,
                    "_build_wbs_cost_snapshot",
                    return_value=(None, None, 0, Decimal("0")),
                ):
                    result = await repo.create_snapshot(
                        program_id=program_id,
                        name="Test Snapshot",
                        description="Test",
                        created_by_id=user_id,
                        include_schedule=True,
                        include_cost=False,
                        include_wbs=False,
                    )

        assert result.name == "Test Snapshot"
        assert result.version == 1
        assert result.activity_count == 5
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_snapshot_version_increment(self, repo, mock_session):
        """Should increment version number."""
        program_id = uuid4()
        user_id = uuid4()

        with patch.object(repo, "get_latest_version", return_value=5):
            with patch.object(
                repo, "_build_schedule_snapshot", return_value=(None, 0, None)
            ):
                with patch.object(
                    repo,
                    "_build_wbs_cost_snapshot",
                    return_value=(None, None, 0, Decimal("0")),
                ):
                    result = await repo.create_snapshot(
                        program_id=program_id,
                        name="Version 6",
                        description=None,
                        created_by_id=user_id,
                        include_schedule=False,
                        include_cost=False,
                        include_wbs=False,
                    )

        assert result.version == 6


class TestBaselineRepositoryBuildScheduleSnapshot:
    """Tests for _build_schedule_snapshot method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaselineRepository(Baseline, mock_session)

    @pytest.mark.asyncio
    async def test_build_schedule_snapshot_no_activities(self, repo, mock_session):
        """Should return None when no activities."""
        program_id = uuid4()

        # Mock empty activity query
        mock_activity_result = MagicMock()
        mock_activity_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_activity_result

        snapshot, count, finish = await repo._build_schedule_snapshot(program_id)

        assert snapshot is None
        assert count == 0
        assert finish is None

    @pytest.mark.asyncio
    async def test_build_schedule_snapshot_with_activities(self, repo, mock_session):
        """Should build snapshot from activities."""
        program_id = uuid4()

        activity = MagicMock(spec=Activity)
        activity.id = uuid4()
        activity.code = "ACT-001"
        activity.name = "Test Activity"
        activity.duration = 10
        activity.planned_start = date(2026, 1, 1)
        activity.planned_finish = date(2026, 1, 15)
        activity.early_start = date(2026, 1, 1)
        activity.early_finish = date(2026, 1, 15)
        activity.late_start = date(2026, 1, 5)
        activity.late_finish = date(2026, 1, 20)
        activity.total_float = 5
        activity.is_critical = True
        activity.budgeted_cost = Decimal("10000.00")
        activity.percent_complete = Decimal("50.00")
        activity.ev_method = "percent_complete"

        # First call returns activities, second returns dependencies
        mock_activity_result = MagicMock()
        mock_activity_result.scalars.return_value.all.return_value = [activity]

        mock_dep_result = MagicMock()
        mock_dep_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_activity_result, mock_dep_result]

        snapshot, count, finish = await repo._build_schedule_snapshot(program_id)

        assert snapshot is not None
        assert count == 1
        assert len(snapshot["activities"]) == 1
        assert snapshot["activities"][0]["code"] == "ACT-001"
        assert str(activity.id) in snapshot["critical_path_ids"]

    @pytest.mark.asyncio
    async def test_build_schedule_snapshot_with_dependencies(self, repo, mock_session):
        """Should include dependencies in snapshot."""
        program_id = uuid4()
        act_id1 = uuid4()
        act_id2 = uuid4()

        activity1 = MagicMock(spec=Activity)
        activity1.id = act_id1
        activity1.code = "ACT-001"
        activity1.name = "Activity 1"
        activity1.duration = 5
        activity1.planned_start = None
        activity1.planned_finish = None
        activity1.early_start = date(2026, 1, 1)
        activity1.early_finish = date(2026, 1, 6)
        activity1.late_start = None
        activity1.late_finish = None
        activity1.total_float = 0
        activity1.is_critical = True
        activity1.budgeted_cost = Decimal("5000.00")
        activity1.percent_complete = Decimal("0")
        activity1.ev_method = "percent_complete"

        activity2 = MagicMock(spec=Activity)
        activity2.id = act_id2
        activity2.code = "ACT-002"
        activity2.name = "Activity 2"
        activity2.duration = 5
        activity2.planned_start = None
        activity2.planned_finish = None
        activity2.early_start = date(2026, 1, 7)
        activity2.early_finish = date(2026, 1, 12)
        activity2.late_start = None
        activity2.late_finish = None
        activity2.total_float = 0
        activity2.is_critical = True
        activity2.budgeted_cost = Decimal("5000.00")
        activity2.percent_complete = Decimal("0")
        activity2.ev_method = "percent_complete"

        dependency = MagicMock(spec=Dependency)
        dependency.predecessor_id = act_id1
        dependency.successor_id = act_id2
        dependency.dependency_type = "FS"
        dependency.lag = 0

        mock_activity_result = MagicMock()
        mock_activity_result.scalars.return_value.all.return_value = [
            activity1,
            activity2,
        ]

        mock_dep_result = MagicMock()
        mock_dep_result.scalars.return_value.all.return_value = [dependency]

        mock_session.execute.side_effect = [mock_activity_result, mock_dep_result]

        snapshot, count, finish = await repo._build_schedule_snapshot(program_id)

        assert len(snapshot["dependencies"]) == 1
        assert snapshot["dependencies"][0]["predecessor_id"] == str(act_id1)
        assert snapshot["dependencies"][0]["dependency_type"] == "FS"


class TestBaselineRepositoryBuildWbsCostSnapshot:
    """Tests for _build_wbs_cost_snapshot method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BaselineRepository(Baseline, mock_session)

    @pytest.mark.asyncio
    async def test_build_wbs_cost_snapshot_no_elements(self, repo, mock_session):
        """Should return None when no WBS elements."""
        program_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        wbs, cost, count, bac = await repo._build_wbs_cost_snapshot(
            program_id, True, True
        )

        assert wbs is None
        assert cost is None
        assert count == 0
        assert bac == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_build_wbs_cost_snapshot_with_elements(self, repo, mock_session):
        """Should build snapshot from WBS elements."""
        program_id = uuid4()

        wbs_elem = MagicMock(spec=WBSElement)
        wbs_elem.id = uuid4()
        wbs_elem.wbs_code = "1.1"
        wbs_elem.name = "Work Package"
        wbs_elem.parent_id = None
        wbs_elem.path = "1.1"
        wbs_elem.budget_at_completion = Decimal("50000.00")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [wbs_elem]
        mock_session.execute.return_value = mock_result

        wbs, cost, count, bac = await repo._build_wbs_cost_snapshot(
            program_id, True, True
        )

        assert wbs is not None
        assert cost is not None
        assert count == 1
        assert bac == Decimal("50000.00")
        assert len(wbs["wbs_elements"]) == 1

    @pytest.mark.asyncio
    async def test_build_wbs_cost_snapshot_wbs_only(self, repo, mock_session):
        """Should return only WBS snapshot when cost is False."""
        program_id = uuid4()

        wbs_elem = MagicMock(spec=WBSElement)
        wbs_elem.id = uuid4()
        wbs_elem.wbs_code = "1.1"
        wbs_elem.name = "Work Package"
        wbs_elem.parent_id = None
        wbs_elem.path = "1.1"
        wbs_elem.budget_at_completion = Decimal("25000.00")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [wbs_elem]
        mock_session.execute.return_value = mock_result

        wbs, cost, count, bac = await repo._build_wbs_cost_snapshot(
            program_id, True, False
        )

        assert wbs is not None
        assert cost is None
        assert count == 1

    @pytest.mark.asyncio
    async def test_build_wbs_cost_snapshot_cost_only(self, repo, mock_session):
        """Should return only cost snapshot when WBS is False."""
        program_id = uuid4()

        wbs_elem = MagicMock(spec=WBSElement)
        wbs_elem.id = uuid4()
        wbs_elem.wbs_code = "1.2"
        wbs_elem.name = "Control Account"
        wbs_elem.parent_id = uuid4()
        wbs_elem.path = "1.2"
        wbs_elem.budget_at_completion = Decimal("75000.00")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [wbs_elem]
        mock_session.execute.return_value = mock_result

        wbs, cost, count, bac = await repo._build_wbs_cost_snapshot(
            program_id, False, True
        )

        assert wbs is None
        assert cost is not None
        assert cost["total_bac"] == str(Decimal("75000.00"))

    @pytest.mark.asyncio
    async def test_build_wbs_cost_snapshot_total_bac_calculation(
        self, repo, mock_session
    ):
        """Should calculate total BAC from all WBS elements."""
        program_id = uuid4()

        wbs1 = MagicMock(spec=WBSElement)
        wbs1.id = uuid4()
        wbs1.wbs_code = "1.1"
        wbs1.name = "WP 1"
        wbs1.parent_id = None
        wbs1.path = "1.1"
        wbs1.budget_at_completion = Decimal("30000.00")

        wbs2 = MagicMock(spec=WBSElement)
        wbs2.id = uuid4()
        wbs2.wbs_code = "1.2"
        wbs2.name = "WP 2"
        wbs2.parent_id = None
        wbs2.path = "1.2"
        wbs2.budget_at_completion = Decimal("20000.00")

        wbs3 = MagicMock(spec=WBSElement)
        wbs3.id = uuid4()
        wbs3.wbs_code = "1.3"
        wbs3.name = "WP 3"
        wbs3.parent_id = None
        wbs3.path = "1.3"
        wbs3.budget_at_completion = Decimal("50000.00")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [wbs1, wbs2, wbs3]
        mock_session.execute.return_value = mock_result

        wbs, cost, count, bac = await repo._build_wbs_cost_snapshot(
            program_id, True, True
        )

        assert count == 3
        assert bac == Decimal("100000.00")
