"""Unit tests for CrossProgramAvailabilityService."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.cross_program_availability import (
    CrossProgramAvailabilityService,
    CrossProgramConflict,
    PoolAvailability,
)


class TestCrossProgramConflict:
    """Tests for CrossProgramConflict dataclass."""

    def test_conflict_creation(self):
        """Test basic conflict creation."""
        resource_id = uuid4()
        conflict = CrossProgramConflict(
            resource_id=resource_id,
            resource_name="Engineer A",
            conflict_date=date(2026, 1, 15),
            programs_involved=[
                {"program_id": str(uuid4()), "program_name": "Program 1", "assigned_hours": 4.0},
                {"program_id": str(uuid4()), "program_name": "Program 2", "assigned_hours": 6.0},
            ],
            total_assigned=Decimal("10.0"),
            available_hours=Decimal("8.0"),
            overallocation=Decimal("2.0"),
        )

        assert conflict.resource_id == resource_id
        assert conflict.resource_name == "Engineer A"
        assert conflict.conflict_date == date(2026, 1, 15)
        assert len(conflict.programs_involved) == 2
        assert conflict.total_assigned == Decimal("10.0")
        assert conflict.available_hours == Decimal("8.0")
        assert conflict.overallocation == Decimal("2.0")

    def test_conflict_with_single_program(self):
        """Test conflict with single program (shouldn't normally happen)."""
        conflict = CrossProgramConflict(
            resource_id=uuid4(),
            resource_name="Tech",
            conflict_date=date(2026, 2, 1),
            programs_involved=[
                {"program_id": str(uuid4()), "assigned_hours": 10.0},
            ],
            total_assigned=Decimal("10.0"),
            available_hours=Decimal("8.0"),
            overallocation=Decimal("2.0"),
        )

        assert len(conflict.programs_involved) == 1

    def test_conflict_decimal_precision(self):
        """Test conflict handles decimal precision correctly."""
        conflict = CrossProgramConflict(
            resource_id=uuid4(),
            resource_name="Analyst",
            conflict_date=date(2026, 3, 1),
            programs_involved=[],
            total_assigned=Decimal("8.333"),
            available_hours=Decimal("8.000"),
            overallocation=Decimal("0.333"),
        )

        assert conflict.overallocation == Decimal("0.333")


class TestPoolAvailability:
    """Tests for PoolAvailability dataclass."""

    def test_pool_availability_creation(self):
        """Test basic pool availability creation."""
        pool_id = uuid4()
        availability = PoolAvailability(
            pool_id=pool_id,
            pool_name="Engineering Pool",
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 1, 31),
            resources=[
                {
                    "resource_id": str(uuid4()),
                    "resource_code": "ENG-001",
                    "resource_name": "Engineer A",
                    "allocation_percentage": 100.0,
                    "is_active": True,
                    "conflict_count": 0,
                }
            ],
            conflicts=[],
        )

        assert availability.pool_id == pool_id
        assert availability.pool_name == "Engineering Pool"
        assert availability.date_range_start == date(2026, 1, 1)
        assert availability.date_range_end == date(2026, 1, 31)
        assert len(availability.resources) == 1
        assert len(availability.conflicts) == 0

    def test_pool_availability_with_conflicts(self):
        """Test pool availability with conflicts."""
        conflict = CrossProgramConflict(
            resource_id=uuid4(),
            resource_name="Engineer",
            conflict_date=date(2026, 1, 15),
            programs_involved=[],
            total_assigned=Decimal("10"),
            available_hours=Decimal("8"),
            overallocation=Decimal("2"),
        )

        availability = PoolAvailability(
            pool_id=uuid4(),
            pool_name="Pool",
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 1, 31),
            resources=[],
            conflicts=[conflict],
        )

        assert len(availability.conflicts) == 1
        assert availability.conflicts[0].overallocation == Decimal("2")

    def test_pool_availability_empty(self):
        """Test empty pool availability."""
        availability = PoolAvailability(
            pool_id=uuid4(),
            pool_name="Empty Pool",
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 1, 7),
            resources=[],
            conflicts=[],
        )

        assert len(availability.resources) == 0
        assert len(availability.conflicts) == 0


class TestCrossProgramAvailabilityServiceInit:
    """Tests for CrossProgramAvailabilityService initialization."""

    def test_service_initialization(self):
        """Test service initializes with database session."""
        mock_db = MagicMock()
        service = CrossProgramAvailabilityService(mock_db)

        assert service.db == mock_db


class TestCrossProgramAvailabilityServiceGetPoolAvailability:
    """Tests for get_pool_availability method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return CrossProgramAvailabilityService(mock_db)

    @pytest.mark.asyncio
    async def test_get_pool_availability_pool_not_found(self, service, mock_db):
        """Test error when pool not found."""
        pool_id = uuid4()

        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match=f"Pool {pool_id} not found"):
            await service.get_pool_availability(
                pool_id,
                date(2026, 1, 1),
                date(2026, 1, 31),
            )

    @pytest.mark.asyncio
    async def test_get_pool_availability_empty_pool(self, service, mock_db):
        """Test pool with no members."""
        pool_id = uuid4()

        # Mock pool with no members
        mock_pool = MagicMock()
        mock_pool.id = pool_id
        mock_pool.name = "Empty Pool"
        mock_pool.members = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pool
        mock_db.execute.return_value = mock_result

        result = await service.get_pool_availability(
            pool_id,
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        assert result.pool_id == pool_id
        assert result.pool_name == "Empty Pool"
        assert len(result.resources) == 0
        assert len(result.conflicts) == 0

    @pytest.mark.asyncio
    async def test_get_pool_availability_with_inactive_member(self, service, mock_db):
        """Test pool skips inactive members."""
        pool_id = uuid4()

        # Create inactive member
        mock_member = MagicMock()
        mock_member.is_active = False

        mock_pool = MagicMock()
        mock_pool.id = pool_id
        mock_pool.name = "Pool"
        mock_pool.members = [mock_member]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pool
        mock_db.execute.return_value = mock_result

        result = await service.get_pool_availability(
            pool_id,
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        # Inactive member should be skipped
        assert len(result.resources) == 0

    @pytest.mark.asyncio
    async def test_get_pool_availability_with_active_member(self, service, mock_db):
        """Test pool includes active members."""
        pool_id = uuid4()
        resource_id = uuid4()

        # Create mock resource
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.code = "ENG-001"
        mock_resource.name = "Engineer"
        mock_resource.capacity_per_day = Decimal("8")

        # Create active member
        mock_member = MagicMock()
        mock_member.is_active = True
        mock_member.allocation_percentage = Decimal("100")
        mock_member.resource = mock_resource

        mock_pool = MagicMock()
        mock_pool.id = pool_id
        mock_pool.name = "Pool"
        mock_pool.members = [mock_member]

        # Setup db mock to return pool first, then empty assignments
        call_count = [0]

        def mock_execute(query):
            result = MagicMock()
            if call_count[0] == 0:
                result.scalar_one_or_none.return_value = mock_pool
            else:
                result.scalars.return_value.all.return_value = []
            call_count[0] += 1
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        result = await service.get_pool_availability(
            pool_id,
            date(2026, 1, 1),
            date(2026, 1, 7),
        )

        assert len(result.resources) == 1
        assert result.resources[0]["resource_code"] == "ENG-001"
        assert result.resources[0]["resource_name"] == "Engineer"


class TestCrossProgramAvailabilityServiceCheckResourceConflict:
    """Tests for check_resource_conflict method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return CrossProgramAvailabilityService(mock_db)

    @pytest.mark.asyncio
    async def test_check_resource_conflict_resource_not_found(self, service, mock_db):
        """Test error when resource not found."""
        resource_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match=f"Resource {resource_id} not found"):
            await service.check_resource_conflict(
                resource_id,
                uuid4(),
                date(2026, 1, 1),
                date(2026, 1, 5),
                Decimal("1.0"),
            )

    @pytest.mark.asyncio
    async def test_check_resource_conflict_no_existing_assignments(self, service, mock_db):
        """Test no conflicts when no existing assignments."""
        resource_id = uuid4()
        program_id = uuid4()

        # Mock resource
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.name = "Engineer"
        mock_resource.capacity_per_day = Decimal("8")

        # Setup db mock
        call_count = [0]

        def mock_execute(query):
            result = MagicMock()
            if call_count[0] == 0:
                result.scalar_one_or_none.return_value = mock_resource
            else:
                result.scalars.return_value.all.return_value = []
            call_count[0] += 1
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        conflicts = await service.check_resource_conflict(
            resource_id,
            program_id,
            date(2026, 1, 1),
            date(2026, 1, 5),
            Decimal("0.5"),  # 50% allocation
        )

        # 0.5 * 8 = 4 hours, under 8 hour capacity
        assert len(conflicts) == 0

    @pytest.mark.asyncio
    async def test_check_resource_conflict_over_capacity(self, service, mock_db):
        """Test conflict detected when over capacity."""
        resource_id = uuid4()
        program_id = uuid4()
        other_program_id = uuid4()

        # Mock resource with 8 hour capacity
        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.name = "Engineer"
        mock_resource.capacity_per_day = Decimal("8")

        # Existing assignment using 6 hours
        mock_activity = MagicMock()
        mock_activity.program_id = other_program_id
        mock_activity.early_start = date(2026, 1, 1)
        mock_activity.early_finish = date(2026, 1, 3)

        mock_assignment = MagicMock()
        mock_assignment.activity_id = uuid4()
        mock_assignment.activity = mock_activity
        mock_assignment.start_date = date(2026, 1, 1)
        mock_assignment.finish_date = date(2026, 1, 3)
        mock_assignment.units = Decimal("0.75")  # 75% = 6 hours

        # Setup db mock
        call_count = [0]

        def mock_execute(query):
            result = MagicMock()
            if call_count[0] == 0:
                result.scalar_one_or_none.return_value = mock_resource
            else:
                result.scalars.return_value.all.return_value = [mock_assignment]
            call_count[0] += 1
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        # Try to add another 0.5 (4 hours) - total 10 hours > 8 capacity
        conflicts = await service.check_resource_conflict(
            resource_id,
            program_id,
            date(2026, 1, 1),
            date(2026, 1, 3),
            Decimal("0.5"),
        )

        # Should have conflicts for each day
        assert len(conflicts) == 3  # Jan 1, 2, 3


class TestCrossProgramAvailabilityServiceInternalMethods:
    """Tests for internal helper methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return CrossProgramAvailabilityService(mock_db)

    @pytest.mark.asyncio
    async def test_get_cross_program_assignments(self, service, mock_db):
        """Test fetching cross-program assignments."""
        resource_id = uuid4()
        program_id = uuid4()

        mock_activity = MagicMock()
        mock_activity.program_id = program_id
        mock_activity.early_start = date(2026, 1, 5)
        mock_activity.early_finish = date(2026, 1, 10)

        mock_assignment = MagicMock()
        mock_assignment.activity_id = uuid4()
        mock_assignment.activity = mock_activity
        mock_assignment.start_date = date(2026, 1, 5)
        mock_assignment.finish_date = date(2026, 1, 10)
        mock_assignment.units = Decimal("1.0")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_assignment]
        mock_db.execute.return_value = mock_result

        assignments = await service._get_cross_program_assignments(
            resource_id,
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        assert len(assignments) == 1
        assert assignments[0]["program_id"] == program_id
        assert assignments[0]["units"] == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_detect_conflicts_no_overlap(self, service, mock_db):
        """Test no conflicts when assignments don't overlap."""
        resource_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.name = "Engineer"
        mock_resource.capacity_per_day = Decimal("8")

        # Two assignments on different days
        assignments = [
            {
                "program_id": uuid4(),
                "activity_id": uuid4(),
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 1, 1),
                "units": Decimal("1.0"),
            },
            {
                "program_id": uuid4(),
                "activity_id": uuid4(),
                "start_date": date(2026, 1, 3),
                "end_date": date(2026, 1, 3),
                "units": Decimal("1.0"),
            },
        ]

        conflicts = await service._detect_conflicts(
            mock_resource,
            assignments,
            date(2026, 1, 1),
            date(2026, 1, 5),
        )

        assert len(conflicts) == 0

    @pytest.mark.asyncio
    async def test_detect_conflicts_with_overlap(self, service, mock_db):
        """Test conflicts detected when assignments overlap and exceed capacity."""
        resource_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.name = "Engineer"
        mock_resource.capacity_per_day = Decimal("8")

        # Two 60% assignments on same day = 120% > 100%
        assignments = [
            {
                "program_id": uuid4(),
                "activity_id": uuid4(),
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 1, 1),
                "units": Decimal("0.6"),
            },
            {
                "program_id": uuid4(),
                "activity_id": uuid4(),
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 1, 1),
                "units": Decimal("0.6"),
            },
        ]

        conflicts = await service._detect_conflicts(
            mock_resource,
            assignments,
            date(2026, 1, 1),
            date(2026, 1, 1),
        )

        assert len(conflicts) == 1
        assert conflicts[0].conflict_date == date(2026, 1, 1)
        # 0.6 * 8 + 0.6 * 8 = 9.6 > 8
        assert conflicts[0].total_assigned == Decimal("9.6")
        assert conflicts[0].overallocation == Decimal("1.6")

    @pytest.mark.asyncio
    async def test_detect_conflicts_with_allocation_percentage(self, service, mock_db):
        """Test conflicts consider pool allocation percentage."""
        resource_id = uuid4()

        mock_resource = MagicMock()
        mock_resource.id = resource_id
        mock_resource.name = "Engineer"
        mock_resource.capacity_per_day = Decimal("8")

        # Two 40% assignments on same day
        assignments = [
            {
                "program_id": uuid4(),
                "activity_id": uuid4(),
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 1, 1),
                "units": Decimal("0.4"),
            },
            {
                "program_id": uuid4(),
                "activity_id": uuid4(),
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 1, 1),
                "units": Decimal("0.4"),
            },
        ]

        # Pool only has 50% allocation of this resource
        # So available = 8 * 0.5 = 4 hours
        # Total assigned = 0.4 * 8 + 0.4 * 8 = 6.4 hours > 4 hours
        conflicts = await service._detect_conflicts(
            mock_resource,
            assignments,
            date(2026, 1, 1),
            date(2026, 1, 1),
            allocation_percentage=Decimal("50.00"),
        )

        assert len(conflicts) == 1
        assert conflicts[0].available_hours == Decimal("4.0")

    @pytest.mark.asyncio
    async def test_detect_conflicts_single_assignment_no_conflict(self, service, mock_db):
        """Test single assignment never causes conflict (needs 2+ to conflict)."""
        mock_resource = MagicMock()
        mock_resource.id = uuid4()
        mock_resource.name = "Engineer"
        mock_resource.capacity_per_day = Decimal("8")

        # Single 200% assignment (shouldn't create cross-program conflict)
        assignments = [
            {
                "program_id": uuid4(),
                "activity_id": uuid4(),
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 1, 1),
                "units": Decimal("2.0"),
            },
        ]

        conflicts = await service._detect_conflicts(
            mock_resource,
            assignments,
            date(2026, 1, 1),
            date(2026, 1, 1),
        )

        # No conflict because only 1 assignment
        assert len(conflicts) == 0


class TestCrossProgramAvailabilityServiceDateRange:
    """Tests for date range handling."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return CrossProgramAvailabilityService(mock_db)

    @pytest.mark.asyncio
    async def test_detect_conflicts_multi_day_range(self, service, mock_db):
        """Test conflict detection across multiple days."""
        mock_resource = MagicMock()
        mock_resource.id = uuid4()
        mock_resource.name = "Engineer"
        mock_resource.capacity_per_day = Decimal("8")

        # Overlapping assignments for 3 days
        assignments = [
            {
                "program_id": uuid4(),
                "activity_id": uuid4(),
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 1, 3),
                "units": Decimal("0.6"),
            },
            {
                "program_id": uuid4(),
                "activity_id": uuid4(),
                "start_date": date(2026, 1, 2),
                "end_date": date(2026, 1, 4),
                "units": Decimal("0.6"),
            },
        ]

        conflicts = await service._detect_conflicts(
            mock_resource,
            assignments,
            date(2026, 1, 1),
            date(2026, 1, 5),
        )

        # Conflicts only on days 2 and 3 where both overlap
        assert len(conflicts) == 2
        conflict_dates = [c.conflict_date for c in conflicts]
        assert date(2026, 1, 2) in conflict_dates
        assert date(2026, 1, 3) in conflict_dates

    @pytest.mark.asyncio
    async def test_detect_conflicts_handles_none_dates(self, service, mock_db):
        """Test handling of assignments with None dates."""
        mock_resource = MagicMock()
        mock_resource.id = uuid4()
        mock_resource.name = "Engineer"
        mock_resource.capacity_per_day = Decimal("8")

        # One assignment with None dates
        assignments = [
            {
                "program_id": uuid4(),
                "activity_id": uuid4(),
                "start_date": None,
                "end_date": None,
                "units": Decimal("1.0"),
            },
            {
                "program_id": uuid4(),
                "activity_id": uuid4(),
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 1, 1),
                "units": Decimal("0.5"),
            },
        ]

        # Should not crash, just skip None-dated assignments
        conflicts = await service._detect_conflicts(
            mock_resource,
            assignments,
            date(2026, 1, 1),
            date(2026, 1, 1),
        )

        # No conflict - only 1 valid assignment
        assert len(conflicts) == 0
