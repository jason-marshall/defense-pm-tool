"""Integration tests for Resource, ResourceAssignment, and ResourceCalendar repositories."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import Activity
from src.models.enums import ResourceType
from src.models.program import Program
from src.models.resource import Resource, ResourceAssignment
from src.models.user import User
from src.models.wbs import WBSElement
from src.repositories.resource import (
    ResourceAssignmentRepository,
    ResourceCalendarRepository,
    ResourceRepository,
)

pytestmark = pytest.mark.asyncio


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        email=f"test_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
        full_name="Test User",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_program(db_session: AsyncSession, test_user: User) -> Program:
    """Create a test program."""
    program = Program(
        id=uuid4(),
        code=f"PRG-{uuid4().hex[:6]}",
        name="Test Program",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        owner_id=test_user.id,
    )
    db_session.add(program)
    await db_session.flush()
    return program


@pytest_asyncio.fixture
async def test_wbs(db_session: AsyncSession, test_program: Program) -> WBSElement:
    """Create a test WBS element."""
    wbs = WBSElement(
        id=uuid4(),
        program_id=test_program.id,
        wbs_code="1.1",
        name="Work Package 1",
        path="1.1",  # ltree path required
        level=1,
    )
    db_session.add(wbs)
    await db_session.flush()
    return wbs


@pytest_asyncio.fixture
async def test_activity(
    db_session: AsyncSession, test_program: Program, test_wbs: WBSElement
) -> Activity:
    """Create a test activity."""
    activity = Activity(
        id=uuid4(),
        program_id=test_program.id,
        wbs_id=test_wbs.id,
        code="ACT-001",
        name="Test Activity",
        duration=10,
    )
    db_session.add(activity)
    await db_session.flush()
    return activity


@pytest_asyncio.fixture
async def test_resource(db_session: AsyncSession, test_program: Program) -> Resource:
    """Create a test resource."""
    resource = Resource(
        id=uuid4(),
        program_id=test_program.id,
        code="ENG-001",
        name="Senior Engineer",
        resource_type=ResourceType.LABOR,
        capacity_per_day=Decimal("8.0"),
        cost_rate=Decimal("150.00"),
        is_active=True,
    )
    db_session.add(resource)
    await db_session.flush()
    return resource


# =============================================================================
# ResourceRepository Tests
# =============================================================================


class TestResourceRepository:
    """Tests for ResourceRepository."""

    async def test_create_resource(self, db_session: AsyncSession, test_program: Program) -> None:
        """Test creating a resource."""
        repo = ResourceRepository(db_session)

        resource = await repo.create(
            {
                "program_id": test_program.id,
                "code": "DEV-001",
                "name": "Developer",
                "resource_type": ResourceType.LABOR,
                "capacity_per_day": Decimal("8.0"),
            }
        )

        assert resource.id is not None
        assert resource.code == "DEV-001"
        assert resource.name == "Developer"
        assert resource.resource_type == ResourceType.LABOR

    async def test_get_by_program(
        self, db_session: AsyncSession, test_program: Program, test_resource: Resource
    ) -> None:
        """Test getting resources by program."""
        repo = ResourceRepository(db_session)

        # Create another resource
        await repo.create(
            {
                "program_id": test_program.id,
                "code": "EQP-001",
                "name": "Excavator",
                "resource_type": ResourceType.EQUIPMENT,
            }
        )

        resources, total = await repo.get_by_program(test_program.id)

        assert total == 2
        assert len(resources) == 2

    async def test_get_by_program_with_type_filter(
        self, db_session: AsyncSession, test_program: Program, test_resource: Resource
    ) -> None:
        """Test filtering resources by type."""
        repo = ResourceRepository(db_session)

        # Create equipment resource
        await repo.create(
            {
                "program_id": test_program.id,
                "code": "EQP-001",
                "name": "Excavator",
                "resource_type": ResourceType.EQUIPMENT,
            }
        )

        # Filter by LABOR only
        resources, total = await repo.get_by_program(
            test_program.id, resource_type=ResourceType.LABOR
        )

        assert total == 1
        assert resources[0].code == "ENG-001"

    async def test_get_by_program_with_active_filter(
        self, db_session: AsyncSession, test_program: Program, test_resource: Resource
    ) -> None:
        """Test filtering resources by active status."""
        repo = ResourceRepository(db_session)

        # Create inactive resource
        await repo.create(
            {
                "program_id": test_program.id,
                "code": "OLD-001",
                "name": "Old Resource",
                "is_active": False,
            }
        )

        # Filter by active only
        resources, total = await repo.get_by_program(test_program.id, is_active=True)

        assert total == 1
        assert resources[0].is_active is True

    async def test_get_by_code(
        self, db_session: AsyncSession, test_program: Program, test_resource: Resource
    ) -> None:
        """Test getting resource by code."""
        repo = ResourceRepository(db_session)

        resource = await repo.get_by_code(test_program.id, "ENG-001")

        assert resource is not None
        assert resource.code == "ENG-001"

    async def test_get_by_code_case_insensitive(
        self, db_session: AsyncSession, test_program: Program, test_resource: Resource
    ) -> None:
        """Test that code lookup is case-insensitive."""
        repo = ResourceRepository(db_session)

        resource = await repo.get_by_code(test_program.id, "eng-001")

        assert resource is not None
        assert resource.code == "ENG-001"

    async def test_get_by_code_not_found(
        self, db_session: AsyncSession, test_program: Program
    ) -> None:
        """Test getting non-existent resource by code."""
        repo = ResourceRepository(db_session)

        resource = await repo.get_by_code(test_program.id, "NONEXISTENT")

        assert resource is None

    async def test_code_exists(
        self, db_session: AsyncSession, test_program: Program, test_resource: Resource
    ) -> None:
        """Test checking if code exists."""
        repo = ResourceRepository(db_session)

        exists = await repo.code_exists(test_program.id, "ENG-001")
        assert exists is True

        not_exists = await repo.code_exists(test_program.id, "NONEXISTENT")
        assert not_exists is False

    async def test_code_exists_with_exclude(
        self, db_session: AsyncSession, test_program: Program, test_resource: Resource
    ) -> None:
        """Test code exists check with exclusion."""
        repo = ResourceRepository(db_session)

        # Should return False when excluding the resource itself
        exists = await repo.code_exists(test_program.id, "ENG-001", exclude_id=test_resource.id)
        assert exists is False

    async def test_count_by_program(
        self, db_session: AsyncSession, test_program: Program, test_resource: Resource
    ) -> None:
        """Test counting resources by program."""
        repo = ResourceRepository(db_session)

        count = await repo.count_by_program(test_program.id)
        assert count == 1

    async def test_get_with_assignments(
        self,
        db_session: AsyncSession,
        test_resource: Resource,
        test_activity: Activity,
    ) -> None:
        """Test getting resource with assignments eagerly loaded."""
        # Create an assignment
        assignment = ResourceAssignment(
            id=uuid4(),
            activity_id=test_activity.id,
            resource_id=test_resource.id,
            units=Decimal("1.0"),
        )
        db_session.add(assignment)
        await db_session.flush()

        repo = ResourceRepository(db_session)
        resource = await repo.get_with_assignments(test_resource.id)

        assert resource is not None
        assert len(resource.assignments) == 1
        assert resource.assignments[0].units == Decimal("1.0")


# =============================================================================
# ResourceAssignmentRepository Tests
# =============================================================================


class TestResourceAssignmentRepository:
    """Tests for ResourceAssignmentRepository."""

    async def test_create_assignment(
        self,
        db_session: AsyncSession,
        test_resource: Resource,
        test_activity: Activity,
    ) -> None:
        """Test creating a resource assignment."""
        repo = ResourceAssignmentRepository(db_session)

        assignment = await repo.create(
            {
                "activity_id": test_activity.id,
                "resource_id": test_resource.id,
                "units": Decimal("1.5"),
                "start_date": date(2024, 1, 1),
                "finish_date": date(2024, 1, 31),
            }
        )

        assert assignment.id is not None
        assert assignment.units == Decimal("1.5")

    async def test_get_by_activity(
        self,
        db_session: AsyncSession,
        test_resource: Resource,
        test_activity: Activity,
    ) -> None:
        """Test getting assignments by activity."""
        repo = ResourceAssignmentRepository(db_session)

        # Create assignment
        await repo.create(
            {
                "activity_id": test_activity.id,
                "resource_id": test_resource.id,
                "units": Decimal("1.0"),
            }
        )

        assignments = await repo.get_by_activity(test_activity.id)

        assert len(assignments) == 1
        assert assignments[0].resource is not None  # Eagerly loaded
        assert assignments[0].resource.code == "ENG-001"

    async def test_get_by_resource(
        self,
        db_session: AsyncSession,
        test_resource: Resource,
        test_activity: Activity,
    ) -> None:
        """Test getting assignments by resource."""
        repo = ResourceAssignmentRepository(db_session)

        await repo.create(
            {
                "activity_id": test_activity.id,
                "resource_id": test_resource.id,
                "units": Decimal("1.0"),
                "start_date": date(2024, 1, 15),
                "finish_date": date(2024, 1, 31),
            }
        )

        # Get all assignments
        assignments = await repo.get_by_resource(test_resource.id)
        assert len(assignments) == 1

        # Filter by date range - should include
        assignments = await repo.get_by_resource(
            test_resource.id, start_date=date(2024, 1, 1), end_date=date(2024, 1, 20)
        )
        assert len(assignments) == 1

        # Filter by date range - should exclude
        assignments = await repo.get_by_resource(
            test_resource.id, start_date=date(2024, 2, 1), end_date=date(2024, 2, 28)
        )
        assert len(assignments) == 0

    async def test_assignment_exists(
        self,
        db_session: AsyncSession,
        test_resource: Resource,
        test_activity: Activity,
    ) -> None:
        """Test checking if assignment exists."""
        repo = ResourceAssignmentRepository(db_session)

        # No assignment yet
        exists = await repo.assignment_exists(test_activity.id, test_resource.id)
        assert exists is False

        # Create assignment
        await repo.create(
            {
                "activity_id": test_activity.id,
                "resource_id": test_resource.id,
                "units": Decimal("1.0"),
            }
        )

        exists = await repo.assignment_exists(test_activity.id, test_resource.id)
        assert exists is True

    async def test_get_total_units_for_resource(
        self,
        db_session: AsyncSession,
        test_program: Program,
        test_wbs: WBSElement,
        test_resource: Resource,
    ) -> None:
        """Test getting total allocation units for a resource on a date."""
        repo = ResourceAssignmentRepository(db_session)

        # Create two activities with assignments
        activity1 = Activity(
            id=uuid4(),
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            code="ACT-A",
            name="Activity A",
            duration=10,
        )
        activity2 = Activity(
            id=uuid4(),
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            code="ACT-B",
            name="Activity B",
            duration=10,
        )
        db_session.add_all([activity1, activity2])
        await db_session.flush()

        # Create assignments overlapping on Jan 15
        await repo.create(
            {
                "activity_id": activity1.id,
                "resource_id": test_resource.id,
                "units": Decimal("0.5"),
                "start_date": date(2024, 1, 1),
                "finish_date": date(2024, 1, 20),
            }
        )
        await repo.create(
            {
                "activity_id": activity2.id,
                "resource_id": test_resource.id,
                "units": Decimal("0.75"),
                "start_date": date(2024, 1, 10),
                "finish_date": date(2024, 1, 31),
            }
        )

        total = await repo.get_total_units_for_resource(test_resource.id, date(2024, 1, 15))
        assert total == Decimal("1.25")


# =============================================================================
# ResourceCalendarRepository Tests
# =============================================================================


class TestResourceCalendarRepository:
    """Tests for ResourceCalendarRepository."""

    async def test_create_calendar_entry(
        self, db_session: AsyncSession, test_resource: Resource
    ) -> None:
        """Test creating a calendar entry."""
        repo = ResourceCalendarRepository(db_session)

        entry = await repo.create(
            {
                "resource_id": test_resource.id,
                "calendar_date": date(2024, 1, 15),
                "available_hours": Decimal("8.0"),
                "is_working_day": True,
            }
        )

        assert entry.id is not None
        assert entry.calendar_date == date(2024, 1, 15)
        assert entry.available_hours == Decimal("8.0")

    async def test_get_for_date_range(
        self, db_session: AsyncSession, test_resource: Resource
    ) -> None:
        """Test getting calendar entries for a date range."""
        repo = ResourceCalendarRepository(db_session)

        # Create entries for a week
        for i in range(7):
            await repo.create(
                {
                    "resource_id": test_resource.id,
                    "calendar_date": date(2024, 1, 1) + timedelta(days=i),
                    "available_hours": Decimal("8.0") if i < 5 else Decimal("0.0"),
                    "is_working_day": i < 5,  # Mon-Fri working
                }
            )

        entries = await repo.get_for_date_range(
            test_resource.id, date(2024, 1, 1), date(2024, 1, 7)
        )

        assert len(entries) == 7
        # Check they're ordered by date
        assert entries[0].calendar_date == date(2024, 1, 1)
        assert entries[6].calendar_date == date(2024, 1, 7)

    async def test_get_by_date(self, db_session: AsyncSession, test_resource: Resource) -> None:
        """Test getting a calendar entry by date."""
        repo = ResourceCalendarRepository(db_session)

        await repo.create(
            {
                "resource_id": test_resource.id,
                "calendar_date": date(2024, 1, 15),
                "available_hours": Decimal("4.0"),
                "is_working_day": True,
            }
        )

        entry = await repo.get_by_date(test_resource.id, date(2024, 1, 15))

        assert entry is not None
        assert entry.available_hours == Decimal("4.0")

    async def test_get_by_date_not_found(
        self, db_session: AsyncSession, test_resource: Resource
    ) -> None:
        """Test getting non-existent calendar entry."""
        repo = ResourceCalendarRepository(db_session)

        entry = await repo.get_by_date(test_resource.id, date(2024, 1, 15))

        assert entry is None

    async def test_bulk_create_entries(
        self, db_session: AsyncSession, test_resource: Resource
    ) -> None:
        """Test bulk creating calendar entries."""
        repo = ResourceCalendarRepository(db_session)

        entries_data = [
            {
                "resource_id": test_resource.id,
                "calendar_date": date(2024, 1, 1) + timedelta(days=i),
                "available_hours": Decimal("8.0"),
                "is_working_day": True,
            }
            for i in range(5)
        ]

        entries = await repo.bulk_create_entries(entries_data)

        assert len(entries) == 5

    async def test_get_working_days_count(
        self, db_session: AsyncSession, test_resource: Resource
    ) -> None:
        """Test counting working days in a range."""
        repo = ResourceCalendarRepository(db_session)

        # Create a week with 5 working days
        for i in range(7):
            await repo.create(
                {
                    "resource_id": test_resource.id,
                    "calendar_date": date(2024, 1, 1) + timedelta(days=i),
                    "available_hours": Decimal("8.0") if i < 5 else Decimal("0.0"),
                    "is_working_day": i < 5,
                }
            )

        count = await repo.get_working_days_count(
            test_resource.id, date(2024, 1, 1), date(2024, 1, 7)
        )

        assert count == 5

    async def test_get_total_hours(self, db_session: AsyncSession, test_resource: Resource) -> None:
        """Test getting total hours in a range."""
        repo = ResourceCalendarRepository(db_session)

        # Create entries with varying hours
        await repo.create(
            {
                "resource_id": test_resource.id,
                "calendar_date": date(2024, 1, 1),
                "available_hours": Decimal("8.0"),
                "is_working_day": True,
            }
        )
        await repo.create(
            {
                "resource_id": test_resource.id,
                "calendar_date": date(2024, 1, 2),
                "available_hours": Decimal("4.0"),
                "is_working_day": True,
            }
        )
        await repo.create(
            {
                "resource_id": test_resource.id,
                "calendar_date": date(2024, 1, 3),
                "available_hours": Decimal("6.0"),
                "is_working_day": True,
            }
        )

        total = await repo.get_total_hours(test_resource.id, date(2024, 1, 1), date(2024, 1, 3))

        assert total == Decimal("18.0")

    async def test_delete_range(self, db_session: AsyncSession, test_resource: Resource) -> None:
        """Test deleting calendar entries in a range."""
        repo = ResourceCalendarRepository(db_session)

        # Create 10 days of entries
        for i in range(10):
            await repo.create(
                {
                    "resource_id": test_resource.id,
                    "calendar_date": date(2024, 1, 1) + timedelta(days=i),
                    "available_hours": Decimal("8.0"),
                    "is_working_day": True,
                }
            )

        # Delete middle 5 days
        deleted_count = await repo.delete_range(
            test_resource.id, date(2024, 1, 3), date(2024, 1, 7)
        )

        assert deleted_count == 5

        # Verify remaining entries
        remaining = await repo.get_for_date_range(
            test_resource.id, date(2024, 1, 1), date(2024, 1, 10)
        )
        assert len(remaining) == 5
