"""Unit tests for dependency management endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.dependencies import (
    create_dependency,
    delete_dependency,
    get_dependency,
    list_dependencies_for_activity,
    list_dependencies_for_program,
    update_dependency,
    would_create_cycle,
)
from src.core.exceptions import (
    AuthorizationError,
    CircularDependencyError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from src.models.enums import DependencyType


def _make_dependency_mock(
    dep_id=None,
    predecessor_id=None,
    successor_id=None,
    dependency_type=DependencyType.FS,
    lag=0,
):
    """Create a mock dependency ORM object."""
    dep = MagicMock()
    dep.id = dep_id or uuid4()
    dep.predecessor_id = predecessor_id or uuid4()
    dep.successor_id = successor_id or uuid4()
    dep.dependency_type = dependency_type
    dep.lag = lag
    dep.predecessor = None
    dep.successor = None
    dep.created_at = datetime.now(UTC)
    dep.updated_at = datetime.now(UTC)
    return dep


def _make_activity_mock(activity_id=None, program_id=None):
    """Create a mock activity ORM object."""
    activity = MagicMock()
    activity.id = activity_id or uuid4()
    activity.program_id = program_id or uuid4()
    return activity


def _make_program_mock(program_id=None, owner_id=None):
    """Create a mock program ORM object."""
    program = MagicMock()
    program.id = program_id or uuid4()
    program.owner_id = owner_id or uuid4()
    return program


def _make_user_mock(user_id=None, is_admin=False):
    """Create a mock user object."""
    user = MagicMock()
    user.id = user_id or uuid4()
    user.is_admin = is_admin
    return user


class TestListDependenciesForActivity:
    """Tests for list_dependencies_for_activity endpoint."""

    @pytest.mark.asyncio
    async def test_list_dependencies_for_activity_success(self):
        """Should return dependencies for an activity the user owns."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_user_mock(user_id=user_id)

        program_id = uuid4()
        activity_id = uuid4()

        mock_activity = _make_activity_mock(activity_id=activity_id, program_id=program_id)
        mock_program = _make_program_mock(program_id=program_id, owner_id=user_id)

        dep1 = _make_dependency_mock(predecessor_id=activity_id)
        dep2 = _make_dependency_mock(successor_id=activity_id)

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyResponse") as mock_resp_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyListResponse") as mock_list_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_activity)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_dep_repo = MagicMock()
            mock_dep_repo.get_for_activity = AsyncMock(return_value=[dep1, dep2])
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_resp_cls.from_orm_safe.side_effect = lambda d: MagicMock(id=d.id)

            mock_result = MagicMock()
            mock_result.total = 2
            mock_result.items = [MagicMock(), MagicMock()]
            mock_list_cls.return_value = mock_result

            result = await list_dependencies_for_activity(activity_id, mock_db, mock_user)

            assert result.total == 2
            assert len(result.items) == 2
            mock_act_repo.get_by_id.assert_called_once_with(activity_id)
            mock_dep_repo.get_for_activity.assert_called_once_with(activity_id)

    @pytest.mark.asyncio
    async def test_list_dependencies_for_activity_not_found(self):
        """Should raise NotFoundError when activity does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock()
        activity_id = uuid4()

        with patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls:
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=None)
            mock_act_repo_cls.return_value = mock_act_repo

            with pytest.raises(NotFoundError) as exc_info:
                await list_dependencies_for_activity(activity_id, mock_db, mock_user)

            assert exc_info.value.code == "ACTIVITY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_list_dependencies_for_activity_program_not_found(self):
        """Should raise NotFoundError when activity's program does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock()
        activity_id = uuid4()
        mock_activity = _make_activity_mock(activity_id=activity_id)

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_activity)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await list_dependencies_for_activity(activity_id, mock_db, mock_user)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_list_dependencies_for_activity_not_authorized(self):
        """Should raise AuthorizationError when user is not owner and not admin."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock(is_admin=False)
        activity_id = uuid4()
        program_id = uuid4()

        mock_activity = _make_activity_mock(activity_id=activity_id, program_id=program_id)
        mock_program = _make_program_mock(program_id=program_id, owner_id=uuid4())

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_activity)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await list_dependencies_for_activity(activity_id, mock_db, mock_user)

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_list_dependencies_for_activity_admin_bypass(self):
        """Should allow admin users to view dependencies for any activity."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock(is_admin=True)
        activity_id = uuid4()
        program_id = uuid4()

        mock_activity = _make_activity_mock(activity_id=activity_id, program_id=program_id)
        # Program owned by someone else
        mock_program = _make_program_mock(program_id=program_id, owner_id=uuid4())

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyResponse") as mock_resp_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyListResponse") as mock_list_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_activity)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_dep_repo = MagicMock()
            mock_dep_repo.get_for_activity = AsyncMock(return_value=[])
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_resp_cls.from_orm_safe.side_effect = lambda d: MagicMock(id=d.id)

            mock_result = MagicMock()
            mock_result.total = 0
            mock_result.items = []
            mock_list_cls.return_value = mock_result

            result = await list_dependencies_for_activity(activity_id, mock_db, mock_user)

            assert result.total == 0


class TestListDependenciesForProgram:
    """Tests for list_dependencies_for_program endpoint."""

    @pytest.mark.asyncio
    async def test_list_dependencies_for_program_success(self):
        """Should return all dependencies for a program the user owns."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_user_mock(user_id=user_id)
        program_id = uuid4()

        mock_program = _make_program_mock(program_id=program_id, owner_id=user_id)
        dep1 = _make_dependency_mock()
        dep2 = _make_dependency_mock()
        dep3 = _make_dependency_mock()

        with (
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyResponse") as mock_resp_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyListResponse") as mock_list_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_program = AsyncMock(return_value=[dep1, dep2, dep3])
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_resp_cls.from_orm_safe.side_effect = lambda d: MagicMock(id=d.id)

            mock_result = MagicMock()
            mock_result.total = 3
            mock_result.items = [MagicMock(), MagicMock(), MagicMock()]
            mock_list_cls.return_value = mock_result

            result = await list_dependencies_for_program(program_id, mock_db, mock_user)

            assert result.total == 3
            assert len(result.items) == 3

    @pytest.mark.asyncio
    async def test_list_dependencies_for_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock()
        program_id = uuid4()

        with patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await list_dependencies_for_program(program_id, mock_db, mock_user)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_list_dependencies_for_program_not_authorized(self):
        """Should raise AuthorizationError when user is not owner and not admin."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock(is_admin=False)
        program_id = uuid4()

        mock_program = _make_program_mock(program_id=program_id, owner_id=uuid4())

        with patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await list_dependencies_for_program(program_id, mock_db, mock_user)

            assert exc_info.value.code == "NOT_AUTHORIZED"


class TestGetDependency:
    """Tests for get_dependency endpoint."""

    @pytest.mark.asyncio
    async def test_get_dependency_success(self):
        """Should return dependency details when user is the program owner."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_user_mock(user_id=user_id)

        program_id = uuid4()
        predecessor_id = uuid4()
        dep_id = uuid4()

        mock_dep = _make_dependency_mock(dep_id=dep_id, predecessor_id=predecessor_id)
        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=program_id)
        mock_program = _make_program_mock(program_id=program_id, owner_id=user_id)

        with (
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyResponse") as mock_resp_cls,
        ):
            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_id = AsyncMock(return_value=mock_dep)
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_predecessor)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_response = MagicMock()
            mock_response.id = dep_id
            mock_resp_cls.from_orm_safe.return_value = mock_response

            result = await get_dependency(dep_id, mock_db, mock_user)

            assert result.id == dep_id
            mock_dep_repo.get_by_id.assert_called_once_with(dep_id)

    @pytest.mark.asyncio
    async def test_get_dependency_not_found(self):
        """Should raise NotFoundError when dependency does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock()
        dep_id = uuid4()

        with patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls:
            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_id = AsyncMock(return_value=None)
            mock_dep_repo_cls.return_value = mock_dep_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_dependency(dep_id, mock_db, mock_user)

            assert exc_info.value.code == "DEPENDENCY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_dependency_not_authorized(self):
        """Should raise AuthorizationError when user does not own the program."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock(is_admin=False)

        program_id = uuid4()
        predecessor_id = uuid4()
        dep_id = uuid4()

        mock_dep = _make_dependency_mock(dep_id=dep_id, predecessor_id=predecessor_id)
        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=program_id)
        mock_program = _make_program_mock(program_id=program_id, owner_id=uuid4())

        with (
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_id = AsyncMock(return_value=mock_dep)
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_predecessor)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await get_dependency(dep_id, mock_db, mock_user)

            assert exc_info.value.code == "NOT_AUTHORIZED"


class TestCreateDependency:
    """Tests for create_dependency endpoint."""

    @pytest.mark.asyncio
    async def test_create_dependency_fs_success(self):
        """Should create a Finish-to-Start dependency successfully."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_user_mock(user_id=user_id)

        program_id = uuid4()
        predecessor_id = uuid4()
        successor_id = uuid4()

        from src.schemas.dependency import DependencyCreate

        dep_data = DependencyCreate(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=DependencyType.FS,
            lag=0,
        )

        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=program_id)
        mock_successor = _make_activity_mock(activity_id=successor_id, program_id=program_id)
        mock_program = _make_program_mock(program_id=program_id, owner_id=user_id)

        created_dep = _make_dependency_mock(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=DependencyType.FS,
        )

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.dependencies.would_create_cycle") as mock_cycle,
            patch("src.api.v1.endpoints.dependencies.DependencyResponse") as mock_resp_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(side_effect=[mock_predecessor, mock_successor])
            mock_act_repo_cls.return_value = mock_act_repo

            mock_dep_repo = MagicMock()
            mock_dep_repo.dependency_exists = AsyncMock(return_value=False)
            mock_dep_repo.create = AsyncMock(return_value=created_dep)
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_cycle.return_value = (False, None)

            mock_response = MagicMock()
            mock_response.id = created_dep.id
            mock_response.dependency_type = DependencyType.FS
            mock_resp_cls.from_orm_safe.return_value = mock_response

            result = await create_dependency(dep_data, mock_db, mock_user)

            assert result.id == created_dep.id
            assert result.dependency_type == DependencyType.FS
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(created_dep)

    @pytest.mark.asyncio
    async def test_create_dependency_ss_success(self):
        """Should create a Start-to-Start dependency successfully."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_user_mock(user_id=user_id)

        program_id = uuid4()
        predecessor_id = uuid4()
        successor_id = uuid4()

        from src.schemas.dependency import DependencyCreate

        dep_data = DependencyCreate(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=DependencyType.SS,
            lag=2,
        )

        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=program_id)
        mock_successor = _make_activity_mock(activity_id=successor_id, program_id=program_id)
        mock_program = _make_program_mock(program_id=program_id, owner_id=user_id)

        created_dep = _make_dependency_mock(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=DependencyType.SS,
            lag=2,
        )

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.dependencies.would_create_cycle") as mock_cycle,
            patch("src.api.v1.endpoints.dependencies.DependencyResponse") as mock_resp_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(side_effect=[mock_predecessor, mock_successor])
            mock_act_repo_cls.return_value = mock_act_repo

            mock_dep_repo = MagicMock()
            mock_dep_repo.dependency_exists = AsyncMock(return_value=False)
            mock_dep_repo.create = AsyncMock(return_value=created_dep)
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_cycle.return_value = (False, None)

            mock_response = MagicMock()
            mock_response.dependency_type = DependencyType.SS
            mock_response.lag = 2
            mock_resp_cls.from_orm_safe.return_value = mock_response

            result = await create_dependency(dep_data, mock_db, mock_user)

            assert result.dependency_type == DependencyType.SS
            assert result.lag == 2

    @pytest.mark.asyncio
    async def test_create_dependency_ff_success(self):
        """Should create a Finish-to-Finish dependency successfully."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_user_mock(user_id=user_id)

        program_id = uuid4()
        predecessor_id = uuid4()
        successor_id = uuid4()

        from src.schemas.dependency import DependencyCreate

        dep_data = DependencyCreate(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=DependencyType.FF,
            lag=0,
        )

        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=program_id)
        mock_successor = _make_activity_mock(activity_id=successor_id, program_id=program_id)
        mock_program = _make_program_mock(program_id=program_id, owner_id=user_id)

        created_dep = _make_dependency_mock(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=DependencyType.FF,
        )

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.dependencies.would_create_cycle") as mock_cycle,
            patch("src.api.v1.endpoints.dependencies.DependencyResponse") as mock_resp_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(side_effect=[mock_predecessor, mock_successor])
            mock_act_repo_cls.return_value = mock_act_repo

            mock_dep_repo = MagicMock()
            mock_dep_repo.dependency_exists = AsyncMock(return_value=False)
            mock_dep_repo.create = AsyncMock(return_value=created_dep)
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_cycle.return_value = (False, None)

            mock_response = MagicMock()
            mock_response.dependency_type = DependencyType.FF
            mock_resp_cls.from_orm_safe.return_value = mock_response

            result = await create_dependency(dep_data, mock_db, mock_user)

            assert result.dependency_type == DependencyType.FF

    @pytest.mark.asyncio
    async def test_create_dependency_sf_success(self):
        """Should create a Start-to-Finish dependency successfully."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_user_mock(user_id=user_id)

        program_id = uuid4()
        predecessor_id = uuid4()
        successor_id = uuid4()

        from src.schemas.dependency import DependencyCreate

        dep_data = DependencyCreate(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=DependencyType.SF,
            lag=-1,
        )

        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=program_id)
        mock_successor = _make_activity_mock(activity_id=successor_id, program_id=program_id)
        mock_program = _make_program_mock(program_id=program_id, owner_id=user_id)

        created_dep = _make_dependency_mock(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=DependencyType.SF,
            lag=-1,
        )

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.dependencies.would_create_cycle") as mock_cycle,
            patch("src.api.v1.endpoints.dependencies.DependencyResponse") as mock_resp_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(side_effect=[mock_predecessor, mock_successor])
            mock_act_repo_cls.return_value = mock_act_repo

            mock_dep_repo = MagicMock()
            mock_dep_repo.dependency_exists = AsyncMock(return_value=False)
            mock_dep_repo.create = AsyncMock(return_value=created_dep)
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_cycle.return_value = (False, None)

            mock_response = MagicMock()
            mock_response.dependency_type = DependencyType.SF
            mock_response.lag = -1
            mock_resp_cls.from_orm_safe.return_value = mock_response

            result = await create_dependency(dep_data, mock_db, mock_user)

            assert result.dependency_type == DependencyType.SF
            assert result.lag == -1

    @pytest.mark.asyncio
    async def test_create_dependency_predecessor_not_found(self):
        """Should raise NotFoundError when predecessor activity does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock()

        predecessor_id = uuid4()
        successor_id = uuid4()

        from src.schemas.dependency import DependencyCreate

        dep_data = DependencyCreate(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=DependencyType.FS,
            lag=0,
        )

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository"),
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=None)
            mock_act_repo_cls.return_value = mock_act_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_dependency(dep_data, mock_db, mock_user)

            assert exc_info.value.code == "PREDECESSOR_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_dependency_successor_not_found(self):
        """Should raise NotFoundError when successor activity does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock()

        program_id = uuid4()
        predecessor_id = uuid4()
        successor_id = uuid4()

        from src.schemas.dependency import DependencyCreate

        dep_data = DependencyCreate(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=DependencyType.FS,
            lag=0,
        )

        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=program_id)

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository"),
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(side_effect=[mock_predecessor, None])
            mock_act_repo_cls.return_value = mock_act_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_dependency(dep_data, mock_db, mock_user)

            assert exc_info.value.code == "SUCCESSOR_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_dependency_cross_program_validation(self):
        """Should raise ValidationError when activities belong to different programs."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock()

        predecessor_id = uuid4()
        successor_id = uuid4()

        from src.schemas.dependency import DependencyCreate

        dep_data = DependencyCreate(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=DependencyType.FS,
            lag=0,
        )

        # Activities in different programs
        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=uuid4())
        mock_successor = _make_activity_mock(activity_id=successor_id, program_id=uuid4())

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository"),
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(side_effect=[mock_predecessor, mock_successor])
            mock_act_repo_cls.return_value = mock_act_repo

            with pytest.raises(ValidationError) as exc_info:
                await create_dependency(dep_data, mock_db, mock_user)

            assert exc_info.value.code == "CROSS_PROGRAM_DEPENDENCY"

    @pytest.mark.asyncio
    async def test_create_dependency_not_authorized(self):
        """Should raise AuthorizationError when user does not own the program."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock(is_admin=False)

        program_id = uuid4()
        predecessor_id = uuid4()
        successor_id = uuid4()

        from src.schemas.dependency import DependencyCreate

        dep_data = DependencyCreate(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=DependencyType.FS,
            lag=0,
        )

        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=program_id)
        mock_successor = _make_activity_mock(activity_id=successor_id, program_id=program_id)
        mock_program = _make_program_mock(program_id=program_id, owner_id=uuid4())

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository"),
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(side_effect=[mock_predecessor, mock_successor])
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await create_dependency(dep_data, mock_db, mock_user)

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_create_dependency_duplicate(self):
        """Should raise ConflictError when dependency already exists."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_user_mock(user_id=user_id)

        program_id = uuid4()
        predecessor_id = uuid4()
        successor_id = uuid4()

        from src.schemas.dependency import DependencyCreate

        dep_data = DependencyCreate(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=DependencyType.FS,
            lag=0,
        )

        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=program_id)
        mock_successor = _make_activity_mock(activity_id=successor_id, program_id=program_id)
        mock_program = _make_program_mock(program_id=program_id, owner_id=user_id)

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(side_effect=[mock_predecessor, mock_successor])
            mock_act_repo_cls.return_value = mock_act_repo

            mock_dep_repo = MagicMock()
            mock_dep_repo.dependency_exists = AsyncMock(return_value=True)
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(ConflictError) as exc_info:
                await create_dependency(dep_data, mock_db, mock_user)

            assert exc_info.value.code == "DUPLICATE_DEPENDENCY"

    @pytest.mark.asyncio
    async def test_create_dependency_circular_dependency(self):
        """Should raise CircularDependencyError when cycle is detected."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_user_mock(user_id=user_id)

        program_id = uuid4()
        predecessor_id = uuid4()
        successor_id = uuid4()

        from src.schemas.dependency import DependencyCreate

        dep_data = DependencyCreate(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=DependencyType.FS,
            lag=0,
        )

        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=program_id)
        mock_successor = _make_activity_mock(activity_id=successor_id, program_id=program_id)
        mock_program = _make_program_mock(program_id=program_id, owner_id=user_id)

        cycle_path = [predecessor_id, successor_id, predecessor_id]

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.dependencies.would_create_cycle") as mock_cycle,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(side_effect=[mock_predecessor, mock_successor])
            mock_act_repo_cls.return_value = mock_act_repo

            mock_dep_repo = MagicMock()
            mock_dep_repo.dependency_exists = AsyncMock(return_value=False)
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_cycle.return_value = (True, cycle_path)

            with pytest.raises(CircularDependencyError) as exc_info:
                await create_dependency(dep_data, mock_db, mock_user)

            assert exc_info.value.code == "CIRCULAR_DEPENDENCY"
            assert exc_info.value.cycle_path == cycle_path


class TestUpdateDependency:
    """Tests for update_dependency endpoint."""

    @pytest.mark.asyncio
    async def test_update_dependency_success(self):
        """Should update dependency type and lag successfully."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_user_mock(user_id=user_id)

        program_id = uuid4()
        predecessor_id = uuid4()
        dep_id = uuid4()

        from src.schemas.dependency import DependencyUpdate

        update_data = DependencyUpdate(
            dependency_type=DependencyType.SS,
            lag=3,
        )

        mock_dep = _make_dependency_mock(dep_id=dep_id, predecessor_id=predecessor_id)
        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=program_id)
        mock_program = _make_program_mock(program_id=program_id, owner_id=user_id)
        updated_dep = _make_dependency_mock(
            dep_id=dep_id,
            predecessor_id=predecessor_id,
            dependency_type=DependencyType.SS,
            lag=3,
        )

        with (
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyResponse") as mock_resp_cls,
        ):
            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_id = AsyncMock(return_value=mock_dep)
            mock_dep_repo.update = AsyncMock(return_value=updated_dep)
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_predecessor)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_response = MagicMock()
            mock_response.id = dep_id
            mock_response.dependency_type = DependencyType.SS
            mock_response.lag = 3
            mock_resp_cls.from_orm_safe.return_value = mock_response

            result = await update_dependency(dep_id, update_data, mock_db, mock_user)

            assert result.id == dep_id
            assert result.dependency_type == DependencyType.SS
            assert result.lag == 3
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(updated_dep)

    @pytest.mark.asyncio
    async def test_update_dependency_not_found(self):
        """Should raise NotFoundError when dependency does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock()
        dep_id = uuid4()

        from src.schemas.dependency import DependencyUpdate

        update_data = DependencyUpdate(lag=5)

        with patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls:
            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_id = AsyncMock(return_value=None)
            mock_dep_repo_cls.return_value = mock_dep_repo

            with pytest.raises(NotFoundError) as exc_info:
                await update_dependency(dep_id, update_data, mock_db, mock_user)

            assert exc_info.value.code == "DEPENDENCY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_dependency_not_authorized(self):
        """Should raise AuthorizationError when user does not own the program."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock(is_admin=False)

        program_id = uuid4()
        predecessor_id = uuid4()
        dep_id = uuid4()

        from src.schemas.dependency import DependencyUpdate

        update_data = DependencyUpdate(lag=2)

        mock_dep = _make_dependency_mock(dep_id=dep_id, predecessor_id=predecessor_id)
        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=program_id)
        mock_program = _make_program_mock(program_id=program_id, owner_id=uuid4())

        with (
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_id = AsyncMock(return_value=mock_dep)
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_predecessor)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await update_dependency(dep_id, update_data, mock_db, mock_user)

            assert exc_info.value.code == "NOT_AUTHORIZED"


class TestDeleteDependency:
    """Tests for delete_dependency endpoint."""

    @pytest.mark.asyncio
    async def test_delete_dependency_success(self):
        """Should delete dependency and commit successfully."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_user_mock(user_id=user_id)

        program_id = uuid4()
        predecessor_id = uuid4()
        dep_id = uuid4()

        mock_dep = _make_dependency_mock(dep_id=dep_id, predecessor_id=predecessor_id)
        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=program_id)
        mock_program = _make_program_mock(program_id=program_id, owner_id=user_id)

        with (
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_id = AsyncMock(return_value=mock_dep)
            mock_dep_repo.delete = AsyncMock(return_value=None)
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_predecessor)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            result = await delete_dependency(dep_id, mock_db, mock_user)

            assert result is None
            mock_dep_repo.delete.assert_called_once_with(dep_id)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_dependency_not_found(self):
        """Should raise NotFoundError when dependency does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock()
        dep_id = uuid4()

        with patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls:
            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_id = AsyncMock(return_value=None)
            mock_dep_repo_cls.return_value = mock_dep_repo

            with pytest.raises(NotFoundError) as exc_info:
                await delete_dependency(dep_id, mock_db, mock_user)

            assert exc_info.value.code == "DEPENDENCY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_dependency_not_authorized(self):
        """Should raise AuthorizationError when user does not own the program."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock(is_admin=False)

        program_id = uuid4()
        predecessor_id = uuid4()
        dep_id = uuid4()

        mock_dep = _make_dependency_mock(dep_id=dep_id, predecessor_id=predecessor_id)
        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=program_id)
        mock_program = _make_program_mock(program_id=program_id, owner_id=uuid4())

        with (
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_id = AsyncMock(return_value=mock_dep)
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_predecessor)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await delete_dependency(dep_id, mock_db, mock_user)

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_delete_dependency_admin_bypass(self):
        """Should allow admin to delete dependency for any program."""
        mock_db = AsyncMock()
        mock_user = _make_user_mock(is_admin=True)

        program_id = uuid4()
        predecessor_id = uuid4()
        dep_id = uuid4()

        mock_dep = _make_dependency_mock(dep_id=dep_id, predecessor_id=predecessor_id)
        mock_predecessor = _make_activity_mock(activity_id=predecessor_id, program_id=program_id)
        # Program owned by someone else
        mock_program = _make_program_mock(program_id=program_id, owner_id=uuid4())

        with (
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_id = AsyncMock(return_value=mock_dep)
            mock_dep_repo.delete = AsyncMock(return_value=None)
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_predecessor)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            result = await delete_dependency(dep_id, mock_db, mock_user)

            assert result is None
            mock_dep_repo.delete.assert_called_once_with(dep_id)
            mock_db.commit.assert_called_once()


class TestWouldCreateCycle:
    """Tests for the would_create_cycle helper function."""

    @pytest.mark.asyncio
    async def test_no_cycle_detected(self):
        """Should return False when no cycle would be created."""
        mock_db = AsyncMock()
        program_id = uuid4()
        predecessor_id = uuid4()
        successor_id = uuid4()

        mock_activities = [MagicMock(), MagicMock()]
        mock_deps = []

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.CPMEngine") as mock_cpm_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_program = AsyncMock(return_value=mock_activities)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_program = AsyncMock(return_value=mock_deps)
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_engine = MagicMock()
            mock_engine._detect_cycles.return_value = None
            mock_cpm_cls.return_value = mock_engine

            has_cycle, path = await would_create_cycle(
                mock_db, program_id, predecessor_id, successor_id
            )

            assert has_cycle is False
            assert path is None

    @pytest.mark.asyncio
    async def test_cycle_detected(self):
        """Should return True with cycle path when cycle would be created."""
        mock_db = AsyncMock()
        program_id = uuid4()
        predecessor_id = uuid4()
        successor_id = uuid4()

        mock_activities = [MagicMock(), MagicMock()]
        mock_deps = []
        cycle_path = [predecessor_id, successor_id, predecessor_id]

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.CPMEngine") as mock_cpm_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_program = AsyncMock(return_value=mock_activities)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_program = AsyncMock(return_value=mock_deps)
            mock_dep_repo_cls.return_value = mock_dep_repo

            mock_engine = MagicMock()
            mock_engine._detect_cycles.return_value = cycle_path
            mock_cpm_cls.return_value = mock_engine

            has_cycle, path = await would_create_cycle(
                mock_db, program_id, predecessor_id, successor_id
            )

            assert has_cycle is True
            assert path == cycle_path

    @pytest.mark.asyncio
    async def test_no_activities_returns_no_cycle(self):
        """Should return False when program has no activities."""
        mock_db = AsyncMock()
        program_id = uuid4()
        predecessor_id = uuid4()
        successor_id = uuid4()

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_program = AsyncMock(return_value=[])
            mock_act_repo_cls.return_value = mock_act_repo

            mock_dep_repo = MagicMock()
            mock_dep_repo_cls.return_value = mock_dep_repo

            has_cycle, path = await would_create_cycle(
                mock_db, program_id, predecessor_id, successor_id
            )

            assert has_cycle is False
            assert path is None

    @pytest.mark.asyncio
    async def test_cycle_detected_via_exception(self):
        """Should catch CircularDependencyError from CPMEngine and return cycle path."""
        mock_db = AsyncMock()
        program_id = uuid4()
        predecessor_id = uuid4()
        successor_id = uuid4()

        mock_activities = [MagicMock()]
        cycle_path = [predecessor_id, successor_id, predecessor_id]

        with (
            patch("src.api.v1.endpoints.dependencies.ActivityRepository") as mock_act_repo_cls,
            patch("src.api.v1.endpoints.dependencies.DependencyRepository") as mock_dep_repo_cls,
            patch("src.api.v1.endpoints.dependencies.CPMEngine") as mock_cpm_cls,
        ):
            mock_act_repo = MagicMock()
            mock_act_repo.get_by_program = AsyncMock(return_value=mock_activities)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_dep_repo = MagicMock()
            mock_dep_repo.get_by_program = AsyncMock(return_value=[])
            mock_dep_repo_cls.return_value = mock_dep_repo

            error = CircularDependencyError(cycle_path)
            mock_cpm_cls.side_effect = error

            has_cycle, path = await would_create_cycle(
                mock_db, program_id, predecessor_id, successor_id
            )

            assert has_cycle is True
            assert path == cycle_path
