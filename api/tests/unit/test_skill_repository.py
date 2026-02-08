"""Tests for Skill, ResourceSkill, and SkillRequirement repositories."""

from datetime import date
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import Activity
from src.models.enums import ResourceType
from src.models.program import Program
from src.models.resource import Resource
from src.models.skill import ResourceSkill, Skill, SkillRequirement
from src.models.user import User
from src.models.wbs import WBSElement
from src.repositories.skill import (
    ResourceSkillRepository,
    SkillRepository,
    SkillRequirementRepository,
)


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user for ownership."""
    u = User(
        id=uuid4(),
        email="repo-test@example.com",
        hashed_password="hashed",
        full_name="Repo Test",
        is_active=True,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def program(db_session: AsyncSession, test_user: User) -> Program:
    """Create test program."""
    p = Program(
        id=uuid4(),
        name="Test Program",
        code="TP-001",
        owner_id=test_user.id,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture
async def wbs_element(db_session: AsyncSession, program: Program) -> WBSElement:
    """Create test WBS element."""
    w = WBSElement(
        id=uuid4(),
        program_id=program.id,
        name="Test WBS",
        wbs_code="1",
        path="1",
        level=1,
    )
    db_session.add(w)
    await db_session.flush()
    return w


@pytest_asyncio.fixture
async def global_skill(db_session: AsyncSession) -> Skill:
    """Create a global skill."""
    s = Skill(
        id=uuid4(),
        name="Python Programming",
        code="PYTHON",
        category="Technical",
        is_active=True,
        requires_certification=False,
        program_id=None,
    )
    db_session.add(s)
    await db_session.flush()
    return s


@pytest_asyncio.fixture
async def program_skill(db_session: AsyncSession, program: Program) -> Skill:
    """Create a program-specific skill."""
    s = Skill(
        id=uuid4(),
        name="Systems Engineering",
        code="SYS-ENG",
        category="Technical",
        is_active=True,
        requires_certification=False,
        program_id=program.id,
    )
    db_session.add(s)
    await db_session.flush()
    return s


@pytest_asyncio.fixture
async def resource(db_session: AsyncSession, program: Program) -> Resource:
    """Create test resource."""
    r = Resource(
        id=uuid4(),
        program_id=program.id,
        name="John Doe",
        code="JD-001",
        resource_type=ResourceType.LABOR,
    )
    db_session.add(r)
    await db_session.flush()
    return r


@pytest_asyncio.fixture
async def activity(db_session: AsyncSession, program: Program, wbs_element: WBSElement) -> Activity:
    """Create test activity."""
    a = Activity(
        id=uuid4(),
        program_id=program.id,
        wbs_id=wbs_element.id,
        name="Test Activity",
        code="ACT-001",
        duration=10,
    )
    db_session.add(a)
    await db_session.flush()
    return a


class TestSkillRepository:
    """Tests for SkillRepository."""

    @pytest.mark.asyncio
    async def test_create_skill(self, db_session: AsyncSession, program: Program) -> None:
        """Should create a skill."""
        repo = SkillRepository(db_session)
        skill = await repo.create(
            {
                "name": "New Skill",
                "code": "NEW-001",
                "category": "Technical",
                "program_id": program.id,
            }
        )
        assert skill.name == "New Skill"
        assert skill.code == "NEW-001"

    @pytest.mark.asyncio
    async def test_get_by_program_includes_global(
        self,
        db_session: AsyncSession,
        program: Program,
        global_skill: Skill,
        program_skill: Skill,
    ) -> None:
        """Should include both global and program-specific skills."""
        repo = SkillRepository(db_session)
        items, total = await repo.get_by_program(program.id)
        assert total >= 2
        codes = {s.code for s in items}
        assert "PYTHON" in codes  # global
        assert "SYS-ENG" in codes  # program-specific

    @pytest.mark.asyncio
    async def test_get_by_program_none_returns_global_only(
        self,
        db_session: AsyncSession,
        global_skill: Skill,
        program_skill: Skill,
    ) -> None:
        """Should return only global skills when program_id is None."""
        repo = SkillRepository(db_session)
        items, _total = await repo.get_by_program(None)
        codes = {s.code for s in items}
        assert "PYTHON" in codes
        assert "SYS-ENG" not in codes

    @pytest.mark.asyncio
    async def test_get_by_program_filter_category(
        self,
        db_session: AsyncSession,
        program: Program,
        global_skill: Skill,
    ) -> None:
        """Should filter by category."""
        # Create a Management skill
        mgmt = Skill(
            id=uuid4(),
            name="Leadership",
            code="LEAD",
            category="Management",
            program_id=program.id,
        )
        db_session.add(mgmt)
        await db_session.flush()

        repo = SkillRepository(db_session)
        items, _total = await repo.get_by_program(program.id, category="Management")
        assert all(s.category == "Management" for s in items)

    @pytest.mark.asyncio
    async def test_get_by_code(
        self,
        db_session: AsyncSession,
        global_skill: Skill,
    ) -> None:
        """Should find skill by code."""
        repo = SkillRepository(db_session)
        found = await repo.get_by_code("python")  # case-insensitive
        assert found is not None
        assert found.id == global_skill.id

    @pytest.mark.asyncio
    async def test_get_by_code_not_found(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Should return None for unknown code."""
        repo = SkillRepository(db_session)
        found = await repo.get_by_code("NONEXISTENT")
        assert found is None

    @pytest.mark.asyncio
    async def test_code_exists(
        self,
        db_session: AsyncSession,
        global_skill: Skill,
    ) -> None:
        """Should detect existing code."""
        repo = SkillRepository(db_session)
        assert await repo.code_exists("PYTHON") is True
        assert await repo.code_exists("NONEXISTENT") is False

    @pytest.mark.asyncio
    async def test_code_exists_exclude_id(
        self,
        db_session: AsyncSession,
        global_skill: Skill,
    ) -> None:
        """Should exclude specific ID from check."""
        repo = SkillRepository(db_session)
        assert await repo.code_exists("PYTHON", exclude_id=global_skill.id) is False

    @pytest.mark.asyncio
    async def test_soft_delete_skill(
        self,
        db_session: AsyncSession,
        global_skill: Skill,
    ) -> None:
        """Should soft-delete skill."""
        repo = SkillRepository(db_session)
        await repo.delete(global_skill.id)
        await db_session.flush()

        found = await repo.get_by_id(global_skill.id)
        assert found is None

        # Should find with include_deleted
        found = await repo.get_by_id(global_skill.id, include_deleted=True)
        assert found is not None


class TestResourceSkillRepository:
    """Tests for ResourceSkillRepository."""

    @pytest.mark.asyncio
    async def test_create_resource_skill(
        self,
        db_session: AsyncSession,
        resource: Resource,
        global_skill: Skill,
    ) -> None:
        """Should assign skill to resource."""
        repo = ResourceSkillRepository(db_session)
        rs = await repo.create(
            {
                "resource_id": resource.id,
                "skill_id": global_skill.id,
                "proficiency_level": 3,
            }
        )
        assert rs.proficiency_level == 3

    @pytest.mark.asyncio
    async def test_get_by_resource(
        self,
        db_session: AsyncSession,
        resource: Resource,
        global_skill: Skill,
    ) -> None:
        """Should get all skills for a resource."""
        rs = ResourceSkill(
            id=uuid4(),
            resource_id=resource.id,
            skill_id=global_skill.id,
            proficiency_level=4,
        )
        db_session.add(rs)
        await db_session.flush()

        repo = ResourceSkillRepository(db_session)
        items = await repo.get_by_resource(resource.id)
        assert len(items) == 1
        assert items[0].proficiency_level == 4

    @pytest.mark.asyncio
    async def test_get_by_skill(
        self,
        db_session: AsyncSession,
        resource: Resource,
        global_skill: Skill,
    ) -> None:
        """Should get all resources with a skill."""
        rs = ResourceSkill(
            id=uuid4(),
            resource_id=resource.id,
            skill_id=global_skill.id,
            proficiency_level=3,
        )
        db_session.add(rs)
        await db_session.flush()

        repo = ResourceSkillRepository(db_session)
        items = await repo.get_by_skill(global_skill.id)
        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_find_matching_resources(
        self,
        db_session: AsyncSession,
        program: Program,
        global_skill: Skill,
    ) -> None:
        """Should find resources matching minimum level."""
        # Create two resources with different levels
        r1 = Resource(
            id=uuid4(),
            program_id=program.id,
            name="Expert",
            code="R-EXP",
            resource_type=ResourceType.LABOR,
        )
        r2 = Resource(
            id=uuid4(),
            program_id=program.id,
            name="Novice",
            code="R-NOV",
            resource_type=ResourceType.LABOR,
        )
        db_session.add_all([r1, r2])
        await db_session.flush()

        rs1 = ResourceSkill(
            id=uuid4(),
            resource_id=r1.id,
            skill_id=global_skill.id,
            proficiency_level=5,
        )
        rs2 = ResourceSkill(
            id=uuid4(),
            resource_id=r2.id,
            skill_id=global_skill.id,
            proficiency_level=2,
        )
        db_session.add_all([rs1, rs2])
        await db_session.flush()

        repo = ResourceSkillRepository(db_session)
        matches = await repo.find_matching_resources(global_skill.id, min_level=3)
        assert len(matches) == 1
        assert matches[0].resource_id == r1.id

    @pytest.mark.asyncio
    async def test_find_matching_certified_only(
        self,
        db_session: AsyncSession,
        resource: Resource,
        global_skill: Skill,
    ) -> None:
        """Should filter by certified_only."""
        rs = ResourceSkill(
            id=uuid4(),
            resource_id=resource.id,
            skill_id=global_skill.id,
            proficiency_level=3,
            is_certified=False,
        )
        db_session.add(rs)
        await db_session.flush()

        repo = ResourceSkillRepository(db_session)
        matches = await repo.find_matching_resources(global_skill.id, certified_only=True)
        assert len(matches) == 0

    @pytest.mark.asyncio
    async def test_assignment_exists(
        self,
        db_session: AsyncSession,
        resource: Resource,
        global_skill: Skill,
    ) -> None:
        """Should detect existing assignment."""
        rs = ResourceSkill(
            id=uuid4(),
            resource_id=resource.id,
            skill_id=global_skill.id,
            proficiency_level=3,
        )
        db_session.add(rs)
        await db_session.flush()

        repo = ResourceSkillRepository(db_session)
        assert await repo.assignment_exists(resource.id, global_skill.id) is True
        assert await repo.assignment_exists(resource.id, uuid4()) is False

    @pytest.mark.asyncio
    async def test_get_certified_resources(
        self,
        db_session: AsyncSession,
        resource: Resource,
        global_skill: Skill,
    ) -> None:
        """Should return only certified resources."""
        rs = ResourceSkill(
            id=uuid4(),
            resource_id=resource.id,
            skill_id=global_skill.id,
            proficiency_level=5,
            is_certified=True,
        )
        db_session.add(rs)
        await db_session.flush()

        repo = ResourceSkillRepository(db_session)
        certified = await repo.get_certified_resources(global_skill.id)
        assert len(certified) == 1
        assert certified[0].is_certified is True


class TestSkillRequirementRepository:
    """Tests for SkillRequirementRepository."""

    @pytest.mark.asyncio
    async def test_create_requirement(
        self,
        db_session: AsyncSession,
        activity: Activity,
        global_skill: Skill,
    ) -> None:
        """Should create skill requirement."""
        repo = SkillRequirementRepository(db_session)
        sr = await repo.create(
            {
                "activity_id": activity.id,
                "skill_id": global_skill.id,
                "required_level": 3,
                "is_mandatory": True,
            }
        )
        assert sr.required_level == 3
        assert sr.is_mandatory is True

    @pytest.mark.asyncio
    async def test_get_by_activity(
        self,
        db_session: AsyncSession,
        activity: Activity,
        global_skill: Skill,
    ) -> None:
        """Should get all requirements for an activity."""
        sr = SkillRequirement(
            id=uuid4(),
            activity_id=activity.id,
            skill_id=global_skill.id,
            required_level=2,
        )
        db_session.add(sr)
        await db_session.flush()

        repo = SkillRequirementRepository(db_session)
        items = await repo.get_by_activity(activity.id)
        assert len(items) == 1
        assert items[0].required_level == 2

    @pytest.mark.asyncio
    async def test_requirement_exists(
        self,
        db_session: AsyncSession,
        activity: Activity,
        global_skill: Skill,
    ) -> None:
        """Should detect existing requirement."""
        sr = SkillRequirement(
            id=uuid4(),
            activity_id=activity.id,
            skill_id=global_skill.id,
            required_level=3,
        )
        db_session.add(sr)
        await db_session.flush()

        repo = SkillRequirementRepository(db_session)
        assert await repo.requirement_exists(activity.id, global_skill.id) is True
        assert await repo.requirement_exists(activity.id, uuid4()) is False

    @pytest.mark.asyncio
    async def test_soft_delete_requirement(
        self,
        db_session: AsyncSession,
        activity: Activity,
        global_skill: Skill,
    ) -> None:
        """Should soft-delete requirement."""
        sr = SkillRequirement(
            id=uuid4(),
            activity_id=activity.id,
            skill_id=global_skill.id,
            required_level=3,
        )
        db_session.add(sr)
        await db_session.flush()

        repo = SkillRequirementRepository(db_session)
        await repo.delete(sr.id)
        await db_session.flush()

        items = await repo.get_by_activity(activity.id)
        assert len(items) == 0
