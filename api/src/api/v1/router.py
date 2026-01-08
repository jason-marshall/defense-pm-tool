"""Main API router that aggregates all v1 endpoints."""

from fastapi import APIRouter

from src.api.v1.endpoints import activities, dependencies, programs, schedule, wbs

api_router = APIRouter()

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
