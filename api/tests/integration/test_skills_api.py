"""Integration tests for Skills API endpoints (Skill CRUD, Resource Skills, Skill Requirements)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestSkillsAuth:
    """Tests for authentication requirements on skill endpoints."""

    async def test_create_skill_requires_auth(self, client: AsyncClient):
        """Should return 401 when not authenticated."""
        response = await client.post("/api/v1/skills", json={})
        assert response.status_code == 401

    async def test_list_skills_requires_auth(self, client: AsyncClient):
        """Should return 401 when listing skills without auth."""
        response = await client.get("/api/v1/skills")
        assert response.status_code == 401

    async def test_get_skill_requires_auth(self, client: AsyncClient):
        """Should return 401 when getting skill without auth."""
        response = await client.get("/api/v1/skills/fake-id")
        assert response.status_code == 401


class TestSkillCRUD:
    """Tests for authenticated skill CRUD operations."""

    async def test_list_skills_empty(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should return empty list when no skills exist."""
        response = await client.get(
            "/api/v1/skills",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] == 0

    async def test_create_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should create a new skill."""
        response = await client.post(
            "/api/v1/skills",
            json={
                "name": "Systems Engineering",
                "code": "SE",
                "category": "Technical",
                "description": "Systems engineering expertise",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Systems Engineering"
        assert data["code"] == "SE"
        assert data["category"] == "Technical"

    async def test_create_skill_with_certification(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should create a skill that requires certification."""
        response = await client.post(
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
        assert response.status_code == 201
        data = response.json()
        assert data["requires_certification"] is True
        assert data["certification_expiry_months"] == 36

    async def test_create_program_specific_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should create a program-specific skill."""
        response = await client.post(
            "/api/v1/skills",
            json={
                "name": "F-35 Assembly",
                "code": "F35-ASM",
                "category": "Technical",
                "program_id": test_program["id"],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["program_id"] == test_program["id"]

    async def test_get_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should retrieve a specific skill by ID."""
        create_response = await client.post(
            "/api/v1/skills",
            json={"name": "Get Test Skill", "code": "GTS", "category": "Technical"},
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        skill_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/skills/{skill_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test Skill"

    async def test_update_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should update a skill."""
        create_response = await client.post(
            "/api/v1/skills",
            json={"name": "Original Skill", "code": "ORIG", "category": "Technical"},
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        skill_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/skills/{skill_id}",
            json={"name": "Updated Skill"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Skill"

    async def test_delete_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should soft-delete a skill."""
        create_response = await client.post(
            "/api/v1/skills",
            json={"name": "Delete Skill", "code": "DELS", "category": "Technical"},
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        skill_id = create_response.json()["id"]

        response = await client.delete(
            f"/api/v1/skills/{skill_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    async def test_duplicate_skill_code(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should reject duplicate skill codes."""
        await client.post(
            "/api/v1/skills",
            json={"name": "Skill A", "code": "DUPA", "category": "Technical"},
            headers=auth_headers,
        )

        response = await client.post(
            "/api/v1/skills",
            json={"name": "Skill B", "code": "DUPA", "category": "Technical"},
            headers=auth_headers,
        )
        assert response.status_code == 409

    async def test_get_nonexistent_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should return 404 for nonexistent skill."""
        response = await client.get(
            "/api/v1/skills/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestResourceSkills:
    """Tests for resource skill assignment endpoints."""

    async def test_add_skill_to_resource(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should add a skill to a resource."""
        # Create resource
        res_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": test_program["id"],
                "name": "Skilled Worker",
                "code": "SW-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
            },
            headers=auth_headers,
        )
        assert res_response.status_code == 201
        resource_id = res_response.json()["id"]

        # Create skill
        skill_response = await client.post(
            "/api/v1/skills",
            json={"name": "Welding", "code": "WELD", "category": "Technical"},
            headers=auth_headers,
        )
        assert skill_response.status_code == 201
        skill_id = skill_response.json()["id"]

        # Add skill to resource
        response = await client.post(
            f"/api/v1/resources/{resource_id}/skills",
            json={
                "skill_id": skill_id,
                "proficiency_level": 3,
                "is_certified": True,
                "certification_date": "2024-06-15",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["proficiency_level"] == 3
        assert data["is_certified"] is True

    async def test_list_resource_skills(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should list skills for a resource."""
        res_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": test_program["id"],
                "name": "List Skills Worker",
                "code": "LSW-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
            },
            headers=auth_headers,
        )
        assert res_response.status_code == 201
        resource_id = res_response.json()["id"]

        response = await client.get(
            f"/api/v1/resources/{resource_id}/skills",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_update_resource_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should update a resource's skill proficiency."""
        # Create resource
        res_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": test_program["id"],
                "name": "Update Skill Worker",
                "code": "USW-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
            },
            headers=auth_headers,
        )
        assert res_response.status_code == 201
        resource_id = res_response.json()["id"]

        # Create and assign skill
        skill_response = await client.post(
            "/api/v1/skills",
            json={"name": "Painting", "code": "PAINT", "category": "Technical"},
            headers=auth_headers,
        )
        assert skill_response.status_code == 201
        skill_id = skill_response.json()["id"]

        await client.post(
            f"/api/v1/resources/{resource_id}/skills",
            json={"skill_id": skill_id, "proficiency_level": 1},
            headers=auth_headers,
        )

        # Update proficiency
        response = await client.put(
            f"/api/v1/resources/{resource_id}/skills/{skill_id}",
            json={"proficiency_level": 4},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["proficiency_level"] == 4

    async def test_remove_resource_skill(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should remove a skill from a resource."""
        # Create resource
        res_response = await client.post(
            "/api/v1/resources",
            json={
                "program_id": test_program["id"],
                "name": "Remove Skill Worker",
                "code": "RSW-001",
                "resource_type": "labor",
                "capacity_per_day": "8.0",
            },
            headers=auth_headers,
        )
        assert res_response.status_code == 201
        resource_id = res_response.json()["id"]

        # Create and assign skill
        skill_response = await client.post(
            "/api/v1/skills",
            json={"name": "Soldering", "code": "SOLD", "category": "Technical"},
            headers=auth_headers,
        )
        assert skill_response.status_code == 201
        skill_id = skill_response.json()["id"]

        await client.post(
            f"/api/v1/resources/{resource_id}/skills",
            json={"skill_id": skill_id},
            headers=auth_headers,
        )

        # Remove skill
        response = await client.delete(
            f"/api/v1/resources/{resource_id}/skills/{skill_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204


class TestSkillRequirements:
    """Tests for activity skill requirement endpoints."""

    async def test_add_skill_requirement(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should add a skill requirement to an activity."""
        program_id = test_program["id"]

        # Create WBS element
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "wbs_code": "1.0",
                "name": "Project Root",
            },
            headers=auth_headers,
        )
        assert wbs_response.status_code == 201
        wbs_id = wbs_response.json()["id"]

        # Create activity
        act_response = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "Skill Req Activity",
                "code": "SKREQ-001",
                "duration": 5,
                "budgeted_cost": "5000.00",
            },
            headers=auth_headers,
        )
        assert act_response.status_code == 201
        activity_id = act_response.json()["id"]

        # Create skill
        skill_response = await client.post(
            "/api/v1/skills",
            json={"name": "Testing", "code": "TEST-SKL", "category": "Technical"},
            headers=auth_headers,
        )
        assert skill_response.status_code == 201
        skill_id = skill_response.json()["id"]

        # Add requirement
        response = await client.post(
            f"/api/v1/activities/{activity_id}/skill-requirements",
            json={
                "skill_id": skill_id,
                "required_level": 3,
                "is_mandatory": True,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["required_level"] == 3
        assert data["is_mandatory"] is True

    async def test_list_skill_requirements(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should list skill requirements for an activity."""
        program_id = test_program["id"]

        # Create WBS element
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "wbs_code": "1.0",
                "name": "Project Root",
            },
            headers=auth_headers,
        )
        assert wbs_response.status_code == 201
        wbs_id = wbs_response.json()["id"]

        # Create activity
        act_response = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "List Req Activity",
                "code": "LSTREQ-001",
                "duration": 5,
                "budgeted_cost": "5000.00",
            },
            headers=auth_headers,
        )
        assert act_response.status_code == 201
        activity_id = act_response.json()["id"]

        response = await client.get(
            f"/api/v1/activities/{activity_id}/skill-requirements",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_remove_skill_requirement(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_program: dict,
    ):
        """Should remove a skill requirement from an activity."""
        program_id = test_program["id"]

        # Create WBS element
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "wbs_code": "1.0",
                "name": "Project Root",
            },
            headers=auth_headers,
        )
        assert wbs_response.status_code == 201
        wbs_id = wbs_response.json()["id"]

        # Create activity
        act_response = await client.post(
            "/api/v1/activities",
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "Remove Req Activity",
                "code": "RMREQ-001",
                "duration": 5,
                "budgeted_cost": "5000.00",
            },
            headers=auth_headers,
        )
        assert act_response.status_code == 201
        activity_id = act_response.json()["id"]

        # Create skill
        skill_response = await client.post(
            "/api/v1/skills",
            json={"name": "Removal Test", "code": "REMTST", "category": "Technical"},
            headers=auth_headers,
        )
        assert skill_response.status_code == 201
        skill_id = skill_response.json()["id"]

        # Add requirement
        await client.post(
            f"/api/v1/activities/{activity_id}/skill-requirements",
            json={"skill_id": skill_id, "required_level": 2},
            headers=auth_headers,
        )

        # Remove requirement
        response = await client.delete(
            f"/api/v1/activities/{activity_id}/skill-requirements/{skill_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204


class TestQualifiedResources:
    """Tests for qualified resources lookup endpoint."""

    async def test_get_qualified_resources(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should return resources qualified for a skill."""
        # Create skill
        skill_response = await client.post(
            "/api/v1/skills",
            json={"name": "Qualified Test", "code": "QUALTST", "category": "Technical"},
            headers=auth_headers,
        )
        assert skill_response.status_code == 201
        skill_id = skill_response.json()["id"]

        response = await client.get(
            f"/api/v1/skills/{skill_id}/qualified-resources",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_qualified_resources_with_min_level(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Should filter qualified resources by minimum level."""
        skill_response = await client.post(
            "/api/v1/skills",
            json={"name": "Min Level Test", "code": "MINLEV", "category": "Technical"},
            headers=auth_headers,
        )
        assert skill_response.status_code == 201
        skill_id = skill_response.json()["id"]

        response = await client.get(
            f"/api/v1/skills/{skill_id}/qualified-resources?min_level=3",
            headers=auth_headers,
        )
        assert response.status_code == 200
