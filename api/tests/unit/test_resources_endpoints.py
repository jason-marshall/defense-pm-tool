"""Unit tests for resource management endpoints."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.resources import (
    create_assignment,
    create_calendar_entries,
    create_resource,
    delete_assignment,
    delete_calendar_range,
    delete_resource,
    get_assignment,
    get_resource,
    get_resource_calendar,
    list_resource_assignments,
    list_resources,
    update_assignment,
    update_resource,
)
from src.core.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from src.models.enums import ResourceType


def _make_mock_user(*, is_admin: bool = False) -> MagicMock:
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.is_admin = is_admin
    return user


def _make_mock_program(owner_id) -> MagicMock:
    """Create a mock program."""
    program = MagicMock()
    program.id = uuid4()
    program.owner_id = owner_id
    return program


def _make_mock_resource(program_id, code: str = "ENG-001") -> MagicMock:
    """Create a mock resource."""
    resource = MagicMock()
    resource.id = uuid4()
    resource.program_id = program_id
    resource.code = code
    resource.name = "Engineer"
    resource.resource_type = ResourceType.LABOR
    resource.capacity_per_day = Decimal("8.0")
    resource.cost_rate = Decimal("100.00")
    resource.effective_date = None
    resource.is_active = True
    resource.quantity_unit = None
    resource.unit_cost = None
    resource.quantity_available = None
    resource.created_at = datetime.now(UTC)
    resource.updated_at = None
    return resource


def _make_mock_assignment(resource_id, activity_id) -> MagicMock:
    """Create a mock assignment."""
    assignment = MagicMock()
    assignment.id = uuid4()
    assignment.resource_id = resource_id
    assignment.activity_id = activity_id
    assignment.units = Decimal("1.0")
    assignment.start_date = None
    assignment.finish_date = None
    assignment.planned_hours = None
    assignment.actual_hours = Decimal("0")
    assignment.planned_cost = None
    assignment.actual_cost = Decimal("0")
    assignment.quantity_assigned = None
    assignment.quantity_consumed = Decimal("0")
    assignment.resource = None
    return assignment


# =============================================================================
# Resource CRUD Tests
# =============================================================================


class TestCreateResource:
    """Tests for create_resource endpoint."""

    @pytest.mark.asyncio
    async def test_create_resource_success(self):
        """Should create resource when user owns the program."""
        from src.schemas.resource import ResourceCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id

        mock_resource = _make_mock_resource(program_id)

        resource_in = ResourceCreate(
            program_id=program_id,
            name="Engineer",
            code="ENG-001",
            resource_type=ResourceType.LABOR,
            capacity_per_day=Decimal("8.0"),
        )

        with (
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_res_repo = MagicMock()
            mock_res_repo.code_exists = AsyncMock(return_value=False)
            mock_res_repo.create = AsyncMock(return_value=mock_resource)
            mock_res_repo_cls.return_value = mock_res_repo

            result = await create_resource(resource_in, mock_db, mock_user)

            assert result.id == mock_resource.id
            assert result.code == "ENG-001"
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_resource_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        from src.schemas.resource import ResourceCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program_id = uuid4()

        resource_in = ResourceCreate(
            program_id=program_id,
            name="Engineer",
            code="ENG-001",
        )

        with patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=None)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_resource(resource_in, mock_db, mock_user)

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_resource_not_authorized(self):
        """Should raise AuthorizationError when user does not own program."""
        from src.schemas.resource import ResourceCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=False)
        other_owner_id = uuid4()
        mock_program = _make_mock_program(other_owner_id)
        program_id = mock_program.id

        resource_in = ResourceCreate(
            program_id=program_id,
            name="Engineer",
            code="ENG-001",
        )

        with patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError) as exc_info:
                await create_resource(resource_in, mock_db, mock_user)

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_create_resource_admin_bypasses_ownership(self):
        """Should allow admin to create resource in any program."""
        from src.schemas.resource import ResourceCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=True)
        other_owner_id = uuid4()
        mock_program = _make_mock_program(other_owner_id)
        program_id = mock_program.id

        mock_resource = _make_mock_resource(program_id)

        resource_in = ResourceCreate(
            program_id=program_id,
            name="Engineer",
            code="ENG-001",
        )

        with (
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_res_repo = MagicMock()
            mock_res_repo.code_exists = AsyncMock(return_value=False)
            mock_res_repo.create = AsyncMock(return_value=mock_resource)
            mock_res_repo_cls.return_value = mock_res_repo

            result = await create_resource(resource_in, mock_db, mock_user)

            assert result.id == mock_resource.id
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_resource_duplicate_code(self):
        """Should raise ConflictError when resource code already exists."""
        from src.schemas.resource import ResourceCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id

        resource_in = ResourceCreate(
            program_id=program_id,
            name="Engineer",
            code="ENG-001",
        )

        with (
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_res_repo = MagicMock()
            mock_res_repo.code_exists = AsyncMock(return_value=True)
            mock_res_repo_cls.return_value = mock_res_repo

            with pytest.raises(ConflictError) as exc_info:
                await create_resource(resource_in, mock_db, mock_user)

            assert exc_info.value.code == "DUPLICATE_RESOURCE_CODE"


class TestListResources:
    """Tests for list_resources endpoint."""

    @pytest.mark.asyncio
    async def test_list_resources_success(self):
        """Should return paginated list of resources."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id

        mock_r1 = _make_mock_resource(program_id, code="ENG-001")
        mock_r2 = _make_mock_resource(program_id, code="ENG-002")

        with (
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_res_repo = MagicMock()
            mock_res_repo.get_by_program = AsyncMock(return_value=([mock_r1, mock_r2], 2))
            mock_res_repo_cls.return_value = mock_res_repo

            result = await list_resources(mock_db, mock_user, program_id=program_id)

            assert result.total == 2
            assert result.page == 1
            assert result.page_size == 50
            assert result.pages == 1
            assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_list_resources_empty(self):
        """Should return empty list when no resources exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id

        with (
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
        ):
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_res_repo = MagicMock()
            mock_res_repo.get_by_program = AsyncMock(return_value=([], 0))
            mock_res_repo_cls.return_value = mock_res_repo

            result = await list_resources(mock_db, mock_user, program_id=program_id)

            assert result.total == 0
            assert result.pages == 0
            assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_list_resources_not_authorized(self):
        """Should raise AuthorizationError when user does not own program."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=False)
        mock_program = _make_mock_program(uuid4())
        program_id = mock_program.id

        with patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls:
            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(AuthorizationError):
                await list_resources(mock_db, mock_user, program_id=program_id)


class TestGetResource:
    """Tests for get_resource endpoint."""

    @pytest.mark.asyncio
    async def test_get_resource_success(self):
        """Should return resource details."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id
        mock_resource = _make_mock_resource(program_id)
        resource_id = mock_resource.id

        with (
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_res_repo_cls.return_value = mock_res_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            result = await get_resource(resource_id, mock_db, mock_user)

            assert result.id == resource_id
            assert result.code == "ENG-001"

    @pytest.mark.asyncio
    async def test_get_resource_not_found(self):
        """Should raise NotFoundError when resource does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        resource_id = uuid4()

        with patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls:
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=None)
            mock_res_repo_cls.return_value = mock_res_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_resource(resource_id, mock_db, mock_user)

            assert exc_info.value.code == "RESOURCE_NOT_FOUND"


class TestUpdateResource:
    """Tests for update_resource endpoint."""

    @pytest.mark.asyncio
    async def test_update_resource_success(self):
        """Should update resource fields."""
        from src.schemas.resource import ResourceUpdate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id
        mock_resource = _make_mock_resource(program_id)
        resource_id = mock_resource.id

        updated_resource = _make_mock_resource(program_id, code="ENG-001")
        updated_resource.id = resource_id
        updated_resource.name = "Senior Engineer"

        resource_in = ResourceUpdate(name="Senior Engineer")

        with (
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_res_repo.code_exists = AsyncMock(return_value=False)
            mock_res_repo.update = AsyncMock(return_value=updated_resource)
            mock_res_repo_cls.return_value = mock_res_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            result = await update_resource(resource_id, resource_in, mock_db, mock_user)

            assert result.name == "Senior Engineer"
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_resource_duplicate_code(self):
        """Should raise ConflictError when changing to existing code."""
        from src.schemas.resource import ResourceUpdate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id
        mock_resource = _make_mock_resource(program_id, code="ENG-001")
        resource_id = mock_resource.id

        resource_in = ResourceUpdate(code="ENG-002")

        with (
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_res_repo.code_exists = AsyncMock(return_value=True)
            mock_res_repo_cls.return_value = mock_res_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            with pytest.raises(ConflictError) as exc_info:
                await update_resource(resource_id, resource_in, mock_db, mock_user)

            assert exc_info.value.code == "DUPLICATE_RESOURCE_CODE"

    @pytest.mark.asyncio
    async def test_update_resource_not_found(self):
        """Should raise NotFoundError when resource does not exist."""
        from src.schemas.resource import ResourceUpdate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        resource_id = uuid4()

        resource_in = ResourceUpdate(name="Updated")

        with patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls:
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=None)
            mock_res_repo_cls.return_value = mock_res_repo

            with pytest.raises(NotFoundError) as exc_info:
                await update_resource(resource_id, resource_in, mock_db, mock_user)

            assert exc_info.value.code == "RESOURCE_NOT_FOUND"


class TestDeleteResource:
    """Tests for delete_resource endpoint."""

    @pytest.mark.asyncio
    async def test_delete_resource_success(self):
        """Should soft-delete resource and return message."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id
        mock_resource = _make_mock_resource(program_id)
        resource_id = mock_resource.id

        with (
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_res_repo.delete = AsyncMock(return_value=None)
            mock_res_repo_cls.return_value = mock_res_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            result = await delete_resource(resource_id, mock_db, mock_user)

            assert result.message == "Resource deleted successfully"
            mock_res_repo.delete.assert_called_once_with(resource_id)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_resource_not_found(self):
        """Should raise NotFoundError when resource does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        resource_id = uuid4()

        with patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls:
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=None)
            mock_res_repo_cls.return_value = mock_res_repo

            with pytest.raises(NotFoundError) as exc_info:
                await delete_resource(resource_id, mock_db, mock_user)

            assert exc_info.value.code == "RESOURCE_NOT_FOUND"


# =============================================================================
# Resource Assignment Tests
# =============================================================================


class TestCreateAssignment:
    """Tests for create_assignment endpoint."""

    @pytest.mark.asyncio
    async def test_create_assignment_success(self):
        """Should create assignment when resource and activity are valid."""
        from src.schemas.resource import ResourceAssignmentCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id
        mock_resource = _make_mock_resource(program_id)
        resource_id = mock_resource.id

        activity_id = uuid4()
        mock_activity = MagicMock()
        mock_activity.id = activity_id
        mock_activity.program_id = program_id

        mock_assignment = _make_mock_assignment(resource_id, activity_id)

        assignment_in = ResourceAssignmentCreate(
            activity_id=activity_id,
            resource_id=resource_id,
            units=Decimal("1.0"),
        )

        with (
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.resources.ActivityRepository") as mock_act_repo_cls,
            patch(
                "src.api.v1.endpoints.resources.ResourceAssignmentRepository"
            ) as mock_assign_repo_cls,
        ):
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_res_repo_cls.return_value = mock_res_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_activity)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_assign_repo = MagicMock()
            mock_assign_repo.assignment_exists = AsyncMock(return_value=False)
            mock_assign_repo.create = AsyncMock(return_value=mock_assignment)
            mock_assign_repo_cls.return_value = mock_assign_repo

            result = await create_assignment(resource_id, assignment_in, mock_db, mock_user)

            assert result.resource_id == resource_id
            assert result.activity_id == activity_id
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_assignment)

    @pytest.mark.asyncio
    async def test_create_assignment_activity_not_found(self):
        """Should raise NotFoundError when activity does not exist."""
        from src.schemas.resource import ResourceAssignmentCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id
        mock_resource = _make_mock_resource(program_id)
        resource_id = mock_resource.id
        activity_id = uuid4()

        assignment_in = ResourceAssignmentCreate(
            activity_id=activity_id,
            resource_id=resource_id,
        )

        with (
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.resources.ActivityRepository") as mock_act_repo_cls,
        ):
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_res_repo_cls.return_value = mock_res_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=None)
            mock_act_repo_cls.return_value = mock_act_repo

            with pytest.raises(NotFoundError) as exc_info:
                await create_assignment(resource_id, assignment_in, mock_db, mock_user)

            assert exc_info.value.code == "ACTIVITY_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_assignment_cross_program(self):
        """Should raise ValidationError when activity is in a different program."""
        from src.schemas.resource import ResourceAssignmentCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id
        mock_resource = _make_mock_resource(program_id)
        resource_id = mock_resource.id

        activity_id = uuid4()
        mock_activity = MagicMock()
        mock_activity.id = activity_id
        mock_activity.program_id = uuid4()  # Different program

        assignment_in = ResourceAssignmentCreate(
            activity_id=activity_id,
            resource_id=resource_id,
        )

        with (
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.resources.ActivityRepository") as mock_act_repo_cls,
        ):
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_res_repo_cls.return_value = mock_res_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_activity)
            mock_act_repo_cls.return_value = mock_act_repo

            with pytest.raises(ValidationError) as exc_info:
                await create_assignment(resource_id, assignment_in, mock_db, mock_user)

            assert exc_info.value.code == "CROSS_PROGRAM_ASSIGNMENT"

    @pytest.mark.asyncio
    async def test_create_assignment_duplicate(self):
        """Should raise ConflictError when assignment already exists."""
        from src.schemas.resource import ResourceAssignmentCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id
        mock_resource = _make_mock_resource(program_id)
        resource_id = mock_resource.id

        activity_id = uuid4()
        mock_activity = MagicMock()
        mock_activity.id = activity_id
        mock_activity.program_id = program_id

        assignment_in = ResourceAssignmentCreate(
            activity_id=activity_id,
            resource_id=resource_id,
        )

        with (
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.resources.ActivityRepository") as mock_act_repo_cls,
            patch(
                "src.api.v1.endpoints.resources.ResourceAssignmentRepository"
            ) as mock_assign_repo_cls,
        ):
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_res_repo_cls.return_value = mock_res_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_act_repo = MagicMock()
            mock_act_repo.get_by_id = AsyncMock(return_value=mock_activity)
            mock_act_repo_cls.return_value = mock_act_repo

            mock_assign_repo = MagicMock()
            mock_assign_repo.assignment_exists = AsyncMock(return_value=True)
            mock_assign_repo_cls.return_value = mock_assign_repo

            with pytest.raises(ConflictError) as exc_info:
                await create_assignment(resource_id, assignment_in, mock_db, mock_user)

            assert exc_info.value.code == "DUPLICATE_ASSIGNMENT"


class TestListResourceAssignments:
    """Tests for list_resource_assignments endpoint."""

    @pytest.mark.asyncio
    async def test_list_assignments_success(self):
        """Should return list of assignments for a resource."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id
        mock_resource = _make_mock_resource(program_id)
        resource_id = mock_resource.id

        a1 = _make_mock_assignment(resource_id, uuid4())
        a2 = _make_mock_assignment(resource_id, uuid4())

        with (
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
            patch(
                "src.api.v1.endpoints.resources.ResourceAssignmentRepository"
            ) as mock_assign_repo_cls,
        ):
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_res_repo_cls.return_value = mock_res_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_assign_repo = MagicMock()
            mock_assign_repo.get_by_resource = AsyncMock(return_value=[a1, a2])
            mock_assign_repo_cls.return_value = mock_assign_repo

            result = await list_resource_assignments(resource_id, mock_db, mock_user)

            assert result.total == 2
            assert len(result.items) == 2


# =============================================================================
# Standalone Assignment Endpoint Tests
# =============================================================================


class TestGetAssignment:
    """Tests for get_assignment endpoint (standalone router)."""

    @pytest.mark.asyncio
    async def test_get_assignment_success(self):
        """Should return assignment details."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id

        resource_id = uuid4()
        activity_id = uuid4()
        mock_assignment = _make_mock_assignment(resource_id, activity_id)
        assignment_id = mock_assignment.id

        mock_resource = _make_mock_resource(program_id)
        mock_resource.id = resource_id

        with (
            patch(
                "src.api.v1.endpoints.resources.ResourceAssignmentRepository"
            ) as mock_assign_repo_cls,
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_assign_repo = MagicMock()
            mock_assign_repo.get_by_id = AsyncMock(return_value=mock_assignment)
            mock_assign_repo_cls.return_value = mock_assign_repo

            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_res_repo_cls.return_value = mock_res_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            result = await get_assignment(assignment_id, mock_db, mock_user)

            assert result.id == assignment_id

    @pytest.mark.asyncio
    async def test_get_assignment_not_found(self):
        """Should raise NotFoundError when assignment does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        assignment_id = uuid4()

        with patch(
            "src.api.v1.endpoints.resources.ResourceAssignmentRepository"
        ) as mock_assign_repo_cls:
            mock_assign_repo = MagicMock()
            mock_assign_repo.get_by_id = AsyncMock(return_value=None)
            mock_assign_repo_cls.return_value = mock_assign_repo

            with pytest.raises(NotFoundError) as exc_info:
                await get_assignment(assignment_id, mock_db, mock_user)

            assert exc_info.value.code == "ASSIGNMENT_NOT_FOUND"


class TestUpdateAssignment:
    """Tests for update_assignment endpoint (standalone router)."""

    @pytest.mark.asyncio
    async def test_update_assignment_success(self):
        """Should update assignment fields."""
        from src.schemas.resource import ResourceAssignmentUpdate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id

        resource_id = uuid4()
        activity_id = uuid4()
        mock_assignment = _make_mock_assignment(resource_id, activity_id)
        assignment_id = mock_assignment.id

        updated_assignment = _make_mock_assignment(resource_id, activity_id)
        updated_assignment.id = assignment_id
        updated_assignment.units = Decimal("0.5")

        mock_resource = _make_mock_resource(program_id)
        mock_resource.id = resource_id

        assignment_in = ResourceAssignmentUpdate(units=Decimal("0.5"))

        with (
            patch(
                "src.api.v1.endpoints.resources.ResourceAssignmentRepository"
            ) as mock_assign_repo_cls,
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_assign_repo = MagicMock()
            mock_assign_repo.get_by_id = AsyncMock(return_value=mock_assignment)
            mock_assign_repo.update = AsyncMock(return_value=updated_assignment)
            mock_assign_repo_cls.return_value = mock_assign_repo

            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_res_repo_cls.return_value = mock_res_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            result = await update_assignment(assignment_id, assignment_in, mock_db, mock_user)

            assert result.units == Decimal("0.5")
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_assignment_not_found(self):
        """Should raise NotFoundError when assignment does not exist."""
        from src.schemas.resource import ResourceAssignmentUpdate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        assignment_id = uuid4()

        assignment_in = ResourceAssignmentUpdate(units=Decimal("0.5"))

        with patch(
            "src.api.v1.endpoints.resources.ResourceAssignmentRepository"
        ) as mock_assign_repo_cls:
            mock_assign_repo = MagicMock()
            mock_assign_repo.get_by_id = AsyncMock(return_value=None)
            mock_assign_repo_cls.return_value = mock_assign_repo

            with pytest.raises(NotFoundError) as exc_info:
                await update_assignment(assignment_id, assignment_in, mock_db, mock_user)

            assert exc_info.value.code == "ASSIGNMENT_NOT_FOUND"


class TestDeleteAssignment:
    """Tests for delete_assignment endpoint (standalone router)."""

    @pytest.mark.asyncio
    async def test_delete_assignment_success(self):
        """Should delete assignment and return message."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id

        resource_id = uuid4()
        activity_id = uuid4()
        mock_assignment = _make_mock_assignment(resource_id, activity_id)
        assignment_id = mock_assignment.id

        mock_resource = _make_mock_resource(program_id)
        mock_resource.id = resource_id

        with (
            patch(
                "src.api.v1.endpoints.resources.ResourceAssignmentRepository"
            ) as mock_assign_repo_cls,
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
        ):
            mock_assign_repo = MagicMock()
            mock_assign_repo.get_by_id = AsyncMock(return_value=mock_assignment)
            mock_assign_repo.delete = AsyncMock(return_value=None)
            mock_assign_repo_cls.return_value = mock_assign_repo

            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_res_repo_cls.return_value = mock_res_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            result = await delete_assignment(assignment_id, mock_db, mock_user)

            assert result.message == "Assignment deleted successfully"
            mock_assign_repo.delete.assert_called_once_with(assignment_id)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_assignment_not_found(self):
        """Should raise NotFoundError when assignment does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        assignment_id = uuid4()

        with patch(
            "src.api.v1.endpoints.resources.ResourceAssignmentRepository"
        ) as mock_assign_repo_cls:
            mock_assign_repo = MagicMock()
            mock_assign_repo.get_by_id = AsyncMock(return_value=None)
            mock_assign_repo_cls.return_value = mock_assign_repo

            with pytest.raises(NotFoundError) as exc_info:
                await delete_assignment(assignment_id, mock_db, mock_user)

            assert exc_info.value.code == "ASSIGNMENT_NOT_FOUND"


# =============================================================================
# Resource Calendar Tests
# =============================================================================


class TestGetResourceCalendar:
    """Tests for get_resource_calendar endpoint."""

    @pytest.mark.asyncio
    async def test_get_calendar_success(self):
        """Should return calendar entries for date range."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id
        mock_resource = _make_mock_resource(program_id)
        resource_id = mock_resource.id

        start = date(2026, 3, 1)
        end = date(2026, 3, 31)

        mock_entry = MagicMock()
        mock_entry.id = uuid4()
        mock_entry.resource_id = resource_id
        mock_entry.calendar_date = date(2026, 3, 1)
        mock_entry.available_hours = Decimal("8.0")
        mock_entry.is_working_day = True

        with (
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.resources.ResourceCalendarRepository") as mock_cal_repo_cls,
        ):
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_res_repo_cls.return_value = mock_res_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_cal_repo = MagicMock()
            mock_cal_repo.get_for_date_range = AsyncMock(return_value=[mock_entry])
            mock_cal_repo.get_working_days_count = AsyncMock(return_value=22)
            mock_cal_repo.get_total_hours = AsyncMock(return_value=Decimal("176.0"))
            mock_cal_repo_cls.return_value = mock_cal_repo

            result = await get_resource_calendar(resource_id, mock_db, mock_user, start, end)

            assert result.resource_id == resource_id
            assert result.start_date == start
            assert result.end_date == end
            assert result.working_days == 22
            assert result.total_hours == Decimal("176.0")
            assert len(result.entries) == 1

    @pytest.mark.asyncio
    async def test_get_calendar_invalid_date_range(self):
        """Should raise ValidationError when end_date < start_date."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        resource_id = uuid4()

        start = date(2026, 3, 31)
        end = date(2026, 3, 1)

        with pytest.raises(ValidationError) as exc_info:
            await get_resource_calendar(resource_id, mock_db, mock_user, start, end)

        assert exc_info.value.code == "INVALID_DATE_RANGE"


class TestCreateCalendarEntries:
    """Tests for create_calendar_entries endpoint."""

    @pytest.mark.asyncio
    async def test_create_calendar_entries_success(self):
        """Should bulk-create calendar entries."""
        from src.schemas.resource import (
            ResourceCalendarBulkCreate,
            ResourceCalendarEntry,
        )

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id
        mock_resource = _make_mock_resource(program_id)
        resource_id = mock_resource.id

        mock_entry = MagicMock()
        mock_entry.id = uuid4()
        mock_entry.resource_id = resource_id
        mock_entry.calendar_date = date(2026, 3, 1)
        mock_entry.available_hours = Decimal("8.0")
        mock_entry.is_working_day = True

        calendar_in = ResourceCalendarBulkCreate(
            resource_id=resource_id,
            entries=[
                ResourceCalendarEntry(
                    calendar_date=date(2026, 3, 1),
                    available_hours=Decimal("8.0"),
                    is_working_day=True,
                ),
            ],
        )

        with (
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.resources.ResourceCalendarRepository") as mock_cal_repo_cls,
        ):
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_res_repo_cls.return_value = mock_res_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_cal_repo = MagicMock()
            mock_cal_repo.delete_range = AsyncMock(return_value=0)
            mock_cal_repo.bulk_create_entries = AsyncMock(return_value=[mock_entry])
            mock_cal_repo_cls.return_value = mock_cal_repo

            result = await create_calendar_entries(resource_id, calendar_in, mock_db, mock_user)

            assert len(result) == 1
            mock_cal_repo.delete_range.assert_called_once()
            mock_cal_repo.bulk_create_entries.assert_called_once()
            mock_db.commit.assert_called_once()


class TestDeleteCalendarRange:
    """Tests for delete_calendar_range endpoint."""

    @pytest.mark.asyncio
    async def test_delete_calendar_range_success(self):
        """Should delete calendar entries in date range."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program(mock_user.id)
        program_id = mock_program.id
        mock_resource = _make_mock_resource(program_id)
        resource_id = mock_resource.id

        start = date(2026, 3, 1)
        end = date(2026, 3, 31)

        with (
            patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls,
            patch("src.api.v1.endpoints.resources.ProgramRepository") as mock_prog_repo_cls,
            patch("src.api.v1.endpoints.resources.ResourceCalendarRepository") as mock_cal_repo_cls,
        ):
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=mock_resource)
            mock_res_repo_cls.return_value = mock_res_repo

            mock_prog_repo = MagicMock()
            mock_prog_repo.get_by_id = AsyncMock(return_value=mock_program)
            mock_prog_repo_cls.return_value = mock_prog_repo

            mock_cal_repo = MagicMock()
            mock_cal_repo.delete_range = AsyncMock(return_value=5)
            mock_cal_repo_cls.return_value = mock_cal_repo

            result = await delete_calendar_range(resource_id, mock_db, mock_user, start, end)

            assert "5" in result.message
            assert "calendar entries" in result.message.lower()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_calendar_range_invalid_dates(self):
        """Should raise ValidationError when end_date < start_date."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        resource_id = uuid4()

        start = date(2026, 3, 31)
        end = date(2026, 3, 1)

        with pytest.raises(ValidationError) as exc_info:
            await delete_calendar_range(resource_id, mock_db, mock_user, start, end)

        assert exc_info.value.code == "INVALID_DATE_RANGE"

    @pytest.mark.asyncio
    async def test_delete_calendar_range_resource_not_found(self):
        """Should raise NotFoundError when resource does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        resource_id = uuid4()

        start = date(2026, 3, 1)
        end = date(2026, 3, 31)

        with patch("src.api.v1.endpoints.resources.ResourceRepository") as mock_res_repo_cls:
            mock_res_repo = MagicMock()
            mock_res_repo.get_by_id = AsyncMock(return_value=None)
            mock_res_repo_cls.return_value = mock_res_repo

            with pytest.raises(NotFoundError) as exc_info:
                await delete_calendar_range(resource_id, mock_db, mock_user, start, end)

            assert exc_info.value.code == "RESOURCE_NOT_FOUND"
