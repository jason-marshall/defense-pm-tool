"""Integration tests for Variance Explanation API endpoints."""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestVarianceExplanationCRUD:
    """Tests for variance explanation CRUD operations."""

    @pytest.fixture
    async def variance_context(self, client: AsyncClient) -> dict:
        """Create user, program, and related data for testing variance explanations."""
        # Register and login user
        email = f"variance_test_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "TestPass123!",
                "full_name": "Variance Tester",
            },
        )
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create program
        program_response = await client.post(
            "/api/v1/programs",
            headers=headers,
            json={
                "name": "Variance Test Program",
                "code": f"VAR-{uuid4().hex[:6]}",
                "description": "Program for variance testing",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        )
        program_id = program_response.json()["id"]

        return {
            "headers": headers,
            "program_id": program_id,
        }

    async def test_create_variance_explanation(self, client: AsyncClient, variance_context: dict):
        """Should create a variance explanation with valid data."""
        explanation_data = {
            "program_id": variance_context["program_id"],
            "variance_type": "cost",
            "variance_amount": "1500.00",
            "variance_percent": "12.5",
            "explanation": "Cost overrun due to unexpected material price increases affecting procurement.",
            "corrective_action": "Negotiating with alternative suppliers for better rates.",
            "expected_resolution": str(date.today() + timedelta(days=30)),
        }

        response = await client.post(
            "/api/v1/variance-explanations",
            headers=variance_context["headers"],
            json=explanation_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["variance_type"] == "cost"
        assert data["variance_amount"] == "1500.00"
        assert data["variance_percent"] == "12.5000"
        assert "material price" in data["explanation"]
        assert data["corrective_action"] is not None

    async def test_create_schedule_variance(self, client: AsyncClient, variance_context: dict):
        """Should create a schedule variance explanation."""
        explanation_data = {
            "program_id": variance_context["program_id"],
            "variance_type": "schedule",
            "variance_amount": "-5000.00",
            "variance_percent": "-8.5",
            "explanation": "Schedule delay due to resource constraints and personnel availability issues.",
        }

        response = await client.post(
            "/api/v1/variance-explanations",
            headers=variance_context["headers"],
            json=explanation_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["variance_type"] == "schedule"
        assert data["variance_amount"] == "-5000.00"

    async def test_create_variance_invalid_program(
        self, client: AsyncClient, variance_context: dict
    ):
        """Should return 404 for non-existent program."""
        explanation_data = {
            "program_id": str(uuid4()),  # Non-existent program
            "variance_type": "cost",
            "variance_amount": "1000.00",
            "variance_percent": "10.0",
            "explanation": "Test variance explanation for invalid program check.",
        }

        response = await client.post(
            "/api/v1/variance-explanations",
            headers=variance_context["headers"],
            json=explanation_data,
        )

        assert response.status_code == 404
        detail = response.json()["detail"]
        # Handle both string and dict response formats
        if isinstance(detail, dict):
            assert "PROGRAM_NOT_FOUND" in detail.get("code", "")
        else:
            assert "PROGRAM_NOT_FOUND" in str(detail) or "not found" in str(detail).lower()

    async def test_create_variance_explanation_short(
        self, client: AsyncClient, variance_context: dict
    ):
        """Should reject explanation shorter than 10 characters."""
        explanation_data = {
            "program_id": variance_context["program_id"],
            "variance_type": "cost",
            "variance_amount": "1000.00",
            "variance_percent": "10.0",
            "explanation": "Short",  # Too short
        }

        response = await client.post(
            "/api/v1/variance-explanations",
            headers=variance_context["headers"],
            json=explanation_data,
        )

        assert response.status_code == 422  # Validation error

    async def test_list_variance_explanations(self, client: AsyncClient, variance_context: dict):
        """Should list variance explanations for a program."""
        # Create a variance explanation first
        explanation_data = {
            "program_id": variance_context["program_id"],
            "variance_type": "cost",
            "variance_amount": "2000.00",
            "variance_percent": "15.0",
            "explanation": "Variance for list testing purposes in integration test.",
        }
        await client.post(
            "/api/v1/variance-explanations",
            headers=variance_context["headers"],
            json=explanation_data,
        )

        # List explanations
        response = await client.get(
            f"/api/v1/variance-explanations/program/{variance_context['program_id']}",
            headers=variance_context["headers"],
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1

    async def test_list_variance_explanations_with_filter(
        self, client: AsyncClient, variance_context: dict
    ):
        """Should filter variance explanations by type."""
        # Create both types
        cost_data = {
            "program_id": variance_context["program_id"],
            "variance_type": "cost",
            "variance_amount": "1000.00",
            "variance_percent": "10.0",
            "explanation": "Cost variance for filter testing in integration test.",
        }
        schedule_data = {
            "program_id": variance_context["program_id"],
            "variance_type": "schedule",
            "variance_amount": "500.00",
            "variance_percent": "5.0",
            "explanation": "Schedule variance for filter testing in integration test.",
        }
        await client.post(
            "/api/v1/variance-explanations",
            headers=variance_context["headers"],
            json=cost_data,
        )
        await client.post(
            "/api/v1/variance-explanations",
            headers=variance_context["headers"],
            json=schedule_data,
        )

        # Filter by cost type
        response = await client.get(
            f"/api/v1/variance-explanations/program/{variance_context['program_id']}?variance_type=cost",
            headers=variance_context["headers"],
        )

        assert response.status_code == 200
        data = response.json()
        assert all(item["variance_type"] == "cost" for item in data["items"])

    async def test_get_variance_explanation(self, client: AsyncClient, variance_context: dict):
        """Should get a specific variance explanation by ID."""
        # Create first
        explanation_data = {
            "program_id": variance_context["program_id"],
            "variance_type": "cost",
            "variance_amount": "3000.00",
            "variance_percent": "20.0",
            "explanation": "Significant cost variance for get test in integration test.",
        }
        create_response = await client.post(
            "/api/v1/variance-explanations",
            headers=variance_context["headers"],
            json=explanation_data,
        )
        explanation_id = create_response.json()["id"]

        # Get by ID
        response = await client.get(
            f"/api/v1/variance-explanations/{explanation_id}",
            headers=variance_context["headers"],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == explanation_id
        assert data["variance_amount"] == "3000.00"

    async def test_get_nonexistent_variance_explanation(
        self, client: AsyncClient, variance_context: dict
    ):
        """Should return 404 for non-existent explanation."""
        response = await client.get(
            f"/api/v1/variance-explanations/{uuid4()}",
            headers=variance_context["headers"],
        )

        assert response.status_code == 404

    async def test_update_variance_explanation(self, client: AsyncClient, variance_context: dict):
        """Should update a variance explanation."""
        # Create first
        explanation_data = {
            "program_id": variance_context["program_id"],
            "variance_type": "cost",
            "variance_amount": "1000.00",
            "variance_percent": "10.0",
            "explanation": "Initial variance explanation for update test.",
        }
        create_response = await client.post(
            "/api/v1/variance-explanations",
            headers=variance_context["headers"],
            json=explanation_data,
        )
        explanation_id = create_response.json()["id"]

        # Update
        update_data = {
            "explanation": "Updated variance explanation with more detail about the cause.",
            "corrective_action": "New corrective action plan to address the variance.",
            "expected_resolution": str(date.today() + timedelta(days=45)),
        }
        response = await client.patch(
            f"/api/v1/variance-explanations/{explanation_id}",
            headers=variance_context["headers"],
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert "Updated variance explanation" in data["explanation"]
        assert data["corrective_action"] is not None

    async def test_delete_variance_explanation(self, client: AsyncClient, variance_context: dict):
        """Should soft delete a variance explanation."""
        # Create first
        explanation_data = {
            "program_id": variance_context["program_id"],
            "variance_type": "schedule",
            "variance_amount": "500.00",
            "variance_percent": "5.0",
            "explanation": "Variance explanation to be deleted in test.",
        }
        create_response = await client.post(
            "/api/v1/variance-explanations",
            headers=variance_context["headers"],
            json=explanation_data,
        )
        explanation_id = create_response.json()["id"]

        # Delete
        response = await client.delete(
            f"/api/v1/variance-explanations/{explanation_id}",
            headers=variance_context["headers"],
        )

        assert response.status_code == 204

        # Verify deleted (should be 404)
        get_response = await client.get(
            f"/api/v1/variance-explanations/{explanation_id}",
            headers=variance_context["headers"],
        )
        assert get_response.status_code == 404

    async def test_get_significant_variances(self, client: AsyncClient, variance_context: dict):
        """Should get variance explanations above threshold."""
        # Create variances of different percentages
        small_variance = {
            "program_id": variance_context["program_id"],
            "variance_type": "cost",
            "variance_amount": "200.00",
            "variance_percent": "5.0",
            "explanation": "Small variance below threshold for significant test.",
        }
        large_variance = {
            "program_id": variance_context["program_id"],
            "variance_type": "cost",
            "variance_amount": "5000.00",
            "variance_percent": "25.0",
            "explanation": "Large variance above threshold for significant test.",
        }
        await client.post(
            "/api/v1/variance-explanations",
            headers=variance_context["headers"],
            json=small_variance,
        )
        await client.post(
            "/api/v1/variance-explanations",
            headers=variance_context["headers"],
            json=large_variance,
        )

        # Get significant (default 10% threshold)
        response = await client.get(
            f"/api/v1/variance-explanations/program/{variance_context['program_id']}/significant",
            headers=variance_context["headers"],
        )

        assert response.status_code == 200
        data = response.json()
        # All returned variances should be >= 10%
        for item in data:
            assert float(item["variance_percent"]) >= 10.0

    async def test_get_significant_variances_custom_threshold(
        self, client: AsyncClient, variance_context: dict
    ):
        """Should get variances above custom threshold."""
        response = await client.get(
            f"/api/v1/variance-explanations/program/{variance_context['program_id']}/significant?threshold_percent=20.0",
            headers=variance_context["headers"],
        )

        assert response.status_code == 200


class TestVarianceExplanationValidation:
    """Tests for variance explanation validation rules."""

    @pytest.fixture
    async def validation_context(self, client: AsyncClient) -> dict:
        """Create context for validation tests."""
        email = f"val_test_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "TestPass123!",
                "full_name": "Validation Tester",
            },
        )
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        program_response = await client.post(
            "/api/v1/programs",
            headers=headers,
            json={
                "name": "Validation Test Program",
                "code": f"VLD-{uuid4().hex[:6]}",
                "description": "Program for validation testing",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        )
        program_id = program_response.json()["id"]

        return {
            "headers": headers,
            "program_id": program_id,
        }

    async def test_missing_required_fields(self, client: AsyncClient, validation_context: dict):
        """Should reject missing required fields."""
        # Missing explanation
        response = await client.post(
            "/api/v1/variance-explanations",
            headers=validation_context["headers"],
            json={
                "program_id": validation_context["program_id"],
                "variance_type": "cost",
                "variance_amount": "1000.00",
                "variance_percent": "10.0",
                # Missing explanation
            },
        )

        assert response.status_code == 422

    async def test_invalid_variance_type(self, client: AsyncClient, validation_context: dict):
        """Should reject invalid variance type."""
        response = await client.post(
            "/api/v1/variance-explanations",
            headers=validation_context["headers"],
            json={
                "program_id": validation_context["program_id"],
                "variance_type": "invalid_type",  # Invalid
                "variance_amount": "1000.00",
                "variance_percent": "10.0",
                "explanation": "Test explanation for invalid type validation.",
            },
        )

        assert response.status_code == 422


class TestVarianceExplanationPagination:
    """Tests for variance explanation pagination."""

    @pytest.fixture
    async def pagination_context(self, client: AsyncClient) -> dict:
        """Create context with multiple variance explanations."""
        email = f"pag_test_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "TestPass123!",
                "full_name": "Pagination Tester",
            },
        )
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        program_response = await client.post(
            "/api/v1/programs",
            headers=headers,
            json={
                "name": "Pagination Test Program",
                "code": f"PAG-{uuid4().hex[:6]}",
                "description": "Program for pagination testing",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        )
        program_id = program_response.json()["id"]

        # Create multiple variance explanations
        for i in range(5):
            await client.post(
                "/api/v1/variance-explanations",
                headers=headers,
                json={
                    "program_id": program_id,
                    "variance_type": "cost" if i % 2 == 0 else "schedule",
                    "variance_amount": str(1000 * (i + 1)),
                    "variance_percent": str(5 * (i + 1)),
                    "explanation": f"Variance explanation number {i + 1} for pagination testing.",
                },
            )

        return {
            "headers": headers,
            "program_id": program_id,
        }

    async def test_pagination_first_page(self, client: AsyncClient, pagination_context: dict):
        """Should return first page of results."""
        response = await client.get(
            f"/api/v1/variance-explanations/program/{pagination_context['program_id']}?page=1&per_page=2",
            headers=pagination_context["headers"],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 2
        assert len(data["items"]) == 2
        assert data["total"] >= 5
        assert data["pages"] >= 3

    async def test_pagination_second_page(self, client: AsyncClient, pagination_context: dict):
        """Should return second page of results."""
        response = await client.get(
            f"/api/v1/variance-explanations/program/{pagination_context['program_id']}?page=2&per_page=2",
            headers=pagination_context["headers"],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert len(data["items"]) == 2
