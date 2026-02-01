"""Unit tests for resource repository."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.enums import ResourceType
from src.repositories.resource import (
    ResourceAssignmentRepository,
    ResourceCalendarRepository,
    ResourceRepository,
)


class TestResourceRepositoryInit:
    """Tests for ResourceRepository initialization."""

    def test_init(self):
        """Test repository initialization."""
        mock_session = MagicMock()
        repo = ResourceRepository(mock_session)
        assert repo.session == mock_session


class TestResourceRepositoryGetByProgram:
    """Tests for ResourceRepository.get_by_program method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_program_basic(self, repo, mock_session):
        """Test getting resources for a program."""
        resource = MagicMock()
        resource.id = uuid4()
        resource.code = "R-001"

        # Count query
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        # Items query
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [resource]

        mock_session.execute.side_effect = [count_result, items_result]

        items, total = await repo.get_by_program(uuid4())

        assert total == 1
        assert len(items) == 1
        assert items[0].code == "R-001"

    @pytest.mark.asyncio
    async def test_get_by_program_with_type_filter(self, repo, mock_session):
        """Test getting resources with type filter."""
        resource = MagicMock()
        resource.resource_type = ResourceType.LABOR

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [resource]

        mock_session.execute.side_effect = [count_result, items_result]

        items, total = await repo.get_by_program(
            uuid4(),
            resource_type=ResourceType.LABOR,
        )

        assert total == 1

    @pytest.mark.asyncio
    async def test_get_by_program_with_active_filter(self, repo, mock_session):
        """Test getting resources with active filter."""
        resource = MagicMock()
        resource.is_active = True

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [resource]

        mock_session.execute.side_effect = [count_result, items_result]

        items, total = await repo.get_by_program(
            uuid4(),
            is_active=True,
        )

        assert total == 1

    @pytest.mark.asyncio
    async def test_get_by_program_with_pagination(self, repo, mock_session):
        """Test getting resources with pagination."""
        resources = [MagicMock() for _ in range(10)]

        count_result = MagicMock()
        count_result.scalar_one.return_value = 100

        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = resources

        mock_session.execute.side_effect = [count_result, items_result]

        items, total = await repo.get_by_program(
            uuid4(),
            skip=10,
            limit=10,
        )

        assert total == 100
        assert len(items) == 10


class TestResourceRepositoryCountByProgram:
    """Tests for ResourceRepository.count_by_program method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceRepository(mock_session)

    @pytest.mark.asyncio
    async def test_count_by_program_basic(self, repo, mock_session):
        """Test counting resources for a program."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_session.execute.return_value = mock_result

        count = await repo.count_by_program(uuid4())

        assert count == 5

    @pytest.mark.asyncio
    async def test_count_by_program_with_filters(self, repo, mock_session):
        """Test counting resources with filters."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 3
        mock_session.execute.return_value = mock_result

        count = await repo.count_by_program(
            uuid4(),
            resource_type=ResourceType.EQUIPMENT,
            is_active=True,
        )

        assert count == 3


class TestResourceRepositoryGetByCode:
    """Tests for ResourceRepository.get_by_code method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_code_found(self, repo, mock_session):
        """Test finding a resource by code."""
        resource = MagicMock()
        resource.code = "R-001"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = resource
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_code(uuid4(), "R-001")

        assert result is not None
        assert result.code == "R-001"

    @pytest.mark.asyncio
    async def test_get_by_code_not_found(self, repo, mock_session):
        """Test when resource code not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_code(uuid4(), "NONEXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_code_case_insensitive(self, repo, mock_session):
        """Test case-insensitive code lookup."""
        resource = MagicMock()
        resource.code = "R-001"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = resource
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_code(uuid4(), "r-001")

        assert result is not None


class TestResourceRepositoryCodeExists:
    """Tests for ResourceRepository.code_exists method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceRepository(mock_session)

    @pytest.mark.asyncio
    async def test_code_exists_true(self, repo, mock_session):
        """Test when code exists."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 1
        mock_session.execute.return_value = mock_result

        exists = await repo.code_exists(uuid4(), "R-001")

        assert exists is True

    @pytest.mark.asyncio
    async def test_code_exists_false(self, repo, mock_session):
        """Test when code doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        exists = await repo.code_exists(uuid4(), "R-001")

        assert exists is False

    @pytest.mark.asyncio
    async def test_code_exists_with_exclude(self, repo, mock_session):
        """Test code exists with exclusion."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        exists = await repo.code_exists(
            uuid4(),
            "R-001",
            exclude_id=uuid4(),
        )

        assert exists is False


class TestResourceRepositoryGetWithAssignments:
    """Tests for ResourceRepository.get_with_assignments method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_with_assignments_found(self, repo, mock_session):
        """Test getting resource with assignments."""
        resource = MagicMock()
        resource.id = uuid4()
        resource.assignments = [MagicMock(), MagicMock()]

        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = resource
        mock_session.execute.return_value = mock_result

        result = await repo.get_with_assignments(resource.id)

        assert result is not None
        assert len(result.assignments) == 2

    @pytest.mark.asyncio
    async def test_get_with_assignments_not_found(self, repo, mock_session):
        """Test when resource not found."""
        mock_result = MagicMock()
        mock_result.unique.return_value.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_with_assignments(uuid4())

        assert result is None


class TestResourceAssignmentRepositoryInit:
    """Tests for ResourceAssignmentRepository initialization."""

    def test_init(self):
        """Test repository initialization."""
        mock_session = MagicMock()
        repo = ResourceAssignmentRepository(mock_session)
        assert repo.session == mock_session


class TestResourceAssignmentRepositoryGetByActivity:
    """Tests for ResourceAssignmentRepository.get_by_activity method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceAssignmentRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_activity(self, repo, mock_session):
        """Test getting assignments for an activity."""
        assignment1 = MagicMock()
        assignment2 = MagicMock()

        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = [
            assignment1,
            assignment2,
        ]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_activity(uuid4())

        assert len(result) == 2


class TestResourceAssignmentRepositoryGetByResource:
    """Tests for ResourceAssignmentRepository.get_by_resource method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceAssignmentRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_resource_basic(self, repo, mock_session):
        """Test getting assignments for a resource."""
        assignment = MagicMock()

        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = [
            assignment
        ]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_resource(uuid4())

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_resource_with_date_range(self, repo, mock_session):
        """Test getting assignments with date range filter."""
        assignment = MagicMock()

        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = [
            assignment
        ]
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_resource(
            uuid4(),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        assert len(result) == 1


class TestResourceAssignmentRepositoryAssignmentExists:
    """Tests for ResourceAssignmentRepository.assignment_exists method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceAssignmentRepository(mock_session)

    @pytest.mark.asyncio
    async def test_assignment_exists_true(self, repo, mock_session):
        """Test when assignment exists."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 1
        mock_session.execute.return_value = mock_result

        exists = await repo.assignment_exists(uuid4(), uuid4())

        assert exists is True

    @pytest.mark.asyncio
    async def test_assignment_exists_false(self, repo, mock_session):
        """Test when assignment doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        exists = await repo.assignment_exists(uuid4(), uuid4())

        assert exists is False

    @pytest.mark.asyncio
    async def test_assignment_exists_with_exclude(self, repo, mock_session):
        """Test assignment exists with exclusion."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_session.execute.return_value = mock_result

        exists = await repo.assignment_exists(
            uuid4(),
            uuid4(),
            exclude_id=uuid4(),
        )

        assert exists is False


class TestResourceAssignmentRepositoryGetAssignmentsWithActivities:
    """Tests for ResourceAssignmentRepository.get_assignments_with_activities method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceAssignmentRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_assignments_with_activities(self, repo, mock_session):
        """Test getting assignments with activities loaded."""
        assignment = MagicMock()
        assignment.activity = MagicMock()

        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = [
            assignment
        ]
        mock_session.execute.return_value = mock_result

        result = await repo.get_assignments_with_activities(uuid4())

        assert len(result) == 1
        assert result[0].activity is not None


class TestResourceAssignmentRepositoryGetTotalUnitsForResource:
    """Tests for ResourceAssignmentRepository.get_total_units_for_resource method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceAssignmentRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_total_units(self, repo, mock_session):
        """Test getting total units for a resource on a date."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = Decimal("2.5")
        mock_session.execute.return_value = mock_result

        total = await repo.get_total_units_for_resource(
            uuid4(),
            date(2026, 1, 15),
        )

        assert total == Decimal("2.5")


class TestResourceCalendarRepositoryInit:
    """Tests for ResourceCalendarRepository initialization."""

    def test_init(self):
        """Test repository initialization."""
        mock_session = MagicMock()
        repo = ResourceCalendarRepository(mock_session)
        assert repo.session == mock_session


class TestResourceCalendarRepositoryGetForDateRange:
    """Tests for ResourceCalendarRepository.get_for_date_range method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceCalendarRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_for_date_range(self, repo, mock_session):
        """Test getting calendar entries for date range."""
        entry1 = MagicMock()
        entry1.calendar_date = date(2026, 1, 1)
        entry2 = MagicMock()
        entry2.calendar_date = date(2026, 1, 2)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [entry1, entry2]
        mock_session.execute.return_value = mock_result

        result = await repo.get_for_date_range(
            uuid4(),
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        assert len(result) == 2


class TestResourceCalendarRepositoryGetByDate:
    """Tests for ResourceCalendarRepository.get_by_date method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceCalendarRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_date_found(self, repo, mock_session):
        """Test getting calendar entry by date."""
        entry = MagicMock()
        entry.calendar_date = date(2026, 1, 15)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = entry
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_date(uuid4(), date(2026, 1, 15))

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_by_date_not_found(self, repo, mock_session):
        """Test when calendar entry not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_date(uuid4(), date(2026, 1, 15))

        assert result is None


class TestResourceCalendarRepositoryBulkCreateEntries:
    """Tests for ResourceCalendarRepository.bulk_create_entries method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.add_all = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceCalendarRepository(mock_session)

    @pytest.mark.asyncio
    async def test_bulk_create_entries(self, repo, mock_session):
        """Test bulk creating calendar entries."""
        # The bulk_create_entries method just delegates to bulk_create
        # We verify it returns the result from bulk_create
        entries_data = [
            {"resource_id": uuid4(), "calendar_date": date(2026, 1, 1)},
        ]

        # Mock the base class bulk_create method
        with patch.object(repo, "bulk_create", new_callable=AsyncMock) as mock_bulk:
            mock_bulk.return_value = [MagicMock()]
            result = await repo.bulk_create_entries(entries_data)
            mock_bulk.assert_called_once_with(entries_data)
            assert len(result) == 1


class TestResourceCalendarRepositoryGetWorkingDaysCount:
    """Tests for ResourceCalendarRepository.get_working_days_count method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceCalendarRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_working_days_count(self, repo, mock_session):
        """Test counting working days."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 22
        mock_session.execute.return_value = mock_result

        count = await repo.get_working_days_count(
            uuid4(),
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        assert count == 22


class TestResourceCalendarRepositoryGetTotalHours:
    """Tests for ResourceCalendarRepository.get_total_hours method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceCalendarRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_total_hours(self, repo, mock_session):
        """Test getting total hours."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = Decimal("176.00")
        mock_session.execute.return_value = mock_result

        total = await repo.get_total_hours(
            uuid4(),
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        assert total == Decimal("176.00")


class TestResourceCalendarRepositoryDeleteRange:
    """Tests for ResourceCalendarRepository.delete_range method."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository instance."""
        return ResourceCalendarRepository(mock_session)

    @pytest.mark.asyncio
    async def test_delete_range(self, repo, mock_session):
        """Test deleting calendar entries in range."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 31
        mock_session.execute.return_value = mock_cursor

        deleted = await repo.delete_range(
            uuid4(),
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        assert deleted == 31
