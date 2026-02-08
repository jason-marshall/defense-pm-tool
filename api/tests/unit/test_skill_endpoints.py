"""Tests for skill API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def skill_program(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> dict:
    """Create a program for skill testing."""
    resp = await client.post(
        "/api/v1/programs",
        json={
            "name": "Skill Test Program",
            "code": "SKL-001",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "budget_at_completion": "500000.00",
        },
        headers=auth_headers,
    )
    return resp.json()


@pytest_asyncio.fixture
async def skill(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> dict:
    """Create a test skill."""
    resp = await client.post(
        "/api/v1/skills",
        json={
            "name": "Python Programming",
            "code": "PYTHON",
            "category": "Technical",
        },
        headers=auth_headers,
    )
    return resp.json()


class TestSkillCRUD:
    """Tests for skill CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Should create a global skill."""
        resp = await client.post(
            "/api/v1/skills",
            json={
                "name": "Java Programming",
                "code": "JAVA",
                "category": "Technical",
                "description": "Java development skill",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Java Programming"
        assert data["code"] == "JAVA"
        assert data["category"] == "Technical"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_create_skill_program_specific(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        skill_program: dict,
    ) -> None:
        """Should create program-specific skill."""
        resp = await client.post(
            "/api/v1/skills",
            json={
                "name": "Systems Engineering",
                "code": "SYS-ENG",
                "category": "Technical",
                "program_id": skill_program["id"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["program_id"] == skill_program["id"]

    @pytest.mark.asyncio
    async def test_create_skill_with_certification(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Should create skill requiring certification."""
        resp = await client.post(
            "/api/v1/skills",
            json={
                "name": "PMP Certification",
                "code": "PMP",
                "category": "Certification",
                "requires_certification": True,
                "certification_expiry_months": 36,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["requires_certification"] is True
        assert data["certification_expiry_months"] == 36

    @pytest.mark.asyncio
    async def test_create_skill_duplicate_code(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        skill: dict,
    ) -> None:
        """Should reject duplicate skill code."""
        resp = await client.post(
            "/api/v1/skills",
            json={
                "name": "Another Python",
                "code": "PYTHON",
                "category": "Technical",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_skill_invalid_category(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Should reject invalid category."""
        resp = await client.post(
            "/api/v1/skills",
            json={
                "name": "Test",
                "code": "TST",
                "category": "InvalidCategory",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_skills(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        skill: dict,
    ) -> None:
        """Should list skills."""
        resp = await client.get(
            "/api/v1/skills",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_get_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        skill: dict,
    ) -> None:
        """Should get skill by ID."""
        resp = await client.get(
            f"/api/v1/skills/{skill['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == skill["id"]
        assert data["name"] == "Python Programming"

    @pytest.mark.asyncio
    async def test_get_skill_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Should return 404 for unknown skill."""
        resp = await client.get(
            f"/api/v1/skills/{uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        skill: dict,
    ) -> None:
        """Should update skill."""
        resp = await client.patch(
            f"/api/v1/skills/{skill['id']}",
            json={"name": "Python 3 Programming"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Python 3 Programming"

    @pytest.mark.asyncio
    async def test_delete_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        skill: dict,
    ) -> None:
        """Should soft-delete skill."""
        resp = await client.delete(
            f"/api/v1/skills/{skill['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

        # Should not be found after delete
        resp = await client.get(
            f"/api/v1/skills/{skill['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_skill_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        """Should reject unauthenticated request."""
        resp = await client.post(
            "/api/v1/skills",
            json={
                "name": "Test",
                "code": "TST",
                "category": "Technical",
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_qualified_resources_empty(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        skill: dict,
    ) -> None:
        """Should return empty list when no resources match."""
        resp = await client.get(
            f"/api/v1/skills/{skill['id']}/qualified-resources",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestResourceSkillEndpoints:
    """Tests for resource skill assignment endpoints."""

    @pytest_asyncio.fixture
    async def resource(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        skill_program: dict,
    ) -> dict:
        """Create a test resource."""
        resp = await client.post(
            "/api/v1/resources",
            json={
                "program_id": skill_program["id"],
                "name": "John Doe",
                "code": "JD-001",
                "resource_type": "labor",
            },
            headers=auth_headers,
        )
        return resp.json()

    @pytest.mark.asyncio
    async def test_add_resource_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        resource: dict,
        skill: dict,
    ) -> None:
        """Should assign skill to resource."""
        resp = await client.post(
            f"/api/v1/resources/{resource['id']}/skills",
            json={
                "skill_id": skill["id"],
                "proficiency_level": 3,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["proficiency_level"] == 3
        assert data["skill_id"] == skill["id"]

    @pytest.mark.asyncio
    async def test_list_resource_skills(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        resource: dict,
        skill: dict,
    ) -> None:
        """Should list skills for a resource."""
        # Assign skill first
        await client.post(
            f"/api/v1/resources/{resource['id']}/skills",
            json={"skill_id": skill["id"], "proficiency_level": 4},
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/v1/resources/{resource['id']}/skills",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_update_resource_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        resource: dict,
        skill: dict,
    ) -> None:
        """Should update resource skill proficiency."""
        await client.post(
            f"/api/v1/resources/{resource['id']}/skills",
            json={"skill_id": skill["id"], "proficiency_level": 2},
            headers=auth_headers,
        )

        resp = await client.put(
            f"/api/v1/resources/{resource['id']}/skills/{skill['id']}",
            json={"proficiency_level": 5},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["proficiency_level"] == 5

    @pytest.mark.asyncio
    async def test_remove_resource_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        resource: dict,
        skill: dict,
    ) -> None:
        """Should remove skill from resource."""
        await client.post(
            f"/api/v1/resources/{resource['id']}/skills",
            json={"skill_id": skill["id"], "proficiency_level": 3},
            headers=auth_headers,
        )

        resp = await client.delete(
            f"/api/v1/resources/{resource['id']}/skills/{skill['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_add_duplicate_resource_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        resource: dict,
        skill: dict,
    ) -> None:
        """Should reject duplicate skill assignment."""
        await client.post(
            f"/api/v1/resources/{resource['id']}/skills",
            json={"skill_id": skill["id"], "proficiency_level": 3},
            headers=auth_headers,
        )
        resp = await client.post(
            f"/api/v1/resources/{resource['id']}/skills",
            json={"skill_id": skill["id"], "proficiency_level": 4},
            headers=auth_headers,
        )
        assert resp.status_code == 409


class TestSkillRequirementEndpoints:
    """Tests for activity skill requirement endpoints."""

    @pytest_asyncio.fixture
    async def test_wbs(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        skill_program: dict,
    ) -> dict:
        """Create a test WBS element."""
        resp = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": skill_program["id"],
                "name": "Test WBS",
                "wbs_code": "1",
                "level": 1,
            },
            headers=auth_headers,
        )
        return resp.json()

    @pytest_asyncio.fixture
    async def test_activity(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        skill_program: dict,
        test_wbs: dict,
    ) -> dict:
        """Create a test activity."""
        resp = await client.post(
            "/api/v1/activities",
            json={
                "program_id": skill_program["id"],
                "wbs_id": test_wbs["id"],
                "name": "Design Review",
                "code": "DR-001",
                "duration": 5,
                "budgeted_cost": "5000.00",
            },
            headers=auth_headers,
        )
        return resp.json()

    @pytest.mark.asyncio
    async def test_add_skill_requirement(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_activity: dict,
        skill: dict,
    ) -> None:
        """Should add skill requirement to activity."""
        resp = await client.post(
            f"/api/v1/activities/{test_activity['id']}/skill-requirements",
            json={
                "skill_id": skill["id"],
                "required_level": 3,
                "is_mandatory": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["required_level"] == 3
        assert data["is_mandatory"] is True

    @pytest.mark.asyncio
    async def test_list_skill_requirements(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_activity: dict,
        skill: dict,
    ) -> None:
        """Should list skill requirements for activity."""
        await client.post(
            f"/api/v1/activities/{test_activity['id']}/skill-requirements",
            json={"skill_id": skill["id"], "required_level": 2},
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/v1/activities/{test_activity['id']}/skill-requirements",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_remove_skill_requirement(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_activity: dict,
        skill: dict,
    ) -> None:
        """Should remove skill requirement."""
        await client.post(
            f"/api/v1/activities/{test_activity['id']}/skill-requirements",
            json={"skill_id": skill["id"], "required_level": 3},
            headers=auth_headers,
        )

        resp = await client.delete(
            f"/api/v1/activities/{test_activity['id']}/skill-requirements/{skill['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_add_duplicate_skill_requirement(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_activity: dict,
        skill: dict,
    ) -> None:
        """Should reject duplicate skill requirement."""
        await client.post(
            f"/api/v1/activities/{test_activity['id']}/skill-requirements",
            json={"skill_id": skill["id"], "required_level": 3},
            headers=auth_headers,
        )
        resp = await client.post(
            f"/api/v1/activities/{test_activity['id']}/skill-requirements",
            json={"skill_id": skill["id"], "required_level": 4},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_add_requirement_unknown_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_activity: dict,
    ) -> None:
        """Should reject unknown skill ID."""
        resp = await client.post(
            f"/api/v1/activities/{test_activity['id']}/skill-requirements",
            json={"skill_id": str(uuid4()), "required_level": 3},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_add_requirement_unknown_activity(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        skill: dict,
    ) -> None:
        """Should reject unknown activity ID."""
        resp = await client.post(
            f"/api/v1/activities/{uuid4()}/skill-requirements",
            json={"skill_id": skill["id"], "required_level": 3},
            headers=auth_headers,
        )
        assert resp.status_code == 404
