"""API endpoints for resource pools."""

from datetime import UTC, date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import get_current_user, get_db
from src.core.exceptions import AuthorizationError, NotFoundError
from src.models.program import Program
from src.models.resource_pool import ResourcePool, ResourcePoolAccess, ResourcePoolMember
from src.models.user import User
from src.schemas.resource_pool import (
    ConflictCheckRequest,
    ConflictCheckResponse,
    PoolAccessCreate,
    PoolAccessResponse,
    PoolAvailabilityResponse,
    PoolMemberCreate,
    PoolMemberResponse,
    ResourcePoolCreate,
    ResourcePoolResponse,
    ResourcePoolUpdate,
)
from src.services.cross_program_availability import CrossProgramAvailabilityService

router = APIRouter(prefix="/resource-pools", tags=["Resource Pools"])


@router.post("", response_model=ResourcePoolResponse, status_code=201)
async def create_pool(
    pool_data: ResourcePoolCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResourcePoolResponse:
    """Create a new resource pool."""
    pool = ResourcePool(
        name=pool_data.name,
        code=pool_data.code,
        description=pool_data.description,
        owner_id=current_user.id,
    )
    db.add(pool)
    await db.commit()
    await db.refresh(pool)

    return ResourcePoolResponse.model_validate(pool)


@router.get("", response_model=list[ResourcePoolResponse])
async def list_pools(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ResourcePoolResponse]:
    """List pools owned by or accessible to current user."""
    # Subquery for programs owned by current user
    user_programs_subquery = select(Program.id).where(Program.owner_id == current_user.id)

    query = (
        select(ResourcePool)
        .outerjoin(ResourcePoolAccess)
        .where(ResourcePool.deleted_at.is_(None))
        .where(
            or_(
                ResourcePool.owner_id == current_user.id,
                ResourcePoolAccess.program_id.in_(user_programs_subquery),
            )
        )
    )
    result = await db.execute(query)
    pools = result.scalars().unique().all()

    return [ResourcePoolResponse.model_validate(p) for p in pools]


@router.get("/{pool_id}", response_model=ResourcePoolResponse)
async def get_pool(
    pool_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResourcePoolResponse:
    """Get a specific resource pool."""
    pool = await db.get(ResourcePool, pool_id)
    if not pool or pool.deleted_at:
        raise NotFoundError("Pool not found", "POOL_NOT_FOUND")

    return ResourcePoolResponse.model_validate(pool)


@router.patch("/{pool_id}", response_model=ResourcePoolResponse)
async def update_pool(
    pool_id: UUID,
    pool_data: ResourcePoolUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResourcePoolResponse:
    """Update a resource pool."""
    pool = await db.get(ResourcePool, pool_id)
    if not pool or pool.deleted_at:
        raise NotFoundError("Pool not found", "POOL_NOT_FOUND")
    if pool.owner_id != current_user.id:
        raise AuthorizationError("Only pool owner can update pool", "NOT_AUTHORIZED")

    update_data = pool_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pool, field, value)

    await db.commit()
    await db.refresh(pool)

    return ResourcePoolResponse.model_validate(pool)


@router.delete("/{pool_id}", status_code=204)
async def delete_pool(
    pool_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a resource pool (soft delete)."""
    pool = await db.get(ResourcePool, pool_id)
    if not pool or pool.deleted_at:
        raise NotFoundError("Pool not found", "POOL_NOT_FOUND")
    if pool.owner_id != current_user.id:
        raise AuthorizationError("Only pool owner can delete pool", "NOT_AUTHORIZED")

    from datetime import datetime

    pool.deleted_at = datetime.now(UTC)
    await db.commit()


@router.post("/{pool_id}/members", response_model=PoolMemberResponse, status_code=201)
async def add_pool_member(
    pool_id: UUID,
    member_data: PoolMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PoolMemberResponse:
    """Add a resource to a pool."""
    pool = await db.get(ResourcePool, pool_id)
    if not pool or pool.deleted_at:
        raise NotFoundError("Pool not found", "POOL_NOT_FOUND")
    if pool.owner_id != current_user.id:
        raise AuthorizationError("Only pool owner can add members", "NOT_AUTHORIZED")

    member = ResourcePoolMember(
        pool_id=pool_id,
        resource_id=member_data.resource_id,
        allocation_percentage=member_data.allocation_percentage,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    return PoolMemberResponse.model_validate(member)


@router.get("/{pool_id}/members", response_model=list[PoolMemberResponse])
async def list_pool_members(
    pool_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PoolMemberResponse]:
    """List all members of a pool."""
    pool = await db.get(ResourcePool, pool_id)
    if not pool or pool.deleted_at:
        raise NotFoundError("Pool not found", "POOL_NOT_FOUND")

    query = (
        select(ResourcePoolMember)
        .where(ResourcePoolMember.pool_id == pool_id)
        .where(ResourcePoolMember.deleted_at.is_(None))
    )
    result = await db.execute(query)
    members = result.scalars().all()

    return [PoolMemberResponse.model_validate(m) for m in members]


@router.delete("/{pool_id}/members/{member_id}", status_code=204)
async def remove_pool_member(
    pool_id: UUID,
    member_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a resource from a pool."""
    pool = await db.get(ResourcePool, pool_id)
    if not pool or pool.deleted_at:
        raise NotFoundError("Pool not found", "POOL_NOT_FOUND")
    if pool.owner_id != current_user.id:
        raise AuthorizationError("Only pool owner can remove members", "NOT_AUTHORIZED")

    member = await db.get(ResourcePoolMember, member_id)
    if not member or member.deleted_at or member.pool_id != pool_id:
        raise NotFoundError("Member not found", "MEMBER_NOT_FOUND")

    from datetime import datetime

    member.deleted_at = datetime.now(UTC)
    await db.commit()


@router.post("/{pool_id}/access", response_model=PoolAccessResponse, status_code=201)
async def grant_pool_access(
    pool_id: UUID,
    access_data: PoolAccessCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PoolAccessResponse:
    """Grant a program access to a pool."""
    pool = await db.get(ResourcePool, pool_id)
    if not pool or pool.deleted_at:
        raise NotFoundError("Pool not found", "POOL_NOT_FOUND")
    if pool.owner_id != current_user.id:
        raise AuthorizationError("Only pool owner can grant access", "NOT_AUTHORIZED")

    from datetime import datetime

    access = ResourcePoolAccess(
        pool_id=pool_id,
        program_id=access_data.program_id,
        access_level=access_data.access_level,
        granted_by=current_user.id,
        granted_at=datetime.now(UTC),
    )
    db.add(access)
    await db.commit()
    await db.refresh(access)

    return PoolAccessResponse.model_validate(access)


@router.get("/{pool_id}/availability", response_model=PoolAvailabilityResponse)
async def get_pool_availability(
    pool_id: UUID,
    start_date: date = Query(..., description="Start date for availability check"),
    end_date: date = Query(..., description="End date for availability check"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PoolAvailabilityResponse:
    """Get availability of all resources in a pool."""
    service = CrossProgramAvailabilityService(db)
    try:
        availability = await service.get_pool_availability(pool_id, start_date, end_date)
    except ValueError as e:
        raise NotFoundError(str(e), "POOL_NOT_FOUND") from e

    return PoolAvailabilityResponse(
        pool_id=availability.pool_id,
        pool_name=availability.pool_name,
        date_range_start=availability.date_range_start,
        date_range_end=availability.date_range_end,
        resources=availability.resources,
        conflict_count=len(availability.conflicts),
        conflicts=[
            {
                "resource_id": str(c.resource_id),
                "resource_name": c.resource_name,
                "conflict_date": c.conflict_date.isoformat(),
                "programs_involved": c.programs_involved,
                "overallocation_hours": float(c.overallocation),
            }
            for c in availability.conflicts
        ],
    )


@router.post("/check-conflict", response_model=ConflictCheckResponse)
async def check_assignment_conflict(
    request: ConflictCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConflictCheckResponse:
    """Check if an assignment would cause cross-program conflicts."""
    service = CrossProgramAvailabilityService(db)
    try:
        conflicts = await service.check_resource_conflict(
            resource_id=request.resource_id,
            program_id=request.program_id,
            assignment_start=request.start_date,
            assignment_end=request.end_date,
            units=request.units,
        )
    except ValueError as e:
        raise NotFoundError(str(e), "RESOURCE_NOT_FOUND") from e

    return ConflictCheckResponse(
        has_conflicts=len(conflicts) > 0,
        conflict_count=len(conflicts),
        conflicts=[
            {
                "date": c.conflict_date.isoformat(),
                "programs": c.programs_involved,
                "overallocation_hours": float(c.overallocation),
            }
            for c in conflicts
        ],
    )
