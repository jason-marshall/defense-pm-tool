"""Schemas for resource recommendation requests and responses."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecommendationWeights(BaseModel):
    """Configurable weights for the recommendation scoring algorithm."""

    skill_match: float = Field(0.50, ge=0.0, le=1.0, description="Weight for skill match score")
    availability: float = Field(0.25, ge=0.0, le=1.0, description="Weight for availability score")
    cost: float = Field(0.15, ge=0.0, le=1.0, description="Weight for cost efficiency score")
    certification: float = Field(0.10, ge=0.0, le=1.0, description="Weight for certification bonus")


class RecommendationRequest(BaseModel):
    """Request parameters for generating resource recommendations."""

    top_n: int = Field(10, ge=1, le=50, description="Number of recommendations to return")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum overall score threshold")
    date_range_start: date | None = Field(None, description="Start of availability window")
    date_range_end: date | None = Field(None, description="End of availability window")
    resource_type: str | None = Field(None, description="Filter by resource type (LABOR, EQUIPMENT)")
    weights: RecommendationWeights | None = Field(None, description="Custom scoring weights")


class BulkRecommendationRequest(BaseModel):
    """Request for batch recommendations across multiple activities."""

    activity_ids: list[UUID] = Field(
        ..., min_length=1, max_length=50, description="Activity IDs to get recommendations for"
    )
    top_n: int = Field(5, ge=1, le=20, description="Number of recommendations per activity")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum overall score threshold")
    weights: RecommendationWeights | None = Field(None, description="Custom scoring weights")


class SkillMatchDetail(BaseModel):
    """Detail of how a resource matches a specific skill requirement."""

    model_config = ConfigDict(from_attributes=True)

    skill_id: UUID
    skill_name: str
    skill_code: str
    required_level: int
    resource_level: int
    is_mandatory: bool
    is_met: bool
    is_certified: bool
    certification_required: bool


class ScoreBreakdown(BaseModel):
    """Breakdown of how the recommendation score was calculated."""

    skill_score: float = Field(..., ge=0.0, le=1.0, description="Skill match score (0-1)")
    availability_score: float = Field(..., ge=0.0, le=1.0, description="Availability score (0-1)")
    cost_score: float = Field(..., ge=0.0, le=1.0, description="Cost efficiency score (0-1)")
    certification_score: float = Field(
        ..., ge=0.0, le=1.0, description="Certification bonus score (0-1)"
    )
    mandatory_skills_met: bool = Field(..., description="Whether all mandatory skills are met")
    skills_matched: int = Field(..., ge=0, description="Number of skills matched")
    skills_required: int = Field(..., ge=0, description="Total number of skills required")


class ResourceRecommendation(BaseModel):
    """A single resource recommendation for an activity."""

    model_config = ConfigDict(from_attributes=True)

    resource_id: UUID
    resource_name: str
    resource_code: str
    resource_type: str
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall recommendation score")
    score_breakdown: ScoreBreakdown
    skill_matches: list[SkillMatchDetail]
    cost_rate: Decimal | None = Field(None, description="Resource hourly cost rate")
    capacity_per_day: Decimal = Field(..., description="Resource capacity in hours/day")
    is_active: bool


class RecommendationResponse(BaseModel):
    """Response containing resource recommendations for an activity."""

    activity_id: UUID
    activity_name: str
    recommendations: list[ResourceRecommendation]
    total_candidates: int = Field(..., ge=0, description="Total resources evaluated")
    requirements_count: int = Field(..., ge=0, description="Number of skill requirements")


class BulkRecommendationResponse(BaseModel):
    """Response for bulk recommendations across multiple activities."""

    results: list[RecommendationResponse]
    total_activities: int


class ActivityRecommendation(BaseModel):
    """A recommended activity for a given resource."""

    model_config = ConfigDict(from_attributes=True)

    activity_id: UUID
    activity_name: str
    activity_code: str
    program_id: UUID
    match_score: float = Field(..., ge=0.0, le=1.0)
    skill_matches: list[SkillMatchDetail]
    skills_matched: int
    skills_required: int
    mandatory_skills_met: bool


class ResourceActivityRecommendationResponse(BaseModel):
    """Response containing recommended activities for a resource."""

    resource_id: UUID
    resource_name: str
    recommendations: list[ActivityRecommendation]
    total_activities_evaluated: int
