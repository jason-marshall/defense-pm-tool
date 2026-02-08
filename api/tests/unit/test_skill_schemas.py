"""Tests for Skill, ResourceSkill, and SkillRequirement schemas."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

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


class TestSkillCreate:
    """Tests for SkillCreate schema validation."""

    def test_valid_skill_create(self) -> None:
        """Should create skill with valid data."""
        skill = SkillCreate(
            name="Python Programming",
            code="PYTHON",
            category="Technical",
        )
        assert skill.name == "Python Programming"
        assert skill.code == "PYTHON"
        assert skill.category == "Technical"
        assert skill.is_active is True

    def test_code_uppercase_conversion(self) -> None:
        """Should convert code to uppercase."""
        skill = SkillCreate(name="Test", code="python", category="Technical")
        assert skill.code == "PYTHON"

    def test_code_validation_invalid_chars(self) -> None:
        """Should reject code with invalid characters."""
        with pytest.raises(ValidationError):
            SkillCreate(name="Test", code="py thon", category="Technical")

    def test_name_min_length(self) -> None:
        """Should reject empty name."""
        with pytest.raises(ValidationError):
            SkillCreate(name="", code="TST", category="Technical")

    def test_name_max_length(self) -> None:
        """Should reject name longer than 100 chars."""
        with pytest.raises(ValidationError):
            SkillCreate(name="X" * 101, code="TST", category="Technical")

    def test_valid_categories(self) -> None:
        """Should accept all valid categories."""
        for cat in ("Technical", "Management", "Certification", "Safety"):
            skill = SkillCreate(name="Test", code="TST", category=cat)
            assert skill.category == cat

    def test_invalid_category(self) -> None:
        """Should reject invalid category."""
        with pytest.raises(ValidationError):
            SkillCreate(name="Test", code="TST", category="Invalid")

    def test_global_skill_no_program(self) -> None:
        """Should allow program_id=None for global skills."""
        skill = SkillCreate(name="Test", code="TST", category="Technical", program_id=None)
        assert skill.program_id is None

    def test_program_specific_skill(self) -> None:
        """Should allow program_id for program-specific skills."""
        pid = uuid4()
        skill = SkillCreate(name="Test", code="TST", category="Technical", program_id=pid)
        assert skill.program_id == pid

    def test_certification_expiry_months_range(self) -> None:
        """Should validate expiry months range."""
        skill = SkillCreate(
            name="Test",
            code="TST",
            category="Technical",
            certification_expiry_months=36,
        )
        assert skill.certification_expiry_months == 36

    def test_certification_expiry_months_too_low(self) -> None:
        """Should reject expiry months < 1."""
        with pytest.raises(ValidationError):
            SkillCreate(
                name="Test",
                code="TST",
                category="Technical",
                certification_expiry_months=0,
            )

    def test_certification_expiry_months_too_high(self) -> None:
        """Should reject expiry months > 120."""
        with pytest.raises(ValidationError):
            SkillCreate(
                name="Test",
                code="TST",
                category="Technical",
                certification_expiry_months=121,
            )

    def test_requires_certification_default(self) -> None:
        """Should default requires_certification to False."""
        skill = SkillCreate(name="Test", code="TST", category="Technical")
        assert skill.requires_certification is False

    def test_code_with_hyphens_underscores(self) -> None:
        """Should accept codes with hyphens and underscores."""
        skill = SkillCreate(name="Test", code="SK-001_A", category="Technical")
        assert skill.code == "SK-001_A"


class TestSkillUpdate:
    """Tests for SkillUpdate schema validation."""

    def test_all_fields_optional(self) -> None:
        """Should allow empty update."""
        update = SkillUpdate()
        assert update.name is None
        assert update.code is None
        assert update.category is None

    def test_partial_update(self) -> None:
        """Should allow partial update."""
        update = SkillUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.code is None

    def test_code_uppercase_on_update(self) -> None:
        """Should convert code to uppercase on update."""
        update = SkillUpdate(code="python")
        assert update.code == "PYTHON"

    def test_invalid_category_on_update(self) -> None:
        """Should reject invalid category on update."""
        with pytest.raises(ValidationError):
            SkillUpdate(category="Invalid")


class TestSkillResponse:
    """Tests for SkillResponse schema."""

    def test_from_attributes(self) -> None:
        """Should create from ORM-like object."""
        now = datetime.now(UTC)
        data = {
            "id": uuid4(),
            "name": "Python",
            "code": "PYTHON",
            "category": "Technical",
            "description": None,
            "is_active": True,
            "requires_certification": False,
            "certification_expiry_months": None,
            "program_id": None,
            "created_at": now,
            "updated_at": now,
        }
        response = SkillResponse(**data)
        assert response.name == "Python"
        assert response.code == "PYTHON"

    def test_response_with_all_fields(self) -> None:
        """Should include all fields in response."""
        now = datetime.now(UTC)
        pid = uuid4()
        response = SkillResponse(
            id=uuid4(),
            name="PMP",
            code="PMP-CERT",
            category="Certification",
            description="Project Management Professional",
            is_active=True,
            requires_certification=True,
            certification_expiry_months=36,
            program_id=pid,
            created_at=now,
            updated_at=now,
        )
        assert response.requires_certification is True
        assert response.certification_expiry_months == 36
        assert response.program_id == pid


class TestSkillListResponse:
    """Tests for SkillListResponse schema."""

    def test_empty_list(self) -> None:
        """Should support empty list."""
        resp = SkillListResponse(items=[], total=0, page=1, page_size=20)
        assert resp.total == 0
        assert len(resp.items) == 0

    def test_list_with_items(self) -> None:
        """Should include items."""
        now = datetime.now(UTC)
        item = SkillResponse(
            id=uuid4(),
            name="Test",
            code="TST",
            category="Technical",
            is_active=True,
            requires_certification=False,
            created_at=now,
        )
        resp = SkillListResponse(items=[item], total=1, page=1, page_size=20)
        assert resp.total == 1


class TestResourceSkillCreate:
    """Tests for ResourceSkillCreate schema."""

    def test_valid_create(self) -> None:
        """Should create with valid data."""
        rs = ResourceSkillCreate(
            skill_id=uuid4(),
            proficiency_level=3,
        )
        assert rs.proficiency_level == 3
        assert rs.is_certified is False

    def test_proficiency_level_min(self) -> None:
        """Should reject level < 1."""
        with pytest.raises(ValidationError):
            ResourceSkillCreate(skill_id=uuid4(), proficiency_level=0)

    def test_proficiency_level_max(self) -> None:
        """Should reject level > 5."""
        with pytest.raises(ValidationError):
            ResourceSkillCreate(skill_id=uuid4(), proficiency_level=6)

    def test_with_certification(self) -> None:
        """Should accept certification data."""
        rs = ResourceSkillCreate(
            skill_id=uuid4(),
            proficiency_level=5,
            is_certified=True,
            certification_date=date(2025, 1, 1),
        )
        assert rs.is_certified is True
        assert rs.certification_date == date(2025, 1, 1)

    def test_notes_max_length(self) -> None:
        """Should reject notes > 1000 chars."""
        with pytest.raises(ValidationError):
            ResourceSkillCreate(
                skill_id=uuid4(),
                proficiency_level=1,
                notes="X" * 1001,
            )

    def test_default_proficiency_level(self) -> None:
        """Should default proficiency to 1."""
        rs = ResourceSkillCreate(skill_id=uuid4())
        assert rs.proficiency_level == 1


class TestResourceSkillUpdate:
    """Tests for ResourceSkillUpdate schema."""

    def test_all_fields_optional(self) -> None:
        """Should allow empty update."""
        update = ResourceSkillUpdate()
        assert update.proficiency_level is None

    def test_partial_update(self) -> None:
        """Should allow partial update."""
        update = ResourceSkillUpdate(proficiency_level=4)
        assert update.proficiency_level == 4

    def test_proficiency_validation(self) -> None:
        """Should validate proficiency bounds on update."""
        with pytest.raises(ValidationError):
            ResourceSkillUpdate(proficiency_level=6)


class TestResourceSkillResponse:
    """Tests for ResourceSkillResponse schema."""

    def test_response_fields(self) -> None:
        """Should include all response fields."""
        resp = ResourceSkillResponse(
            id=uuid4(),
            resource_id=uuid4(),
            skill_id=uuid4(),
            proficiency_level=3,
            is_certified=True,
            certification_date=date(2025, 1, 1),
        )
        assert resp.proficiency_level == 3
        assert resp.is_certified is True


class TestSkillRequirementCreate:
    """Tests for SkillRequirementCreate schema."""

    def test_valid_create(self) -> None:
        """Should create with valid data."""
        sr = SkillRequirementCreate(
            skill_id=uuid4(),
            required_level=3,
        )
        assert sr.required_level == 3
        assert sr.is_mandatory is True

    def test_level_min(self) -> None:
        """Should reject level < 1."""
        with pytest.raises(ValidationError):
            SkillRequirementCreate(skill_id=uuid4(), required_level=0)

    def test_level_max(self) -> None:
        """Should reject level > 5."""
        with pytest.raises(ValidationError):
            SkillRequirementCreate(skill_id=uuid4(), required_level=6)

    def test_optional_requirement(self) -> None:
        """Should support non-mandatory requirements."""
        sr = SkillRequirementCreate(skill_id=uuid4(), required_level=2, is_mandatory=False)
        assert sr.is_mandatory is False

    def test_default_values(self) -> None:
        """Should have correct defaults."""
        sr = SkillRequirementCreate(skill_id=uuid4())
        assert sr.required_level == 1
        assert sr.is_mandatory is True


class TestSkillRequirementResponse:
    """Tests for SkillRequirementResponse schema."""

    def test_response_fields(self) -> None:
        """Should include all response fields."""
        resp = SkillRequirementResponse(
            id=uuid4(),
            activity_id=uuid4(),
            skill_id=uuid4(),
            required_level=4,
            is_mandatory=True,
        )
        assert resp.required_level == 4
        assert resp.is_mandatory is True

    def test_response_with_skill(self) -> None:
        """Should include nested skill response."""
        now = datetime.now(UTC)
        skill_resp = SkillResponse(
            id=uuid4(),
            name="Python",
            code="PY",
            category="Technical",
            is_active=True,
            requires_certification=False,
            created_at=now,
        )
        resp = SkillRequirementResponse(
            id=uuid4(),
            activity_id=uuid4(),
            skill_id=skill_resp.id,
            required_level=3,
            is_mandatory=True,
            skill=skill_resp,
        )
        assert resp.skill is not None
        assert resp.skill.name == "Python"
