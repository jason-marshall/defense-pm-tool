"""Jira integration API endpoints.

Provides endpoints for:
- Connecting programs to Jira projects
- Syncing WBS elements to Epics
- Syncing Activities to Issues
- Managing mappings
- Viewing sync logs
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from src.core.deps import DbSession
from src.core.encryption import decrypt_token, encrypt_token
from src.core.exceptions import NotFoundError
from src.core.rate_limit import RATE_LIMIT_SYNC, limiter
from src.repositories.activity import ActivityRepository
from src.repositories.jira_integration import JiraIntegrationRepository
from src.repositories.jira_mapping import JiraMappingRepository
from src.repositories.jira_sync_log import JiraSyncLogRepository
from src.repositories.program import ProgramRepository
from src.repositories.wbs import WBSElementRepository
from src.schemas.jira_integration import (
    ActivityProgressSyncRequest,
    ActivityProgressSyncResponse,
    ActivityProgressSyncResult,
    EntityType,
    JiraConnectionTestResponse,
    JiraIntegrationCreate,
    JiraIntegrationResponse,
    JiraIntegrationUpdate,
    JiraMappingCreate,
    JiraMappingResponse,
    JiraSyncLogListResponse,
    JiraSyncLogResponse,
    JiraSyncRequest,
    JiraSyncResponse,
)
from src.services.jira_activity_sync import (
    ActivitySyncService,
)
from src.services.jira_activity_sync import (
    IntegrationNotFoundError as ActivityIntegrationNotFound,
)
from src.services.jira_activity_sync import (
    SyncDisabledError as ActivitySyncDisabled,
)
from src.services.jira_client import JiraClient
from src.services.jira_wbs_sync import (
    IntegrationNotFoundError as WBSIntegrationNotFound,
)
from src.services.jira_wbs_sync import (
    SyncDisabledError as WBSSyncDisabled,
)
from src.services.jira_wbs_sync import (
    WBSSyncService,
)

router = APIRouter()


# Integration endpoints


@router.post(
    "/integrations",
    response_model=JiraIntegrationResponse,
    status_code=201,
)
async def create_integration(
    integration_in: JiraIntegrationCreate,
    db: DbSession,
) -> JiraIntegrationResponse:
    """Create a new Jira integration for a program."""
    # Verify program exists
    program_repo = ProgramRepository(db)
    program = await program_repo.get_by_id(integration_in.program_id)
    if not program:
        raise NotFoundError(
            f"Program {integration_in.program_id} not found",
            "PROGRAM_NOT_FOUND",
        )

    # Check if integration already exists
    integration_repo = JiraIntegrationRepository(db)
    existing = await integration_repo.get_by_program(integration_in.program_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Jira integration already exists for this program",
        )

    # Encrypt API token (stored as bytes in LargeBinary column)
    encrypted_token = encrypt_token(integration_in.api_token).encode()

    # Create integration
    integration_data = {
        "program_id": integration_in.program_id,
        "jira_url": str(integration_in.jira_url),
        "project_key": integration_in.project_key,
        "email": integration_in.email,
        "api_token_encrypted": encrypted_token,
        "epic_custom_field": integration_in.epic_custom_field,
    }

    integration = await integration_repo.create(integration_data)
    await db.commit()

    return JiraIntegrationResponse.model_validate(integration)


@router.get(
    "/integrations/{integration_id}",
    response_model=JiraIntegrationResponse,
)
async def get_integration(
    integration_id: UUID,
    db: DbSession,
) -> JiraIntegrationResponse:
    """Get a Jira integration by ID."""
    integration_repo = JiraIntegrationRepository(db)
    integration = await integration_repo.get_by_id(integration_id)

    if not integration:
        raise NotFoundError(
            f"Jira integration {integration_id} not found",
            "JIRA_INTEGRATION_NOT_FOUND",
        )

    return JiraIntegrationResponse.model_validate(integration)


@router.get(
    "/programs/{program_id}/integration",
    response_model=JiraIntegrationResponse,
)
async def get_program_integration(
    program_id: UUID,
    db: DbSession,
) -> JiraIntegrationResponse:
    """Get Jira integration for a program."""
    integration_repo = JiraIntegrationRepository(db)
    integration = await integration_repo.get_by_program(program_id)

    if not integration:
        raise NotFoundError(
            f"No Jira integration found for program {program_id}",
            "JIRA_INTEGRATION_NOT_FOUND",
        )

    return JiraIntegrationResponse.model_validate(integration)


@router.patch(
    "/integrations/{integration_id}",
    response_model=JiraIntegrationResponse,
)
async def update_integration(
    integration_id: UUID,
    integration_in: JiraIntegrationUpdate,
    db: DbSession,
) -> JiraIntegrationResponse:
    """Update Jira integration settings."""
    integration_repo = JiraIntegrationRepository(db)
    integration = await integration_repo.get_by_id(integration_id)

    if not integration:
        raise NotFoundError(
            f"Jira integration {integration_id} not found",
            "JIRA_INTEGRATION_NOT_FOUND",
        )

    update_data = integration_in.model_dump(exclude_unset=True)
    updated = await integration_repo.update(integration, update_data)
    await db.commit()

    return JiraIntegrationResponse.model_validate(updated)


@router.delete(
    "/integrations/{integration_id}",
    status_code=204,
)
async def delete_integration(
    integration_id: UUID,
    db: DbSession,
) -> None:
    """Delete a Jira integration and all its mappings."""
    integration_repo = JiraIntegrationRepository(db)
    integration = await integration_repo.get_by_id(integration_id)

    if not integration:
        raise NotFoundError(
            f"Jira integration {integration_id} not found",
            "JIRA_INTEGRATION_NOT_FOUND",
        )

    await integration_repo.delete(integration.id)
    await db.commit()


@router.post(
    "/integrations/{integration_id}/test",
    response_model=JiraConnectionTestResponse,
)
async def test_connection(
    integration_id: UUID,
    db: DbSession,
) -> JiraConnectionTestResponse:
    """Test connection to Jira."""
    integration_repo = JiraIntegrationRepository(db)
    integration = await integration_repo.get_by_id(integration_id)

    if not integration:
        raise NotFoundError(
            f"Jira integration {integration_id} not found",
            "JIRA_INTEGRATION_NOT_FOUND",
        )

    try:
        # Decrypt token and test connection (token stored as bytes)
        token = decrypt_token(integration.api_token_encrypted.decode())
        client = JiraClient(
            jira_url=integration.jira_url,
            email=integration.email,
            api_token=token,
        )

        project_info = await client.get_project(integration.project_key)

        return JiraConnectionTestResponse(
            success=True,
            message="Connection successful",
            project_name=project_info.name,
            issue_types=None,  # Not available from JiraProjectData
        )

    except Exception as e:
        return JiraConnectionTestResponse(
            success=False,
            message=f"Connection failed: {e!s}",
        )


# Sync endpoints


@router.post(
    "/integrations/{integration_id}/sync/wbs",
    response_model=JiraSyncResponse,
)
@limiter.limit(RATE_LIMIT_SYNC)
async def sync_wbs_to_jira(
    request: Request,
    integration_id: UUID,
    sync_request: JiraSyncRequest,
    db: DbSession,
) -> JiraSyncResponse:
    """Sync WBS elements to Jira Epics."""
    integration_repo = JiraIntegrationRepository(db)
    integration = await integration_repo.get_by_id(integration_id)

    if not integration:
        raise NotFoundError(
            f"Jira integration {integration_id} not found",
            "JIRA_INTEGRATION_NOT_FOUND",
        )

    try:
        # Get decrypted token and create client
        token = decrypt_token(integration.api_token_encrypted.decode())
        client = JiraClient(
            jira_url=integration.jira_url,
            email=integration.email,
            api_token=token,
        )

        # Create sync service
        mapping_repo = JiraMappingRepository(db)
        sync_log_repo = JiraSyncLogRepository(db)
        wbs_repo = WBSElementRepository(db)

        service = WBSSyncService(
            jira_client=client,
            integration_repo=integration_repo,
            mapping_repo=mapping_repo,
            sync_log_repo=sync_log_repo,
            wbs_repo=wbs_repo,
        )

        # Run sync
        result = await service.sync_wbs_to_jira(
            integration_id=integration_id,
            wbs_ids=sync_request.entity_ids,
        )

        await db.commit()

        return JiraSyncResponse(
            success=result.success,
            sync_type="push",
            items_synced=result.items_synced,
            items_failed=result.items_failed,
            duration_ms=result.duration_ms,
            errors=result.errors,
        )

    except (WBSIntegrationNotFound, WBSSyncDisabled) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/integrations/{integration_id}/sync/activities",
    response_model=JiraSyncResponse,
)
@limiter.limit(RATE_LIMIT_SYNC)
async def sync_activities_to_jira(
    request: Request,
    integration_id: UUID,
    sync_request: JiraSyncRequest,
    db: DbSession,
) -> JiraSyncResponse:
    """Sync Activities to Jira Issues."""
    integration_repo = JiraIntegrationRepository(db)
    integration = await integration_repo.get_by_id(integration_id)

    if not integration:
        raise NotFoundError(
            f"Jira integration {integration_id} not found",
            "JIRA_INTEGRATION_NOT_FOUND",
        )

    try:
        # Get decrypted token and create client
        token = decrypt_token(integration.api_token_encrypted.decode())
        client = JiraClient(
            jira_url=integration.jira_url,
            email=integration.email,
            api_token=token,
        )

        # Create sync service
        mapping_repo = JiraMappingRepository(db)
        sync_log_repo = JiraSyncLogRepository(db)
        activity_repo = ActivityRepository(db)

        service = ActivitySyncService(
            jira_client=client,
            integration_repo=integration_repo,
            mapping_repo=mapping_repo,
            sync_log_repo=sync_log_repo,
            activity_repo=activity_repo,
        )

        # Run sync
        result = await service.sync_activities_to_jira(
            integration_id=integration_id,
            activity_ids=sync_request.entity_ids,
        )

        await db.commit()

        return JiraSyncResponse(
            success=result.success,
            sync_type="push",
            items_synced=result.items_synced,
            items_failed=result.items_failed,
            duration_ms=result.duration_ms,
            errors=result.errors,
        )

    except (ActivityIntegrationNotFound, ActivitySyncDisabled) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/integrations/{integration_id}/sync/progress",
    response_model=ActivityProgressSyncResponse,
)
@limiter.limit(RATE_LIMIT_SYNC)
async def sync_activity_progress(
    request: Request,
    integration_id: UUID,
    sync_request: ActivityProgressSyncRequest,
    db: DbSession,
) -> ActivityProgressSyncResponse:
    """Sync activity progress to Jira Issues."""
    integration_repo = JiraIntegrationRepository(db)
    integration = await integration_repo.get_by_id(integration_id)

    if not integration:
        raise NotFoundError(
            f"Jira integration {integration_id} not found",
            "JIRA_INTEGRATION_NOT_FOUND",
        )

    try:
        # Get decrypted token and create client
        token = decrypt_token(integration.api_token_encrypted.decode())
        client = JiraClient(
            jira_url=integration.jira_url,
            email=integration.email,
            api_token=token,
        )

        # Create sync service
        mapping_repo = JiraMappingRepository(db)
        sync_log_repo = JiraSyncLogRepository(db)
        activity_repo = ActivityRepository(db)

        service = ActivitySyncService(
            jira_client=client,
            integration_repo=integration_repo,
            mapping_repo=mapping_repo,
            sync_log_repo=sync_log_repo,
            activity_repo=activity_repo,
        )

        # Run progress sync
        result = await service.sync_progress(
            integration_id=integration_id,
            activity_ids=sync_request.activity_ids,
        )

        await db.commit()

        # Build detailed results
        results = []
        for mapping_id in result.updated_mappings:
            mapping = await mapping_repo.get_by_id(mapping_id)
            if mapping and mapping.activity_id:
                activity = await activity_repo.get_by_id(mapping.activity_id)
                if activity:
                    results.append(
                        ActivityProgressSyncResult(
                            activity_id=activity.id,
                            activity_code=activity.code,
                            jira_issue_key=mapping.jira_issue_key,
                            percent_complete=activity.percent_complete,
                            jira_status="synced",
                            success=True,
                        )
                    )

        return ActivityProgressSyncResponse(
            success=result.success,
            synced_count=result.items_synced,
            failed_count=result.items_failed,
            results=results,
        )

    except (ActivityIntegrationNotFound, ActivitySyncDisabled) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/integrations/{integration_id}/sync/pull",
    response_model=JiraSyncResponse,
)
async def pull_from_jira(
    integration_id: UUID,
    sync_request: JiraSyncRequest,
    db: DbSession,
) -> JiraSyncResponse:
    """Pull updates from Jira to Activities."""
    integration_repo = JiraIntegrationRepository(db)
    integration = await integration_repo.get_by_id(integration_id)

    if not integration:
        raise NotFoundError(
            f"Jira integration {integration_id} not found",
            "JIRA_INTEGRATION_NOT_FOUND",
        )

    try:
        # Get decrypted token and create client
        token = decrypt_token(integration.api_token_encrypted.decode())
        client = JiraClient(
            jira_url=integration.jira_url,
            email=integration.email,
            api_token=token,
        )

        # Create sync service
        mapping_repo = JiraMappingRepository(db)
        sync_log_repo = JiraSyncLogRepository(db)
        activity_repo = ActivityRepository(db)

        service = ActivitySyncService(
            jira_client=client,
            integration_repo=integration_repo,
            mapping_repo=mapping_repo,
            sync_log_repo=sync_log_repo,
            activity_repo=activity_repo,
        )

        # Run pull
        result = await service.pull_from_jira(
            integration_id=integration_id,
            mapping_ids=sync_request.entity_ids,
        )

        await db.commit()

        return JiraSyncResponse(
            success=result.success,
            sync_type="pull",
            items_synced=result.items_synced,
            items_failed=result.items_failed,
            duration_ms=result.duration_ms,
            errors=result.errors,
        )

    except (ActivityIntegrationNotFound, ActivitySyncDisabled) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# Mapping endpoints


@router.get(
    "/integrations/{integration_id}/mappings",
    response_model=list[JiraMappingResponse],
)
async def list_mappings(
    integration_id: UUID,
    db: DbSession,
    entity_type: Annotated[
        EntityType | None,
        Query(description="Filter by entity type"),
    ] = None,
) -> list[JiraMappingResponse]:
    """List all mappings for an integration."""
    mapping_repo = JiraMappingRepository(db)
    mappings = await mapping_repo.get_by_integration(
        integration_id,
        entity_type=entity_type.value if entity_type else None,
    )

    return [JiraMappingResponse.model_validate(m) for m in mappings]


@router.post(
    "/integrations/{integration_id}/mappings",
    response_model=JiraMappingResponse,
    status_code=201,
)
async def create_mapping(
    integration_id: UUID,
    mapping_in: JiraMappingCreate,
    db: DbSession,
) -> JiraMappingResponse:
    """Create a manual mapping between an entity and a Jira Issue."""
    integration_repo = JiraIntegrationRepository(db)
    integration = await integration_repo.get_by_id(integration_id)

    if not integration:
        raise NotFoundError(
            f"Jira integration {integration_id} not found",
            "JIRA_INTEGRATION_NOT_FOUND",
        )

    # Validate entity exists
    if mapping_in.entity_type == EntityType.WBS and mapping_in.wbs_id:
        wbs_repo = WBSElementRepository(db)
        wbs = await wbs_repo.get_by_id(mapping_in.wbs_id)
        if not wbs:
            raise NotFoundError(
                f"WBS element {mapping_in.wbs_id} not found",
                "WBS_NOT_FOUND",
            )
    elif mapping_in.entity_type == EntityType.ACTIVITY and mapping_in.activity_id:
        activity_repo = ActivityRepository(db)
        activity = await activity_repo.get_by_id(mapping_in.activity_id)
        if not activity:
            raise NotFoundError(
                f"Activity {mapping_in.activity_id} not found",
                "ACTIVITY_NOT_FOUND",
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Entity ID (wbs_id or activity_id) required based on entity_type",
        )

    mapping_repo = JiraMappingRepository(db)
    mapping_data = {
        "integration_id": integration_id,
        "entity_type": mapping_in.entity_type.value,
        "wbs_id": mapping_in.wbs_id,
        "activity_id": mapping_in.activity_id,
        "jira_issue_key": mapping_in.jira_issue_key,
        "sync_direction": mapping_in.sync_direction.value,
    }

    mapping = await mapping_repo.create(mapping_data)
    await db.commit()

    return JiraMappingResponse.model_validate(mapping)


@router.delete(
    "/mappings/{mapping_id}",
    status_code=204,
)
async def delete_mapping(
    mapping_id: UUID,
    db: DbSession,
) -> None:
    """Delete a mapping."""
    mapping_repo = JiraMappingRepository(db)
    mapping = await mapping_repo.get_by_id(mapping_id)

    if not mapping:
        raise NotFoundError(
            f"Mapping {mapping_id} not found",
            "MAPPING_NOT_FOUND",
        )

    await mapping_repo.delete(mapping.id)
    await db.commit()


# Sync log endpoints


@router.get(
    "/integrations/{integration_id}/logs",
    response_model=JiraSyncLogListResponse,
)
async def list_sync_logs(
    integration_id: UUID,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
) -> JiraSyncLogListResponse:
    """List sync logs for an integration."""
    sync_log_repo = JiraSyncLogRepository(db)
    # Get logs with high limit to enable pagination
    all_logs = await sync_log_repo.get_by_integration(
        integration_id,
        limit=1000,
    )

    # Manual pagination
    total = len(all_logs)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_logs = all_logs[start_idx:end_idx]

    return JiraSyncLogListResponse(
        items=[JiraSyncLogResponse.model_validate(log) for log in paginated_logs],
        total=total,
        page=page,
        per_page=per_page,
    )
