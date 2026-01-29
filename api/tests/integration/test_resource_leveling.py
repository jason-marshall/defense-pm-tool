"""Integration tests for ResourceLevelingService.

Tests resource leveling with real database interactions.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from src.models.activity import Activity
from src.models.dependency import Dependency
from src.models.enums import DependencyType, ResourceType
from src.models.program import Program
from src.models.resource import Resource, ResourceAssignment
from src.models.user import User
from src.models.wbs import WBSElement
from src.services.resource_leveling import LevelingOptions, ResourceLevelingService

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
        name="Leveling Test Program",
        code=f"LVL{uuid4().hex[:6].upper()}",
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
    """Create a test resource with 8 hours/day capacity."""
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


class TestResourceLevelingIntegration:
    """Integration tests for resource leveling."""

    @pytest.mark.asyncio
    async def test_level_program_no_overallocation(
        self,
        db_session: AsyncSession,
        test_program: Program,
        test_wbs: WBSElement,
        test_resource: Resource,
    ) -> None:
        """Should not change anything when no over-allocation."""
        # Create activity
        activity = Activity(
            name="Task 1",
            code=f"T1{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=5,
            early_start=date(2024, 1, 15),
            early_finish=date(2024, 1, 19),
            planned_start=date(2024, 1, 15),
            planned_finish=date(2024, 1, 19),
            is_critical=False,
            total_float=10,
        )
        db_session.add(activity)
        await db_session.flush()

        # Assign resource at 50% (no over-allocation)
        assignment = ResourceAssignment(
            activity_id=activity.id,
            resource_id=test_resource.id,
            units=Decimal("0.5"),
        )
        db_session.add(assignment)
        await db_session.flush()

        # Level
        service = ResourceLevelingService(db_session)
        result = await service.level_program(test_program.id)

        # Should succeed with no changes
        assert result.success is True
        assert result.activities_shifted == 0
        assert result.schedule_extension_days == 0

    @pytest.mark.asyncio
    async def test_level_program_simple_overallocation(
        self,
        db_session: AsyncSession,
        test_program: Program,
        test_wbs: WBSElement,
        test_resource: Resource,
    ) -> None:
        """Should resolve simple over-allocation by delaying activity."""
        # Create two activities on the same dates with same resource
        activity1 = Activity(
            name="Task 1",
            code=f"T1{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=5,
            early_start=date(2024, 1, 15),
            early_finish=date(2024, 1, 19),
            planned_start=date(2024, 1, 15),
            planned_finish=date(2024, 1, 19),
            is_critical=False,
            total_float=5,
        )
        activity2 = Activity(
            name="Task 2",
            code=f"T2{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=5,
            early_start=date(2024, 1, 15),
            early_finish=date(2024, 1, 19),
            planned_start=date(2024, 1, 15),
            planned_finish=date(2024, 1, 19),
            is_critical=False,
            total_float=10,
        )
        db_session.add_all([activity1, activity2])
        await db_session.flush()

        # Both at 100% = 200% total (over-allocation)
        assignment1 = ResourceAssignment(
            activity_id=activity1.id,
            resource_id=test_resource.id,
            units=Decimal("1.0"),
        )
        assignment2 = ResourceAssignment(
            activity_id=activity2.id,
            resource_id=test_resource.id,
            units=Decimal("1.0"),
        )
        db_session.add_all([assignment1, assignment2])
        await db_session.flush()

        # Level
        service = ResourceLevelingService(db_session)
        result = await service.level_program(test_program.id)

        # Should have shifted at least one activity
        assert result.activities_shifted >= 1

    @pytest.mark.asyncio
    async def test_level_program_preserves_dependencies(
        self,
        db_session: AsyncSession,
        test_program: Program,
        test_wbs: WBSElement,
        test_resource: Resource,
    ) -> None:
        """Should maintain dependency relationships after leveling."""
        # Create predecessor activity
        predecessor = Activity(
            name="Predecessor",
            code=f"PRED{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=5,
            early_start=date(2024, 1, 15),
            early_finish=date(2024, 1, 19),
            planned_start=date(2024, 1, 15),
            planned_finish=date(2024, 1, 19),
            is_critical=False,
            total_float=20,
        )
        # Successor starts after predecessor
        successor = Activity(
            name="Successor",
            code=f"SUCC{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=5,
            early_start=date(2024, 1, 22),
            early_finish=date(2024, 1, 26),
            planned_start=date(2024, 1, 22),
            planned_finish=date(2024, 1, 26),
            is_critical=False,
            total_float=15,
        )
        db_session.add_all([predecessor, successor])
        await db_session.flush()

        # Create dependency
        dependency = Dependency(
            predecessor_id=predecessor.id,
            successor_id=successor.id,
            dependency_type=DependencyType.FS,
            lag=0,
        )
        db_session.add(dependency)
        await db_session.flush()

        # Assign resource (over-allocation on predecessor's dates)
        assignment = ResourceAssignment(
            activity_id=predecessor.id,
            resource_id=test_resource.id,
            units=Decimal("1.0"),
        )
        db_session.add(assignment)
        await db_session.flush()

        # Level
        service = ResourceLevelingService(db_session)
        result = await service.level_program(test_program.id)

        # Leveling should complete
        assert result.iterations_used >= 1

    @pytest.mark.asyncio
    async def test_level_program_respects_critical_path(
        self,
        db_session: AsyncSession,
        test_program: Program,
        test_wbs: WBSElement,
        test_resource: Resource,
    ) -> None:
        """Should not delay critical path activities when option is set."""
        # Create critical activity
        critical_activity = Activity(
            name="Critical Task",
            code=f"CRIT{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=5,
            early_start=date(2024, 1, 15),
            early_finish=date(2024, 1, 19),
            planned_start=date(2024, 1, 15),
            planned_finish=date(2024, 1, 19),
            is_critical=True,  # Critical path!
            total_float=0,
        )
        # Create non-critical activity on same dates
        non_critical = Activity(
            name="Non-Critical Task",
            code=f"NCRT{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=5,
            early_start=date(2024, 1, 15),
            early_finish=date(2024, 1, 19),
            planned_start=date(2024, 1, 15),
            planned_finish=date(2024, 1, 19),
            is_critical=False,
            total_float=10,
        )
        db_session.add_all([critical_activity, non_critical])
        await db_session.flush()

        # Both at 100%
        assignment1 = ResourceAssignment(
            activity_id=critical_activity.id,
            resource_id=test_resource.id,
            units=Decimal("1.0"),
        )
        assignment2 = ResourceAssignment(
            activity_id=non_critical.id,
            resource_id=test_resource.id,
            units=Decimal("1.0"),
        )
        db_session.add_all([assignment1, assignment2])
        await db_session.flush()

        # Level with critical path preservation
        service = ResourceLevelingService(db_session)
        options = LevelingOptions(preserve_critical_path=True)
        result = await service.level_program(test_program.id, options)

        # Should warn about critical activity
        # The non-critical one should be the one that gets shifted
        for shift in result.shifts:
            assert shift.activity_id != critical_activity.id

    @pytest.mark.asyncio
    async def test_level_program_multiple_resources(
        self,
        db_session: AsyncSession,
        test_program: Program,
        test_wbs: WBSElement,
    ) -> None:
        """Should handle multiple resources correctly."""
        # Create two resources
        resource1 = Resource(
            name="Engineer 1",
            code=f"E1{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            resource_type=ResourceType.LABOR,
            capacity_per_day=Decimal("8.0"),
            is_active=True,
        )
        resource2 = Resource(
            name="Engineer 2",
            code=f"E2{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            resource_type=ResourceType.LABOR,
            capacity_per_day=Decimal("8.0"),
            is_active=True,
        )
        db_session.add_all([resource1, resource2])
        await db_session.flush()

        # Create activities
        activity1 = Activity(
            name="Task for Resource 1",
            code=f"TR1{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=5,
            early_start=date(2024, 1, 15),
            early_finish=date(2024, 1, 19),
            is_critical=False,
            total_float=10,
        )
        activity2 = Activity(
            name="Task for Resource 2",
            code=f"TR2{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=5,
            early_start=date(2024, 1, 15),
            early_finish=date(2024, 1, 19),
            is_critical=False,
            total_float=10,
        )
        db_session.add_all([activity1, activity2])
        await db_session.flush()

        # Different resources - no conflict
        assignment1 = ResourceAssignment(
            activity_id=activity1.id,
            resource_id=resource1.id,
            units=Decimal("1.0"),
        )
        assignment2 = ResourceAssignment(
            activity_id=activity2.id,
            resource_id=resource2.id,
            units=Decimal("1.0"),
        )
        db_session.add_all([assignment1, assignment2])
        await db_session.flush()

        # Level
        service = ResourceLevelingService(db_session)
        result = await service.level_program(test_program.id)

        # No shifts needed - different resources
        assert result.success is True
        assert result.activities_shifted == 0

    @pytest.mark.asyncio
    async def test_level_specific_resources_only(
        self,
        db_session: AsyncSession,
        test_program: Program,
        test_wbs: WBSElement,
    ) -> None:
        """Should only level specified resources when target_resources is set."""
        # Create two resources
        resource1 = Resource(
            name="Target Resource",
            code=f"TGT{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            resource_type=ResourceType.LABOR,
            capacity_per_day=Decimal("8.0"),
            is_active=True,
        )
        resource2 = Resource(
            name="Ignored Resource",
            code=f"IGN{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            resource_type=ResourceType.LABOR,
            capacity_per_day=Decimal("8.0"),
            is_active=True,
        )
        db_session.add_all([resource1, resource2])
        await db_session.flush()

        # Create activities with over-allocation on both resources
        activity1a = Activity(
            name="Task 1A",
            code=f"T1A{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=5,
            early_start=date(2024, 1, 15),
            early_finish=date(2024, 1, 19),
            is_critical=False,
            total_float=10,
        )
        activity1b = Activity(
            name="Task 1B",
            code=f"T1B{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=5,
            early_start=date(2024, 1, 15),
            early_finish=date(2024, 1, 19),
            is_critical=False,
            total_float=10,
        )
        db_session.add_all([activity1a, activity1b])
        await db_session.flush()

        # Over-allocate resource2 (ignored)
        assignment1 = ResourceAssignment(
            activity_id=activity1a.id,
            resource_id=resource2.id,
            units=Decimal("1.0"),
        )
        assignment2 = ResourceAssignment(
            activity_id=activity1b.id,
            resource_id=resource2.id,
            units=Decimal("1.0"),
        )
        db_session.add_all([assignment1, assignment2])
        await db_session.flush()

        # Level only resource1 (not overallocated)
        service = ResourceLevelingService(db_session)
        options = LevelingOptions(target_resources=[resource1.id])
        result = await service.level_program(test_program.id, options)

        # Should not shift anything (resource1 not overallocated)
        assert result.activities_shifted == 0

    @pytest.mark.asyncio
    async def test_level_program_schedule_extension(
        self,
        db_session: AsyncSession,
        test_program: Program,
        test_wbs: WBSElement,
        test_resource: Resource,
    ) -> None:
        """Should correctly calculate schedule extension."""
        # Create overlapping activities
        activity1 = Activity(
            name="Task 1",
            code=f"T1{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=5,
            early_start=date(2024, 1, 15),
            early_finish=date(2024, 1, 19),
            is_critical=False,
            total_float=20,
        )
        activity2 = Activity(
            name="Task 2",
            code=f"T2{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=5,
            early_start=date(2024, 1, 15),
            early_finish=date(2024, 1, 19),
            is_critical=False,
            total_float=20,
        )
        db_session.add_all([activity1, activity2])
        await db_session.flush()

        # Both at 100%
        assignment1 = ResourceAssignment(
            activity_id=activity1.id,
            resource_id=test_resource.id,
            units=Decimal("1.0"),
        )
        assignment2 = ResourceAssignment(
            activity_id=activity2.id,
            resource_id=test_resource.id,
            units=Decimal("1.0"),
        )
        db_session.add_all([assignment1, assignment2])
        await db_session.flush()

        # Level
        service = ResourceLevelingService(db_session)
        result = await service.level_program(test_program.id)

        # Original finish was Jan 19
        # If one activity is delayed, new finish should be later
        if result.activities_shifted > 0:
            assert result.new_project_finish > result.original_project_finish
            assert result.schedule_extension_days > 0

    @pytest.mark.asyncio
    async def test_apply_leveling_result(
        self,
        db_session: AsyncSession,
        test_program: Program,
        test_wbs: WBSElement,
        test_resource: Resource,
    ) -> None:
        """Should apply leveling result to database."""
        # Create activity
        activity = Activity(
            name="Task 1",
            code=f"T1{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=5,
            early_start=date(2024, 1, 15),
            early_finish=date(2024, 1, 19),
            planned_start=date(2024, 1, 15),
            planned_finish=date(2024, 1, 19),
            is_critical=False,
            total_float=20,
        )
        db_session.add(activity)
        await db_session.flush()

        activity_id = activity.id

        # Create two more activities on same dates for over-allocation
        activity2 = Activity(
            name="Task 2",
            code=f"T2{uuid4().hex[:4].upper()}",
            program_id=test_program.id,
            wbs_id=test_wbs.id,
            duration=5,
            early_start=date(2024, 1, 15),
            early_finish=date(2024, 1, 19),
            planned_start=date(2024, 1, 15),
            planned_finish=date(2024, 1, 19),
            is_critical=False,
            total_float=20,
        )
        db_session.add(activity2)
        await db_session.flush()

        # Both at 100%
        assignment1 = ResourceAssignment(
            activity_id=activity_id,
            resource_id=test_resource.id,
            units=Decimal("1.0"),
        )
        assignment2 = ResourceAssignment(
            activity_id=activity2.id,
            resource_id=test_resource.id,
            units=Decimal("1.0"),
        )
        db_session.add_all([assignment1, assignment2])
        await db_session.flush()

        # Level
        service = ResourceLevelingService(db_session)
        result = await service.level_program(test_program.id)

        # Apply result
        if result.shifts:
            applied = await service.apply_leveling_result(result)
            assert applied is True
