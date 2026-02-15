"""Integration tests for resource recommendation API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def rec_program(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> dict:
    """Create a program for recommendation testing."""
    resp = await client.post(
        "/api/v1/programs",
        json={
            "name": "Recommendation Test Program",
            "code": "REC-001",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "budget_at_completion": "1000000.00",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def rec_skill(
    client: AsyncClient,
    auth_headers: dict[str, str],
    rec_program: dict,
) -> dict:
    """Create a skill for recommendation testing."""
    resp = await client.post(
        "/api/v1/skills",
        json={
            "name": "Python Programming",
            "code": "PYTHON",
            "category": "Technical",
            "program_id": rec_program["id"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def rec_skill_2(
    client: AsyncClient,
    auth_headers: dict[str, str],
    rec_program: dict,
) -> dict:
    """Create a second skill."""
    resp = await client.post(
        "/api/v1/skills",
        json={
            "name": "Project Management",
            "code": "PM",
            "category": "Management",
            "program_id": rec_program["id"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def rec_activity(
    client: AsyncClient,
    auth_headers: dict[str, str],
    rec_program: dict,
) -> dict:
    """Create an activity for recommendation testing."""
    resp = await client.post(
        "/api/v1/activities",
        json={
            "program_id": rec_program["id"],
            "name": "Design Phase",
            "code": "ACT-001",
            "duration": 10,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def rec_activity_2(
    client: AsyncClient,
    auth_headers: dict[str, str],
    rec_program: dict,
) -> dict:
    """Create a second activity."""
    resp = await client.post(
        "/api/v1/activities",
        json={
            "program_id": rec_program["id"],
            "name": "Coding Phase",
            "code": "ACT-002",
            "duration": 20,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def rec_resource(
    client: AsyncClient,
    auth_headers: dict[str, str],
    rec_program: dict,
) -> dict:
    """Create a resource for recommendation testing."""
    resp = await client.post(
        "/api/v1/resources",
        json={
            "program_id": rec_program["id"],
            "name": "Alice Developer",
            "code": "DEV-001",
            "resource_type": "LABOR",
            "cost_rate": "100.00",
            "capacity_per_day": "8.00",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def rec_resource_2(
    client: AsyncClient,
    auth_headers: dict[str, str],
    rec_program: dict,
) -> dict:
    """Create a second resource."""
    resp = await client.post(
        "/api/v1/resources",
        json={
            "program_id": rec_program["id"],
            "name": "Bob Manager",
            "code": "MGR-001",
            "resource_type": "LABOR",
            "cost_rate": "150.00",
            "capacity_per_day": "8.00",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


class TestActivityRecommendations:
    """Tests for GET /recommendations/activities/{activity_id}."""

    @pytest.mark.asyncio
    async def test_recommendations_no_requirements(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        rec_activity: dict,
        rec_resource: dict,
    ) -> None:
        """Should return recommendations even with no skill requirements."""
        resp = await client.get(
            f"/api/v1/recommendations/activities/{rec_activity['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["activity_id"] == rec_activity["id"]
        assert data["requirements_count"] == 0
        assert len(data["recommendations"]) >= 1

    @pytest.mark.asyncio
    async def test_recommendations_with_skill_match(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        rec_activity: dict,
        rec_skill: dict,
        rec_resource: dict,
    ) -> None:
        """Should rank resources by skill match."""
        # Add skill requirement to activity
        await client.post(
            f"/api/v1/activities/{rec_activity['id']}/skill-requirements",
            json={"skill_id": rec_skill["id"], "required_level": 3, "is_mandatory": True},
            headers=auth_headers,
        )

        # Add skill to resource
        await client.post(
            f"/api/v1/resources/{rec_resource['id']}/skills",
            json={"skill_id": rec_skill["id"], "proficiency_level": 4},
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/v1/recommendations/activities/{rec_activity['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["requirements_count"] == 1
        assert len(data["recommendations"]) >= 1

        # First recommendation should have high skill score
        rec = data["recommendations"][0]
        assert rec["score_breakdown"]["skill_score"] > 0
        assert rec["score_breakdown"]["mandatory_skills_met"] is True

    @pytest.mark.asyncio
    async def test_recommendations_top_n_limit(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        rec_activity: dict,
        rec_resource: dict,
        rec_resource_2: dict,
    ) -> None:
        """Should respect top_n limit."""
        resp = await client.get(
            f"/api/v1/recommendations/activities/{rec_activity['id']}?top_n=1",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["recommendations"]) <= 1

    @pytest.mark.asyncio
    async def test_recommendations_min_score_filter(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        rec_activity: dict,
        rec_resource: dict,
    ) -> None:
        """Should filter by min_score."""
        resp = await client.get(
            f"/api/v1/recommendations/activities/{rec_activity['id']}?min_score=0.99",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        for rec in data["recommendations"]:
            assert rec["overall_score"] >= 0.99

    @pytest.mark.asyncio
    async def test_recommendations_activity_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent activity."""
        resp = await client.get(
            f"/api/v1/recommendations/activities/{uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_recommendations_unauthenticated(
        self,
        client: AsyncClient,
        rec_activity: dict,
    ) -> None:
        """Should return 401 without auth headers."""
        resp = await client.get(
            f"/api/v1/recommendations/activities/{rec_activity['id']}",
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_recommendations_resource_type_filter(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        rec_program: dict,
        rec_activity: dict,
        rec_resource: dict,
    ) -> None:
        """Should filter recommendations by resource type."""
        # Create an EQUIPMENT resource
        resp = await client.post(
            "/api/v1/resources",
            json={
                "program_id": rec_program["id"],
                "name": "Crane Equipment",
                "code": "EQP-001",
                "resource_type": "EQUIPMENT",
                "cost_rate": "200.00",
                "capacity_per_day": "8.00",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201

        # Request only LABOR resources
        resp = await client.get(
            f"/api/v1/recommendations/activities/{rec_activity['id']}?resource_type=LABOR",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        for rec in data["recommendations"]:
            assert rec["resource_type"] == "LABOR"

    @pytest.mark.asyncio
    async def test_recommendations_with_date_range(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        rec_activity: dict,
        rec_resource: dict,
    ) -> None:
        """Should accept date_range_start and date_range_end query params."""
        resp = await client.get(
            f"/api/v1/recommendations/activities/{rec_activity['id']}"
            "?date_range_start=2024-03-01&date_range_end=2024-06-30",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["activity_id"] == rec_activity["id"]

    @pytest.mark.asyncio
    async def test_recommendations_with_partial_date_range(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        rec_activity: dict,
        rec_resource: dict,
    ) -> None:
        """Should accept only date_range_start without date_range_end."""
        resp = await client.get(
            f"/api/v1/recommendations/activities/{rec_activity['id']}?date_range_start=2024-03-01",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["activity_id"] == rec_activity["id"]


class TestResourceRecommendations:
    """Tests for GET /recommendations/resources/{resource_id}."""

    @pytest.mark.asyncio
    async def test_resource_recommendations_basic(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        rec_resource: dict,
        rec_activity: dict,
        rec_skill: dict,
    ) -> None:
        """Should return activity recommendations for a resource."""
        # Add skill to resource
        await client.post(
            f"/api/v1/resources/{rec_resource['id']}/skills",
            json={"skill_id": rec_skill["id"], "proficiency_level": 4},
            headers=auth_headers,
        )

        # Add skill requirement to activity
        await client.post(
            f"/api/v1/activities/{rec_activity['id']}/skill-requirements",
            json={"skill_id": rec_skill["id"], "required_level": 3},
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/v1/recommendations/resources/{rec_resource['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["resource_id"] == rec_resource["id"]
        assert len(data["recommendations"]) >= 1

    @pytest.mark.asyncio
    async def test_resource_recommendations_no_matching_activities(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        rec_resource: dict,
        rec_activity: dict,
    ) -> None:
        """Should return empty when no activities have skill requirements."""
        resp = await client.get(
            f"/api/v1/recommendations/resources/{rec_resource['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_activities_evaluated"] == 0

    @pytest.mark.asyncio
    async def test_resource_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for nonexistent resource."""
        resp = await client.get(
            f"/api/v1/recommendations/resources/{uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestBulkRecommendations:
    """Tests for POST /recommendations/bulk."""

    @pytest.mark.asyncio
    async def test_bulk_recommendations(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        rec_activity: dict,
        rec_activity_2: dict,
        rec_resource: dict,
    ) -> None:
        """Should return recommendations for multiple activities."""
        resp = await client.post(
            "/api/v1/recommendations/bulk",
            json={
                "activity_ids": [rec_activity["id"], rec_activity_2["id"]],
                "top_n": 5,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_activities"] == 2
        assert len(data["results"]) == 2

    @pytest.mark.asyncio
    async def test_bulk_skips_invalid_activities(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        rec_activity: dict,
        rec_resource: dict,
    ) -> None:
        """Should skip activities that don't exist."""
        resp = await client.post(
            "/api/v1/recommendations/bulk",
            json={
                "activity_ids": [rec_activity["id"], str(uuid4())],
                "top_n": 5,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_activities"] == 1

    @pytest.mark.asyncio
    async def test_bulk_with_custom_weights(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        rec_activity: dict,
        rec_resource: dict,
    ) -> None:
        """Should apply custom weights in bulk request."""
        resp = await client.post(
            "/api/v1/recommendations/bulk",
            json={
                "activity_ids": [rec_activity["id"]],
                "top_n": 5,
                "weights": {
                    "skill_match": 0.3,
                    "availability": 0.3,
                    "cost": 0.3,
                    "certification": 0.1,
                },
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_activities"] == 1

    @pytest.mark.asyncio
    async def test_bulk_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        """Should return 401 without auth headers."""
        resp = await client.post(
            "/api/v1/recommendations/bulk",
            json={"activity_ids": [str(uuid4())]},
        )
        assert resp.status_code == 401
