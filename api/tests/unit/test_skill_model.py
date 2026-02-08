"""Tests for Skill, ResourceSkill, and SkillRequirement models."""

from datetime import UTC, date, datetime
from uuid import uuid4

from src.models.skill import ResourceSkill, Skill, SkillRequirement


class TestSkillModel:
    """Tests for Skill model creation and properties."""

    def test_create_skill_with_required_fields(self) -> None:
        """Should create skill with name and code."""
        skill = Skill(
            id=uuid4(),
            name="Python Programming",
            code="PYTHON",
            category="Technical",
            is_active=True,
            requires_certification=False,
        )
        assert skill.name == "Python Programming"
        assert skill.code == "PYTHON"
        assert skill.category == "Technical"
        assert skill.is_active is True
        assert skill.requires_certification is False

    def test_create_skill_with_all_fields(self) -> None:
        """Should create skill with all fields."""
        program_id = uuid4()
        skill = Skill(
            id=uuid4(),
            name="PMP Certification",
            code="PMP",
            category="Certification",
            description="Project Management Professional",
            is_active=True,
            requires_certification=True,
            certification_expiry_months=36,
            program_id=program_id,
        )
        assert skill.category == "Certification"
        assert skill.requires_certification is True
        assert skill.certification_expiry_months == 36
        assert skill.program_id == program_id

    def test_skill_repr(self) -> None:
        """Should return readable repr."""
        skill = Skill(id=uuid4(), name="Test", code="TST", category="Technical")
        repr_str = repr(skill)
        assert "Skill" in repr_str
        assert "TST" in repr_str

    def test_create_global_skill(self) -> None:
        """Should create global skill with program_id=None."""
        skill = Skill(
            id=uuid4(),
            name="Safety Training",
            code="SAFE-001",
            category="Safety",
            program_id=None,
        )
        assert skill.program_id is None

    def test_skill_tablename(self) -> None:
        """Should have correct table name."""
        assert Skill.__tablename__ == "skills"

    def test_skill_explicit_category(self) -> None:
        """Should accept explicit category."""
        skill = Skill(id=uuid4(), name="Test", code="TST", category="Technical")
        assert skill.category == "Technical"

    def test_skill_inactive(self) -> None:
        """Should support inactive skills."""
        skill = Skill(id=uuid4(), name="Deprecated", code="DEP", is_active=False)
        assert skill.is_active is False


class TestResourceSkillModel:
    """Tests for ResourceSkill model creation and properties."""

    def test_create_resource_skill_basic(self) -> None:
        """Should create resource skill with required fields."""
        rs = ResourceSkill(
            id=uuid4(),
            resource_id=uuid4(),
            skill_id=uuid4(),
            proficiency_level=3,
            is_certified=False,
        )
        assert rs.proficiency_level == 3
        assert rs.is_certified is False
        assert rs.certification_date is None

    def test_create_resource_skill_with_certification(self) -> None:
        """Should create certified resource skill."""
        now = datetime.now(UTC)
        rs = ResourceSkill(
            id=uuid4(),
            resource_id=uuid4(),
            skill_id=uuid4(),
            proficiency_level=5,
            is_certified=True,
            certification_date=date(2025, 6, 15),
            certification_expires_at=now,
            verified_by=uuid4(),
            verified_at=now,
        )
        assert rs.is_certified is True
        assert rs.certification_date == date(2025, 6, 15)
        assert rs.verified_by is not None

    def test_resource_skill_proficiency_levels(self) -> None:
        """Should support proficiency levels 1-5."""
        for level in range(1, 6):
            rs = ResourceSkill(
                id=uuid4(),
                resource_id=uuid4(),
                skill_id=uuid4(),
                proficiency_level=level,
            )
            assert rs.proficiency_level == level

    def test_resource_skill_repr(self) -> None:
        """Should return readable repr."""
        rs = ResourceSkill(
            id=uuid4(),
            resource_id=uuid4(),
            skill_id=uuid4(),
            proficiency_level=3,
        )
        repr_str = repr(rs)
        assert "ResourceSkill" in repr_str
        assert "level=3" in repr_str

    def test_resource_skill_tablename(self) -> None:
        """Should have correct table name."""
        assert ResourceSkill.__tablename__ == "resource_skills"

    def test_resource_skill_with_notes(self) -> None:
        """Should support notes field."""
        rs = ResourceSkill(
            id=uuid4(),
            resource_id=uuid4(),
            skill_id=uuid4(),
            proficiency_level=2,
            notes="Training in progress",
        )
        assert rs.notes == "Training in progress"

    def test_resource_skill_explicit_proficiency(self) -> None:
        """Should accept explicit proficiency level."""
        rs = ResourceSkill(
            id=uuid4(),
            resource_id=uuid4(),
            skill_id=uuid4(),
            proficiency_level=1,
            is_certified=False,
        )
        assert rs.proficiency_level == 1


class TestSkillRequirementModel:
    """Tests for SkillRequirement model creation and properties."""

    def test_create_skill_requirement_basic(self) -> None:
        """Should create skill requirement with explicit values."""
        sr = SkillRequirement(
            id=uuid4(),
            activity_id=uuid4(),
            skill_id=uuid4(),
            required_level=1,
            is_mandatory=True,
        )
        assert sr.required_level == 1
        assert sr.is_mandatory is True

    def test_create_skill_requirement_with_level(self) -> None:
        """Should create skill requirement with specific level."""
        sr = SkillRequirement(
            id=uuid4(),
            activity_id=uuid4(),
            skill_id=uuid4(),
            required_level=4,
            is_mandatory=False,
        )
        assert sr.required_level == 4
        assert sr.is_mandatory is False

    def test_skill_requirement_repr(self) -> None:
        """Should return readable repr."""
        sr = SkillRequirement(
            id=uuid4(),
            activity_id=uuid4(),
            skill_id=uuid4(),
            required_level=3,
        )
        repr_str = repr(sr)
        assert "SkillRequirement" in repr_str
        assert "level=3" in repr_str

    def test_skill_requirement_tablename(self) -> None:
        """Should have correct table name."""
        assert SkillRequirement.__tablename__ == "skill_requirements"

    def test_skill_requirement_levels(self) -> None:
        """Should support required levels 1-5."""
        for level in range(1, 6):
            sr = SkillRequirement(
                id=uuid4(),
                activity_id=uuid4(),
                skill_id=uuid4(),
                required_level=level,
            )
            assert sr.required_level == level

    def test_skill_requirement_optional(self) -> None:
        """Should support optional (non-mandatory) requirements."""
        sr = SkillRequirement(
            id=uuid4(),
            activity_id=uuid4(),
            skill_id=uuid4(),
            is_mandatory=False,
        )
        assert sr.is_mandatory is False
