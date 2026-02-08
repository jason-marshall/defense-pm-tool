"""API endpoints for skill and certification management."""

from uuid import UUID

from fastapi import APIRouter, Query, status

from src.core.deps import CurrentUser, DbSession
from src.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from src.repositories.activity import ActivityRepository
from src.repositories.program import ProgramRepository
from src.repositories.resource import ResourceRepository
from src.repositories.skill import (
    ResourceSkillRepository,
    SkillRepository,
    SkillRequirementRepository,
)
from src.schemas.skill import (
    ResourceSkillCreate,
    ResourceSkillResponse,
    ResourceSkillUpdate,
    SkillCreate,
    SkillListResponse,
    SkillRequirementCreate,
    SkillRequirementResponse,
    SkillResponse,
    SkillUpdate,
)

router = APIRouter(prefix="/skills", tags=["Skills"])

# =============================================================================
# Skill CRUD
# =============================================================================


@router.get(
    "",
    response_model=SkillListResponse,
    summary="List Skills",
)
async def list_skills(
    db: DbSession,
    current_user: CurrentUser,
    program_id: UUID | None = Query(None, description="Program ID (NULL = global skills only)"),
    category: str | None = Query(None, description="Filter by category"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> SkillListResponse:
    """List skills with optional filters."""
    skip = (page - 1) * page_size
    repo = SkillRepository(db)
    items, total = await repo.get_by_program(
        program_id=program_id,
        category=category,
        is_active=is_active,
        skip=skip,
        limit=page_size,
    )
    return SkillListResponse(
        items=[SkillResponse.model_validate(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Skill",
)
async def create_skill(
    db: DbSession,
    current_user: CurrentUser,
    skill_data: SkillCreate,
) -> SkillResponse:
    """Create a new skill definition."""
    # Verify program access if program-specific
    if skill_data.program_id:
        program_repo = ProgramRepository(db)
        program = await program_repo.get_by_id(skill_data.program_id)
        if not program:
            raise NotFoundError(f"Program {skill_data.program_id} not found", "PROGRAM_NOT_FOUND")
        if program.owner_id != current_user.id and not current_user.is_admin:
            raise AuthorizationError("Access denied to this program")

    repo = SkillRepository(db)
    if await repo.code_exists(skill_data.code, skill_data.program_id):
        raise ConflictError(
            f"Skill code '{skill_data.code}' already exists",
            "SKILL_CODE_DUPLICATE",
        )

    skill = await repo.create(skill_data.model_dump())
    await db.commit()
    await db.refresh(skill)
    return SkillResponse.model_validate(skill)


@router.get(
    "/{skill_id}",
    response_model=SkillResponse,
    summary="Get Skill",
)
async def get_skill(
    db: DbSession,
    current_user: CurrentUser,
    skill_id: UUID,
) -> SkillResponse:
    """Get a skill by ID."""
    repo = SkillRepository(db)
    skill = await repo.get_by_id(skill_id)
    if not skill:
        raise NotFoundError(f"Skill {skill_id} not found", "SKILL_NOT_FOUND")
    return SkillResponse.model_validate(skill)


@router.patch(
    "/{skill_id}",
    response_model=SkillResponse,
    summary="Update Skill",
)
async def update_skill(
    db: DbSession,
    current_user: CurrentUser,
    skill_id: UUID,
    update_data: SkillUpdate,
) -> SkillResponse:
    """Update a skill definition."""
    repo = SkillRepository(db)
    skill = await repo.get_by_id(skill_id)
    if not skill:
        raise NotFoundError(f"Skill {skill_id} not found", "SKILL_NOT_FOUND")

    # Verify program access
    if skill.program_id:
        program_repo = ProgramRepository(db)
        program = await program_repo.get_by_id(skill.program_id)
        if program and program.owner_id != current_user.id and not current_user.is_admin:
            raise AuthorizationError("Access denied")

    # Check code uniqueness if changing
    if (
        update_data.code
        and update_data.code != skill.code
        and await repo.code_exists(update_data.code, skill.program_id, exclude_id=skill_id)
    ):
        raise ConflictError(
            f"Skill code '{update_data.code}' already exists",
            "SKILL_CODE_DUPLICATE",
        )

    data = update_data.model_dump(exclude_unset=True)
    updated = await repo.update(skill, data)
    await db.commit()
    await db.refresh(updated)
    return SkillResponse.model_validate(updated)


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Skill",
)
async def delete_skill(
    db: DbSession,
    current_user: CurrentUser,
    skill_id: UUID,
) -> None:
    """Delete a skill (soft delete)."""
    repo = SkillRepository(db)
    skill = await repo.get_by_id(skill_id)
    if not skill:
        raise NotFoundError(f"Skill {skill_id} not found", "SKILL_NOT_FOUND")

    if skill.program_id:
        program_repo = ProgramRepository(db)
        program = await program_repo.get_by_id(skill.program_id)
        if program and program.owner_id != current_user.id and not current_user.is_admin:
            raise AuthorizationError("Access denied")

    await repo.delete(skill_id)
    await db.commit()


@router.get(
    "/{skill_id}/qualified-resources",
    response_model=list[ResourceSkillResponse],
    summary="Get Qualified Resources",
)
async def get_qualified_resources(
    db: DbSession,
    current_user: CurrentUser,
    skill_id: UUID,
    min_level: int = Query(1, ge=1, le=5, description="Minimum proficiency level"),
    certified_only: bool = Query(False, description="Only certified resources"),
) -> list[ResourceSkillResponse]:
    """Find resources qualified for a specific skill."""
    repo = SkillRepository(db)
    skill = await repo.get_by_id(skill_id)
    if not skill:
        raise NotFoundError(f"Skill {skill_id} not found", "SKILL_NOT_FOUND")

    rs_repo = ResourceSkillRepository(db)
    matches = await rs_repo.find_matching_resources(
        skill_id=skill_id,
        min_level=min_level,
        certified_only=certified_only,
    )
    return [ResourceSkillResponse.model_validate(m) for m in matches]


# =============================================================================
# Resource Skills (nested under /resources)
# =============================================================================

resource_skills_router = APIRouter(tags=["Resource Skills"])


@resource_skills_router.get(
    "/resources/{resource_id}/skills",
    response_model=list[ResourceSkillResponse],
    summary="List Resource Skills",
)
async def list_resource_skills(
    db: DbSession,
    current_user: CurrentUser,
    resource_id: UUID,
) -> list[ResourceSkillResponse]:
    """List all skills for a resource."""
    res_repo = ResourceRepository(db)
    resource = await res_repo.get_by_id(resource_id)
    if not resource:
        raise NotFoundError(f"Resource {resource_id} not found", "RESOURCE_NOT_FOUND")

    rs_repo = ResourceSkillRepository(db)
    items = await rs_repo.get_by_resource(resource_id)
    return [ResourceSkillResponse.model_validate(rs) for rs in items]


@resource_skills_router.post(
    "/resources/{resource_id}/skills",
    response_model=ResourceSkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Resource Skill",
)
async def add_resource_skill(
    db: DbSession,
    current_user: CurrentUser,
    resource_id: UUID,
    skill_data: ResourceSkillCreate,
) -> ResourceSkillResponse:
    """Assign a skill to a resource."""
    res_repo = ResourceRepository(db)
    resource = await res_repo.get_by_id(resource_id)
    if not resource:
        raise NotFoundError(f"Resource {resource_id} not found", "RESOURCE_NOT_FOUND")

    # Verify program access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(resource.program_id)
    if program and program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    # Verify skill exists
    skill_repo = SkillRepository(db)
    skill = await skill_repo.get_by_id(skill_data.skill_id)
    if not skill:
        raise NotFoundError(f"Skill {skill_data.skill_id} not found", "SKILL_NOT_FOUND")

    rs_repo = ResourceSkillRepository(db)
    if await rs_repo.assignment_exists(resource_id, skill_data.skill_id):
        raise ConflictError(
            "Resource already has this skill assigned",
            "RESOURCE_SKILL_DUPLICATE",
        )

    data = skill_data.model_dump()
    data["resource_id"] = resource_id
    rs = await rs_repo.create(data)
    await db.commit()
    await db.refresh(rs)
    return ResourceSkillResponse.model_validate(rs)


@resource_skills_router.put(
    "/resources/{resource_id}/skills/{skill_id}",
    response_model=ResourceSkillResponse,
    summary="Update Resource Skill",
)
async def update_resource_skill(
    db: DbSession,
    current_user: CurrentUser,
    resource_id: UUID,
    skill_id: UUID,
    update_data: ResourceSkillUpdate,
) -> ResourceSkillResponse:
    """Update a resource's skill proficiency or certification."""
    rs_repo = ResourceSkillRepository(db)
    rs = await rs_repo.find_one({"resource_id": resource_id, "skill_id": skill_id})
    if not rs:
        raise NotFoundError("Resource skill not found", "RESOURCE_SKILL_NOT_FOUND")

    data = update_data.model_dump(exclude_unset=True)
    updated = await rs_repo.update(rs, data)
    await db.commit()
    await db.refresh(updated)
    return ResourceSkillResponse.model_validate(updated)


@resource_skills_router.delete(
    "/resources/{resource_id}/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Resource Skill",
)
async def remove_resource_skill(
    db: DbSession,
    current_user: CurrentUser,
    resource_id: UUID,
    skill_id: UUID,
) -> None:
    """Remove a skill from a resource (soft delete)."""
    rs_repo = ResourceSkillRepository(db)
    rs = await rs_repo.find_one({"resource_id": resource_id, "skill_id": skill_id})
    if not rs:
        raise NotFoundError("Resource skill not found", "RESOURCE_SKILL_NOT_FOUND")

    await rs_repo.delete(rs.id)
    await db.commit()


# =============================================================================
# Skill Requirements (nested under /activities)
# =============================================================================

skill_requirements_router = APIRouter(tags=["Skill Requirements"])


@skill_requirements_router.get(
    "/activities/{activity_id}/skill-requirements",
    response_model=list[SkillRequirementResponse],
    summary="List Activity Skill Requirements",
)
async def list_skill_requirements(
    db: DbSession,
    current_user: CurrentUser,
    activity_id: UUID,
) -> list[SkillRequirementResponse]:
    """List all skill requirements for an activity."""
    act_repo = ActivityRepository(db)
    activity = await act_repo.get_by_id(activity_id)
    if not activity:
        raise NotFoundError(f"Activity {activity_id} not found", "ACTIVITY_NOT_FOUND")

    sr_repo = SkillRequirementRepository(db)
    items = await sr_repo.get_by_activity(activity_id)
    return [SkillRequirementResponse.model_validate(sr) for sr in items]


@skill_requirements_router.post(
    "/activities/{activity_id}/skill-requirements",
    response_model=SkillRequirementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Skill Requirement",
)
async def add_skill_requirement(
    db: DbSession,
    current_user: CurrentUser,
    activity_id: UUID,
    req_data: SkillRequirementCreate,
) -> SkillRequirementResponse:
    """Add a skill requirement to an activity."""
    act_repo = ActivityRepository(db)
    activity = await act_repo.get_by_id(activity_id)
    if not activity:
        raise NotFoundError(f"Activity {activity_id} not found", "ACTIVITY_NOT_FOUND")

    # Verify program access
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(activity.program_id)
    if program and program.owner_id != current_user.id and not current_user.is_admin:
        raise AuthorizationError("Access denied")

    # Verify skill exists
    skill_repo = SkillRepository(db)
    skill = await skill_repo.get_by_id(req_data.skill_id)
    if not skill:
        raise NotFoundError(f"Skill {req_data.skill_id} not found", "SKILL_NOT_FOUND")

    sr_repo = SkillRequirementRepository(db)
    if await sr_repo.requirement_exists(activity_id, req_data.skill_id):
        raise ConflictError(
            "Skill requirement already exists for this activity",
            "SKILL_REQUIREMENT_DUPLICATE",
        )

    data = req_data.model_dump()
    data["activity_id"] = activity_id
    sr = await sr_repo.create(data)
    await db.commit()
    await db.refresh(sr)
    return SkillRequirementResponse.model_validate(sr)


@skill_requirements_router.delete(
    "/activities/{activity_id}/skill-requirements/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Skill Requirement",
)
async def remove_skill_requirement(
    db: DbSession,
    current_user: CurrentUser,
    activity_id: UUID,
    skill_id: UUID,
) -> None:
    """Remove a skill requirement from an activity (soft delete)."""
    sr_repo = SkillRequirementRepository(db)
    sr = await sr_repo.find_one({"activity_id": activity_id, "skill_id": skill_id})
    if not sr:
        raise NotFoundError("Skill requirement not found", "SKILL_REQUIREMENT_NOT_FOUND")

    await sr_repo.delete(sr.id)
    await db.commit()
