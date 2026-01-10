"""Integration tests for Authentication flow."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAuthRegistration:
    """Integration tests for user registration."""

    async def test_register_success(self, client: AsyncClient, sample_user_data: dict):
        """Should successfully register a new user."""
        response = await client.post("/api/v1/auth/register", json=sample_user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == sample_user_data["email"]
        assert data["full_name"] == sample_user_data["full_name"]
        assert "id" in data
        # Password should not be in response
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_register_duplicate_email(
        self, client: AsyncClient, sample_user_data: dict
    ):
        """Should return 409 for duplicate email registration."""
        # Register first user
        await client.post("/api/v1/auth/register", json=sample_user_data)

        # Try to register again with same email
        response = await client.post("/api/v1/auth/register", json=sample_user_data)

        assert response.status_code == 409
        assert "EMAIL_ALREADY_EXISTS" in response.json().get("code", "")

    async def test_register_weak_password(self, client: AsyncClient):
        """Should return 422 for password shorter than 8 characters."""
        user_data = {
            "email": "weak@example.com",
            "password": "short",  # Less than 8 characters
            "full_name": "Weak Password User",
        }
        response = await client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        """Should return 422 for invalid email format."""
        user_data = {
            "email": "not-an-email",
            "password": "SecurePassword123!",
            "full_name": "Invalid Email User",
        }
        response = await client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 422


class TestAuthLogin:
    """Integration tests for user login."""

    async def test_login_success(self, client: AsyncClient, sample_user_data: dict):
        """Should successfully login and receive tokens."""
        # Register user first
        await client.post("/api/v1/auth/register", json=sample_user_data)

        # Login
        login_data = {
            "email": sample_user_data["email"],
            "password": sample_user_data["password"],
        }
        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_login_wrong_password(
        self, client: AsyncClient, sample_user_data: dict
    ):
        """Should return 401 for wrong password."""
        # Register user first
        await client.post("/api/v1/auth/register", json=sample_user_data)

        # Login with wrong password
        login_data = {
            "email": sample_user_data["email"],
            "password": "WrongPassword123!",
        }
        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        assert "INVALID_CREDENTIALS" in response.json().get("code", "")

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Should return 401 for non-existent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "AnyPassword123!",
        }
        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401


class TestAuthToken:
    """Integration tests for token validation and refresh."""

    async def test_access_token_valid(
        self, client: AsyncClient, sample_user_data: dict
    ):
        """Should accept valid access token for protected endpoint."""
        # Register and login
        await client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": sample_user_data["email"],
                "password": sample_user_data["password"],
            },
        )
        access_token = login_response.json()["access_token"]

        # Access protected endpoint
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == sample_user_data["email"]

    async def test_access_token_invalid(self, client: AsyncClient):
        """Should return 401 for invalid access token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token-here"},
        )

        assert response.status_code == 401

    async def test_access_token_missing(self, client: AsyncClient):
        """Should return 401 when no token provided."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    async def test_refresh_token_success(
        self, client: AsyncClient, sample_user_data: dict
    ):
        """Should successfully refresh tokens."""
        # Register and login
        await client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": sample_user_data["email"],
                "password": sample_user_data["password"],
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh tokens
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Should return 401 for invalid refresh token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-refresh-token"},
        )

        assert response.status_code == 401


class TestAuthFlow:
    """End-to-end authentication flow tests."""

    async def test_complete_auth_flow(
        self, client: AsyncClient, sample_user_data: dict
    ):
        """
        Complete authentication flow:
        1. Register new user
        2. Login with credentials
        3. Access /auth/me with token
        4. Refresh token
        5. Access /auth/me with new token
        """
        # Step 1: Register new user
        register_response = await client.post(
            "/api/v1/auth/register",
            json=sample_user_data,
        )
        assert register_response.status_code == 201
        user_id = register_response.json()["id"]

        # Step 2: Login with credentials
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": sample_user_data["email"],
                "password": sample_user_data["password"],
            },
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # Step 3: Access /auth/me with token
        me_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["id"] == user_id
        assert me_data["email"] == sample_user_data["email"]

        # Step 4: Refresh token
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        new_access_token = new_tokens["access_token"]

        # Step 5: Access /auth/me with new token
        me_response_2 = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert me_response_2.status_code == 200
        assert me_response_2.json()["id"] == user_id

    async def test_token_cannot_use_access_as_refresh(
        self, client: AsyncClient, sample_user_data: dict
    ):
        """Should not accept access token as refresh token."""
        # Register and login
        await client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": sample_user_data["email"],
                "password": sample_user_data["password"],
            },
        )
        access_token = login_response.json()["access_token"]

        # Try to use access token as refresh token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401
        assert "INVALID_TOKEN_TYPE" in response.json().get("code", "")
