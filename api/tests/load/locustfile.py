"""Load tests using Locust for Defense PM Tool API."""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from locust import HttpUser, between, events, task


class DefensePMUser(HttpUser):  # type: ignore[misc]
    """Simulated user for load testing."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self) -> None:
        """Login and create test program on user start."""
        # Register and login
        self.email = f"loadtest_{uuid4().hex[:8]}@example.com"
        self.password = "LoadTest123!"

        # Register
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": self.email,
                "password": self.password,
                "full_name": "Load Test User",
            },
        )

        # Login
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": self.email,
                "password": self.password,
            },
        )

        if response.status_code == 200:
            token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
            self.program_id = None
            self.activity_ids: list[str] = []
        else:
            self.headers = {}

    @task(5)
    def list_programs(self) -> None:
        """List programs - frequent read operation."""
        self.client.get("/api/v1/programs", headers=self.headers)

    @task(3)
    def create_and_read_program(self) -> None:
        """Create a program and read it back."""
        # Create
        response = self.client.post(
            "/api/v1/programs",
            json={
                "name": f"Load Test Program {uuid4().hex[:6]}",
                "code": f"LT-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=365)),
                "budget_at_completion": "1000000.00",
            },
            headers=self.headers,
        )

        if response.status_code == 201:
            program_id = response.json().get("id")
            self.program_id = program_id

            # Read it back
            self.client.get(f"/api/v1/programs/{program_id}", headers=self.headers)

    @task(2)
    def create_activities(self) -> None:
        """Create activities in a program."""
        if not self.program_id:
            return

        # Create WBS first
        wbs_response = self.client.post(
            "/api/v1/wbs",
            json={
                "program_id": self.program_id,
                "wbs_code": f"1.{random.randint(1, 99)}",
                "name": f"Work Package {uuid4().hex[:4]}",
            },
            headers=self.headers,
        )

        if wbs_response.status_code == 201:
            wbs_id = wbs_response.json().get("id")

            # Create activity
            activity_response = self.client.post(
                "/api/v1/activities",
                json={
                    "program_id": self.program_id,
                    "wbs_id": wbs_id,
                    "code": f"A-{uuid4().hex[:6]}",
                    "name": f"Activity {uuid4().hex[:4]}",
                    "duration": random.randint(5, 30),
                    "budgeted_cost": str(random.randint(10000, 100000)),
                },
                headers=self.headers,
            )

            if activity_response.status_code == 201:
                self.activity_ids.append(activity_response.json().get("id"))

    @task(2)
    def calculate_schedule(self) -> None:
        """Run CPM calculation."""
        if not self.program_id:
            return

        self.client.post(
            f"/api/v1/schedule/calculate/{self.program_id}",
            headers=self.headers,
        )

    @task(1)
    def get_dashboard(self) -> None:
        """Get EVMS dashboard."""
        if not self.program_id:
            return

        self.client.get(
            f"/api/v1/evms/{self.program_id}/dashboard",
            headers=self.headers,
        )

    @task(1)
    def health_check(self) -> None:
        """Check health endpoint."""
        self.client.get("/health")


class HeavyLoadUser(HttpUser):  # type: ignore[misc]
    """User for stress testing with heavy operations."""

    wait_time = between(5, 10)

    def on_start(self) -> None:
        """Setup for heavy load user."""
        self.email = f"heavy_{uuid4().hex[:8]}@example.com"
        self.password = "HeavyLoad123!"

        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": self.email,
                "password": self.password,
                "full_name": "Heavy Load User",
            },
        )

        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": self.email, "password": self.password},
        )

        if response.status_code == 200:
            self.headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
            self._setup_large_program()
        else:
            self.headers = {}
            self.program_id = None

    def _setup_large_program(self) -> None:
        """Create a program with many activities for heavy testing."""
        response = self.client.post(
            "/api/v1/programs",
            json={
                "name": f"Heavy Load Program {uuid4().hex[:6]}",
                "code": f"HL-{uuid4().hex[:6].upper()}",
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=730)),
                "budget_at_completion": "10000000.00",
            },
            headers=self.headers,
        )

        if response.status_code == 201:
            self.program_id = response.json().get("id")

    @task
    def run_monte_carlo(self) -> None:
        """Run Monte Carlo simulation."""
        if not self.program_id:
            return

        self.client.post(
            f"/api/v1/monte-carlo/{self.program_id}/simulate",
            json={"iterations": 100, "seed": random.randint(1, 10000)},
            headers=self.headers,
        )


# Event hooks for custom reporting
@events.test_start.add_listener
def on_test_start(environment: Any, **kwargs: Any) -> None:
    """Log when test starts."""
    print(f"Load test starting with {environment.parsed_options.num_users} users")


@events.test_stop.add_listener
def on_test_stop(environment: Any, **kwargs: Any) -> None:
    """Log when test stops."""
    print("Load test completed")
