"""Service for generating resource recommendations based on skill matching."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enums import ResourceType
from src.models.resource import Resource
from src.models.skill import ResourceSkill, SkillRequirement
from src.repositories.resource import ResourceAssignmentRepository, ResourceRepository
from src.repositories.skill import ResourceSkillRepository, SkillRequirementRepository
from src.schemas.recommendation import (
    ActivityRecommendation,
    RecommendationWeights,
    ResourceRecommendation,
    ScoreBreakdown,
    SkillMatchDetail,
)


@dataclass
class _SkillMatch:
    """Internal representation of a skill match during scoring."""

    skill_id: UUID
    skill_name: str
    skill_code: str
    required_level: int
    resource_level: int
    is_mandatory: bool
    is_met: bool
    is_certified: bool
    certification_required: bool


@dataclass
class _ScoringContext:
    """Aggregated context for scoring a single resource against an activity."""

    resource: Resource
    resource_skills: dict[UUID, ResourceSkill]
    requirements: list[SkillRequirement]
    assignment_count: int = 0
    weights: RecommendationWeights = field(default_factory=lambda: RecommendationWeights())


class ResourceRecommendationService:
    """Scores and ranks resources based on skill match, availability, and cost.

    The scoring algorithm evaluates resources against activity skill requirements
    using configurable weights for each dimension:
    - Skill match (default 50%): How well resource skills match requirements
    - Availability (default 25%): Resource current utilization
    - Cost (default 15%): Cost rate relative to other candidates
    - Certification (default 10%): Bonus for having required certifications
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self._session = session
        self._resource_repo = ResourceRepository(session)
        self._rs_repo = ResourceSkillRepository(session)
        self._sr_repo = SkillRequirementRepository(session)
        self._assignment_repo = ResourceAssignmentRepository(session)

    async def recommend_for_activity(
        self,
        activity_id: UUID,
        program_id: UUID,
        *,
        top_n: int = 10,
        min_score: float = 0.0,
        resource_type: str | None = None,
        weights: RecommendationWeights | None = None,
        date_range_start: date | None = None,
        date_range_end: date | None = None,
    ) -> tuple[list[ResourceRecommendation], int, int]:
        """Generate ranked resource recommendations for an activity.

        Args:
            activity_id: Activity to find resources for
            program_id: Program scope for resources
            top_n: Maximum number of recommendations
            min_score: Minimum score threshold (0-1)
            resource_type: Filter by resource type
            weights: Custom scoring weights

        Returns:
            Tuple of (recommendations, total_candidates, requirements_count)
        """
        if weights is None:
            weights = RecommendationWeights()

        requirements = await self._sr_repo.get_by_activity(activity_id)
        requirements_count = len(requirements)

        # Convert string resource_type to enum if provided
        rt_enum: ResourceType | None = None
        if resource_type is not None:
            try:
                rt_enum = ResourceType(resource_type)
            except ValueError:
                rt_enum = None

        resources = await self._fetch_all_resources(
            program_id, resource_type=rt_enum, is_active=True
        )
        total_candidates = len(resources)

        if not resources:
            return [], total_candidates, requirements_count

        # Build skill map for each resource
        resource_skill_maps: dict[UUID, dict[UUID, ResourceSkill]] = {}
        assignment_counts: dict[UUID, int] = {}
        for resource in resources:
            rs_list = await self._rs_repo.get_by_resource(resource.id)
            resource_skill_maps[resource.id] = {rs.skill_id: rs for rs in rs_list}
            assignments = await self._assignment_repo.get_by_resource(
                resource.id,
                start_date=date_range_start,
                end_date=date_range_end,
            )
            assignment_counts[resource.id] = len(assignments)

        # Collect all cost rates for normalization
        cost_rates = [r.cost_rate for r in resources if r.cost_rate is not None and r.cost_rate > 0]
        max_cost = max(cost_rates) if cost_rates else Decimal("1")

        # Score each resource
        scored: list[ResourceRecommendation] = []
        for resource in resources:
            ctx = _ScoringContext(
                resource=resource,
                resource_skills=resource_skill_maps[resource.id],
                requirements=requirements,
                assignment_count=assignment_counts[resource.id],
                weights=weights,
            )
            recommendation = self._score_resource(ctx, max_cost)
            if recommendation.overall_score >= min_score:
                scored.append(recommendation)

        scored.sort(key=lambda r: r.overall_score, reverse=True)
        return scored[:top_n], total_candidates, requirements_count

    async def recommend_activities_for_resource(
        self,
        resource_id: UUID,
        program_id: UUID,
        *,
        top_n: int = 10,
        min_score: float = 0.0,
    ) -> tuple[list[ActivityRecommendation], int]:
        """Find activities that best match a resource's skills.

        Args:
            resource_id: Resource to find activities for
            program_id: Program scope for activities
            top_n: Maximum recommendations
            min_score: Minimum match score

        Returns:
            Tuple of (activity recommendations, total_activities_evaluated)
        """
        resource_skills_list = await self._rs_repo.get_by_resource(resource_id)
        resource_skills = {rs.skill_id: rs for rs in resource_skills_list}

        # Get all activities in the program that have skill requirements
        activities = await self._fetch_all_activities(program_id)
        total_evaluated = 0

        results: list[ActivityRecommendation] = []
        for activity in activities:
            requirements = await self._sr_repo.get_by_activity(activity.id)
            if not requirements:
                continue
            total_evaluated += 1

            matches = self._compute_skill_matches(requirements, resource_skills)
            skill_score = self._calculate_skill_score(matches)
            mandatory_met = all(m.is_met for m in matches if m.is_mandatory)
            matched_count = sum(1 for m in matches if m.is_met)

            if skill_score >= min_score:
                results.append(
                    ActivityRecommendation(
                        activity_id=activity.id,
                        activity_name=activity.name,
                        activity_code=activity.code,
                        program_id=activity.program_id,
                        match_score=round(skill_score, 4),
                        skill_matches=[
                            SkillMatchDetail(
                                skill_id=m.skill_id,
                                skill_name=m.skill_name,
                                skill_code=m.skill_code,
                                required_level=m.required_level,
                                resource_level=m.resource_level,
                                is_mandatory=m.is_mandatory,
                                is_met=m.is_met,
                                is_certified=m.is_certified,
                                certification_required=m.certification_required,
                            )
                            for m in matches
                        ],
                        skills_matched=matched_count,
                        skills_required=len(requirements),
                        mandatory_skills_met=mandatory_met,
                    )
                )

        results.sort(key=lambda r: r.match_score, reverse=True)
        return results[:top_n], total_evaluated

    def _score_resource(
        self,
        ctx: _ScoringContext,
        max_cost: Decimal,
    ) -> ResourceRecommendation:
        """Score a single resource against activity requirements."""
        matches = self._compute_skill_matches(ctx.requirements, ctx.resource_skills)

        skill_score = self._calculate_skill_score(matches)
        availability_score = self._calculate_availability_score(ctx.assignment_count)
        cost_score = self._calculate_cost_score(ctx.resource, max_cost)
        certification_score = self._calculate_certification_score(matches)

        mandatory_met = all(m.is_met for m in matches if m.is_mandatory)
        matched_count = sum(1 for m in matches if m.is_met)

        # If mandatory skills are not met, heavily penalize
        penalty = 1.0 if mandatory_met else 0.3

        w = ctx.weights
        overall = (
            w.skill_match * skill_score
            + w.availability * availability_score
            + w.cost * cost_score
            + w.certification * certification_score
        ) * penalty

        # Clamp to [0, 1]
        overall = max(0.0, min(1.0, overall))

        return ResourceRecommendation(
            resource_id=ctx.resource.id,
            resource_name=ctx.resource.name,
            resource_code=ctx.resource.code,
            resource_type=ctx.resource.resource_type.value
            if hasattr(ctx.resource.resource_type, "value")
            else str(ctx.resource.resource_type),
            overall_score=round(overall, 4),
            score_breakdown=ScoreBreakdown(
                skill_score=round(skill_score, 4),
                availability_score=round(availability_score, 4),
                cost_score=round(cost_score, 4),
                certification_score=round(certification_score, 4),
                mandatory_skills_met=mandatory_met,
                skills_matched=matched_count,
                skills_required=len(ctx.requirements),
            ),
            skill_matches=[
                SkillMatchDetail(
                    skill_id=m.skill_id,
                    skill_name=m.skill_name,
                    skill_code=m.skill_code,
                    required_level=m.required_level,
                    resource_level=m.resource_level,
                    is_mandatory=m.is_mandatory,
                    is_met=m.is_met,
                    is_certified=m.is_certified,
                    certification_required=m.certification_required,
                )
                for m in matches
            ],
            cost_rate=ctx.resource.cost_rate,
            capacity_per_day=ctx.resource.capacity_per_day,
            is_active=ctx.resource.is_active,
        )

    def _compute_skill_matches(
        self,
        requirements: list[SkillRequirement],
        resource_skills: dict[UUID, ResourceSkill],
    ) -> list[_SkillMatch]:
        """Compute how well resource skills match each requirement."""
        matches: list[_SkillMatch] = []
        for req in requirements:
            rs = resource_skills.get(req.skill_id)
            skill = req.skill

            skill_name = skill.name if skill else "Unknown"
            skill_code = skill.code if skill else "UNKNOWN"
            cert_required = skill.requires_certification if skill else False

            if rs is not None:
                is_met = rs.proficiency_level >= req.required_level
                matches.append(
                    _SkillMatch(
                        skill_id=req.skill_id,
                        skill_name=skill_name,
                        skill_code=skill_code,
                        required_level=req.required_level,
                        resource_level=rs.proficiency_level,
                        is_mandatory=req.is_mandatory,
                        is_met=is_met,
                        is_certified=rs.is_certified,
                        certification_required=cert_required,
                    )
                )
            else:
                matches.append(
                    _SkillMatch(
                        skill_id=req.skill_id,
                        skill_name=skill_name,
                        skill_code=skill_code,
                        required_level=req.required_level,
                        resource_level=0,
                        is_mandatory=req.is_mandatory,
                        is_met=False,
                        is_certified=False,
                        certification_required=cert_required,
                    )
                )
        return matches

    @staticmethod
    def _calculate_skill_score(matches: list[_SkillMatch]) -> float:
        """Calculate skill match score (0-1).

        Scoring logic:
        - If no requirements, return 1.0 (any resource fits)
        - For each matched skill: level_ratio = min(resource_level / required_level, 1.0)
        - Mandatory skills are weighted 2x
        - Unmatched skills contribute 0
        """
        if not matches:
            return 1.0

        total_weight = 0.0
        weighted_score = 0.0

        for m in matches:
            weight = 2.0 if m.is_mandatory else 1.0
            total_weight += weight

            if m.resource_level > 0:
                ratio = min(m.resource_level / m.required_level, 1.0)
                # Bonus for exceeding requirement (up to 10%)
                if m.resource_level > m.required_level:
                    excess = (m.resource_level - m.required_level) / 5.0
                    ratio = min(ratio + excess * 0.1, 1.0)
                weighted_score += weight * ratio

        if total_weight == 0:
            return 1.0
        return weighted_score / total_weight

    @staticmethod
    def _calculate_availability_score(assignment_count: int) -> float:
        """Calculate availability score (0-1).

        Resources with fewer assignments score higher.
        0 assignments = 1.0, 5+ assignments = 0.2
        """
        if assignment_count == 0:
            return 1.0
        if assignment_count >= 5:
            return 0.2
        return 1.0 - (assignment_count * 0.16)

    @staticmethod
    def _calculate_cost_score(resource: Resource, max_cost: Decimal) -> float:
        """Calculate cost efficiency score (0-1).

        Lower cost rates score higher. Resources with no cost rate get 0.5.
        """
        if resource.cost_rate is None or resource.cost_rate == 0:
            return 0.5
        if max_cost == 0:
            return 0.5
        ratio = float(resource.cost_rate / max_cost)
        return max(0.0, 1.0 - ratio * 0.8)

    @staticmethod
    def _calculate_certification_score(matches: list[_SkillMatch]) -> float:
        """Calculate certification bonus score (0-1).

        Resources get credit for having certifications on skills that require them.
        """
        cert_required = [m for m in matches if m.certification_required]
        if not cert_required:
            return 1.0  # No certifications needed = full score

        certified_count = sum(1 for m in cert_required if m.is_certified)
        return certified_count / len(cert_required)

    async def _fetch_all_resources(
        self,
        program_id: UUID,
        *,
        resource_type: ResourceType | None = None,
        is_active: bool | None = None,
    ) -> list[Resource]:
        """Fetch all resources for a program using pagination.

        Iterates through pages to avoid missing resources in large programs.
        """
        batch_size = 100
        all_resources: list[Resource] = []
        skip = 0

        while True:
            batch, total = await self._resource_repo.get_by_program(
                program_id,
                resource_type=resource_type,
                is_active=is_active,
                skip=skip,
                limit=batch_size,
            )
            all_resources.extend(batch)
            if len(all_resources) >= total or len(batch) < batch_size:
                break
            skip += batch_size

        return all_resources

    async def _fetch_all_activities(self, program_id: UUID) -> list[Any]:
        """Fetch all activities for a program using pagination.

        Iterates through pages to avoid missing activities in large programs.
        """
        from src.repositories.activity import ActivityRepository  # noqa: PLC0415

        activity_repo = ActivityRepository(self._session)
        batch_size = 100
        all_activities: list[Any] = []
        skip = 0

        while True:
            batch = await activity_repo.get_by_program(program_id, skip=skip, limit=batch_size)
            all_activities.extend(batch)
            if len(batch) < batch_size:
                break
            skip += batch_size

        return all_activities
