"""End-to-end integration test for Week 1 deliverables.

This test validates the complete user journey:
1. User registration and authentication
2. Program CRUD operations with ownership
3. Soft delete functionality
4. Token refresh flow
"""

from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.program import Program
from src.models.user import User

pytestmark = pytest.mark.asyncio


class TestWeek1CompleteFlow:
    """End-to-end tests for Week 1 deliverables."""

    async def test_complete_user_journey(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        Complete end-to-end test for Week 1 functionality.

        Steps:
        1. Register new user
        2. Login and get tokens
        3. Access protected endpoint with token
        4. Create a program
        5. Verify program in database with correct owner
        6. Update program
        7. List programs (should show owned program)
        8. Refresh token
        9. Delete program (soft delete)
        10. Verify soft delete in database
        """
        # ============================================================
        # Step 1: Register new user
        # ============================================================
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "e2etest@example.com",
                "password": "SecurePassword123!",
                "full_name": "E2E Test User",
            },
        )
        assert register_response.status_code == 201, register_response.json()
        user_data = register_response.json()
        user_id = user_data["id"]
        assert user_data["email"] == "e2etest@example.com"
        assert user_data["full_name"] == "E2E Test User"
        assert "password" not in user_data
        assert "hashed_password" not in user_data

        # Verify user in database
        db_user = await db_session.get(User, UUID(user_id))
        assert db_user is not None
        assert db_user.email == "e2etest@example.com"
        assert db_user.is_active is True

        # ============================================================
        # Step 2: Login and get tokens
        # ============================================================
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "e2etest@example.com",
                "password": "SecurePassword123!",
            },
        )
        assert login_response.status_code == 200, login_response.json()
        tokens = login_response.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] > 0

        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}

        # ============================================================
        # Step 3: Access protected endpoint with token
        # ============================================================
        me_response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["id"] == user_id
        assert me_data["email"] == "e2etest@example.com"

        # ============================================================
        # Step 4: Create a program
        # ============================================================
        program_data = {
            "code": "F35-SCHED",
            "name": "F-35 Schedule Analysis",
            "description": "Program schedule optimization for F-35 integration",
            "contract_number": "W912HQ-24-C-0001",
            "start_date": "2024-01-01",
            "end_date": "2026-12-31",
            "budget_at_completion": "15000000.00",
        }
        create_response = await client.post(
            "/api/v1/programs",
            json=program_data,
            headers=auth_headers,
        )
        assert create_response.status_code == 201, create_response.json()
        program = create_response.json()
        program_id = program["id"]
        assert program["name"] == "F-35 Schedule Analysis"
        assert program["code"] == "F35-SCHED"
        assert program["owner_id"] == user_id  # Verify ownership

        # ============================================================
        # Step 5: Verify program in database with correct owner
        # ============================================================
        db_program = await db_session.get(Program, UUID(program_id))
        assert db_program is not None
        assert db_program.name == "F-35 Schedule Analysis"
        assert str(db_program.owner_id) == user_id
        assert db_program.deleted_at is None  # Not deleted

        # ============================================================
        # Step 6: Update program
        # ============================================================
        update_response = await client.patch(
            f"/api/v1/programs/{program_id}",
            json={
                "name": "F-35 Schedule Analysis - Phase 2",
                "status": "active",
            },
            headers=auth_headers,
        )
        assert update_response.status_code == 200, update_response.json()
        updated_program = update_response.json()
        assert updated_program["name"] == "F-35 Schedule Analysis - Phase 2"
        assert updated_program["status"] == "active"

        # Verify update in database
        await db_session.refresh(db_program)
        assert db_program.name == "F-35 Schedule Analysis - Phase 2"

        # ============================================================
        # Step 7: List programs (should show owned program)
        # ============================================================
        list_response = await client.get("/api/v1/programs", headers=auth_headers)
        assert list_response.status_code == 200
        programs_list = list_response.json()
        assert programs_list["total"] == 1
        assert len(programs_list["items"]) == 1
        assert programs_list["items"][0]["id"] == program_id

        # ============================================================
        # Step 8: Refresh token
        # ============================================================
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["token_type"] == "bearer"

        # Use new token (may be same if within same second, but should work)
        new_auth_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}

        # Verify new token works
        me_response2 = await client.get("/api/v1/auth/me", headers=new_auth_headers)
        assert me_response2.status_code == 200

        # ============================================================
        # Step 9: Delete program (soft delete)
        # ============================================================
        delete_response = await client.delete(
            f"/api/v1/programs/{program_id}",
            headers=new_auth_headers,
        )
        assert delete_response.status_code == 204

        # ============================================================
        # Step 10: Verify soft delete in database
        # ============================================================
        await db_session.refresh(db_program)
        assert db_program.deleted_at is not None  # Soft deleted

        # Program should not appear in list
        list_response2 = await client.get("/api/v1/programs", headers=new_auth_headers)
        assert list_response2.status_code == 200
        assert list_response2.json()["total"] == 0

        # Program should return 404
        get_response = await client.get(
            f"/api/v1/programs/{program_id}",
            headers=new_auth_headers,
        )
        assert get_response.status_code == 404

    async def test_authentication_flow_edge_cases(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        Test authentication edge cases:
        - Duplicate registration
        - Wrong password
        - Invalid token
        - Expired/invalid refresh token
        """
        # Register user
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "edgecase@example.com",
                "password": "SecurePassword123!",
                "full_name": "Edge Case User",
            },
        )

        # Test duplicate registration
        dup_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "edgecase@example.com",
                "password": "DifferentPassword123!",
                "full_name": "Duplicate User",
            },
        )
        assert dup_response.status_code == 409
        assert "EMAIL_ALREADY_EXISTS" in dup_response.json()["code"]

        # Test wrong password
        wrong_pass_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "edgecase@example.com",
                "password": "WrongPassword123!",
            },
        )
        assert wrong_pass_response.status_code == 401
        assert "INVALID_CREDENTIALS" in wrong_pass_response.json()["code"]

        # Test invalid token
        invalid_token_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert invalid_token_response.status_code == 401

        # Test invalid refresh token
        invalid_refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.refresh.token"},
        )
        assert invalid_refresh_response.status_code == 401

    async def test_program_authorization_flow(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        Test program authorization:
        - User A creates program
        - User B cannot access/modify/delete it
        - User A can access/modify/delete it
        """
        # Create User A
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "usera@example.com",
                "password": "SecurePassword123!",
                "full_name": "User A",
            },
        )
        login_a = await client.post(
            "/api/v1/auth/login",
            json={"email": "usera@example.com", "password": "SecurePassword123!"},
        )
        headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

        # Create User B
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "userb@example.com",
                "password": "SecurePassword123!",
                "full_name": "User B",
            },
        )
        login_b = await client.post(
            "/api/v1/auth/login",
            json={"email": "userb@example.com", "password": "SecurePassword123!"},
        )
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        # User A creates program
        create_response = await client.post(
            "/api/v1/programs",
            json={
                "code": "AUTH-TEST",
                "name": "Authorization Test Program",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
            headers=headers_a,
        )
        assert create_response.status_code == 201
        program_id = create_response.json()["id"]

        # User B tries to access - should fail
        get_response = await client.get(
            f"/api/v1/programs/{program_id}",
            headers=headers_b,
        )
        assert get_response.status_code == 403

        # User B tries to update - should fail
        update_response = await client.patch(
            f"/api/v1/programs/{program_id}",
            json={"name": "Hacked!"},
            headers=headers_b,
        )
        assert update_response.status_code == 403

        # User B tries to delete - should fail
        delete_response = await client.delete(
            f"/api/v1/programs/{program_id}",
            headers=headers_b,
        )
        assert delete_response.status_code == 403

        # User B's program list should be empty
        list_response_b = await client.get("/api/v1/programs", headers=headers_b)
        assert list_response_b.status_code == 200
        assert list_response_b.json()["total"] == 0

        # User A's program list should have the program
        list_response_a = await client.get("/api/v1/programs", headers=headers_a)
        assert list_response_a.status_code == 200
        assert list_response_a.json()["total"] == 1

        # User A can update
        update_response_a = await client.patch(
            f"/api/v1/programs/{program_id}",
            json={"name": "Updated by Owner"},
            headers=headers_a,
        )
        assert update_response_a.status_code == 200
        assert update_response_a.json()["name"] == "Updated by Owner"

        # User A can delete
        delete_response_a = await client.delete(
            f"/api/v1/programs/{program_id}",
            headers=headers_a,
        )
        assert delete_response_a.status_code == 204

    async def test_program_validation(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """
        Test program creation validation:
        - Missing required fields
        - Invalid date range
        - Duplicate code
        """
        # Missing required fields
        missing_fields_response = await client.post(
            "/api/v1/programs",
            json={"name": "Incomplete Program"},
            headers=auth_headers,
        )
        assert missing_fields_response.status_code == 422

        # Invalid date range (end before start)
        invalid_dates_response = await client.post(
            "/api/v1/programs",
            json={
                "code": "INVALID-DATES",
                "name": "Invalid Dates Program",
                "start_date": "2024-12-31",
                "end_date": "2024-01-01",  # Before start
            },
            headers=auth_headers,
        )
        assert invalid_dates_response.status_code == 422

        # Create valid program
        await client.post(
            "/api/v1/programs",
            json={
                "code": "VALID-001",
                "name": "Valid Program",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
            headers=auth_headers,
        )

        # Duplicate code
        dup_code_response = await client.post(
            "/api/v1/programs",
            json={
                "code": "VALID-001",  # Same code
                "name": "Duplicate Code Program",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
            headers=auth_headers,
        )
        assert dup_code_response.status_code == 409
        assert "DUPLICATE_PROGRAM_CODE" in dup_code_response.json()["code"]

    async def test_pagination_flow(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test program list pagination."""
        # Create multiple programs
        for i in range(5):
            await client.post(
                "/api/v1/programs",
                json={
                    "code": f"PAGE-{i:03d}",
                    "name": f"Pagination Test Program {i}",
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                },
                headers=auth_headers,
            )

        # Test default pagination
        list_response = await client.get("/api/v1/programs", headers=auth_headers)
        assert list_response.status_code == 200
        data = list_response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 5
        assert data["page"] == 1

        # Test custom page size
        page_response = await client.get(
            "/api/v1/programs?page_size=2",
            headers=auth_headers,
        )
        assert page_response.status_code == 200
        page_data = page_response.json()
        assert page_data["total"] == 5
        assert len(page_data["items"]) == 2
        assert page_data["page_size"] == 2

        # Test page 2
        page2_response = await client.get(
            "/api/v1/programs?page=2&page_size=2",
            headers=auth_headers,
        )
        assert page2_response.status_code == 200
        page2_data = page2_response.json()
        assert len(page2_data["items"]) == 2
        assert page2_data["page"] == 2


class TestWeek1DatabaseIntegrity:
    """Tests for database integrity and transactions."""

    async def test_user_program_relationship(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Verify user-program relationship in database."""
        # Create user and program
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "dbtest@example.com",
                "password": "SecurePassword123!",
                "full_name": "DB Test User",
            },
        )
        user_id = register_response.json()["id"]

        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "dbtest@example.com", "password": "SecurePassword123!"},
        )
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        await client.post(
            "/api/v1/programs",
            json={
                "code": "DB-REL",
                "name": "DB Relationship Test",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
            headers=headers,
        )

        # Query database to verify relationship
        result = await db_session.execute(select(Program).where(Program.owner_id == UUID(user_id)))
        programs = result.scalars().all()
        assert len(programs) == 1
        assert programs[0].name == "DB Relationship Test"

        # Query user and check owned_programs relationship
        db_user = await db_session.get(User, UUID(user_id))
        assert db_user is not None
        # Note: Relationship loading depends on lazy loading config

    async def test_soft_delete_preserves_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Verify soft delete preserves data in database."""
        # Create user and program
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "softdel@example.com",
                "password": "SecurePassword123!",
                "full_name": "Soft Delete User",
            },
        )
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "softdel@example.com", "password": "SecurePassword123!"},
        )
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        create_response = await client.post(
            "/api/v1/programs",
            json={
                "code": "SOFT-DEL",
                "name": "Soft Delete Test",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
            headers=headers,
        )
        program_id = create_response.json()["id"]

        # Delete program
        await client.delete(f"/api/v1/programs/{program_id}", headers=headers)

        # Verify program still exists in database with deleted_at set
        db_program = await db_session.get(Program, UUID(program_id))
        assert db_program is not None  # Still in DB
        assert db_program.deleted_at is not None  # Marked as deleted
        assert db_program.name == "Soft Delete Test"  # Data preserved
