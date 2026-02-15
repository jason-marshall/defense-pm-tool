"""Unit tests for scenario management endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.scenarios import (
    activate_scenario,
    add_change,
    apply_scenario_changes,
    archive_scenario,
    compare_scenario_to_baseline,
    create_scenario,
    delete_scenario,
    get_scenario,
    get_scenario_summary,
    list_changes,
    list_scenarios,
    promote_scenario,
    remove_change,
    simulate_scenario,
    update_scenario,
)
from src.core.exceptions import AuthorizationError, NotFoundError, ValidationError


def _make_mock_scenario(**overrides):
    """Build a mock scenario with sensible defaults."""
    now = datetime.now(UTC)
    mock = MagicMock()
    mock.id = overrides.get("id", uuid4())
    mock.program_id = overrides.get("program_id", uuid4())
    mock.baseline_id = overrides.get("baseline_id")
    mock.parent_scenario_id = overrides.get("parent_scenario_id")
    mock.name = overrides.get("name", "Test Scenario")
    mock.description = overrides.get("description", "A test scenario")
    mock.status = overrides.get("status", "draft")
    mock.is_active = overrides.get("is_active", True)
    mock.change_count = overrides.get("change_count", 0)
    mock.has_cached_results = overrides.get("has_cached_results", False)
    mock.created_at = overrides.get("created_at", now)
    mock.created_by_id = overrides.get("created_by_id", uuid4())
    mock.promoted_at = overrides.get("promoted_at")
    mock.promoted_baseline_id = overrides.get("promoted_baseline_id")
    mock.changes = overrides.get("changes", [])
    mock.results_cache = overrides.get("results_cache")
    mock.updated_at = overrides.get("updated_at", now)
    return mock


def _make_mock_program(owner_id=None):
    """Build a mock program."""
    mock = MagicMock()
    mock.id = uuid4()
    mock.owner_id = owner_id or uuid4()
    mock.name = "Test Program"
    return mock


def _make_mock_user(user_id=None, is_admin=False):
    """Build a mock user."""
    mock = MagicMock()
    mock.id = user_id or uuid4()
    mock.is_admin = is_admin
    mock.full_name = "Test User"
    return mock


def _make_mock_change(**overrides):
    """Build a mock scenario change."""
    now = datetime.now(UTC)
    mock = MagicMock()
    mock.id = overrides.get("id", uuid4())
    mock.scenario_id = overrides.get("scenario_id", uuid4())
    mock.entity_type = overrides.get("entity_type", "activity")
    mock.entity_id = overrides.get("entity_id", uuid4())
    mock.entity_code = overrides.get("entity_code", "ACT-001")
    mock.change_type = overrides.get("change_type", "update")
    mock.field_name = overrides.get("field_name", "duration")
    mock.old_value = overrides.get("old_value", 10)
    mock.new_value = overrides.get("new_value", 15)
    mock.created_at = overrides.get("created_at", now)
    return mock


class TestListScenarios:
    """Tests for list_scenarios endpoint."""

    @pytest.mark.asyncio
    async def test_list_scenarios_success(self):
        """Should return paginated list of scenarios for a program."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program_id = uuid4()

        scenario1 = _make_mock_scenario(program_id=program_id)
        scenario2 = _make_mock_scenario(program_id=program_id)

        mock_program = _make_mock_program()

        with (
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockScenarioRepo.return_value.get_by_program = AsyncMock(
                return_value=[scenario1, scenario2]
            )
            MockScenarioRepo.return_value.count_by_program = AsyncMock(return_value=2)

            result = await list_scenarios(
                db=mock_db,
                current_user=mock_user,
                program_id=program_id,
                page=1,
                per_page=20,
                active_only=False,
            )

            assert result.total == 2
            assert result.page == 1
            assert result.per_page == 20
            assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_list_scenarios_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()

        with patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo:
            MockProgramRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await list_scenarios(
                    db=mock_db,
                    current_user=mock_user,
                    program_id=uuid4(),
                    page=1,
                    per_page=20,
                    active_only=False,
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_list_scenarios_empty(self):
        """Should return empty list when no scenarios exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        program_id = uuid4()
        mock_program = _make_mock_program()

        with (
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockScenarioRepo.return_value.get_by_program = AsyncMock(return_value=[])
            MockScenarioRepo.return_value.count_by_program = AsyncMock(return_value=0)

            result = await list_scenarios(
                db=mock_db,
                current_user=mock_user,
                program_id=program_id,
                page=1,
                per_page=20,
                active_only=False,
            )

            assert result.total == 0
            assert result.pages == 1
            assert len(result.items) == 0


class TestCreateScenario:
    """Tests for create_scenario endpoint."""

    @pytest.mark.asyncio
    async def test_create_scenario_success(self):
        """Should create a new scenario from scratch."""
        from src.schemas.scenario import ScenarioCreate

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # db.add is sync, not async
        mock_user = _make_mock_user()
        program_id = uuid4()

        mock_program = _make_mock_program()
        created_scenario = _make_mock_scenario(program_id=program_id)

        scenario_data = ScenarioCreate(
            name="What-if Scenario",
            description="Test what-if",
            program_id=program_id,
        )

        with (
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
            patch("src.api.v1.endpoints.scenarios.Scenario", create=True),
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockScenarioRepo.return_value.get_with_changes = AsyncMock(
                return_value=created_scenario
            )

            result = await create_scenario(
                db=mock_db,
                current_user=mock_user,
                scenario_data=scenario_data,
            )

            assert result.name == created_scenario.name
            assert result.program_id == created_scenario.program_id
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_scenario_program_not_found(self):
        """Should raise NotFoundError when program does not exist."""
        from src.schemas.scenario import ScenarioCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()

        scenario_data = ScenarioCreate(
            name="Scenario",
            program_id=uuid4(),
        )

        with patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo:
            MockProgramRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await create_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_data=scenario_data,
                )

            assert exc_info.value.code == "PROGRAM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_scenario_baseline_not_found(self):
        """Should raise NotFoundError when baseline does not exist."""
        from src.schemas.scenario import ScenarioCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program()

        scenario_data = ScenarioCreate(
            name="Scenario",
            program_id=uuid4(),
            baseline_id=uuid4(),
        )

        with (
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.scenarios.BaselineRepository") as MockBaselineRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockBaselineRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await create_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_data=scenario_data,
                )

            assert exc_info.value.code == "BASELINE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_scenario_branch_from_parent(self):
        """Should branch from parent scenario when parent_scenario_id is set."""
        from src.schemas.scenario import ScenarioCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program()
        parent_id = uuid4()
        branched = _make_mock_scenario(parent_scenario_id=parent_id)

        scenario_data = ScenarioCreate(
            name="Branched Scenario",
            program_id=uuid4(),
            parent_scenario_id=parent_id,
        )

        with (
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockScenarioRepo.return_value.branch_from_scenario = AsyncMock(return_value=branched)
            MockScenarioRepo.return_value.get_with_changes = AsyncMock(return_value=branched)

            result = await create_scenario(
                db=mock_db,
                current_user=mock_user,
                scenario_data=scenario_data,
            )

            assert result.parent_scenario_id == parent_id
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_scenario_parent_not_found(self):
        """Should raise NotFoundError when parent scenario does not exist."""
        from src.schemas.scenario import ScenarioCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        mock_program = _make_mock_program()

        scenario_data = ScenarioCreate(
            name="Branched",
            program_id=uuid4(),
            parent_scenario_id=uuid4(),
        )

        with (
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
        ):
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockScenarioRepo.return_value.branch_from_scenario = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await create_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_data=scenario_data,
                )

            assert exc_info.value.code == "PARENT_SCENARIO_NOT_FOUND"


class TestGetScenario:
    """Tests for get_scenario endpoint."""

    @pytest.mark.asyncio
    async def test_get_scenario_with_changes(self):
        """Should return scenario with change details."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario = _make_mock_scenario()

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get_with_changes = AsyncMock(return_value=scenario)

            result = await get_scenario(
                db=mock_db,
                current_user=mock_user,
                scenario_id=scenario.id,
                include_changes=True,
            )

            assert result.id == scenario.id
            assert result.name == scenario.name
            MockRepo.return_value.get_with_changes.assert_called_once_with(scenario.id)

    @pytest.mark.asyncio
    async def test_get_scenario_without_changes(self):
        """Should return scenario metadata only when include_changes is False."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario = _make_mock_scenario()

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=scenario)

            result = await get_scenario(
                db=mock_db,
                current_user=mock_user,
                scenario_id=scenario.id,
                include_changes=False,
            )

            assert result.id == scenario.id
            MockRepo.return_value.get.assert_called_once_with(scenario.id)

    @pytest.mark.asyncio
    async def test_get_scenario_not_found(self):
        """Should raise NotFoundError when scenario does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get_with_changes = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await get_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=uuid4(),
                    include_changes=True,
                )

            assert exc_info.value.code == "SCENARIO_NOT_FOUND"


class TestUpdateScenario:
    """Tests for update_scenario endpoint."""

    @pytest.mark.asyncio
    async def test_update_scenario_success(self):
        """Should update scenario metadata."""
        from src.schemas.scenario import ScenarioUpdate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario = _make_mock_scenario(status="draft")
        updated_scenario = _make_mock_scenario(id=scenario.id, name="Updated Name", status="draft")

        update_data = ScenarioUpdate(name="Updated Name")

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=scenario)
            MockRepo.return_value.get_with_changes = AsyncMock(return_value=updated_scenario)

            result = await update_scenario(
                db=mock_db,
                current_user=mock_user,
                scenario_id=scenario.id,
                update_data=update_data,
            )

            assert result.name == "Updated Name"
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_scenario_not_found(self):
        """Should raise NotFoundError when scenario does not exist."""
        from src.schemas.scenario import ScenarioUpdate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        update_data = ScenarioUpdate(name="New Name")

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await update_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=uuid4(),
                    update_data=update_data,
                )

            assert exc_info.value.code == "SCENARIO_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_promoted_scenario_raises_validation_error(self):
        """Should raise ValidationError when trying to update a promoted scenario."""
        from src.schemas.scenario import ScenarioUpdate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario = _make_mock_scenario(status="promoted")
        update_data = ScenarioUpdate(name="New Name")

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=scenario)

            with pytest.raises(ValidationError) as exc_info:
                await update_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=scenario.id,
                    update_data=update_data,
                )

            assert exc_info.value.code == "PROMOTED_SCENARIO_MODIFY"


class TestDeleteScenario:
    """Tests for delete_scenario endpoint."""

    @pytest.mark.asyncio
    async def test_delete_scenario_success(self):
        """Should soft delete a scenario."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario = _make_mock_scenario(status="draft")

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=scenario)
            MockRepo.return_value.delete = AsyncMock()

            result = await delete_scenario(
                db=mock_db,
                current_user=mock_user,
                scenario_id=scenario.id,
            )

            assert result is None
            MockRepo.return_value.delete.assert_called_once_with(scenario.id)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_scenario_not_found(self):
        """Should raise NotFoundError when scenario does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await delete_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=uuid4(),
                )

            assert exc_info.value.code == "SCENARIO_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_promoted_scenario_raises_validation_error(self):
        """Should raise ValidationError when trying to delete a promoted scenario."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario = _make_mock_scenario(status="promoted")

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=scenario)

            with pytest.raises(ValidationError) as exc_info:
                await delete_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=scenario.id,
                )

            assert exc_info.value.code == "PROMOTED_SCENARIO_DELETE"


class TestAddChange:
    """Tests for add_change endpoint."""

    @pytest.mark.asyncio
    async def test_add_change_success(self):
        """Should add a change to a scenario."""
        from src.schemas.scenario import ChangeType, EntityType, ScenarioChangeCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario = _make_mock_scenario(status="draft")
        mock_change = _make_mock_change(scenario_id=scenario.id)

        change_data = ScenarioChangeCreate(
            entity_type=EntityType.ACTIVITY,
            entity_id=uuid4(),
            entity_code="ACT-001",
            change_type=ChangeType.UPDATE,
            field_name="duration",
            old_value=10,
            new_value=15,
        )

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=scenario)
            MockRepo.return_value.add_change = AsyncMock(return_value=mock_change)

            result = await add_change(
                db=mock_db,
                current_user=mock_user,
                scenario_id=scenario.id,
                change_data=change_data,
            )

            assert result.scenario_id == scenario.id
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_change_scenario_not_found(self):
        """Should raise NotFoundError when scenario does not exist."""
        from src.schemas.scenario import ChangeType, EntityType, ScenarioChangeCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()

        change_data = ScenarioChangeCreate(
            entity_type=EntityType.ACTIVITY,
            entity_id=uuid4(),
            change_type=ChangeType.UPDATE,
            field_name="duration",
            new_value=15,
        )

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await add_change(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=uuid4(),
                    change_data=change_data,
                )

            assert exc_info.value.code == "SCENARIO_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_add_change_promoted_scenario_raises_validation_error(self):
        """Should raise ValidationError when adding change to promoted scenario."""
        from src.schemas.scenario import ChangeType, EntityType, ScenarioChangeCreate

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario = _make_mock_scenario(status="promoted")

        change_data = ScenarioChangeCreate(
            entity_type=EntityType.ACTIVITY,
            entity_id=uuid4(),
            change_type=ChangeType.UPDATE,
            field_name="duration",
            new_value=20,
        )

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=scenario)

            with pytest.raises(ValidationError) as exc_info:
                await add_change(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=scenario.id,
                    change_data=change_data,
                )

            assert exc_info.value.code == "PROMOTED_SCENARIO_MODIFY"


class TestListChanges:
    """Tests for list_changes endpoint."""

    @pytest.mark.asyncio
    async def test_list_changes_success(self):
        """Should list all changes for a scenario."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario_id = uuid4()
        scenario = _make_mock_scenario(id=scenario_id)

        change1 = _make_mock_change(scenario_id=scenario_id)
        change2 = _make_mock_change(scenario_id=scenario_id)

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=scenario)
            MockRepo.return_value.get_changes = AsyncMock(return_value=[change1, change2])

            result = await list_changes(
                db=mock_db,
                current_user=mock_user,
                scenario_id=scenario_id,
                entity_type=None,
            )

            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_changes_scenario_not_found(self):
        """Should raise NotFoundError when scenario does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await list_changes(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=uuid4(),
                    entity_type=None,
                )

            assert exc_info.value.code == "SCENARIO_NOT_FOUND"


class TestRemoveChange:
    """Tests for remove_change endpoint."""

    @pytest.mark.asyncio
    async def test_remove_change_success(self):
        """Should remove a specific change from a scenario."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario = _make_mock_scenario(status="draft")
        change_id = uuid4()

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=scenario)
            MockRepo.return_value.remove_change = AsyncMock(return_value=True)

            result = await remove_change(
                db=mock_db,
                current_user=mock_user,
                scenario_id=scenario.id,
                change_id=change_id,
            )

            assert result is None
            MockRepo.return_value.remove_change.assert_called_once_with(change_id)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_change_scenario_not_found(self):
        """Should raise NotFoundError when scenario does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await remove_change(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=uuid4(),
                    change_id=uuid4(),
                )

            assert exc_info.value.code == "SCENARIO_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_remove_change_promoted_scenario_raises_validation_error(self):
        """Should raise ValidationError when removing change from promoted scenario."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario = _make_mock_scenario(status="promoted")

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=scenario)

            with pytest.raises(ValidationError) as exc_info:
                await remove_change(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=scenario.id,
                    change_id=uuid4(),
                )

            assert exc_info.value.code == "PROMOTED_SCENARIO_MODIFY"

    @pytest.mark.asyncio
    async def test_remove_change_change_not_found(self):
        """Should raise NotFoundError when change does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario = _make_mock_scenario(status="draft")

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=scenario)
            MockRepo.return_value.remove_change = AsyncMock(return_value=False)

            with pytest.raises(NotFoundError) as exc_info:
                await remove_change(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=scenario.id,
                    change_id=uuid4(),
                )

            assert exc_info.value.code == "CHANGE_NOT_FOUND"


class TestArchiveScenario:
    """Tests for archive_scenario endpoint."""

    @pytest.mark.asyncio
    async def test_archive_scenario_success(self):
        """Should archive a scenario."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario = _make_mock_scenario(status="archived", is_active=False)

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.archive = AsyncMock(return_value=scenario)
            MockRepo.return_value.get_with_changes = AsyncMock(return_value=scenario)

            result = await archive_scenario(
                db=mock_db,
                current_user=mock_user,
                scenario_id=scenario.id,
            )

            assert result.id == scenario.id
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_archive_scenario_not_found(self):
        """Should raise NotFoundError when scenario does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.archive = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await archive_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=uuid4(),
                )

            assert exc_info.value.code == "SCENARIO_NOT_FOUND"


class TestActivateScenario:
    """Tests for activate_scenario endpoint."""

    @pytest.mark.asyncio
    async def test_activate_scenario_success(self):
        """Should activate a draft scenario."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario = _make_mock_scenario(status="draft")
        activated = _make_mock_scenario(id=scenario.id, status="active")

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=scenario)
            MockRepo.return_value.get_with_changes = AsyncMock(return_value=activated)

            result = await activate_scenario(
                db=mock_db,
                current_user=mock_user,
                scenario_id=scenario.id,
            )

            assert result.id == scenario.id
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_scenario_not_found(self):
        """Should raise NotFoundError when scenario does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await activate_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=uuid4(),
                )

            assert exc_info.value.code == "SCENARIO_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_activate_non_draft_scenario_raises_validation_error(self):
        """Should raise ValidationError when activating a non-draft scenario."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario = _make_mock_scenario(status="active")

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=scenario)

            with pytest.raises(ValidationError) as exc_info:
                await activate_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=scenario.id,
                )

            assert exc_info.value.code == "INVALID_STATUS_TRANSITION"


class TestPromoteScenario:
    """Tests for promote_scenario endpoint."""

    @pytest.mark.asyncio
    async def test_promote_scenario_success(self):
        """Should promote scenario to baseline as program owner."""
        from src.schemas.scenario import ScenarioPromoteRequest
        from src.services.scenario_promotion import PromotionResult

        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_mock_user(user_id=user_id, is_admin=False)

        program_id = uuid4()
        scenario = _make_mock_scenario(program_id=program_id)
        mock_program = _make_mock_program(owner_id=user_id)

        promote_request = ScenarioPromoteRequest(
            baseline_name="V2 Baseline",
            baseline_description="Promoted from scenario",
        )

        promotion_result = PromotionResult(
            success=True,
            scenario_id=scenario.id,
            baseline_id=uuid4(),
            baseline_name="V2 Baseline",
            baseline_version=2,
            changes_count=5,
            duration_ms=120,
        )

        with (
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.scenarios.BaselineRepository"),
            patch("src.api.v1.endpoints.scenarios.ActivityRepository"),
            patch("src.api.v1.endpoints.scenarios.WBSElementRepository"),
            patch(
                "src.services.scenario_promotion.ScenarioPromotionService"
            ) as MockPromotionService,
        ):
            MockScenarioRepo.return_value.get = AsyncMock(return_value=scenario)
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockPromotionService.return_value.promote_scenario = AsyncMock(
                return_value=promotion_result
            )

            result = await promote_scenario(
                db=mock_db,
                current_user=mock_user,
                scenario_id=scenario.id,
                promote_request=promote_request,
            )

            assert result["success"] is True
            assert result["baseline_name"] == "V2 Baseline"
            assert result["baseline_version"] == 2

    @pytest.mark.asyncio
    async def test_promote_scenario_not_found(self):
        """Should raise NotFoundError when scenario does not exist."""
        from src.schemas.scenario import ScenarioPromoteRequest

        mock_db = AsyncMock()
        mock_user = _make_mock_user()

        promote_request = ScenarioPromoteRequest(baseline_name="V2")

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await promote_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=uuid4(),
                    promote_request=promote_request,
                )

            assert exc_info.value.code == "SCENARIO_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_promote_scenario_not_authorized(self):
        """Should raise AuthorizationError when user is not owner or admin."""
        from src.schemas.scenario import ScenarioPromoteRequest

        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=False)  # Not admin

        program_id = uuid4()
        scenario = _make_mock_scenario(program_id=program_id)
        # Program owner is different from current user
        mock_program = _make_mock_program(owner_id=uuid4())

        promote_request = ScenarioPromoteRequest(baseline_name="V2")

        with (
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
        ):
            MockScenarioRepo.return_value.get = AsyncMock(return_value=scenario)
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)

            with pytest.raises(AuthorizationError) as exc_info:
                await promote_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=scenario.id,
                    promote_request=promote_request,
                )

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_promote_scenario_admin_bypasses_ownership(self):
        """Should allow admin to promote scenario regardless of ownership."""
        from src.schemas.scenario import ScenarioPromoteRequest
        from src.services.scenario_promotion import PromotionResult

        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=True)

        program_id = uuid4()
        scenario = _make_mock_scenario(program_id=program_id)
        mock_program = _make_mock_program(owner_id=uuid4())  # Different owner

        promote_request = ScenarioPromoteRequest(baseline_name="Admin Baseline")

        promotion_result = PromotionResult(
            success=True,
            scenario_id=scenario.id,
            baseline_id=uuid4(),
            baseline_name="Admin Baseline",
            baseline_version=1,
            changes_count=3,
            duration_ms=80,
        )

        with (
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.scenarios.BaselineRepository"),
            patch("src.api.v1.endpoints.scenarios.ActivityRepository"),
            patch("src.api.v1.endpoints.scenarios.WBSElementRepository"),
            patch(
                "src.services.scenario_promotion.ScenarioPromotionService"
            ) as MockPromotionService,
        ):
            MockScenarioRepo.return_value.get = AsyncMock(return_value=scenario)
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockPromotionService.return_value.promote_scenario = AsyncMock(
                return_value=promotion_result
            )

            result = await promote_scenario(
                db=mock_db,
                current_user=mock_user,
                scenario_id=scenario.id,
                promote_request=promote_request,
            )

            assert result["success"] is True


class TestApplyScenarioChanges:
    """Tests for apply_scenario_changes endpoint."""

    @pytest.mark.asyncio
    async def test_apply_changes_success(self):
        """Should apply scenario changes to program data."""
        from src.schemas.scenario import ScenarioApplyChangesRequest
        from src.services.scenario_apply import ApplyResult

        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_mock_user(user_id=user_id)

        program_id = uuid4()
        scenario = _make_mock_scenario(program_id=program_id)
        mock_program = _make_mock_program(owner_id=user_id)

        apply_request = ScenarioApplyChangesRequest(confirm=True)

        apply_result = ApplyResult(
            success=True,
            scenario_id=scenario.id,
            changes_applied=5,
            changes_failed=0,
            activities_modified=3,
            wbs_modified=1,
            dependencies_modified=1,
            errors=[],
            duration_ms=50,
        )

        with (
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.scenarios.ActivityRepository"),
            patch("src.api.v1.endpoints.scenarios.WBSElementRepository"),
            patch("src.api.v1.endpoints.scenarios.DependencyRepository"),
            patch("src.services.scenario_apply.ScenarioApplyService") as MockApplyService,
        ):
            MockScenarioRepo.return_value.get = AsyncMock(return_value=scenario)
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockApplyService.return_value.apply_changes = AsyncMock(return_value=apply_result)

            result = await apply_scenario_changes(
                db=mock_db,
                current_user=mock_user,
                scenario_id=scenario.id,
                apply_request=apply_request,
            )

            assert result["success"] is True
            assert result["changes_applied"] == 5
            assert result["summary"]["activities_modified"] == 3
            assert result["archived"] is True

    @pytest.mark.asyncio
    async def test_apply_changes_without_confirm_raises_validation_error(self):
        """Should raise ValidationError when confirm is not set to True."""
        from src.schemas.scenario import ScenarioApplyChangesRequest

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        apply_request = ScenarioApplyChangesRequest(confirm=False)

        with pytest.raises(ValidationError) as exc_info:
            await apply_scenario_changes(
                db=mock_db,
                current_user=mock_user,
                scenario_id=uuid4(),
                apply_request=apply_request,
            )

        assert exc_info.value.code == "CONFIRM_REQUIRED"

    @pytest.mark.asyncio
    async def test_apply_changes_scenario_not_found(self):
        """Should raise NotFoundError when scenario does not exist."""
        from src.schemas.scenario import ScenarioApplyChangesRequest

        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        apply_request = ScenarioApplyChangesRequest(confirm=True)

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await apply_scenario_changes(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=uuid4(),
                    apply_request=apply_request,
                )

            assert exc_info.value.code == "SCENARIO_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_apply_changes_not_authorized(self):
        """Should raise AuthorizationError when user is not owner or admin."""
        from src.schemas.scenario import ScenarioApplyChangesRequest

        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=False)

        program_id = uuid4()
        scenario = _make_mock_scenario(program_id=program_id)
        mock_program = _make_mock_program(owner_id=uuid4())  # Different owner

        apply_request = ScenarioApplyChangesRequest(confirm=True)

        with (
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
        ):
            MockScenarioRepo.return_value.get = AsyncMock(return_value=scenario)
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)

            with pytest.raises(AuthorizationError) as exc_info:
                await apply_scenario_changes(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=scenario.id,
                    apply_request=apply_request,
                )

            assert exc_info.value.code == "NOT_AUTHORIZED"


class TestGetScenarioSummary:
    """Tests for get_scenario_summary endpoint."""

    @pytest.mark.asyncio
    async def test_get_scenario_summary_success(self):
        """Should return summary of scenario changes."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()
        scenario = _make_mock_scenario(name="Summary Test")

        summary_data = {
            "activities_created": 2,
            "activities_updated": 3,
            "activities_deleted": 1,
            "dependencies_created": 1,
            "dependencies_updated": 0,
            "dependencies_deleted": 0,
            "wbs_created": 0,
            "wbs_updated": 1,
            "wbs_deleted": 0,
            "total_changes": 8,
        }

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=scenario)
            MockRepo.return_value.get_change_summary = AsyncMock(return_value=summary_data)

            result = await get_scenario_summary(
                db=mock_db,
                current_user=mock_user,
                scenario_id=scenario.id,
            )

            assert result.scenario_id == scenario.id
            assert result.scenario_name == "Summary Test"
            assert result.activities_created == 2
            assert result.activities_updated == 3
            assert result.activities_deleted == 1
            assert result.total_changes == 8

    @pytest.mark.asyncio
    async def test_get_scenario_summary_not_found(self):
        """Should raise NotFoundError when scenario does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await get_scenario_summary(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=uuid4(),
                )

            assert exc_info.value.code == "SCENARIO_NOT_FOUND"


class TestSimulateScenario:
    """Tests for simulate_scenario endpoint."""

    @pytest.mark.asyncio
    async def test_simulate_scenario_success(self):
        """Should run simulation and return results."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_mock_user(user_id=user_id)

        program_id = uuid4()
        scenario = _make_mock_scenario(program_id=program_id, name="Sim Test")
        mock_program = _make_mock_program(owner_id=user_id)

        mock_activity = MagicMock()
        mock_activity.id = uuid4()
        mock_activity.duration = 10

        mock_output = MagicMock()
        mock_output.iterations = 1000
        mock_output.elapsed_seconds = 1.5
        mock_output.seed = 42
        mock_output.project_duration_p10 = 80.0
        mock_output.project_duration_p50 = 100.0
        mock_output.project_duration_p80 = 115.0
        mock_output.project_duration_p90 = 120.0
        mock_output.project_duration_mean = 100.5
        mock_output.project_duration_std = 12.34
        mock_output.project_duration_min = 70.0
        mock_output.project_duration_max = 140.0
        mock_output.activity_criticality = {mock_activity.id: 85.0}
        mock_output.sensitivity = {mock_activity.id: 0.75}

        with (
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.scenarios.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.scenarios.DependencyRepository") as MockDepRepo,
            patch("src.api.v1.endpoints.scenarios.ScenarioSimulationService") as MockSimService,
        ):
            MockScenarioRepo.return_value.get_with_changes = AsyncMock(return_value=scenario)
            MockScenarioRepo.return_value.get_changes = AsyncMock(return_value=[])
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[mock_activity])
            MockDepRepo.return_value.get_by_program = AsyncMock(return_value=[])
            MockSimService.return_value.simulate = MagicMock(return_value=mock_output)

            result = await simulate_scenario(
                db=mock_db,
                current_user=mock_user,
                scenario_id=scenario.id,
                iterations=1000,
                seed=42,
            )

            assert result["scenario_name"] == "Sim Test"
            assert result["iterations"] == 1000
            assert result["project_duration"]["p50"] == 100.0
            assert result["project_duration"]["mean"] == 100.5

    @pytest.mark.asyncio
    async def test_simulate_scenario_not_found(self):
        """Should raise NotFoundError when scenario does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get_with_changes = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await simulate_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=uuid4(),
                    iterations=1000,
                    seed=None,
                )

            assert exc_info.value.code == "SCENARIO_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_simulate_scenario_not_authorized(self):
        """Should raise AuthorizationError when user is not owner or admin."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=False)

        program_id = uuid4()
        scenario = _make_mock_scenario(program_id=program_id)
        mock_program = _make_mock_program(owner_id=uuid4())  # Different owner

        with (
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
        ):
            MockScenarioRepo.return_value.get_with_changes = AsyncMock(return_value=scenario)
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)

            with pytest.raises(AuthorizationError) as exc_info:
                await simulate_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=scenario.id,
                    iterations=1000,
                    seed=None,
                )

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_simulate_scenario_no_activities(self):
        """Should raise ValidationError when program has no activities."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_mock_user(user_id=user_id)

        program_id = uuid4()
        scenario = _make_mock_scenario(program_id=program_id)
        mock_program = _make_mock_program(owner_id=user_id)

        with (
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.scenarios.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.scenarios.DependencyRepository") as MockDepRepo,
        ):
            MockScenarioRepo.return_value.get_with_changes = AsyncMock(return_value=scenario)
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[])
            MockDepRepo.return_value.get_by_program = AsyncMock(return_value=[])

            with pytest.raises(ValidationError) as exc_info:
                await simulate_scenario(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=scenario.id,
                    iterations=1000,
                    seed=None,
                )

            assert exc_info.value.code == "NO_ACTIVITIES"


class TestCompareScenarioToBaseline:
    """Tests for compare_scenario_to_baseline endpoint."""

    @pytest.mark.asyncio
    async def test_compare_scenario_success(self):
        """Should compare scenario simulation to baseline."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_mock_user(user_id=user_id)

        program_id = uuid4()
        scenario = _make_mock_scenario(program_id=program_id, name="Compare Test")
        mock_program = _make_mock_program(owner_id=user_id)

        mock_activity = MagicMock()
        mock_activity.id = uuid4()

        mock_baseline_output = MagicMock()
        mock_baseline_output.project_duration_p50 = 100.0
        mock_baseline_output.project_duration_p90 = 120.0
        mock_baseline_output.project_duration_mean = 101.0
        mock_baseline_output.project_duration_std = 10.0

        mock_scenario_output = MagicMock()
        mock_scenario_output.project_duration_p50 = 95.0
        mock_scenario_output.project_duration_p90 = 115.0
        mock_scenario_output.project_duration_mean = 96.0
        mock_scenario_output.project_duration_std = 9.0

        mock_comparison = MagicMock()
        mock_comparison.p50_delta = -5.0
        mock_comparison.p90_delta = -5.0
        mock_comparison.mean_delta = -5.0
        mock_comparison.std_delta = -1.0
        mock_comparison.risk_improved = True
        mock_comparison.summary = "Scenario reduces duration by 5.0 days"

        with (
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.scenarios.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.scenarios.DependencyRepository") as MockDepRepo,
            patch("src.api.v1.endpoints.scenarios.ScenarioSimulationService") as MockSimService,
            patch(
                "src.services.scenario_simulation.compare_scenario_simulations"
            ) as mock_compare_fn,
        ):
            MockScenarioRepo.return_value.get_with_changes = AsyncMock(return_value=scenario)
            MockScenarioRepo.return_value.get_changes = AsyncMock(return_value=[])
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[mock_activity])
            MockDepRepo.return_value.get_by_program = AsyncMock(return_value=[])

            # The service is instantiated twice (baseline + scenario), each calls simulate
            MockSimService.return_value.simulate = MagicMock(
                side_effect=[mock_baseline_output, mock_scenario_output]
            )
            mock_compare_fn.return_value = mock_comparison

            result = await compare_scenario_to_baseline(
                db=mock_db,
                current_user=mock_user,
                scenario_id=scenario.id,
                iterations=1000,
                seed=42,
            )

            assert result["scenario_name"] == "Compare Test"
            assert result["baseline"]["p50"] == 100.0
            assert result["scenario"]["p50"] == 95.0
            assert result["comparison"]["p50_delta"] == -5.0
            assert result["comparison"]["risk_improved"] is True

    @pytest.mark.asyncio
    async def test_compare_scenario_not_found(self):
        """Should raise NotFoundError when scenario does not exist."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user()

        with patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockRepo:
            MockRepo.return_value.get_with_changes = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError) as exc_info:
                await compare_scenario_to_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=uuid4(),
                    iterations=1000,
                    seed=None,
                )

            assert exc_info.value.code == "SCENARIO_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_compare_scenario_not_authorized(self):
        """Should raise AuthorizationError when user is not owner or admin."""
        mock_db = AsyncMock()
        mock_user = _make_mock_user(is_admin=False)

        program_id = uuid4()
        scenario = _make_mock_scenario(program_id=program_id)
        mock_program = _make_mock_program(owner_id=uuid4())

        with (
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
        ):
            MockScenarioRepo.return_value.get_with_changes = AsyncMock(return_value=scenario)
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)

            with pytest.raises(AuthorizationError) as exc_info:
                await compare_scenario_to_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=scenario.id,
                    iterations=1000,
                    seed=None,
                )

            assert exc_info.value.code == "NOT_AUTHORIZED"

    @pytest.mark.asyncio
    async def test_compare_scenario_no_activities(self):
        """Should raise ValidationError when program has no activities."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = _make_mock_user(user_id=user_id)

        program_id = uuid4()
        scenario = _make_mock_scenario(program_id=program_id)
        mock_program = _make_mock_program(owner_id=user_id)

        with (
            patch("src.api.v1.endpoints.scenarios.ScenarioRepository") as MockScenarioRepo,
            patch("src.api.v1.endpoints.scenarios.ProgramRepository") as MockProgramRepo,
            patch("src.api.v1.endpoints.scenarios.ActivityRepository") as MockActivityRepo,
            patch("src.api.v1.endpoints.scenarios.DependencyRepository") as MockDepRepo,
        ):
            MockScenarioRepo.return_value.get_with_changes = AsyncMock(return_value=scenario)
            MockProgramRepo.return_value.get = AsyncMock(return_value=mock_program)
            MockActivityRepo.return_value.get_by_program = AsyncMock(return_value=[])
            MockDepRepo.return_value.get_by_program = AsyncMock(return_value=[])

            with pytest.raises(ValidationError) as exc_info:
                await compare_scenario_to_baseline(
                    db=mock_db,
                    current_user=mock_user,
                    scenario_id=scenario.id,
                    iterations=1000,
                    seed=None,
                )

            assert exc_info.value.code == "NO_ACTIVITIES"
