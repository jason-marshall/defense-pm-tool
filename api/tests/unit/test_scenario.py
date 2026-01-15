"""Unit tests for Scenario model and schemas."""

from datetime import datetime
from uuid import uuid4

import pytest

from src.models.scenario import (
    ChangeType,
    EntityType,
    Scenario,
    ScenarioChange,
    ScenarioStatus,
)
from src.schemas.scenario import (
    ChangeType as SchemaChangeType,
)
from src.schemas.scenario import (
    EntityType as SchemaEntityType,
)
from src.schemas.scenario import (
    ScenarioBase,
    ScenarioChangeCreate,
    ScenarioChangeResponse,
    ScenarioCreate,
    ScenarioDiffSummary,
    ScenarioListResponse,
    ScenarioResponse,
    ScenarioSummary,
    ScenarioUpdate,
)
from src.schemas.scenario import (
    ScenarioStatus as SchemaScenarioStatus,
)


class TestScenarioStatusEnum:
    """Tests for ScenarioStatus enum values."""

    def test_draft_status(self):
        """Test draft status value."""
        assert ScenarioStatus.DRAFT == "draft"

    def test_active_status(self):
        """Test active status value."""
        assert ScenarioStatus.ACTIVE == "active"

    def test_promoted_status(self):
        """Test promoted status value."""
        assert ScenarioStatus.PROMOTED == "promoted"

    def test_archived_status(self):
        """Test archived status value."""
        assert ScenarioStatus.ARCHIVED == "archived"


class TestChangeTypeEnum:
    """Tests for ChangeType enum values."""

    def test_create_type(self):
        """Test create change type."""
        assert ChangeType.CREATE == "create"

    def test_update_type(self):
        """Test update change type."""
        assert ChangeType.UPDATE == "update"

    def test_delete_type(self):
        """Test delete change type."""
        assert ChangeType.DELETE == "delete"


class TestEntityTypeEnum:
    """Tests for EntityType enum values."""

    def test_activity_type(self):
        """Test activity entity type."""
        assert EntityType.ACTIVITY == "activity"

    def test_dependency_type(self):
        """Test dependency entity type."""
        assert EntityType.DEPENDENCY == "dependency"

    def test_wbs_type(self):
        """Test WBS entity type."""
        assert EntityType.WBS == "wbs"


class TestScenarioModel:
    """Tests for Scenario model."""

    def test_scenario_tablename(self):
        """Test scenario table name."""
        assert Scenario.__tablename__ == "scenarios"

    def test_is_draft_property(self):
        """Test is_draft property."""
        scenario = Scenario(
            program_id=uuid4(),
            name="Test",
            status=ScenarioStatus.DRAFT,
            created_by_id=uuid4(),
        )
        assert scenario.is_draft is True

        scenario.status = ScenarioStatus.ACTIVE
        assert scenario.is_draft is False

    def test_is_promoted_property(self):
        """Test is_promoted property."""
        scenario = Scenario(
            program_id=uuid4(),
            name="Test",
            status=ScenarioStatus.DRAFT,
            created_by_id=uuid4(),
        )
        assert scenario.is_promoted is False

        scenario.status = ScenarioStatus.PROMOTED
        assert scenario.is_promoted is True

    def test_has_cached_results_property(self):
        """Test has_cached_results property."""
        scenario = Scenario(
            program_id=uuid4(),
            name="Test",
            status=ScenarioStatus.DRAFT,
            created_by_id=uuid4(),
        )
        assert scenario.has_cached_results is False

        scenario.results_cache = {"duration": 100}
        assert scenario.has_cached_results is True

    def test_invalidate_cache(self):
        """Test cache invalidation."""
        scenario = Scenario(
            program_id=uuid4(),
            name="Test",
            status=ScenarioStatus.DRAFT,
            created_by_id=uuid4(),
            results_cache={"duration": 100},
        )
        assert scenario.results_cache is not None

        scenario.invalidate_cache()
        assert scenario.results_cache is None

    def test_scenario_repr(self):
        """Test scenario string representation."""
        scenario = Scenario(
            program_id=uuid4(),
            name="Test Scenario",
            status=ScenarioStatus.DRAFT,
            is_active=True,
            created_by_id=uuid4(),
        )
        # Set a mock ID for repr
        scenario.id = uuid4()

        repr_str = repr(scenario)
        assert "Scenario" in repr_str
        assert "Test Scenario" in repr_str
        assert "draft" in repr_str


class TestScenarioChangeModel:
    """Tests for ScenarioChange model."""

    def test_scenario_change_tablename(self):
        """Test scenario change table name."""
        assert ScenarioChange.__tablename__ == "scenario_changes"

    def test_is_create_property(self):
        """Test is_create property."""
        change = ScenarioChange(
            scenario_id=uuid4(),
            entity_type=EntityType.ACTIVITY,
            entity_id=uuid4(),
            change_type=ChangeType.CREATE,
        )
        assert change.is_create is True
        assert change.is_update is False
        assert change.is_delete is False

    def test_is_update_property(self):
        """Test is_update property."""
        change = ScenarioChange(
            scenario_id=uuid4(),
            entity_type=EntityType.ACTIVITY,
            entity_id=uuid4(),
            change_type=ChangeType.UPDATE,
        )
        assert change.is_create is False
        assert change.is_update is True
        assert change.is_delete is False

    def test_is_delete_property(self):
        """Test is_delete property."""
        change = ScenarioChange(
            scenario_id=uuid4(),
            entity_type=EntityType.ACTIVITY,
            entity_id=uuid4(),
            change_type=ChangeType.DELETE,
        )
        assert change.is_create is False
        assert change.is_update is False
        assert change.is_delete is True

    def test_scenario_change_repr(self):
        """Test scenario change string representation."""
        change = ScenarioChange(
            scenario_id=uuid4(),
            entity_type=EntityType.ACTIVITY,
            entity_id=uuid4(),
            change_type=ChangeType.UPDATE,
        )
        change.id = uuid4()

        repr_str = repr(change)
        assert "ScenarioChange" in repr_str
        assert "activity" in repr_str
        assert "update" in repr_str


class TestScenarioSchemas:
    """Tests for Scenario Pydantic schemas."""

    def test_scenario_base_validation(self):
        """Test ScenarioBase validation."""
        schema = ScenarioBase(name="Test Scenario", description="A test")
        assert schema.name == "Test Scenario"
        assert schema.description == "A test"

    def test_scenario_base_name_required(self):
        """Test that name is required."""
        with pytest.raises(ValueError):
            ScenarioBase(name="", description="Test")

    def test_scenario_create_with_program_id(self):
        """Test ScenarioCreate with program ID."""
        program_id = uuid4()
        schema = ScenarioCreate(
            name="Test",
            program_id=program_id,
        )
        assert schema.program_id == program_id
        assert schema.baseline_id is None
        assert schema.parent_scenario_id is None

    def test_scenario_create_with_baseline(self):
        """Test ScenarioCreate with baseline reference."""
        program_id = uuid4()
        baseline_id = uuid4()
        schema = ScenarioCreate(
            name="Test",
            program_id=program_id,
            baseline_id=baseline_id,
        )
        assert schema.baseline_id == baseline_id

    def test_scenario_create_with_parent(self):
        """Test ScenarioCreate with parent scenario."""
        program_id = uuid4()
        parent_id = uuid4()
        schema = ScenarioCreate(
            name="Branch",
            program_id=program_id,
            parent_scenario_id=parent_id,
        )
        assert schema.parent_scenario_id == parent_id

    def test_scenario_update_partial(self):
        """Test ScenarioUpdate with partial data."""
        schema = ScenarioUpdate(name="New Name")
        assert schema.name == "New Name"
        assert schema.description is None
        assert schema.status is None

    def test_scenario_update_status(self):
        """Test ScenarioUpdate with status change."""
        schema = ScenarioUpdate(status=SchemaScenarioStatus.ACTIVE)
        assert schema.status == SchemaScenarioStatus.ACTIVE


class TestScenarioChangeSchemas:
    """Tests for ScenarioChange Pydantic schemas."""

    def test_change_create_activity_update(self):
        """Test creating an activity update change."""
        entity_id = uuid4()
        schema = ScenarioChangeCreate(
            entity_type=SchemaEntityType.ACTIVITY,
            entity_id=entity_id,
            entity_code="ACT-001",
            change_type=SchemaChangeType.UPDATE,
            field_name="duration",
            old_value=10,
            new_value=15,
        )
        assert schema.entity_type == SchemaEntityType.ACTIVITY
        assert schema.change_type == SchemaChangeType.UPDATE
        assert schema.old_value == 10
        assert schema.new_value == 15

    def test_change_create_dependency_create(self):
        """Test creating a dependency create change."""
        entity_id = uuid4()
        schema = ScenarioChangeCreate(
            entity_type=SchemaEntityType.DEPENDENCY,
            entity_id=entity_id,
            change_type=SchemaChangeType.CREATE,
            new_value={"predecessor_id": str(uuid4()), "successor_id": str(uuid4())},
        )
        assert schema.entity_type == SchemaEntityType.DEPENDENCY
        assert schema.change_type == SchemaChangeType.CREATE

    def test_change_create_wbs_delete(self):
        """Test creating a WBS delete change."""
        entity_id = uuid4()
        schema = ScenarioChangeCreate(
            entity_type=SchemaEntityType.WBS,
            entity_id=entity_id,
            entity_code="1.2.3",
            change_type=SchemaChangeType.DELETE,
            old_value={"name": "Deleted WBS"},
        )
        assert schema.entity_type == SchemaEntityType.WBS
        assert schema.change_type == SchemaChangeType.DELETE

    def test_change_response_from_attributes(self):
        """Test ScenarioChangeResponse model validation."""
        change_id = uuid4()
        scenario_id = uuid4()
        entity_id = uuid4()

        response = ScenarioChangeResponse(
            id=change_id,
            scenario_id=scenario_id,
            entity_type="activity",
            entity_id=entity_id,
            entity_code="ACT-001",
            change_type="update",
            field_name="duration",
            old_value=10,
            new_value=15,
            created_at=datetime.now(),
        )
        assert response.id == change_id
        assert response.change_type == "update"


class TestScenarioSummarySchema:
    """Tests for ScenarioSummary schema."""

    def test_scenario_summary_creation(self):
        """Test creating a scenario summary."""
        scenario_id = uuid4()
        program_id = uuid4()
        created_by_id = uuid4()

        summary = ScenarioSummary(
            id=scenario_id,
            program_id=program_id,
            baseline_id=None,
            parent_scenario_id=None,
            name="Test Scenario",
            description="Description",
            status="draft",
            is_active=True,
            change_count=5,
            has_cached_results=False,
            created_at=datetime.now(),
            created_by_id=created_by_id,
            promoted_at=None,
            promoted_baseline_id=None,
        )
        assert summary.change_count == 5
        assert summary.status == "draft"
        assert summary.is_active is True


class TestScenarioDiffSummary:
    """Tests for ScenarioDiffSummary schema."""

    def test_diff_summary_creation(self):
        """Test creating a diff summary."""
        summary = ScenarioDiffSummary(
            scenario_id=uuid4(),
            scenario_name="Test",
            activities_created=2,
            activities_updated=3,
            activities_deleted=1,
            dependencies_created=1,
            total_changes=7,
        )
        assert summary.activities_created == 2
        assert summary.activities_updated == 3
        assert summary.activities_deleted == 1
        assert summary.total_changes == 7

    def test_diff_summary_defaults(self):
        """Test diff summary default values."""
        summary = ScenarioDiffSummary(
            scenario_id=uuid4(),
            scenario_name="Test",
        )
        assert summary.activities_created == 0
        assert summary.activities_updated == 0
        assert summary.activities_deleted == 0
        assert summary.dependencies_created == 0
        assert summary.wbs_created == 0
        assert summary.total_changes == 0


class TestScenarioListResponse:
    """Tests for ScenarioListResponse schema."""

    def test_list_response_empty(self):
        """Test empty list response."""
        response = ScenarioListResponse(
            items=[],
            total=0,
            page=1,
            per_page=20,
            pages=1,
        )
        assert len(response.items) == 0
        assert response.total == 0

    def test_list_response_with_items(self):
        """Test list response with items."""
        summary = ScenarioSummary(
            id=uuid4(),
            program_id=uuid4(),
            baseline_id=None,
            parent_scenario_id=None,
            name="Test",
            description=None,
            status="draft",
            is_active=True,
            change_count=0,
            has_cached_results=False,
            created_at=datetime.now(),
            created_by_id=uuid4(),
            promoted_at=None,
            promoted_baseline_id=None,
        )

        response = ScenarioListResponse(
            items=[summary],
            total=1,
            page=1,
            per_page=20,
            pages=1,
        )
        assert len(response.items) == 1
        assert response.total == 1


class TestScenarioResponse:
    """Tests for ScenarioResponse schema."""

    def test_scenario_response_full(self):
        """Test full scenario response with changes."""
        scenario_id = uuid4()
        program_id = uuid4()
        created_by_id = uuid4()

        change = ScenarioChangeResponse(
            id=uuid4(),
            scenario_id=scenario_id,
            entity_type="activity",
            entity_id=uuid4(),
            entity_code="ACT-001",
            change_type="update",
            field_name="duration",
            old_value=10,
            new_value=15,
            created_at=datetime.now(),
        )

        response = ScenarioResponse(
            id=scenario_id,
            program_id=program_id,
            baseline_id=None,
            parent_scenario_id=None,
            name="Test Scenario",
            description="Full test",
            status="active",
            is_active=True,
            change_count=1,
            has_cached_results=False,
            created_at=datetime.now(),
            created_by_id=created_by_id,
            promoted_at=None,
            promoted_baseline_id=None,
            changes=[change],
            results_cache=None,
            updated_at=datetime.now(),
        )
        assert len(response.changes) == 1
        assert response.changes[0].field_name == "duration"

    def test_scenario_response_with_cache(self):
        """Test scenario response with cached results."""
        response = ScenarioResponse(
            id=uuid4(),
            program_id=uuid4(),
            baseline_id=None,
            parent_scenario_id=None,
            name="Test",
            description=None,
            status="draft",
            is_active=True,
            change_count=0,
            has_cached_results=True,
            created_at=datetime.now(),
            created_by_id=uuid4(),
            promoted_at=None,
            promoted_baseline_id=None,
            changes=[],
            results_cache={"duration": 100, "critical_path": ["A", "B", "C"]},
            updated_at=None,
        )
        assert response.results_cache is not None
        assert response.results_cache["duration"] == 100
