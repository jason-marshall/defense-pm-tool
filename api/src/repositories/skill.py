"""Repository layer for Skill, ResourceSkill, and SkillRequirement."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.models.skill import ResourceSkill, Skill, SkillRequirement
from src.repositories.base import BaseRepository


class SkillRepository(BaseRepository[Skill]):
    """Repository for Skill model operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with Skill model."""
        super().__init__(Skill, session)

    async def get_by_program(
        self,
        program_id: UUID | None,
        *,
        category: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Skill], int]:
        """
        Get skills for a program (or global skills if program_id is None).

        Args:
            program_id: Program UUID or None for global skills
            category: Filter by category
            is_active: Filter by active status
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of skills, total count)
        """
        query = select(Skill)
        if program_id is not None:
            # Include both program-specific and global skills
            query = query.where((Skill.program_id == program_id) | (Skill.program_id.is_(None)))
        else:
            query = query.where(Skill.program_id.is_(None))

        query = self._apply_soft_delete_filter(query)

        if category is not None:
            query = query.where(Skill.category == category)
        if is_active is not None:
            query = query.where(Skill.is_active == is_active)

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        query = query.order_by(Skill.code).offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_code(
        self,
        code: str,
        program_id: UUID | None = None,
    ) -> Skill | None:
        """
        Get a skill by code within a program scope.

        Args:
            code: Skill code (case-insensitive)
            program_id: Program UUID or None for global

        Returns:
            Skill if found, None otherwise
        """
        query = select(Skill).where(func.upper(Skill.code) == code.upper())

        if program_id is not None:
            query = query.where((Skill.program_id == program_id) | (Skill.program_id.is_(None)))
        else:
            query = query.where(Skill.program_id.is_(None))

        query = self._apply_soft_delete_filter(query)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def code_exists(
        self,
        code: str,
        program_id: UUID | None = None,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if a skill code exists within the scope."""
        query = (
            select(func.count()).select_from(Skill).where(func.upper(Skill.code) == code.upper())
        )

        if program_id is not None:
            query = query.where(Skill.program_id == program_id)
        else:
            query = query.where(Skill.program_id.is_(None))

        query = self._apply_soft_delete_filter(query)

        if exclude_id is not None:
            query = query.where(Skill.id != exclude_id)

        result = await self.session.execute(query)
        count: int = result.scalar_one()
        return count > 0


class ResourceSkillRepository(BaseRepository[ResourceSkill]):
    """Repository for ResourceSkill model operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with ResourceSkill model."""
        super().__init__(ResourceSkill, session)

    async def get_by_resource(
        self,
        resource_id: UUID,
    ) -> list[ResourceSkill]:
        """
        Get all skills for a resource with skill eagerly loaded.

        Args:
            resource_id: Resource UUID

        Returns:
            List of resource skills with skill details
        """
        query = (
            select(ResourceSkill)
            .where(ResourceSkill.resource_id == resource_id)
            .options(joinedload(ResourceSkill.skill))
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return list(result.unique().scalars().all())

    async def get_by_skill(
        self,
        skill_id: UUID,
    ) -> list[ResourceSkill]:
        """
        Get all resources that have a specific skill.

        Args:
            skill_id: Skill UUID

        Returns:
            List of resource skills
        """
        query = (
            select(ResourceSkill)
            .where(ResourceSkill.skill_id == skill_id)
            .options(joinedload(ResourceSkill.resource))
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return list(result.unique().scalars().all())

    async def find_matching_resources(
        self,
        skill_id: UUID,
        min_level: int = 1,
        *,
        certified_only: bool = False,
    ) -> list[ResourceSkill]:
        """
        Find resources matching a skill requirement.

        Args:
            skill_id: Required skill UUID
            min_level: Minimum proficiency level (1-5)
            certified_only: Only return certified resources

        Returns:
            List of matching resource skills, ordered by proficiency descending
        """
        query = (
            select(ResourceSkill)
            .where(ResourceSkill.skill_id == skill_id)
            .where(ResourceSkill.proficiency_level >= min_level)
            .options(joinedload(ResourceSkill.resource))
        )
        query = self._apply_soft_delete_filter(query)

        if certified_only:
            query = query.where(ResourceSkill.is_certified.is_(True))

        query = query.order_by(ResourceSkill.proficiency_level.desc())

        result = await self.session.execute(query)
        return list(result.unique().scalars().all())

    async def get_certified_resources(
        self,
        skill_id: UUID,
    ) -> list[ResourceSkill]:
        """Get all certified resources for a skill."""
        return await self.find_matching_resources(skill_id, certified_only=True)

    async def assignment_exists(
        self,
        resource_id: UUID,
        skill_id: UUID,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if a resource-skill assignment exists."""
        query = (
            select(func.count())
            .select_from(ResourceSkill)
            .where(ResourceSkill.resource_id == resource_id)
            .where(ResourceSkill.skill_id == skill_id)
        )
        query = self._apply_soft_delete_filter(query)

        if exclude_id is not None:
            query = query.where(ResourceSkill.id != exclude_id)

        result = await self.session.execute(query)
        count: int = result.scalar_one()
        return count > 0


class SkillRequirementRepository(BaseRepository[SkillRequirement]):
    """Repository for SkillRequirement model operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with SkillRequirement model."""
        super().__init__(SkillRequirement, session)

    async def get_by_activity(
        self,
        activity_id: UUID,
    ) -> list[SkillRequirement]:
        """
        Get all skill requirements for an activity.

        Args:
            activity_id: Activity UUID

        Returns:
            List of skill requirements with skill details
        """
        query = (
            select(SkillRequirement)
            .where(SkillRequirement.activity_id == activity_id)
            .options(joinedload(SkillRequirement.skill))
        )
        query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return list(result.unique().scalars().all())

    async def requirement_exists(
        self,
        activity_id: UUID,
        skill_id: UUID,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if a skill requirement exists for an activity."""
        query = (
            select(func.count())
            .select_from(SkillRequirement)
            .where(SkillRequirement.activity_id == activity_id)
            .where(SkillRequirement.skill_id == skill_id)
        )
        query = self._apply_soft_delete_filter(query)

        if exclude_id is not None:
            query = query.where(SkillRequirement.id != exclude_id)

        result = await self.session.execute(query)
        count: int = result.scalar_one()
        return count > 0
