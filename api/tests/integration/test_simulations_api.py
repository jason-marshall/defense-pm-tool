"""Integration tests for Monte Carlo simulation API endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestSimulationConfigCRUD:
    """Tests for simulation configuration CRUD operations."""

    @pytest.fixture
    async def sim_context(self, client: AsyncClient) -> dict:
        """Create user and program for testing simulations."""
        # Register and login user
        email = f"sim_test_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "TestPass123!",
                "full_name": "Simulation Tester",
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
                "name": "Simulation Test Program",
                "code": f"SIM-{uuid4().hex[:6]}",
                "description": "Program for simulation testing",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        )
        program_id = program_response.json()["id"]

        return {
            "headers": headers,
            "program_id": program_id,
        }

    async def test_create_simulation_config(self, client: AsyncClient, sim_context: dict):
        """Should create a simulation config with valid data."""
        activity_id = str(uuid4())
        config_data = {
            "program_id": sim_context["program_id"],
            "name": "Test Simulation",
            "description": "Test simulation config",
            "iterations": 100,
            "activity_distributions": {
                activity_id: {
                    "distribution": "triangular",
                    "min": 5,
                    "mode": 10,
                    "max": 15,
                }
            },
        }

        response = await client.post(
            "/api/v1/simulations",
            headers=sim_context["headers"],
            json=config_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Simulation"
        assert data["iterations"] == 100
        assert data["activity_count"] == 1

    async def test_list_simulation_configs(self, client: AsyncClient, sim_context: dict):
        """Should list simulation configs for a program."""
        activity_id = str(uuid4())
        config_data = {
            "program_id": sim_context["program_id"],
            "name": "List Test Config",
            "iterations": 100,
            "activity_distributions": {
                activity_id: {
                    "distribution": "uniform",
                    "min": 5,
                    "max": 10,
                }
            },
        }

        await client.post(
            "/api/v1/simulations",
            headers=sim_context["headers"],
            json=config_data,
        )

        # List configs
        response = await client.get(
            f"/api/v1/simulations?program_id={sim_context['program_id']}",
            headers=sim_context["headers"],
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(c["name"] == "List Test Config" for c in data)

    async def test_get_simulation_config(self, client: AsyncClient, sim_context: dict):
        """Should get a specific simulation config by ID."""
        activity_id = str(uuid4())
        config_data = {
            "program_id": sim_context["program_id"],
            "name": "Get Test Config",
            "iterations": 200,
            "activity_distributions": {
                activity_id: {
                    "distribution": "pert",
                    "min": 10,
                    "mode": 15,
                    "max": 25,
                }
            },
        }

        create_response = await client.post(
            "/api/v1/simulations",
            headers=sim_context["headers"],
            json=config_data,
        )
        config_id = create_response.json()["id"]

        # Get config
        response = await client.get(
            f"/api/v1/simulations/{config_id}",
            headers=sim_context["headers"],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Test Config"
        assert data["iterations"] == 200

    async def test_update_simulation_config(self, client: AsyncClient, sim_context: dict):
        """Should update a simulation config."""
        activity_id = str(uuid4())
        config_data = {
            "program_id": sim_context["program_id"],
            "name": "Update Test Config",
            "iterations": 100,
            "activity_distributions": {
                activity_id: {
                    "distribution": "normal",
                    "mean": 10,
                    "std": 2,
                }
            },
        }

        create_response = await client.post(
            "/api/v1/simulations",
            headers=sim_context["headers"],
            json=config_data,
        )
        config_id = create_response.json()["id"]

        # Update config
        update_data = {
            "name": "Updated Config Name",
            "iterations": 500,
        }

        response = await client.patch(
            f"/api/v1/simulations/{config_id}",
            headers=sim_context["headers"],
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Config Name"
        assert data["iterations"] == 500

    async def test_delete_simulation_config(self, client: AsyncClient, sim_context: dict):
        """Should soft delete a simulation config."""
        activity_id = str(uuid4())
        config_data = {
            "program_id": sim_context["program_id"],
            "name": "Delete Test Config",
            "iterations": 100,
            "activity_distributions": {
                activity_id: {
                    "distribution": "triangular",
                    "min": 5,
                    "mode": 10,
                    "max": 15,
                }
            },
        }

        create_response = await client.post(
            "/api/v1/simulations",
            headers=sim_context["headers"],
            json=config_data,
        )
        config_id = create_response.json()["id"]

        # Delete config
        response = await client.delete(
            f"/api/v1/simulations/{config_id}",
            headers=sim_context["headers"],
        )

        assert response.status_code == 204

        # Verify deleted (should return 404)
        get_response = await client.get(
            f"/api/v1/simulations/{config_id}",
            headers=sim_context["headers"],
        )
        assert get_response.status_code == 404


class TestSimulationExecution:
    """Tests for running simulations."""

    @pytest.fixture
    async def sim_context(self, client: AsyncClient) -> dict:
        """Create user and program for testing simulations."""
        email = f"sim_exec_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "TestPass123!",
                "full_name": "Simulation Executor",
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
                "name": "Execution Test Program",
                "code": f"EXE-{uuid4().hex[:6]}",
                "description": "Program for execution testing",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        )
        program_id = program_response.json()["id"]

        return {"headers": headers, "program_id": program_id}

    async def test_run_simulation(self, client: AsyncClient, sim_context: dict):
        """Should run a simulation and return results."""
        activity_id_1 = str(uuid4())
        activity_id_2 = str(uuid4())
        config_data = {
            "program_id": sim_context["program_id"],
            "name": "Run Test Config",
            "iterations": 100,
            "activity_distributions": {
                activity_id_1: {
                    "distribution": "triangular",
                    "min": 5,
                    "mode": 10,
                    "max": 15,
                },
                activity_id_2: {
                    "distribution": "uniform",
                    "min": 3,
                    "max": 8,
                },
            },
        }

        create_response = await client.post(
            "/api/v1/simulations",
            headers=sim_context["headers"],
            json=config_data,
        )
        config_id = create_response.json()["id"]

        # Run simulation
        response = await client.post(
            f"/api/v1/simulations/{config_id}/run",
            headers=sim_context["headers"],
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["iterations_completed"] == 100
        assert data["duration_results"] is not None
        assert "p50" in data["duration_results"]
        assert "p90" in data["duration_results"]

    async def test_run_simulation_with_seed(self, client: AsyncClient, sim_context: dict):
        """Should run reproducible simulation with seed."""
        activity_id = str(uuid4())
        config_data = {
            "program_id": sim_context["program_id"],
            "name": "Seed Test Config",
            "iterations": 100,
            "activity_distributions": {
                activity_id: {
                    "distribution": "triangular",
                    "min": 5,
                    "mode": 10,
                    "max": 15,
                },
            },
        }

        create_response = await client.post(
            "/api/v1/simulations",
            headers=sim_context["headers"],
            json=config_data,
        )
        config_id = create_response.json()["id"]

        # Run simulation with seed
        run_request = {"seed": 12345}

        response1 = await client.post(
            f"/api/v1/simulations/{config_id}/run",
            headers=sim_context["headers"],
            json=run_request,
        )

        response2 = await client.post(
            f"/api/v1/simulations/{config_id}/run",
            headers=sim_context["headers"],
            json=run_request,
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Results should be reproducible with same seed
        assert data1["duration_results"]["p50"] == data2["duration_results"]["p50"]
        assert data1["duration_results"]["p90"] == data2["duration_results"]["p90"]

    async def test_list_simulation_results(self, client: AsyncClient, sim_context: dict):
        """Should list results for a simulation config."""
        activity_id = str(uuid4())
        config_data = {
            "program_id": sim_context["program_id"],
            "name": "Results List Test",
            "iterations": 100,
            "activity_distributions": {
                activity_id: {
                    "distribution": "uniform",
                    "min": 5,
                    "max": 10,
                },
            },
        }

        create_response = await client.post(
            "/api/v1/simulations",
            headers=sim_context["headers"],
            json=config_data,
        )
        config_id = create_response.json()["id"]

        # Run simulation
        await client.post(
            f"/api/v1/simulations/{config_id}/run",
            headers=sim_context["headers"],
            json={},
        )

        # List results
        response = await client.get(
            f"/api/v1/simulations/{config_id}/results",
            headers=sim_context["headers"],
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["status"] == "completed"


class TestQuickSimulation:
    """Tests for quick/one-off simulations."""

    @pytest.fixture
    async def sim_context(self, client: AsyncClient) -> dict:
        """Create user and program for testing simulations."""
        email = f"sim_quick_{uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "TestPass123!",
                "full_name": "Quick Simulator",
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
                "name": "Quick Test Program",
                "code": f"QCK-{uuid4().hex[:6]}",
                "description": "Program for quick simulation testing",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        )
        program_id = program_response.json()["id"]

        return {"headers": headers, "program_id": program_id}

    async def test_quick_simulation(self, client: AsyncClient, sim_context: dict):
        """Should run a quick simulation without saving config."""
        activity_id_1 = str(uuid4())
        activity_id_2 = str(uuid4())
        request_data = {
            "program_id": sim_context["program_id"],
            "iterations": 100,
            "activity_distributions": {
                activity_id_1: {
                    "distribution": "triangular",
                    "min": 5,
                    "mode": 10,
                    "max": 15,
                },
                activity_id_2: {
                    "distribution": "pert",
                    "min": 8,
                    "mode": 12,
                    "max": 20,
                },
            },
        }

        response = await client.post(
            "/api/v1/simulations/quick",
            headers=sim_context["headers"],
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["iterations_completed"] == 100
        assert data["duration_results"] is not None

    async def test_quick_simulation_with_cost_distributions(
        self, client: AsyncClient, sim_context: dict
    ):
        """Should run quick simulation with cost distributions."""
        activity_id = str(uuid4())
        request_data = {
            "program_id": sim_context["program_id"],
            "iterations": 100,
            "activity_distributions": {
                activity_id: {
                    "distribution": "uniform",
                    "min": 5,
                    "max": 10,
                },
            },
            "cost_distributions": {
                activity_id: {
                    "distribution": "triangular",
                    "min": 1000,
                    "mode": 1500,
                    "max": 2500,
                },
            },
        }

        response = await client.post(
            "/api/v1/simulations/quick",
            headers=sim_context["headers"],
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["cost_results"] is not None
        assert "p50" in data["cost_results"]


class TestSimulationValidation:
    """Tests for simulation input validation."""

    async def test_create_config_nonexistent_program(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for nonexistent program."""
        activity_id = str(uuid4())
        config_data = {
            "program_id": "00000000-0000-0000-0000-000000000000",
            "name": "Invalid Program Test",
            "iterations": 100,
            "activity_distributions": {
                activity_id: {
                    "distribution": "uniform",
                    "min": 5,
                    "max": 10,
                }
            },
        }

        response = await client.post(
            "/api/v1/simulations",
            headers=auth_headers,
            json=config_data,
        )

        assert response.status_code == 404

    async def test_get_nonexistent_config(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for nonexistent config."""
        response = await client.get(
            "/api/v1/simulations/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_run_nonexistent_config(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for running nonexistent config."""
        response = await client.post(
            "/api/v1/simulations/00000000-0000-0000-0000-000000000000/run",
            headers=auth_headers,
            json={},
        )

        assert response.status_code == 404
