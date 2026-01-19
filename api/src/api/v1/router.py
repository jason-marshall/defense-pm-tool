"""Main API router that aggregates all v1 endpoints."""

from fastapi import APIRouter

from src.api.v1.endpoints import (
    activities,
    auth,
    baselines,
    dependencies,
    evms,
    import_export,
    jira_integration,
    management_reserve,
    programs,
    reports,
    scenarios,
    schedule,
    simulations,
    variance_explanations,
    wbs,
)

api_router = APIRouter()

# Authentication endpoints (no prefix needed, auth is the prefix)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

api_router.include_router(
    programs.router,
    prefix="/programs",
    tags=["Programs"],
)

api_router.include_router(
    activities.router,
    prefix="/activities",
    tags=["Activities"],
)

api_router.include_router(
    dependencies.router,
    prefix="/dependencies",
    tags=["Dependencies"],
)

api_router.include_router(
    wbs.router,
    prefix="/wbs",
    tags=["WBS"],
)

api_router.include_router(
    schedule.router,
    prefix="/schedule",
    tags=["Schedule"],
)

api_router.include_router(
    evms.router,
    prefix="/evms",
    tags=["EVMS"],
)

api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports"],
)

api_router.include_router(
    import_export.router,
    prefix="/import",
    tags=["Import/Export"],
)

api_router.include_router(
    baselines.router,
    prefix="/baselines",
    tags=["Baselines"],
)

api_router.include_router(
    scenarios.router,
    prefix="/scenarios",
    tags=["Scenarios"],
)

api_router.include_router(
    simulations.router,
    prefix="/simulations",
    tags=["Simulations"],
)

api_router.include_router(
    variance_explanations.router,
    prefix="/variance-explanations",
    tags=["Variance Explanations"],
)

api_router.include_router(
    management_reserve.router,
    prefix="/mr",
    tags=["Management Reserve"],
)

api_router.include_router(
    jira_integration.router,
    prefix="/jira",
    tags=["Jira Integration"],
)
