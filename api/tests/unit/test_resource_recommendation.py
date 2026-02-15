"""Tests for the ResourceRecommendationService scoring algorithms."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.schemas.recommendation import (
    BulkRecommendationRequest,
    RecommendationRequest,
    RecommendationWeights,
    ScoreBreakdown,
    SkillMatchDetail,
)
from src.services.resource_recommendation import (
    ResourceRecommendationService,
    _ScoringContext,
    _SkillMatch,
)

# =============================================================================
# Helper factories
# =============================================================================


def _make_resource(
    *,
    name: str = "Test Resource",
    code: str = "RES-001",
    cost_rate: Decimal | None = Decimal("100.00"),
    capacity: Decimal = Decimal("8.00"),
    is_active: bool = True,
    resource_type: str = "LABOR",
) -> MagicMock:
    """Create a mock Resource object."""
    r = MagicMock()
    r.id = uuid4()
    r.name = name
    r.code = code
    r.cost_rate = cost_rate
    r.capacity_per_day = capacity
    r.is_active = is_active
    r.resource_type = MagicMock()
    r.resource_type.value = resource_type
    r.program_id = uuid4()
    return r


def _make_skill_match(
    *,
    required_level: int = 3,
    resource_level: int = 3,
    is_mandatory: bool = True,
    is_certified: bool = False,
    certification_required: bool = False,
) -> _SkillMatch:
    """Create a _SkillMatch for testing."""
    return _SkillMatch(
        skill_id=uuid4(),
        skill_name="Test Skill",
        skill_code="TEST",
        required_level=required_level,
        resource_level=resource_level,
        is_mandatory=is_mandatory,
        is_met=resource_level >= required_level,
        is_certified=is_certified,
        certification_required=certification_required,
    )


def _make_requirement(
    *,
    skill_id=None,
    required_level: int = 3,
    is_mandatory: bool = True,
    skill_name: str = "Test Skill",
    skill_code: str = "TEST",
    requires_cert: bool = False,
) -> MagicMock:
    """Create a mock SkillRequirement."""
    req = MagicMock()
    req.skill_id = skill_id or uuid4()
    req.required_level = required_level
    req.is_mandatory = is_mandatory
    req.skill = MagicMock()
    req.skill.name = skill_name
    req.skill.code = skill_code
    req.skill.requires_certification = requires_cert
    return req


def _make_resource_skill(
    *,
    skill_id=None,
    proficiency_level: int = 3,
    is_certified: bool = False,
) -> MagicMock:
    """Create a mock ResourceSkill."""
    rs = MagicMock()
    rs.skill_id = skill_id or uuid4()
    rs.proficiency_level = proficiency_level
    rs.is_certified = is_certified
    return rs


# =============================================================================
# Skill Score Tests
# =============================================================================


class TestCalculateSkillScore:
    """Tests for the skill match scoring algorithm."""

    def test_no_requirements_returns_perfect_score(self) -> None:
        """Should return 1.0 when no requirements exist."""
        score = ResourceRecommendationService._calculate_skill_score([])
        assert score == 1.0

    def test_exact_match_returns_high_score(self) -> None:
        """Should return ~1.0 when resource meets all requirements exactly."""
        matches = [
            _make_skill_match(required_level=3, resource_level=3, is_mandatory=True),
        ]
        score = ResourceRecommendationService._calculate_skill_score(matches)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_exceeding_requirement_gets_bonus(self) -> None:
        """Should get bonus when resource exceeds requirement."""
        matches = [
            _make_skill_match(required_level=2, resource_level=5, is_mandatory=True),
        ]
        score = ResourceRecommendationService._calculate_skill_score(matches)
        assert score >= 1.0 or score == pytest.approx(1.0, abs=0.01)

    def test_below_requirement_gets_partial(self) -> None:
        """Should get partial score when resource has skill but below level."""
        matches = [
            _make_skill_match(required_level=4, resource_level=2, is_mandatory=True),
        ]
        score = ResourceRecommendationService._calculate_skill_score(matches)
        assert 0.0 < score < 1.0

    def test_no_skill_returns_zero(self) -> None:
        """Should get zero for unmatched skills."""
        matches = [
            _make_skill_match(required_level=3, resource_level=0, is_mandatory=True),
        ]
        score = ResourceRecommendationService._calculate_skill_score(matches)
        assert score == 0.0

    def test_mandatory_skills_weighted_higher(self) -> None:
        """Mandatory skills should be weighted 2x vs optional."""
        mandatory_match = _make_skill_match(required_level=3, resource_level=3, is_mandatory=True)
        optional_miss = _make_skill_match(required_level=3, resource_level=0, is_mandatory=False)
        score = ResourceRecommendationService._calculate_skill_score(
            [mandatory_match, optional_miss]
        )
        # Mandatory met (weight 2 * 1.0) + optional miss (weight 1 * 0) = 2/3
        assert score == pytest.approx(2.0 / 3.0, abs=0.01)

    def test_all_optional_missed(self) -> None:
        """Should return 0 when all optional skills are missed."""
        matches = [
            _make_skill_match(required_level=3, resource_level=0, is_mandatory=False),
            _make_skill_match(required_level=2, resource_level=0, is_mandatory=False),
        ]
        score = ResourceRecommendationService._calculate_skill_score(matches)
        assert score == 0.0

    def test_mixed_match_and_miss(self) -> None:
        """Should get partial score with mixed results."""
        matches = [
            _make_skill_match(required_level=3, resource_level=3, is_mandatory=True),
            _make_skill_match(required_level=3, resource_level=0, is_mandatory=True),
        ]
        score = ResourceRecommendationService._calculate_skill_score(matches)
        assert 0.0 < score < 1.0

    def test_multiple_skills_averaged(self) -> None:
        """Should average across multiple skill matches."""
        matches = [
            _make_skill_match(required_level=3, resource_level=3, is_mandatory=True),
            _make_skill_match(required_level=3, resource_level=3, is_mandatory=True),
            _make_skill_match(required_level=3, resource_level=3, is_mandatory=True),
        ]
        score = ResourceRecommendationService._calculate_skill_score(matches)
        assert score == pytest.approx(1.0, abs=0.01)


# =============================================================================
# Availability Score Tests
# =============================================================================


class TestCalculateAvailabilityScore:
    """Tests for the availability scoring algorithm."""

    def test_no_assignments_returns_perfect(self) -> None:
        """Should return 1.0 with no assignments."""
        score = ResourceRecommendationService._calculate_availability_score(0)
        assert score == 1.0

    def test_one_assignment_returns_high(self) -> None:
        """Should return ~0.84 with one assignment."""
        score = ResourceRecommendationService._calculate_availability_score(1)
        assert 0.8 < score < 1.0

    def test_five_plus_assignments_returns_low(self) -> None:
        """Should return 0.2 with 5+ assignments."""
        score = ResourceRecommendationService._calculate_availability_score(5)
        assert score == 0.2
        score = ResourceRecommendationService._calculate_availability_score(10)
        assert score == 0.2

    def test_linear_decrease(self) -> None:
        """Scores should decrease as assignment count increases."""
        scores = [ResourceRecommendationService._calculate_availability_score(i) for i in range(6)]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]


# =============================================================================
# Cost Score Tests
# =============================================================================


class TestCalculateCostScore:
    """Tests for the cost efficiency scoring algorithm."""

    def test_no_cost_rate_returns_neutral(self) -> None:
        """Should return 0.5 when resource has no cost rate."""
        resource = _make_resource(cost_rate=None)
        score = ResourceRecommendationService._calculate_cost_score(resource, Decimal("200"))
        assert score == 0.5

    def test_zero_cost_rate_returns_neutral(self) -> None:
        """Should return 0.5 when cost rate is zero."""
        resource = _make_resource(cost_rate=Decimal("0"))
        score = ResourceRecommendationService._calculate_cost_score(resource, Decimal("200"))
        assert score == 0.5

    def test_lowest_cost_returns_highest_score(self) -> None:
        """Cheapest resource should get highest score."""
        resource = _make_resource(cost_rate=Decimal("10"))
        score = ResourceRecommendationService._calculate_cost_score(resource, Decimal("200"))
        assert score > 0.9

    def test_highest_cost_returns_lowest_score(self) -> None:
        """Most expensive resource should get lowest score."""
        resource = _make_resource(cost_rate=Decimal("200"))
        score = ResourceRecommendationService._calculate_cost_score(resource, Decimal("200"))
        assert score == pytest.approx(0.2, abs=0.01)

    def test_cost_score_inversely_proportional(self) -> None:
        """Higher cost should yield lower score."""
        max_cost = Decimal("200")
        cheap = _make_resource(cost_rate=Decimal("50"))
        expensive = _make_resource(cost_rate=Decimal("150"))
        assert ResourceRecommendationService._calculate_cost_score(
            cheap, max_cost
        ) > ResourceRecommendationService._calculate_cost_score(expensive, max_cost)

    def test_zero_max_cost_returns_neutral(self) -> None:
        """Should return 0.5 when max_cost is zero."""
        resource = _make_resource(cost_rate=Decimal("100"))
        score = ResourceRecommendationService._calculate_cost_score(resource, Decimal("0"))
        assert score == 0.5


# =============================================================================
# Certification Score Tests
# =============================================================================


class TestCalculateCertificationScore:
    """Tests for the certification bonus scoring algorithm."""

    def test_no_certifications_needed_returns_perfect(self) -> None:
        """Should return 1.0 when no certifications are required."""
        matches = [
            _make_skill_match(certification_required=False),
        ]
        score = ResourceRecommendationService._calculate_certification_score(matches)
        assert score == 1.0

    def test_all_certified_returns_perfect(self) -> None:
        """Should return 1.0 when all required certifications are met."""
        matches = [
            _make_skill_match(certification_required=True, is_certified=True),
            _make_skill_match(certification_required=True, is_certified=True),
        ]
        score = ResourceRecommendationService._calculate_certification_score(matches)
        assert score == 1.0

    def test_none_certified_returns_zero(self) -> None:
        """Should return 0.0 when no certifications are met."""
        matches = [
            _make_skill_match(certification_required=True, is_certified=False),
            _make_skill_match(certification_required=True, is_certified=False),
        ]
        score = ResourceRecommendationService._calculate_certification_score(matches)
        assert score == 0.0

    def test_partial_certification(self) -> None:
        """Should return partial score for partial certification."""
        matches = [
            _make_skill_match(certification_required=True, is_certified=True),
            _make_skill_match(certification_required=True, is_certified=False),
        ]
        score = ResourceRecommendationService._calculate_certification_score(matches)
        assert score == 0.5

    def test_empty_matches_returns_perfect(self) -> None:
        """Should return 1.0 when matches list is empty."""
        score = ResourceRecommendationService._calculate_certification_score([])
        assert score == 1.0


# =============================================================================
# _compute_skill_matches Tests
# =============================================================================


class TestComputeSkillMatches:
    """Tests for skill requirement matching logic."""

    def test_matching_skill_detected(self) -> None:
        """Should detect when resource has the required skill."""
        skill_id = uuid4()
        req = _make_requirement(skill_id=skill_id, required_level=3)
        rs = _make_resource_skill(skill_id=skill_id, proficiency_level=4)
        resource_skills = {skill_id: rs}

        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        matches = service._compute_skill_matches([req], resource_skills)

        assert len(matches) == 1
        assert matches[0].is_met is True
        assert matches[0].resource_level == 4
        assert matches[0].required_level == 3

    def test_missing_skill_detected(self) -> None:
        """Should detect when resource lacks a required skill."""
        req = _make_requirement(required_level=3)
        resource_skills: dict = {}

        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        matches = service._compute_skill_matches([req], resource_skills)

        assert len(matches) == 1
        assert matches[0].is_met is False
        assert matches[0].resource_level == 0

    def test_insufficient_level_not_met(self) -> None:
        """Should not mark as met when level is below requirement."""
        skill_id = uuid4()
        req = _make_requirement(skill_id=skill_id, required_level=4)
        rs = _make_resource_skill(skill_id=skill_id, proficiency_level=2)
        resource_skills = {skill_id: rs}

        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        matches = service._compute_skill_matches([req], resource_skills)

        assert len(matches) == 1
        assert matches[0].is_met is False

    def test_certification_status_captured(self) -> None:
        """Should capture certification status from resource skill."""
        skill_id = uuid4()
        req = _make_requirement(skill_id=skill_id, requires_cert=True)
        rs = _make_resource_skill(skill_id=skill_id, is_certified=True)
        resource_skills = {skill_id: rs}

        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        matches = service._compute_skill_matches([req], resource_skills)

        assert matches[0].is_certified is True
        assert matches[0].certification_required is True


# =============================================================================
# Full _score_resource Tests
# =============================================================================


class TestScoreResource:
    """Tests for the complete resource scoring pipeline."""

    def test_perfect_match_scores_high(self) -> None:
        """Resource with perfect skill match should score near 1.0."""
        skill_id = uuid4()
        resource = _make_resource(cost_rate=Decimal("50"))
        req = _make_requirement(skill_id=skill_id, required_level=3)
        rs = _make_resource_skill(skill_id=skill_id, proficiency_level=5)

        ctx = _ScoringContext(
            resource=resource,
            resource_skills={skill_id: rs},
            requirements=[req],
            assignment_count=0,
        )

        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        rec = service._score_resource(ctx, Decimal("200"))

        assert rec.overall_score > 0.8
        assert rec.score_breakdown.mandatory_skills_met is True
        assert rec.resource_name == resource.name

    def test_no_skill_match_scores_low(self) -> None:
        """Resource with no matching skills should score low."""
        resource = _make_resource(cost_rate=Decimal("50"))
        req = _make_requirement(required_level=3)

        ctx = _ScoringContext(
            resource=resource,
            resource_skills={},
            requirements=[req],
            assignment_count=0,
        )

        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        rec = service._score_resource(ctx, Decimal("200"))

        # Mandatory not met → penalty of 0.3
        assert rec.overall_score < 0.5
        assert rec.score_breakdown.mandatory_skills_met is False

    def test_mandatory_skills_not_met_penalized(self) -> None:
        """Failing mandatory skills should heavily penalize score."""
        skill_id = uuid4()
        resource = _make_resource()
        req = _make_requirement(skill_id=skill_id, required_level=5, is_mandatory=True)
        rs = _make_resource_skill(skill_id=skill_id, proficiency_level=2)

        ctx_fail = _ScoringContext(
            resource=resource,
            resource_skills={skill_id: rs},
            requirements=[req],
            assignment_count=0,
        )

        ctx_pass = _ScoringContext(
            resource=resource,
            resource_skills={
                skill_id: _make_resource_skill(skill_id=skill_id, proficiency_level=5)
            },
            requirements=[req],
            assignment_count=0,
        )

        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        rec_fail = service._score_resource(ctx_fail, Decimal("200"))
        rec_pass = service._score_resource(ctx_pass, Decimal("200"))

        assert rec_pass.overall_score > rec_fail.overall_score

    def test_custom_weights_applied(self) -> None:
        """Custom weights should change the scoring balance."""
        skill_id = uuid4()
        resource = _make_resource(cost_rate=Decimal("10"))
        req = _make_requirement(skill_id=skill_id, required_level=3)
        rs = _make_resource_skill(skill_id=skill_id, proficiency_level=3)

        # Heavy cost weighting
        weights = RecommendationWeights(
            skill_match=0.1, availability=0.1, cost=0.7, certification=0.1
        )
        ctx = _ScoringContext(
            resource=resource,
            resource_skills={skill_id: rs},
            requirements=[req],
            assignment_count=0,
            weights=weights,
        )

        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        rec = service._score_resource(ctx, Decimal("200"))

        # Cost should dominate the score
        assert rec.overall_score > 0.7
        assert rec.score_breakdown.cost_score > 0.9

    def test_no_requirements_scores_on_availability_and_cost(self) -> None:
        """With no skill requirements, score based on availability and cost."""
        resource = _make_resource(cost_rate=Decimal("50"))
        ctx = _ScoringContext(
            resource=resource,
            resource_skills={},
            requirements=[],
            assignment_count=0,
        )

        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        rec = service._score_resource(ctx, Decimal("200"))

        assert rec.overall_score > 0.5
        assert rec.score_breakdown.skill_score == 1.0
        assert rec.score_breakdown.skills_required == 0


# =============================================================================
# Schema Validation Tests
# =============================================================================


class TestRecommendationSchemas:
    """Tests for recommendation Pydantic schemas."""

    def test_recommendation_request_defaults(self) -> None:
        """Should have sensible defaults."""
        req = RecommendationRequest()
        assert req.top_n == 10
        assert req.min_score == 0.0
        assert req.weights is None

    def test_recommendation_request_custom_values(self) -> None:
        """Should accept custom values."""
        req = RecommendationRequest(
            top_n=5,
            min_score=0.5,
            resource_type="LABOR",
        )
        assert req.top_n == 5
        assert req.min_score == 0.5
        assert req.resource_type == "LABOR"

    def test_recommendation_weights_defaults(self) -> None:
        """Default weights should sum close to 1.0."""
        w = RecommendationWeights()
        total = w.skill_match + w.availability + w.cost + w.certification
        assert total == pytest.approx(1.0, abs=0.01)

    def test_recommendation_weights_custom(self) -> None:
        """Should accept custom weights."""
        w = RecommendationWeights(skill_match=0.4, availability=0.3, cost=0.2, certification=0.1)
        assert w.skill_match == 0.4

    def test_bulk_request_validation(self) -> None:
        """Should validate bulk request constraints."""
        req = BulkRecommendationRequest(
            activity_ids=[uuid4(), uuid4()],
            top_n=5,
        )
        assert len(req.activity_ids) == 2
        assert req.top_n == 5

    def test_bulk_request_empty_ids_rejected(self) -> None:
        """Should reject empty activity_ids list."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BulkRecommendationRequest(activity_ids=[])

    def test_score_breakdown_valid(self) -> None:
        """Should create valid score breakdown."""
        sb = ScoreBreakdown(
            skill_score=0.8,
            availability_score=1.0,
            cost_score=0.6,
            certification_score=1.0,
            mandatory_skills_met=True,
            skills_matched=3,
            skills_required=4,
        )
        assert sb.skill_score == 0.8
        assert sb.mandatory_skills_met is True

    def test_skill_match_detail_valid(self) -> None:
        """Should create valid skill match detail."""
        detail = SkillMatchDetail(
            skill_id=uuid4(),
            skill_name="Python",
            skill_code="PYTHON",
            required_level=3,
            resource_level=4,
            is_mandatory=True,
            is_met=True,
            is_certified=True,
            certification_required=True,
        )
        assert detail.is_met is True
        assert detail.resource_level > detail.required_level


# =============================================================================
# Date Range Filtering Tests
# =============================================================================


class TestDateRangeFiltering:
    """Tests for date range parameter pass-through."""

    @pytest.mark.asyncio
    async def test_date_range_passed_to_assignment_repo(self) -> None:
        """Should pass date_range_start/end to assignment repo."""
        session = AsyncMock()
        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        service._session = session
        service._resource_repo = AsyncMock()
        service._rs_repo = AsyncMock()
        service._sr_repo = AsyncMock()
        service._assignment_repo = AsyncMock()

        # Setup: one resource, no requirements
        resource = _make_resource()
        service._sr_repo.get_by_activity = AsyncMock(return_value=[])
        service._fetch_all_resources = AsyncMock(return_value=[resource])
        service._rs_repo.get_by_resource = AsyncMock(return_value=[])
        service._assignment_repo.get_by_resource = AsyncMock(return_value=[])

        start = date(2024, 3, 1)
        end = date(2024, 6, 30)

        await service.recommend_for_activity(
            activity_id=uuid4(),
            program_id=uuid4(),
            date_range_start=start,
            date_range_end=end,
        )

        service._assignment_repo.get_by_resource.assert_called_once_with(
            resource.id,
            start_date=start,
            end_date=end,
        )

    @pytest.mark.asyncio
    async def test_none_dates_passed_when_not_specified(self) -> None:
        """Should pass None for dates when not specified."""
        session = AsyncMock()
        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        service._session = session
        service._resource_repo = AsyncMock()
        service._rs_repo = AsyncMock()
        service._sr_repo = AsyncMock()
        service._assignment_repo = AsyncMock()

        resource = _make_resource()
        service._sr_repo.get_by_activity = AsyncMock(return_value=[])
        service._fetch_all_resources = AsyncMock(return_value=[resource])
        service._rs_repo.get_by_resource = AsyncMock(return_value=[])
        service._assignment_repo.get_by_resource = AsyncMock(return_value=[])

        await service.recommend_for_activity(
            activity_id=uuid4(),
            program_id=uuid4(),
        )

        service._assignment_repo.get_by_resource.assert_called_once_with(
            resource.id,
            start_date=None,
            end_date=None,
        )


# =============================================================================
# Pagination Helper Tests
# =============================================================================


class TestFetchAllResources:
    """Tests for the _fetch_all_resources pagination helper."""

    @pytest.mark.asyncio
    async def test_single_page(self) -> None:
        """Should return all resources when total fits in one page."""
        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        service._resource_repo = AsyncMock()

        resources = [_make_resource(name=f"R{i}") for i in range(3)]
        service._resource_repo.get_by_program = AsyncMock(return_value=(resources, 3))

        result = await service._fetch_all_resources(uuid4())
        assert len(result) == 3
        service._resource_repo.get_by_program.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_pages(self) -> None:
        """Should paginate through all resources."""
        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        service._resource_repo = AsyncMock()

        page1 = [_make_resource(name=f"R{i}") for i in range(100)]
        page2 = [_make_resource(name=f"R{i}") for i in range(100, 150)]

        service._resource_repo.get_by_program = AsyncMock(side_effect=[(page1, 150), (page2, 150)])

        result = await service._fetch_all_resources(uuid4())
        assert len(result) == 150
        assert service._resource_repo.get_by_program.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_result(self) -> None:
        """Should return empty list when no resources exist."""
        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        service._resource_repo = AsyncMock()
        service._resource_repo.get_by_program = AsyncMock(return_value=([], 0))

        result = await service._fetch_all_resources(uuid4())
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_filter_passthrough(self) -> None:
        """Should pass resource_type and is_active filters."""
        from src.models.enums import ResourceType

        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        service._resource_repo = AsyncMock()
        service._resource_repo.get_by_program = AsyncMock(return_value=([], 0))

        program_id = uuid4()
        await service._fetch_all_resources(
            program_id, resource_type=ResourceType.LABOR, is_active=True
        )

        service._resource_repo.get_by_program.assert_called_once_with(
            program_id,
            resource_type=ResourceType.LABOR,
            is_active=True,
            skip=0,
            limit=100,
        )


class TestFetchAllActivities:
    """Tests for the _fetch_all_activities pagination helper."""

    @pytest.mark.asyncio
    async def test_single_page(self) -> None:
        """Should return all activities when total fits in one page."""
        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        service._session = AsyncMock()

        activities = [MagicMock() for _ in range(5)]
        with patch("src.repositories.activity.ActivityRepository") as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(return_value=activities)
            result = await service._fetch_all_activities(uuid4())

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_multiple_pages(self) -> None:
        """Should paginate through all activities."""
        service = ResourceRecommendationService.__new__(ResourceRecommendationService)
        service._session = AsyncMock()

        page1 = [MagicMock() for _ in range(100)]
        page2 = [MagicMock() for _ in range(30)]

        with patch("src.repositories.activity.ActivityRepository") as MockRepo:
            MockRepo.return_value.get_by_program = AsyncMock(side_effect=[page1, page2])
            result = await service._fetch_all_activities(uuid4())

        assert len(result) == 130
