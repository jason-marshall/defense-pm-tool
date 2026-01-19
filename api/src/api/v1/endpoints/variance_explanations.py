"""API endpoints for Variance Explanation management.

Per EVMS guidelines (GL 21), significant variances require documented explanations.
This module provides CRUD operations for variance explanations.
"""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from fastapi import APIRouter, Query, status

from src.core.deps import CurrentUser, DbSession
from src.core.encryption import decrypt_token
from src.core.exceptions import NotFoundError, ValidationError
from src.repositories.evms_period import EVMSPeriodRepository
from src.repositories.jira_integration import JiraIntegrationRepository
from src.repositories.jira_mapping import JiraMappingRepository
from src.repositories.jira_sync_log import JiraSyncLogRepository
from src.repositories.program import ProgramRepository
from src.repositories.variance_explanation import VarianceExplanationRepository
from src.repositories.wbs import WBSElementRepository
from src.schemas.variance_explanation import (
    VarianceExplanationCreate,
    VarianceExplanationListResponse,
    VarianceExplanationResponse,
    VarianceExplanationUpdate,
    VarianceExplanationWithJiraResponse,
)
from src.services.jira_client import JiraClient
from src.services.jira_variance_alert import VarianceAlertService

if TYPE_CHECKING:
    from src.models.variance_explanation import VarianceExplanation

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/program/{program_id}", response_model=VarianceExplanationListResponse)
async def list_variance_explanations(
    db: DbSession,
    current_user: CurrentUser,
    program_id: UUID,
    variance_type: str | None = Query(
        None, description="Filter by variance type: 'schedule' or 'cost'"
    ),
    threshold_percent: Decimal = Query(
        Decimal("0"), description="Minimum variance percent to include"
    ),
    include_resolved: bool = Query(False, description="Include resolved variances"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
) -> VarianceExplanationListResponse:
    """
    List all variance explanations for a program.

    Returns variance explanations ordered by creation date (newest first).
    Optionally filter by variance type and threshold.
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    repo = VarianceExplanationRepository(db)

    # Get all explanations for the program
    if threshold_percent > 0:
        explanations = await repo.get_significant_variances(
            program_id=program_id,
            threshold_percent=threshold_percent,
            include_deleted=False,
        )
    else:
        explanations = await repo.get_by_program(
            program_id=program_id,
            variance_type=variance_type,
            include_deleted=False,
        )

    # Filter by variance type if specified (for significant variances)
    if threshold_percent > 0 and variance_type:
        explanations = [e for e in explanations if e.variance_type == variance_type]

    # Filter out resolved if requested
    if not include_resolved:
        from datetime import date

        today = date.today()
        explanations = [
            e
            for e in explanations
            if e.expected_resolution is None or e.expected_resolution > today
        ]

    # Calculate pagination
    total = len(explanations)
    skip = (page - 1) * per_page
    paginated = explanations[skip : skip + per_page]

    return VarianceExplanationListResponse(
        items=[VarianceExplanationResponse.model_validate(e) for e in paginated],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 1,
    )


@router.get("/period/{period_id}", response_model=list[VarianceExplanationResponse])
async def list_variance_explanations_by_period(
    db: DbSession,
    current_user: CurrentUser,
    period_id: UUID,
) -> list[VarianceExplanationResponse]:
    """
    List all variance explanations for a specific EVMS period.

    Returns variance explanations ordered by variance percent (highest first).
    """
    # Verify period exists
    period_repo = EVMSPeriodRepository(db)
    period = await period_repo.get(period_id)
    if not period:
        raise NotFoundError(f"Period {period_id} not found", "PERIOD_NOT_FOUND")

    repo = VarianceExplanationRepository(db)
    explanations = await repo.get_by_period(period_id)

    return [VarianceExplanationResponse.model_validate(e) for e in explanations]


@router.get("/wbs/{wbs_id}", response_model=list[VarianceExplanationResponse])
async def list_variance_explanations_by_wbs(
    db: DbSession,
    current_user: CurrentUser,
    wbs_id: UUID,
) -> list[VarianceExplanationResponse]:
    """
    List all variance explanations for a specific WBS element.

    Returns variance explanations ordered by creation date (newest first).
    """
    # Verify WBS element exists
    wbs_repo = WBSElementRepository(db)
    wbs = await wbs_repo.get(wbs_id)
    if not wbs:
        raise NotFoundError(f"WBS element {wbs_id} not found", "WBS_NOT_FOUND")

    repo = VarianceExplanationRepository(db)
    explanations = await repo.get_by_wbs(wbs_id)

    return [VarianceExplanationResponse.model_validate(e) for e in explanations]


@router.post(
    "",
    response_model=VarianceExplanationWithJiraResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_variance_explanation(
    db: DbSession,
    current_user: CurrentUser,
    explanation_data: VarianceExplanationCreate,
) -> VarianceExplanationWithJiraResponse:
    """
    Create a new variance explanation.

    Per DFARS requirements, variances exceeding threshold (typically 10%)
    require a written explanation and optionally a corrective action plan.

    Optionally creates a Jira issue for tracking if:
    - create_jira_issue is True
    - Program has Jira integration configured
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get(explanation_data.program_id)
    if not program:
        raise NotFoundError(
            f"Program {explanation_data.program_id} not found",
            "PROGRAM_NOT_FOUND",
        )

    # Verify WBS element if provided
    wbs = None
    wbs_name = None
    if explanation_data.wbs_id:
        wbs_repo = WBSElementRepository(db)
        wbs = await wbs_repo.get(explanation_data.wbs_id)
        if not wbs:
            raise NotFoundError(
                f"WBS element {explanation_data.wbs_id} not found",
                "WBS_NOT_FOUND",
            )
        # Verify WBS belongs to the program
        if wbs.program_id != explanation_data.program_id:
            raise ValidationError(
                "WBS element does not belong to the specified program",
                "WBS_PROGRAM_MISMATCH",
            )
        wbs_name = wbs.name

    # Verify period if provided
    if explanation_data.period_id:
        period_repo = EVMSPeriodRepository(db)
        period = await period_repo.get(explanation_data.period_id)
        if not period:
            raise NotFoundError(
                f"Period {explanation_data.period_id} not found",
                "PERIOD_NOT_FOUND",
            )
        # Verify period belongs to the program
        if period.program_id != explanation_data.program_id:
            raise ValidationError(
                "Period does not belong to the specified program",
                "PERIOD_PROGRAM_MISMATCH",
            )

    repo = VarianceExplanationRepository(db)

    # Create the explanation
    data = explanation_data.model_dump(exclude={"create_jira_issue"})
    data["variance_type"] = data["variance_type"].value  # Convert enum to string
    data["created_by"] = current_user.id

    explanation = await repo.create(data)
    await db.commit()
    await db.refresh(explanation)

    # Create Jira issue if requested
    jira_issue_key = None
    jira_issue_created = False

    if explanation_data.create_jira_issue:
        jira_issue_key, jira_issue_created = await _try_create_jira_issue(
            db=db,
            program_id=explanation_data.program_id,
            variance=explanation,
            wbs_name=wbs_name,
        )

    response = VarianceExplanationWithJiraResponse.model_validate(explanation)
    response.jira_issue_key = jira_issue_key
    response.jira_issue_created = jira_issue_created

    return response


async def _try_create_jira_issue(
    db: DbSession,
    program_id: UUID,
    variance: "VarianceExplanation",
    wbs_name: str | None,
) -> tuple[str | None, bool]:
    """Try to create a Jira issue for the variance.

    Returns:
        Tuple of (jira_issue_key, success_flag)
    """

    # Check if program has Jira integration
    integration_repo = JiraIntegrationRepository(db)
    integration = await integration_repo.get_by_program(program_id)

    if not integration:
        logger.debug(
            "variance_jira_skip_no_integration",
            program_id=str(program_id),
        )
        return None, False

    if not integration.sync_enabled:
        logger.debug(
            "variance_jira_skip_sync_disabled",
            program_id=str(program_id),
        )
        return None, False

    try:
        # Create Jira client
        token = decrypt_token(integration.api_token_encrypted.decode())
        client = JiraClient(
            jira_url=integration.jira_url,
            email=integration.email,
            api_token=token,
        )

        # Create variance alert service
        mapping_repo = JiraMappingRepository(db)
        sync_log_repo = JiraSyncLogRepository(db)

        service = VarianceAlertService(
            jira_client=client,
            integration_repo=integration_repo,
            mapping_repo=mapping_repo,
            sync_log_repo=sync_log_repo,
        )

        # Create the issue
        result = await service.create_variance_issue(
            integration_id=integration.id,
            variance=variance,
            wbs_name=wbs_name,
        )

        await db.commit()

        if result.success:
            logger.info(
                "variance_jira_issue_created",
                variance_id=str(variance.id),
                jira_key=result.jira_issue_key,
            )
            return result.jira_issue_key, True
        else:
            logger.warning(
                "variance_jira_issue_failed",
                variance_id=str(variance.id),
                error=result.error_message,
            )
            return None, False

    except Exception as e:
        logger.error(
            "variance_jira_issue_error",
            variance_id=str(variance.id),
            error=str(e),
        )
        return None, False


@router.get("/{explanation_id}", response_model=VarianceExplanationResponse)
async def get_variance_explanation(
    db: DbSession,
    current_user: CurrentUser,
    explanation_id: UUID,
) -> VarianceExplanationResponse:
    """
    Get a specific variance explanation by ID.
    """
    repo = VarianceExplanationRepository(db)
    explanation = await repo.get(explanation_id)

    if not explanation:
        raise NotFoundError(
            f"Variance explanation {explanation_id} not found",
            "VARIANCE_EXPLANATION_NOT_FOUND",
        )

    return VarianceExplanationResponse.model_validate(explanation)


@router.patch("/{explanation_id}", response_model=VarianceExplanationResponse)
async def update_variance_explanation(
    db: DbSession,
    current_user: CurrentUser,
    explanation_id: UUID,
    update_data: VarianceExplanationUpdate,
) -> VarianceExplanationResponse:
    """
    Update a variance explanation.

    Can update explanation text, corrective action, expected resolution,
    and variance amounts.
    """
    repo = VarianceExplanationRepository(db)
    explanation = await repo.get(explanation_id)

    if not explanation:
        raise NotFoundError(
            f"Variance explanation {explanation_id} not found",
            "VARIANCE_EXPLANATION_NOT_FOUND",
        )

    # Update only provided fields
    update_dict = update_data.model_dump(exclude_unset=True)
    if update_dict:
        explanation = await repo.update(explanation, update_dict)

    await db.commit()
    await db.refresh(explanation)

    return VarianceExplanationResponse.model_validate(explanation)


@router.delete("/{explanation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variance_explanation(
    db: DbSession,
    current_user: CurrentUser,
    explanation_id: UUID,
) -> None:
    """
    Soft delete a variance explanation.

    The explanation is marked as deleted but retained for audit purposes.
    """
    repo = VarianceExplanationRepository(db)
    explanation = await repo.get(explanation_id)

    if not explanation:
        raise NotFoundError(
            f"Variance explanation {explanation_id} not found",
            "VARIANCE_EXPLANATION_NOT_FOUND",
        )

    await repo.delete(explanation_id)
    await db.commit()


@router.post("/{explanation_id}/restore", response_model=VarianceExplanationResponse)
async def restore_variance_explanation(
    db: DbSession,
    current_user: CurrentUser,
    explanation_id: UUID,
) -> VarianceExplanationResponse:
    """
    Restore a soft-deleted variance explanation.
    """
    repo = VarianceExplanationRepository(db)
    explanation = await repo.restore(explanation_id)

    if not explanation:
        raise NotFoundError(
            f"Variance explanation {explanation_id} not found",
            "VARIANCE_EXPLANATION_NOT_FOUND",
        )

    await db.commit()
    await db.refresh(explanation)

    return VarianceExplanationResponse.model_validate(explanation)


@router.get("/program/{program_id}/significant", response_model=list[VarianceExplanationResponse])
async def get_significant_variances(
    db: DbSession,
    current_user: CurrentUser,
    program_id: UUID,
    threshold_percent: Decimal = Query(
        Decimal("10.0"),
        description="Minimum variance percent threshold",
    ),
) -> list[VarianceExplanationResponse]:
    """
    Get variance explanations for significant variances (above threshold).

    Per EVMS guidelines, variances exceeding 10% typically require explanation.
    This endpoint returns all explanations above the specified threshold.
    """
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get(program_id)
    if not program:
        raise NotFoundError(f"Program {program_id} not found", "PROGRAM_NOT_FOUND")

    repo = VarianceExplanationRepository(db)
    explanations = await repo.get_significant_variances(
        program_id=program_id,
        threshold_percent=threshold_percent,
    )

    return [VarianceExplanationResponse.model_validate(e) for e in explanations]
