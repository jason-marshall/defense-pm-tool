"""End-to-end integration test for Week 2 functionality."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestWeek2EndToEnd:
    """Complete workflow test for Week 2 features."""

    @pytest.fixture
    async def setup_user(self, client: AsyncClient) -> tuple[dict, str]:
        """Create user and return auth headers + user email."""
        email = f"e2e_test_{uuid4().hex[:8]}@example.com"

        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "E2ETestPass123!",
                "full_name": "E2E Test User",
            },
        )

        # Login
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "E2ETestPass123!"},
        )
        token = response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}, email

    async def test_complete_schedule_workflow(self, client: AsyncClient, setup_user: tuple):
        """
        Test complete workflow:
        1. Create program
        2. Create WBS element
        3. Create activities (A -> B -> D with parallel path through C)
        4. Create dependencies
        5. Calculate schedule
        6. Verify critical path
        """
        headers, _ = setup_user

        # Step 1: Create program
        program_response = await client.post(
            "/api/v1/programs",
            headers=headers,
            json={
                "name": "E2E Test Program",
                "code": f"E2E-{uuid4().hex[:6]}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]

        # Step 2: Create WBS element
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "name": "Work Package",
                "wbs_code": "1.1",
            },
        )
        assert wbs_response.status_code == 201
        wbs_id = wbs_response.json()["id"]

        # Step 3: Create activities
        # Critical path: Start -> A(5d) -> B(3d) -> D(2d) -> End
        # Parallel:      Start -> C(4d) -------> D(2d) -> End
        activities = {}
        activity_data = [
            {"name": "Start", "code": "START", "duration": 0, "is_milestone": True},
            {"name": "Activity A", "code": "A", "duration": 5},
            {"name": "Activity B", "code": "B", "duration": 3},
            {"name": "Activity C", "code": "C", "duration": 4},
            {"name": "Activity D", "code": "D", "duration": 2},
            {"name": "End", "code": "END", "duration": 0, "is_milestone": True},
        ]

        for data in activity_data:
            response = await client.post(
                "/api/v1/activities",
                headers=headers,
                json={"program_id": program_id, "wbs_id": wbs_id, **data},
            )
            assert response.status_code == 201, f"Failed to create {data['name']}"
            activities[data["code"]] = response.json()["id"]

        # Step 4: Create dependencies
        # START -> A, START -> C
        # A -> B
        # B -> D, C -> D
        # D -> END
        dependencies = [
            ("START", "A"),
            ("START", "C"),
            ("A", "B"),
            ("B", "D"),
            ("C", "D"),
            ("D", "END"),
        ]

        for pred_code, succ_code in dependencies:
            response = await client.post(
                "/api/v1/dependencies",
                headers=headers,
                json={
                    "predecessor_id": activities[pred_code],
                    "successor_id": activities[succ_code],
                    "dependency_type": "FS",
                    "lag": 0,
                },
            )
            assert response.status_code == 201, f"Failed: {pred_code} -> {succ_code}"

        # Step 5: Calculate schedule
        schedule_response = await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=headers,
        )
        assert schedule_response.status_code == 200
        results = {r["activity_id"]: r for r in schedule_response.json()}

        # Step 6: Verify calculations
        # Critical path: Start(0) -> A(0-5) -> B(5-8) -> D(8-10) -> End(10)
        # A should be critical (on longest path)
        assert results[activities["A"]]["is_critical"] is True
        assert results[activities["A"]]["early_start"] == 0
        assert results[activities["A"]]["early_finish"] == 5

        # B should be critical
        assert results[activities["B"]]["is_critical"] is True
        assert results[activities["B"]]["early_start"] == 5
        assert results[activities["B"]]["early_finish"] == 8

        # C should have float (not critical)
        # C starts at 0, takes 4 days, but D doesn't start until day 8
        # So C finishes at day 4, but D starts at day 8 -> float = 4
        assert results[activities["C"]]["is_critical"] is False
        assert results[activities["C"]]["total_float"] > 0

        # D should be critical
        assert results[activities["D"]]["is_critical"] is True
        assert results[activities["D"]]["early_start"] == 8
        assert results[activities["D"]]["early_finish"] == 10

        # Step 7: Get project duration
        duration_response = await client.get(
            f"/api/v1/schedule/duration/{program_id}",
            headers=headers,
        )
        assert duration_response.status_code == 200
        assert duration_response.json()["duration"] == 10  # 5 + 3 + 2 (milestones = 0)

    async def test_cycle_detection_prevents_invalid_dependency(
        self, client: AsyncClient, setup_user: tuple
    ):
        """Test that creating a circular dependency is prevented."""
        headers, _ = setup_user

        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            headers=headers,
            json={
                "name": "Cycle Test",
                "code": f"CYC-{uuid4().hex[:6]}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        program_id = program_response.json()["id"]

        # Create WBS
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "name": "WBS 1",
                "wbs_code": "1.1",
            },
        )
        wbs_id = wbs_response.json()["id"]

        # Create 3 activities
        activity_ids = []
        for name in ["A", "B", "C"]:
            response = await client.post(
                "/api/v1/activities",
                headers=headers,
                json={
                    "program_id": program_id,
                    "wbs_id": wbs_id,
                    "name": f"Activity {name}",
                    "code": name,
                    "duration": 5,
                },
            )
            activity_ids.append(response.json()["id"])

        # Create A -> B
        await client.post(
            "/api/v1/dependencies",
            headers=headers,
            json={
                "predecessor_id": activity_ids[0],
                "successor_id": activity_ids[1],
            },
        )

        # Create B -> C
        await client.post(
            "/api/v1/dependencies",
            headers=headers,
            json={
                "predecessor_id": activity_ids[1],
                "successor_id": activity_ids[2],
            },
        )

        # Try to create C -> A (would create cycle)
        response = await client.post(
            "/api/v1/dependencies",
            headers=headers,
            json={
                "predecessor_id": activity_ids[2],
                "successor_id": activity_ids[0],
            },
        )

        assert response.status_code == 400
        assert "CIRCULAR_DEPENDENCY" in response.json()["code"]

    async def test_activity_crud_with_auth(self, client: AsyncClient, setup_user: tuple):
        """Test complete activity CRUD flow."""
        headers, _ = setup_user

        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            headers=headers,
            json={
                "name": "Activity CRUD Test",
                "code": f"ACT-{uuid4().hex[:6]}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        program_id = program_response.json()["id"]

        # Create WBS
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "name": "WBS 1",
                "wbs_code": "1.1",
            },
        )
        wbs_id = wbs_response.json()["id"]

        # Create activity
        create_response = await client.post(
            "/api/v1/activities",
            headers=headers,
            json={
                "program_id": program_id,
                "wbs_id": wbs_id,
                "name": "Test Activity",
                "code": "TA-001",
                "duration": 5,
            },
        )
        assert create_response.status_code == 201
        activity_id = create_response.json()["id"]

        # Read activity
        get_response = await client.get(
            f"/api/v1/activities/{activity_id}",
            headers=headers,
        )
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Test Activity"

        # Update activity
        update_response = await client.patch(
            f"/api/v1/activities/{activity_id}",
            headers=headers,
            json={"name": "Updated Activity", "duration": 10},
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Activity"
        assert update_response.json()["duration"] == 10

        # Delete activity
        delete_response = await client.delete(
            f"/api/v1/activities/{activity_id}",
            headers=headers,
        )
        assert delete_response.status_code == 204

        # Verify deleted
        verify_response = await client.get(
            f"/api/v1/activities/{activity_id}",
            headers=headers,
        )
        assert verify_response.status_code == 404

    async def test_dependency_crud_with_auth(self, client: AsyncClient, setup_user: tuple):
        """Test complete dependency CRUD flow."""
        headers, _ = setup_user

        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            headers=headers,
            json={
                "name": "Dependency CRUD Test",
                "code": f"DEP-{uuid4().hex[:6]}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        program_id = program_response.json()["id"]

        # Create WBS
        wbs_response = await client.post(
            "/api/v1/wbs",
            json={
                "program_id": program_id,
                "name": "WBS 1",
                "wbs_code": "1.1",
            },
        )
        wbs_id = wbs_response.json()["id"]

        # Create activities
        activity_ids = []
        for name in ["A", "B"]:
            response = await client.post(
                "/api/v1/activities",
                headers=headers,
                json={
                    "program_id": program_id,
                    "wbs_id": wbs_id,
                    "name": f"Activity {name}",
                    "code": name,
                    "duration": 5,
                },
            )
            activity_ids.append(response.json()["id"])

        # Create dependency
        create_response = await client.post(
            "/api/v1/dependencies",
            headers=headers,
            json={
                "predecessor_id": activity_ids[0],
                "successor_id": activity_ids[1],
                "dependency_type": "FS",
                "lag": 0,
            },
        )
        assert create_response.status_code == 201
        dep_id = create_response.json()["id"]

        # Read dependency
        get_response = await client.get(
            f"/api/v1/dependencies/{dep_id}",
            headers=headers,
        )
        assert get_response.status_code == 200
        assert get_response.json()["dependency_type"] == "FS"

        # Update dependency
        update_response = await client.patch(
            f"/api/v1/dependencies/{dep_id}",
            headers=headers,
            json={"lag": 2},
        )
        assert update_response.status_code == 200
        assert update_response.json()["lag"] == 2

        # Delete dependency
        delete_response = await client.delete(
            f"/api/v1/dependencies/{dep_id}",
            headers=headers,
        )
        assert delete_response.status_code == 204

        # Verify deleted
        verify_response = await client.get(
            f"/api/v1/dependencies/{dep_id}",
            headers=headers,
        )
        assert verify_response.status_code == 404


class TestWeek2Authorization:
    """Tests for authorization across Week 2 features."""

    async def test_cannot_access_other_users_schedule(self, client: AsyncClient):
        """User should not be able to calculate schedule for another user's program."""
        # Create first user and their program
        user1_email = f"sched_owner_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": user1_email,
                "password": "TestPass123!",
                "full_name": "Schedule Owner",
            },
        )
        login1 = await client.post(
            "/api/v1/auth/login",
            json={"email": user1_email, "password": "TestPass123!"},
        )
        headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

        program_response = await client.post(
            "/api/v1/programs",
            headers=headers1,
            json={
                "name": "Owner's Program",
                "code": f"OWN-{uuid4().hex[:6]}",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        program_id = program_response.json()["id"]

        # Create second user
        user2_email = f"sched_other_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": user2_email,
                "password": "TestPass123!",
                "full_name": "Other User",
            },
        )
        login2 = await client.post(
            "/api/v1/auth/login",
            json={"email": user2_email, "password": "TestPass123!"},
        )
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        # Other user tries to calculate schedule for owner's program
        response = await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=headers2,
        )
        assert response.status_code == 403
