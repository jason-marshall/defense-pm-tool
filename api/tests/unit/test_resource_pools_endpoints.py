"""Unit tests for resource pool management endpoints."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.resource_pools import (
    add_pool_member,
    check_assignment_conflict,
    create_pool,
    delete_pool,
    get_pool,
    get_pool_availability,
    grant_pool_access,
    list_pool_members,
    list_pools,
    remove_pool_member,
    update_pool,
)
from src.core.exceptions import AuthorizationError, NotFoundError
from src.models.resource_pool import PoolAccessLevel


class TestCreatePool:
    """Tests for create_pool endpoint."""

    @pytest.mark.asyncio
    async def test_create_pool_success(self):
        """Should create a resource pool and return it."""
        from src.schemas.resource_pool import ResourcePoolCreate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        now = datetime.now(UTC)

        pool_data = ResourcePoolCreate(
            name="Shared Engineers",
            code="ENG-POOL-01",
            description="Pool of shared engineering resources",
        )

        # After db.refresh, the pool object will have id, timestamps, etc.
        def fake_refresh(pool):
            pool.id = pool_id
            pool.name = "Shared Engineers"
            pool.code = "ENG-POOL-01"
            pool.description = "Pool of shared engineering resources"
            pool.owner_id = mock_user.id
            pool.is_active = True
            pool.created_at = now
            pool.updated_at = now

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        result = await create_pool(pool_data, mock_db, mock_user)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert result.id == pool_id
        assert result.name == "Shared Engineers"
        assert result.code == "ENG-POOL-01"
        assert result.owner_id == mock_user.id

    @pytest.mark.asyncio
    async def test_create_pool_sets_owner_to_current_user(self):
        """Should set pool owner_id to the authenticated user's ID."""
        from src.schemas.resource_pool import ResourcePoolCreate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        user_id = uuid4()
        mock_user.id = user_id

        now = datetime.now(UTC)
        pool_data = ResourcePoolCreate(name="Test Pool", code="TP-01")

        def fake_refresh(pool):
            pool.id = uuid4()
            pool.name = "Test Pool"
            pool.code = "TP-01"
            pool.description = None
            pool.owner_id = pool.owner_id  # preserve what was set
            pool.is_active = True
            pool.created_at = now
            pool.updated_at = now

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        result = await create_pool(pool_data, mock_db, mock_user)

        # Verify the pool was created with the current user as owner
        added_pool = mock_db.add.call_args[0][0]
        assert added_pool.owner_id == user_id


class TestListPools:
    """Tests for list_pools endpoint."""

    @pytest.mark.asyncio
    async def test_list_pools_returns_accessible_pools(self):
        """Should return pools owned by or accessible to the user."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        now = datetime.now(UTC)
        pool1 = MagicMock()
        pool1.id = uuid4()
        pool1.name = "Pool A"
        pool1.code = "POOL-A"
        pool1.description = None
        pool1.owner_id = mock_user.id
        pool1.is_active = True
        pool1.created_at = now
        pool1.updated_at = now

        pool2 = MagicMock()
        pool2.id = uuid4()
        pool2.name = "Pool B"
        pool2.code = "POOL-B"
        pool2.description = "Accessible pool"
        pool2.owner_id = uuid4()
        pool2.is_active = True
        pool2.created_at = now
        pool2.updated_at = now

        mock_result = MagicMock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = [pool1, pool2]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_pools(mock_db, mock_user)

        assert len(result) == 2
        assert result[0].name == "Pool A"
        assert result[1].name == "Pool B"

    @pytest.mark.asyncio
    async def test_list_pools_empty(self):
        """Should return empty list when user has no accessible pools."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_pools(mock_db, mock_user)

        assert len(result) == 0


class TestGetPool:
    """Tests for get_pool endpoint."""

    @pytest.mark.asyncio
    async def test_get_pool_success(self):
        """Should return pool details by ID."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        now = datetime.now(UTC)

        mock_pool = MagicMock()
        mock_pool.id = pool_id
        mock_pool.name = "Engineering Pool"
        mock_pool.code = "ENG-01"
        mock_pool.description = "Shared engineers"
        mock_pool.owner_id = mock_user.id
        mock_pool.is_active = True
        mock_pool.deleted_at = None
        mock_pool.created_at = now
        mock_pool.updated_at = now

        mock_db.get = AsyncMock(return_value=mock_pool)

        result = await get_pool(pool_id, mock_db, mock_user)

        mock_db.get.assert_called_once()
        assert result.id == pool_id
        assert result.name == "Engineering Pool"
        assert result.code == "ENG-01"
        assert result.owner_id == mock_user.id

    @pytest.mark.asyncio
    async def test_get_pool_not_found(self):
        """Should raise NotFoundError when pool doesn't exist."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError) as exc_info:
            await get_pool(pool_id, mock_db, mock_user)

        assert exc_info.value.code == "POOL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_pool_soft_deleted(self):
        """Should raise NotFoundError when pool is soft deleted."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        mock_pool = MagicMock()
        mock_pool.deleted_at = datetime.now(UTC)

        mock_db.get = AsyncMock(return_value=mock_pool)

        with pytest.raises(NotFoundError) as exc_info:
            await get_pool(pool_id, mock_db, mock_user)

        assert exc_info.value.code == "POOL_NOT_FOUND"


class TestUpdatePool:
    """Tests for update_pool endpoint."""

    @pytest.mark.asyncio
    async def test_update_pool_success(self):
        """Should update pool fields and return updated pool."""
        from src.schemas.resource_pool import ResourcePoolUpdate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        user_id = uuid4()
        mock_user.id = user_id

        pool_id = uuid4()
        now = datetime.now(UTC)

        mock_pool = MagicMock()
        mock_pool.id = pool_id
        mock_pool.name = "Old Name"
        mock_pool.code = "ENG-01"
        mock_pool.description = None
        mock_pool.owner_id = user_id
        mock_pool.is_active = True
        mock_pool.deleted_at = None
        mock_pool.created_at = now
        mock_pool.updated_at = now

        mock_db.get = AsyncMock(return_value=mock_pool)

        def fake_refresh(pool):
            pool.name = "Updated Pool"
            pool.updated_at = datetime.now(UTC)

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        update_data = ResourcePoolUpdate(name="Updated Pool")

        result = await update_pool(pool_id, update_data, mock_db, mock_user)

        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_pool_not_found(self):
        """Should raise NotFoundError when pool doesn't exist."""
        from src.schemas.resource_pool import ResourcePoolUpdate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        mock_db.get = AsyncMock(return_value=None)

        update_data = ResourcePoolUpdate(name="New Name")

        with pytest.raises(NotFoundError) as exc_info:
            await update_pool(pool_id, update_data, mock_db, mock_user)

        assert exc_info.value.code == "POOL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_pool_not_owner(self):
        """Should raise AuthorizationError when user is not pool owner."""
        from src.schemas.resource_pool import ResourcePoolUpdate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        mock_pool = MagicMock()
        mock_pool.owner_id = uuid4()  # Different user
        mock_pool.deleted_at = None

        mock_db.get = AsyncMock(return_value=mock_pool)

        update_data = ResourcePoolUpdate(name="New Name")

        with pytest.raises(AuthorizationError) as exc_info:
            await update_pool(pool_id, update_data, mock_db, mock_user)

        assert exc_info.value.code == "NOT_AUTHORIZED"
        mock_db.commit.assert_not_called()


class TestDeletePool:
    """Tests for delete_pool endpoint."""

    @pytest.mark.asyncio
    async def test_delete_pool_success(self):
        """Should soft delete pool by setting deleted_at."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        user_id = uuid4()
        mock_user.id = user_id

        pool_id = uuid4()
        mock_pool = MagicMock()
        mock_pool.owner_id = user_id
        mock_pool.deleted_at = None

        mock_db.get = AsyncMock(return_value=mock_pool)

        result = await delete_pool(pool_id, mock_db, mock_user)

        assert result is None
        assert mock_pool.deleted_at is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_pool_not_found(self):
        """Should raise NotFoundError when pool doesn't exist."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError) as exc_info:
            await delete_pool(pool_id, mock_db, mock_user)

        assert exc_info.value.code == "POOL_NOT_FOUND"
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_pool_not_owner(self):
        """Should raise AuthorizationError when user is not pool owner."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        mock_pool = MagicMock()
        mock_pool.owner_id = uuid4()  # Different user
        mock_pool.deleted_at = None

        mock_db.get = AsyncMock(return_value=mock_pool)

        with pytest.raises(AuthorizationError) as exc_info:
            await delete_pool(pool_id, mock_db, mock_user)

        assert exc_info.value.code == "NOT_AUTHORIZED"
        mock_db.commit.assert_not_called()


class TestAddPoolMember:
    """Tests for add_pool_member endpoint."""

    @pytest.mark.asyncio
    async def test_add_pool_member_success(self):
        """Should add a resource to the pool."""
        from src.schemas.resource_pool import PoolMemberCreate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        user_id = uuid4()
        mock_user.id = user_id

        pool_id = uuid4()
        resource_id = uuid4()
        member_id = uuid4()
        now = datetime.now(UTC)

        mock_pool = MagicMock()
        mock_pool.owner_id = user_id
        mock_pool.deleted_at = None

        mock_db.get = AsyncMock(return_value=mock_pool)

        def fake_refresh(member):
            member.id = member_id
            member.pool_id = pool_id
            member.resource_id = resource_id
            member.allocation_percentage = Decimal("75.00")
            member.is_active = True
            member.created_at = now

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        member_data = PoolMemberCreate(
            resource_id=resource_id,
            allocation_percentage=Decimal("75.00"),
        )

        result = await add_pool_member(pool_id, member_data, mock_db, mock_user)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result.pool_id == pool_id
        assert result.resource_id == resource_id
        assert result.allocation_percentage == Decimal("75.00")

    @pytest.mark.asyncio
    async def test_add_pool_member_pool_not_found(self):
        """Should raise NotFoundError when pool doesn't exist."""
        from src.schemas.resource_pool import PoolMemberCreate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        mock_db.get = AsyncMock(return_value=None)

        member_data = PoolMemberCreate(resource_id=uuid4())

        with pytest.raises(NotFoundError) as exc_info:
            await add_pool_member(pool_id, member_data, mock_db, mock_user)

        assert exc_info.value.code == "POOL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_add_pool_member_not_owner(self):
        """Should raise AuthorizationError when user is not pool owner."""
        from src.schemas.resource_pool import PoolMemberCreate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        mock_pool = MagicMock()
        mock_pool.owner_id = uuid4()  # Different user
        mock_pool.deleted_at = None

        mock_db.get = AsyncMock(return_value=mock_pool)

        member_data = PoolMemberCreate(resource_id=uuid4())

        with pytest.raises(AuthorizationError) as exc_info:
            await add_pool_member(pool_id, member_data, mock_db, mock_user)

        assert exc_info.value.code == "NOT_AUTHORIZED"
        mock_db.add.assert_not_called()


class TestListPoolMembers:
    """Tests for list_pool_members endpoint."""

    @pytest.mark.asyncio
    async def test_list_pool_members_success(self):
        """Should return all active members of a pool."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        now = datetime.now(UTC)

        mock_pool = MagicMock()
        mock_pool.deleted_at = None
        mock_db.get = AsyncMock(return_value=mock_pool)

        member1 = MagicMock()
        member1.id = uuid4()
        member1.pool_id = pool_id
        member1.resource_id = uuid4()
        member1.allocation_percentage = Decimal("100.00")
        member1.is_active = True
        member1.created_at = now

        member2 = MagicMock()
        member2.id = uuid4()
        member2.pool_id = pool_id
        member2.resource_id = uuid4()
        member2.allocation_percentage = Decimal("50.00")
        member2.is_active = True
        member2.created_at = now

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [member1, member2]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_pool_members(pool_id, mock_db, mock_user)

        assert len(result) == 2
        assert result[0].allocation_percentage == Decimal("100.00")
        assert result[1].allocation_percentage == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_list_pool_members_pool_not_found(self):
        """Should raise NotFoundError when pool doesn't exist."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError) as exc_info:
            await list_pool_members(pool_id, mock_db, mock_user)

        assert exc_info.value.code == "POOL_NOT_FOUND"


class TestRemovePoolMember:
    """Tests for remove_pool_member endpoint."""

    @pytest.mark.asyncio
    async def test_remove_pool_member_success(self):
        """Should soft delete the pool member."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        user_id = uuid4()
        mock_user.id = user_id

        pool_id = uuid4()
        member_id = uuid4()

        mock_pool = MagicMock()
        mock_pool.owner_id = user_id
        mock_pool.deleted_at = None

        mock_member = MagicMock()
        mock_member.pool_id = pool_id
        mock_member.deleted_at = None

        mock_db.get = AsyncMock(
            side_effect=lambda model, id: {
                pool_id: mock_pool,
                member_id: mock_member,
            }.get(id)
        )

        result = await remove_pool_member(pool_id, member_id, mock_db, mock_user)

        assert result is None
        assert mock_member.deleted_at is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_pool_member_pool_not_found(self):
        """Should raise NotFoundError when pool doesn't exist."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        member_id = uuid4()

        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError) as exc_info:
            await remove_pool_member(pool_id, member_id, mock_db, mock_user)

        assert exc_info.value.code == "POOL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_remove_pool_member_not_owner(self):
        """Should raise AuthorizationError when user is not pool owner."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        member_id = uuid4()

        mock_pool = MagicMock()
        mock_pool.owner_id = uuid4()  # Different user
        mock_pool.deleted_at = None

        mock_db.get = AsyncMock(return_value=mock_pool)

        with pytest.raises(AuthorizationError) as exc_info:
            await remove_pool_member(pool_id, member_id, mock_db, mock_user)

        assert exc_info.value.code == "NOT_AUTHORIZED"
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_pool_member_member_not_found(self):
        """Should raise NotFoundError when member doesn't exist in pool."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        user_id = uuid4()
        mock_user.id = user_id

        pool_id = uuid4()
        member_id = uuid4()

        mock_pool = MagicMock()
        mock_pool.owner_id = user_id
        mock_pool.deleted_at = None

        # Pool found, but member not found
        mock_db.get = AsyncMock(
            side_effect=lambda model, id: {
                pool_id: mock_pool,
            }.get(id)
        )

        with pytest.raises(NotFoundError) as exc_info:
            await remove_pool_member(pool_id, member_id, mock_db, mock_user)

        assert exc_info.value.code == "MEMBER_NOT_FOUND"
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_pool_member_wrong_pool(self):
        """Should raise NotFoundError when member belongs to a different pool."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        user_id = uuid4()
        mock_user.id = user_id

        pool_id = uuid4()
        member_id = uuid4()

        mock_pool = MagicMock()
        mock_pool.owner_id = user_id
        mock_pool.deleted_at = None

        mock_member = MagicMock()
        mock_member.pool_id = uuid4()  # Different pool
        mock_member.deleted_at = None

        mock_db.get = AsyncMock(
            side_effect=lambda model, id: {
                pool_id: mock_pool,
                member_id: mock_member,
            }.get(id)
        )

        with pytest.raises(NotFoundError) as exc_info:
            await remove_pool_member(pool_id, member_id, mock_db, mock_user)

        assert exc_info.value.code == "MEMBER_NOT_FOUND"


class TestGrantPoolAccess:
    """Tests for grant_pool_access endpoint."""

    @pytest.mark.asyncio
    async def test_grant_pool_access_success(self):
        """Should grant program access to the pool."""
        from src.schemas.resource_pool import PoolAccessCreate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        user_id = uuid4()
        mock_user.id = user_id

        pool_id = uuid4()
        program_id = uuid4()
        access_id = uuid4()
        now = datetime.now(UTC)

        mock_pool = MagicMock()
        mock_pool.owner_id = user_id
        mock_pool.deleted_at = None

        mock_db.get = AsyncMock(return_value=mock_pool)

        def fake_refresh(access):
            access.id = access_id
            access.pool_id = pool_id
            access.program_id = program_id
            access.access_level = PoolAccessLevel.MEMBER
            access.granted_by = user_id
            access.granted_at = now

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        access_data = PoolAccessCreate(
            program_id=program_id,
            access_level=PoolAccessLevel.MEMBER,
        )

        result = await grant_pool_access(pool_id, access_data, mock_db, mock_user)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result.pool_id == pool_id
        assert result.program_id == program_id
        assert result.access_level == PoolAccessLevel.MEMBER
        assert result.granted_by == user_id

    @pytest.mark.asyncio
    async def test_grant_pool_access_pool_not_found(self):
        """Should raise NotFoundError when pool doesn't exist."""
        from src.schemas.resource_pool import PoolAccessCreate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        mock_db.get = AsyncMock(return_value=None)

        access_data = PoolAccessCreate(program_id=uuid4())

        with pytest.raises(NotFoundError) as exc_info:
            await grant_pool_access(pool_id, access_data, mock_db, mock_user)

        assert exc_info.value.code == "POOL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_grant_pool_access_not_owner(self):
        """Should raise AuthorizationError when user is not pool owner."""
        from src.schemas.resource_pool import PoolAccessCreate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        mock_pool = MagicMock()
        mock_pool.owner_id = uuid4()  # Different user
        mock_pool.deleted_at = None

        mock_db.get = AsyncMock(return_value=mock_pool)

        access_data = PoolAccessCreate(program_id=uuid4())

        with pytest.raises(AuthorizationError) as exc_info:
            await grant_pool_access(pool_id, access_data, mock_db, mock_user)

        assert exc_info.value.code == "NOT_AUTHORIZED"
        mock_db.add.assert_not_called()


class TestGetPoolAvailability:
    """Tests for get_pool_availability endpoint."""

    @pytest.mark.asyncio
    async def test_get_pool_availability_success(self):
        """Should return pool availability with conflict info."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        resource_id = uuid4()
        start = date(2026, 3, 1)
        end = date(2026, 3, 31)

        from src.services.cross_program_availability import (
            CrossProgramConflict,
            PoolAvailability,
        )

        mock_conflict = CrossProgramConflict(
            resource_id=resource_id,
            resource_name="Engineer A",
            conflict_date=date(2026, 3, 15),
            programs_involved=[
                {"program_id": str(uuid4()), "assigned_hours": 8.0},
                {"program_id": str(uuid4()), "assigned_hours": 6.0},
            ],
            total_assigned=Decimal("14.0"),
            available_hours=Decimal("8.0"),
            overallocation=Decimal("6.0"),
        )

        mock_availability = PoolAvailability(
            pool_id=pool_id,
            pool_name="Engineering Pool",
            date_range_start=start,
            date_range_end=end,
            resources=[
                {
                    "resource_id": str(resource_id),
                    "resource_code": "ENG-001",
                    "resource_name": "Engineer A",
                    "allocation_percentage": 100.0,
                    "is_active": True,
                    "conflict_count": 1,
                }
            ],
            conflicts=[mock_conflict],
        )

        with patch(
            "src.api.v1.endpoints.resource_pools.CrossProgramAvailabilityService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_pool_availability = AsyncMock(return_value=mock_availability)
            mock_service_class.return_value = mock_service

            result = await get_pool_availability(pool_id, start, end, mock_db, mock_user)

            mock_service.get_pool_availability.assert_called_once_with(pool_id, start, end)
            assert result.pool_id == pool_id
            assert result.pool_name == "Engineering Pool"
            assert result.conflict_count == 1
            assert len(result.conflicts) == 1
            assert result.conflicts[0]["resource_name"] == "Engineer A"
            assert result.conflicts[0]["overallocation_hours"] == 6.0

    @pytest.mark.asyncio
    async def test_get_pool_availability_no_conflicts(self):
        """Should return availability with zero conflicts."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        start = date(2026, 3, 1)
        end = date(2026, 3, 31)

        from src.services.cross_program_availability import PoolAvailability

        mock_availability = PoolAvailability(
            pool_id=pool_id,
            pool_name="Clean Pool",
            date_range_start=start,
            date_range_end=end,
            resources=[],
            conflicts=[],
        )

        with patch(
            "src.api.v1.endpoints.resource_pools.CrossProgramAvailabilityService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_pool_availability = AsyncMock(return_value=mock_availability)
            mock_service_class.return_value = mock_service

            result = await get_pool_availability(pool_id, start, end, mock_db, mock_user)

            assert result.conflict_count == 0
            assert result.conflicts == []

    @pytest.mark.asyncio
    async def test_get_pool_availability_pool_not_found(self):
        """Should raise NotFoundError when service raises ValueError."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        pool_id = uuid4()
        start = date(2026, 3, 1)
        end = date(2026, 3, 31)

        with patch(
            "src.api.v1.endpoints.resource_pools.CrossProgramAvailabilityService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_pool_availability = AsyncMock(
                side_effect=ValueError(f"Pool {pool_id} not found")
            )
            mock_service_class.return_value = mock_service

            with pytest.raises(NotFoundError) as exc_info:
                await get_pool_availability(pool_id, start, end, mock_db, mock_user)

            assert exc_info.value.code == "POOL_NOT_FOUND"


class TestCheckAssignmentConflict:
    """Tests for check_assignment_conflict endpoint."""

    @pytest.mark.asyncio
    async def test_check_conflict_with_conflicts(self):
        """Should return conflicts when assignment would cause overallocation."""
        from src.schemas.resource_pool import ConflictCheckRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        resource_id = uuid4()
        program_id = uuid4()
        start = date(2026, 4, 1)
        end = date(2026, 4, 5)

        from src.services.cross_program_availability import CrossProgramConflict

        mock_conflicts = [
            CrossProgramConflict(
                resource_id=resource_id,
                resource_name="Engineer B",
                conflict_date=date(2026, 4, 2),
                programs_involved=[
                    {"program_id": str(program_id), "assigned_hours": 8.0},
                    {"program_id": str(uuid4()), "assigned_hours": 8.0},
                ],
                total_assigned=Decimal("16.0"),
                available_hours=Decimal("8.0"),
                overallocation=Decimal("8.0"),
            ),
        ]

        request_data = ConflictCheckRequest(
            resource_id=resource_id,
            program_id=program_id,
            start_date=start,
            end_date=end,
            units=Decimal("1.00"),
        )

        with patch(
            "src.api.v1.endpoints.resource_pools.CrossProgramAvailabilityService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.check_resource_conflict = AsyncMock(return_value=mock_conflicts)
            mock_service_class.return_value = mock_service

            result = await check_assignment_conflict(request_data, mock_db, mock_user)

            mock_service.check_resource_conflict.assert_called_once_with(
                resource_id=resource_id,
                program_id=program_id,
                assignment_start=start,
                assignment_end=end,
                units=Decimal("1.00"),
            )
            assert result.has_conflicts is True
            assert result.conflict_count == 1
            assert len(result.conflicts) == 1
            assert result.conflicts[0]["overallocation_hours"] == 8.0

    @pytest.mark.asyncio
    async def test_check_conflict_no_conflicts(self):
        """Should return no conflicts when assignment is safe."""
        from src.schemas.resource_pool import ConflictCheckRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        request_data = ConflictCheckRequest(
            resource_id=uuid4(),
            program_id=uuid4(),
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 5),
            units=Decimal("0.50"),
        )

        with patch(
            "src.api.v1.endpoints.resource_pools.CrossProgramAvailabilityService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.check_resource_conflict = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            result = await check_assignment_conflict(request_data, mock_db, mock_user)

            assert result.has_conflicts is False
            assert result.conflict_count == 0
            assert result.conflicts == []

    @pytest.mark.asyncio
    async def test_check_conflict_resource_not_found(self):
        """Should raise NotFoundError when resource doesn't exist."""
        from src.schemas.resource_pool import ConflictCheckRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        resource_id = uuid4()

        request_data = ConflictCheckRequest(
            resource_id=resource_id,
            program_id=uuid4(),
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 5),
        )

        with patch(
            "src.api.v1.endpoints.resource_pools.CrossProgramAvailabilityService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.check_resource_conflict = AsyncMock(
                side_effect=ValueError(f"Resource {resource_id} not found")
            )
            mock_service_class.return_value = mock_service

            with pytest.raises(NotFoundError) as exc_info:
                await check_assignment_conflict(request_data, mock_db, mock_user)

            assert exc_info.value.code == "RESOURCE_NOT_FOUND"
