"""Integration tests for ResourceLoadingService.

Tests the resource loading calculations with actual database interactions.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from src.models.activity import Activity
from src.models.enums import ResourceType
from src.models.program import Program
from src.models.resource import Resource, ResourceAssignment, ResourceCalendar
from src.models.user import User
from src.models.wbs import WBSElement
from src.services.resource_loading import ResourceLoadingService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email=f"test_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def test_program(db_session: AsyncSession, test_user: User) -> Program:
    """Create a test program."""
    program = Program(
        name="Test Program",
        code=f"TP{uuid4().hex[:6].upper()}",
        owner_id=test_user.id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )
    db_session.add(program)
    await db_session.flush()
    return program


@pytest.fixture
async def test_wbs(db_session: AsyncSession, test_program: Program) -> WBSElement:
    """Create a test WBS element."""
    wbs = WBSElement(
        program_id=test_program.id,
        name="Test Work Package",
        wbs_code=f"1.{uuid4().hex[:4].upper()}",
        path="1",
        level=1,
    )
    db_session.add(wbs)
    await db_session.flush()
    return wbs


@pytest.fixture
async def test_resource(db_session: AsyncSession, test_program: Program) -> Resource:
    """Create a test resource."""
    resource = Resource(
        name="Test Engineer",
        code=f"ENG{uuid4().hex[:6].upper()}",
        program_id=test_program.id,
        resource_type=ResourceType.LABOR,
        capacity_per_day=Decimal("8.0"),
        is_active=True,
    )
    db_session.add(resource)
    await db_session.flush()
    return resource


@pytest.fixture
async def test_activity(
    db_session: AsyncSession, test_program: Program, test_wbs: WBSElement
) -> Activity:
    """Create a test activity."""
    activity = Activity(
        name="Test Activity",
        wbs_id=test_wbs.id,
        code=f"ACT{uuid4().hex[:6].upper()}",
        program_id=test_program.id,
        duration=5,
        planned_start=date(2024, 1, 15),
        planned_finish=date(2024, 1, 19),
        early_start=date(2024, 1, 10),
        early_finish=date(2024, 1, 14),
    )
    db_session.add(activity)
    await db_session.flush()
    return activity


class TestResourceLoadingServiceIntegration:
    """Integration tests for ResourceLoadingService."""

    @pytest.mark.asyncio
    async def test_calculate_daily_loading_with_assignment(
        self,
        db_session: AsyncSession,
        test_resource: Resource,
        test_activity: Activity,
    ) -> None:
        """Should calculate loading for resource with assignment."""
        # Arrange
        assignment = ResourceAssignment(
            activity_id=test_activity.id,
            resource_id=test_resource.id,
            units=Decimal("1.0"),
            start_date=None,  # Should use activity.planned_start
            finish_date=None,  # Should use activity.planned_finish
        )
        db_session.add(assignment)
        await db_session.flush()

        service = ResourceLoadingService(db_session)

        # Act
        result = await service.calculate_daily_loading(
            test_resource.id,
            date(2024, 1, 15),
            date(2024, 1, 19),
        )

        # Assert
        assert len(result) == 5
        for day_date, loading in result.items():
            if day_date.weekday() < 5:  # Weekdays
                assert loading.assigned_hours == Decimal("8.00")
                assert loading.available_hours == Decimal("8.0")
            else:  # Weekends
                assert loading.available_hours == Decimal("0")

    @pytest.mark.asyncio
    async def test_calculate_loading_uses_activity_planned_dates(
        self,
        db_session: AsyncSession,
        test_resource: Resource,
        test_activity: Activity,
    ) -> None:
        """Should use activity planned dates when assignment dates not set."""
        # Arrange
        assignment = ResourceAssignment(
            activity_id=test_activity.id,
            resource_id=test_resource.id,
            units=Decimal("1.0"),
            start_date=None,
            finish_date=None,
        )
        db_session.add(assignment)
        await db_session.flush()

        service = ResourceLoadingService(db_session)

        # Act - Query range that includes before and after activity dates
        result = await service.calculate_daily_loading(
            test_resource.id,
            date(2024, 1, 10),  # Before activity planned_start
            date(2024, 1, 25),  # After activity planned_finish
        )

        # Assert
        # Before planned_start (Jan 10-14) - no assignment active
        for day in range(10, 15):
            d = date(2024, 1, day)
            if d.weekday() < 5:
                assert result[d].assigned_hours == Decimal("0")

        # During planned dates (Jan 15-19) - assignment active
        for day in range(15, 20):
            d = date(2024, 1, day)
            if d.weekday() < 5:
                assert result[d].assigned_hours == Decimal("8.00")

        # After planned_finish (Jan 20-25) - no assignment active
        for day in range(20, 26):
            d = date(2024, 1, day)
            if d in result and d.weekday() < 5:
                assert result[d].assigned_hours == Decimal("0")

    @pytest.mark.asyncio
    async def test_calculate_loading_with_explicit_assignment_dates(
        self,
        db_session: AsyncSession,
        test_resource: Resource,
        test_activity: Activity,
    ) -> None:
        """Should use explicit assignment dates when set."""
        # Arrange - Assignment dates override activity dates
        assignment = ResourceAssignment(
            activity_id=test_activity.id,
            resource_id=test_resource.id,
            units=Decimal("1.0"),
            start_date=date(2024, 1, 8),  # Different from activity
            finish_date=date(2024, 1, 10),  # Different from activity
        )
        db_session.add(assignment)
        await db_session.flush()

        service = ResourceLoadingService(db_session)

        # Act
        result = await service.calculate_daily_loading(
            test_resource.id,
            date(2024, 1, 8),
            date(2024, 1, 19),
        )

        # Assert - Should be active Jan 8-10 only
        assert result[date(2024, 1, 8)].assigned_hours == Decimal("8.00")
        assert result[date(2024, 1, 9)].assigned_hours == Decimal("8.00")
        assert result[date(2024, 1, 10)].assigned_hours == Decimal("8.00")
        assert result[date(2024, 1, 11)].assigned_hours == Decimal("0")

    @pytest.mark.asyncio
    async def test_calculate_loading_with_calendar_entries(
        self,
        db_session: AsyncSession,
        test_resource: Resource,
        test_activity: Activity,
    ) -> None:
        """Should respect calendar entries for availability."""
        # Arrange
        assignment = ResourceAssignment(
            activity_id=test_activity.id,
            resource_id=test_resource.id,
            units=Decimal("1.0"),
            start_date=date(2024, 1, 15),
            finish_date=date(2024, 1, 17),
        )
        db_session.add(assignment)

        # Add calendar entry for Jan 16 - half day
        calendar_entry = ResourceCalendar(
            resource_id=test_resource.id,
            calendar_date=date(2024, 1, 16),
            available_hours=Decimal("4.0"),
            is_working_day=True,
        )
        db_session.add(calendar_entry)
        await db_session.flush()

        service = ResourceLoadingService(db_session)

        # Act
        result = await service.calculate_daily_loading(
            test_resource.id,
            date(2024, 1, 15),
            date(2024, 1, 17),
        )

        # Assert
        assert result[date(2024, 1, 15)].available_hours == Decimal("8.0")  # Default
        assert result[date(2024, 1, 16)].available_hours == Decimal("4.0")  # Calendar
        assert result[date(2024, 1, 17)].available_hours == Decimal("8.0")  # Default

    @pytest.mark.asyncio
    async def test_calculate_loading_with_non_working_day(
        self,
        db_session: AsyncSession,
        test_resource: Resource,
        test_activity: Activity,
    ) -> None:
        """Should show zero availability for non-working days in calendar."""
        # Arrange
        assignment = ResourceAssignment(
            activity_id=test_activity.id,
            resource_id=test_resource.id,
            units=Decimal("1.0"),
            start_date=date(2024, 1, 15),
            finish_date=date(2024, 1, 17),
        )
        db_session.add(assignment)

        # Add calendar entry for Jan 16 - holiday
        calendar_entry = ResourceCalendar(
            resource_id=test_resource.id,
            calendar_date=date(2024, 1, 16),
            available_hours=Decimal("0.0"),
            is_working_day=False,
        )
        db_session.add(calendar_entry)
        await db_session.flush()

        service = ResourceLoadingService(db_session)

        # Act
        result = await service.calculate_daily_loading(
            test_resource.id,
            date(2024, 1, 15),
            date(2024, 1, 17),
        )

        # Assert
        assert result[date(2024, 1, 16)].available_hours == Decimal("0")
        assert result[date(2024, 1, 16)].is_overallocated is True  # 8 assigned, 0 available

    @pytest.mark.asyncio
    async def test_get_overallocated_dates(
        self,
        db_session: AsyncSession,
        test_resource: Resource,
        test_activity: Activity,
    ) -> None:
        """Should return dates where resource is overallocated."""
        # Arrange - 150% allocation
        assignment = ResourceAssignment(
            activity_id=test_activity.id,
            resource_id=test_resource.id,
            units=Decimal("1.5"),  # 150%
            start_date=date(2024, 1, 15),
            finish_date=date(2024, 1, 17),
        )
        db_session.add(assignment)
        await db_session.flush()

        service = ResourceLoadingService(db_session)

        # Act
        result = await service.get_overallocated_dates(
            test_resource.id,
            date(2024, 1, 15),
            date(2024, 1, 17),
        )

        # Assert - All weekdays should be overallocated
        # Jan 15, 16, 17 are Mon, Tue, Wed
        assert date(2024, 1, 15) in result
        assert date(2024, 1, 16) in result
        assert date(2024, 1, 17) in result

    @pytest.mark.asyncio
    async def test_multiple_assignments_aggregate(
        self,
        db_session: AsyncSession,
        test_program: Program,
        test_resource: Resource,
        test_wbs: WBSElement,
    ) -> None:
        """Should aggregate hours from multiple assignments."""
        # Arrange
        activity1 = Activity(
            name="Activity 1",
            code=f"ACT1{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=3,
            planned_start=date(2024, 1, 15),
            planned_finish=date(2024, 1, 17),
        )
        activity2 = Activity(
            name="Activity 2",
            code=f"ACT2{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=3,
            planned_start=date(2024, 1, 16),
            planned_finish=date(2024, 1, 18),
        )
        db_session.add_all([activity1, activity2])
        await db_session.flush()

        # 50% on each activity
        assignment1 = ResourceAssignment(
            activity_id=activity1.id,
            resource_id=test_resource.id,
            units=Decimal("0.5"),
            start_date=None,
            finish_date=None,
        )
        assignment2 = ResourceAssignment(
            activity_id=activity2.id,
            resource_id=test_resource.id,
            units=Decimal("0.5"),
            start_date=None,
            finish_date=None,
        )
        db_session.add_all([assignment1, assignment2])
        await db_session.flush()

        service = ResourceLoadingService(db_session)

        # Act
        result = await service.calculate_daily_loading(
            test_resource.id,
            date(2024, 1, 15),
            date(2024, 1, 18),
        )

        # Assert
        # Jan 15: only activity1 (0.5 * 8 = 4)
        assert result[date(2024, 1, 15)].assigned_hours == Decimal("4.00")
        # Jan 16: both (0.5 * 8 + 0.5 * 8 = 8)
        assert result[date(2024, 1, 16)].assigned_hours == Decimal("8.00")
        # Jan 17: both
        assert result[date(2024, 1, 17)].assigned_hours == Decimal("8.00")
        # Jan 18: only activity2 (0.5 * 8 = 4)
        assert result[date(2024, 1, 18)].assigned_hours == Decimal("4.00")

    @pytest.mark.asyncio
    async def test_aggregate_program_loading(
        self,
        db_session: AsyncSession,
        test_program: Program,
    ) -> None:
        """Should aggregate loading for all resources in a program."""
        # Arrange
        resource1 = Resource(
            name="Engineer 1",
            code=f"ENG1{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            resource_type=ResourceType.LABOR,
            capacity_per_day=Decimal("8.0"),
            is_active=True,
        )
        resource2 = Resource(
            name="Engineer 2",
            code=f"ENG2{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            resource_type=ResourceType.LABOR,
            capacity_per_day=Decimal("8.0"),
            is_active=True,
        )
        db_session.add_all([resource1, resource2])
        await db_session.flush()

        service = ResourceLoadingService(db_session)

        # Act
        result = await service.aggregate_program_loading(
            test_program.id,
            date(2024, 1, 15),
            date(2024, 1, 17),
        )

        # Assert
        assert len(result) == 2
        assert resource1.id in result
        assert resource2.id in result

    @pytest.mark.asyncio
    async def test_aggregate_program_loading_filter_by_type(
        self,
        db_session: AsyncSession,
        test_program: Program,
    ) -> None:
        """Should filter resources by type when specified."""
        # Arrange
        labor_resource = Resource(
            name="Engineer",
            code=f"ENG{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            resource_type=ResourceType.LABOR,
            capacity_per_day=Decimal("8.0"),
            is_active=True,
        )
        equipment_resource = Resource(
            name="Excavator",
            code=f"EXC{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            resource_type=ResourceType.EQUIPMENT,
            capacity_per_day=Decimal("10.0"),
            is_active=True,
        )
        db_session.add_all([labor_resource, equipment_resource])
        await db_session.flush()

        service = ResourceLoadingService(db_session)

        # Act - Filter to LABOR only
        result = await service.aggregate_program_loading(
            test_program.id,
            date(2024, 1, 15),
            date(2024, 1, 17),
            resource_type=ResourceType.LABOR,
        )

        # Assert
        assert len(result) == 1
        assert labor_resource.id in result
        assert equipment_resource.id not in result

    @pytest.mark.asyncio
    async def test_get_program_overallocation_summary(
        self,
        db_session: AsyncSession,
        test_program: Program,
        test_wbs: WBSElement,
    ) -> None:
        """Should return summary of overallocated resources."""
        # Arrange
        resource1 = Resource(
            name="Overallocated Engineer",
            code=f"OVR{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            resource_type=ResourceType.LABOR,
            capacity_per_day=Decimal("8.0"),
            is_active=True,
        )
        resource2 = Resource(
            name="Normal Engineer",
            code=f"NRM{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            resource_type=ResourceType.LABOR,
            capacity_per_day=Decimal("8.0"),
            is_active=True,
        )
        db_session.add_all([resource1, resource2])
        await db_session.flush()

        activity = Activity(
            name="Task",
            code=f"TSK{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=3,
            planned_start=date(2024, 1, 15),
            planned_finish=date(2024, 1, 17),
        )
        db_session.add(activity)
        await db_session.flush()

        # Overallocate resource1
        assignment1 = ResourceAssignment(
            activity_id=activity.id,
            resource_id=resource1.id,
            units=Decimal("1.5"),  # 150%
            start_date=None,
            finish_date=None,
        )
        # Normal allocation for resource2
        assignment2 = ResourceAssignment(
            activity_id=activity.id,
            resource_id=resource2.id,
            units=Decimal("0.5"),  # 50%
            start_date=None,
            finish_date=None,
        )
        db_session.add_all([assignment1, assignment2])
        await db_session.flush()

        service = ResourceLoadingService(db_session)

        # Act
        result = await service.get_program_overallocation_summary(
            test_program.id,
            date(2024, 1, 15),
            date(2024, 1, 17),
        )

        # Assert
        assert resource1.id in result  # Overallocated
        assert resource2.id not in result  # Not overallocated
        assert len(result[resource1.id]) == 3  # All 3 days overallocated

    @pytest.mark.asyncio
    async def test_nonexistent_resource_returns_empty(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Should return empty dict for nonexistent resource."""
        service = ResourceLoadingService(db_session)

        result = await service.calculate_daily_loading(
            uuid4(),
            date(2024, 1, 1),
            date(2024, 1, 5),
        )

        assert result == {}
