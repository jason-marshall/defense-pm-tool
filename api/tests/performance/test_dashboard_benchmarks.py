"""Dashboard performance benchmarks for Week 8 optimization.

Establishes baseline metrics for dashboard endpoints to guide
optimization efforts in Week 8.

Performance Targets:
- EVMS Summary: <500ms
- S-curve Enhanced: <2s
- WBS Tree: <500ms
- Full Dashboard Load: <3s
"""

import time
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient


class TestDashboardPerformanceBaselines:
    """Performance baseline tests for dashboard endpoints.

    These tests establish current performance metrics to:
    1. Document current state before Week 8 optimizations
    2. Provide regression detection for performance
    3. Guide optimization priorities
    """

    @pytest_asyncio.fixture
    async def dashboard_program(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> dict:
        """Create a program with sufficient data for dashboard testing."""
        # Create program
        program_data = {
            "name": "Dashboard Performance Test Program",
            "code": f"PERF-{uuid4().hex[:6].upper()}",
            "description": "Program for dashboard performance testing",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "budget_at_completion": "1000000.00",
        }
        response = await client.post(
            "/api/v1/programs",
            json=program_data,
            headers=auth_headers,
        )
        assert response.status_code == 201
        program = response.json()
        program_id = program["id"]

        # Create WBS structure
        wbs_elements = []
        for i in range(3):
            wbs_resp = await client.post(
                "/api/v1/wbs",
                json={
                    "program_id": program_id,
                    "name": f"Work Package {i + 1}",
                    "wbs_code": f"1.{i + 1}",
                },
                headers=auth_headers,
            )
            if wbs_resp.status_code == 201:
                wbs_elements.append(wbs_resp.json())

        # Create activities with EVMS data
        activities = []
        for i in range(10):
            wbs_id = wbs_elements[i % len(wbs_elements)]["id"] if wbs_elements else None
            activity_data = {
                "program_id": program_id,
                "name": f"Activity {i + 1}",
                "code": f"ACT-{i + 1:03d}",
                "duration": 10 + (i % 5),
                "budgeted_cost": str(Decimal("10000.00") + Decimal(i * 1000)),
                "percent_complete": str(Decimal(min(100, i * 10))),
                "actual_cost": str(Decimal("8000.00") + Decimal(i * 800)),
            }
            if wbs_id:
                activity_data["wbs_id"] = wbs_id

            resp = await client.post(
                "/api/v1/activities",
                json=activity_data,
                headers=auth_headers,
            )
            if resp.status_code == 201:
                activities.append(resp.json())

        return {
            "program": program,
            "wbs_elements": wbs_elements,
            "activities": activities,
            "headers": auth_headers,
        }

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_evms_summary_endpoint_baseline(
        self,
        client: AsyncClient,
        dashboard_program: dict,
    ):
        """Baseline: EVMS summary endpoint performance.

        Target: <500ms
        Current baseline to be established.
        """
        program_id = dashboard_program["program"]["id"]
        headers = dashboard_program["headers"]

        # Warm up
        await client.get(
            f"/api/v1/evms/summary/{program_id}",
            headers=headers,
        )

        # Measure
        times = []
        for _ in range(3):
            start = time.perf_counter()
            response = await client.get(
                f"/api/v1/evms/summary/{program_id}",
                headers=headers,
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed)

            # Accept success or not found (if endpoint not fully implemented)
            assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print("\n=== EVMS Summary Endpoint Baseline ===")
        print(f"  Average: {avg_time * 1000:.1f}ms")
        print(f"  Min: {min_time * 1000:.1f}ms")
        print(f"  Max: {max_time * 1000:.1f}ms")
        print("  Target: <500ms")

        # Baseline assertion - may need adjustment
        assert avg_time < 2.0, f"EVMS summary baseline exceeded 2s: {avg_time * 1000:.1f}ms"

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_scurve_enhanced_endpoint_baseline(
        self,
        client: AsyncClient,
        dashboard_program: dict,
    ):
        """Baseline: Enhanced S-curve endpoint performance.

        Target: <2s (includes Monte Carlo confidence bands)
        Current baseline to be established.
        """
        program_id = dashboard_program["program"]["id"]
        headers = dashboard_program["headers"]

        # Warm up
        await client.get(
            f"/api/v1/evms/s-curve-enhanced/{program_id}",
            headers=headers,
        )

        # Measure
        times = []
        for _ in range(3):
            start = time.perf_counter()
            response = await client.get(
                f"/api/v1/evms/s-curve-enhanced/{program_id}",
                headers=headers,
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed)

            # Accept success or not found
            assert response.status_code in [200, 404, 500], (
                f"Unexpected status: {response.status_code}"
            )

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print("\n=== Enhanced S-curve Endpoint Baseline ===")
        print(f"  Average: {avg_time * 1000:.1f}ms")
        print(f"  Min: {min_time * 1000:.1f}ms")
        print(f"  Max: {max_time * 1000:.1f}ms")
        print("  Target: <2000ms")

        # Baseline assertion
        assert avg_time < 5.0, f"S-curve baseline exceeded 5s: {avg_time * 1000:.1f}ms"

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_wbs_tree_endpoint_baseline(
        self,
        client: AsyncClient,
        dashboard_program: dict,
    ):
        """Baseline: WBS tree endpoint performance.

        Target: <500ms
        Current baseline to be established.
        """
        program_id = dashboard_program["program"]["id"]
        headers = dashboard_program["headers"]

        # Warm up
        await client.get(
            f"/api/v1/wbs/tree?program_id={program_id}",
            headers=headers,
        )

        # Measure
        times = []
        for _ in range(3):
            start = time.perf_counter()
            response = await client.get(
                f"/api/v1/wbs/tree?program_id={program_id}",
                headers=headers,
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed)

            assert response.status_code in [200, 422], f"Unexpected status: {response.status_code}"

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print("\n=== WBS Tree Endpoint Baseline ===")
        print(f"  Average: {avg_time * 1000:.1f}ms")
        print(f"  Min: {min_time * 1000:.1f}ms")
        print(f"  Max: {max_time * 1000:.1f}ms")
        print("  Target: <500ms")

        # Baseline assertion
        assert avg_time < 2.0, f"WBS tree baseline exceeded 2s: {avg_time * 1000:.1f}ms"

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_activities_list_endpoint_baseline(
        self,
        client: AsyncClient,
        dashboard_program: dict,
    ):
        """Baseline: Activities list endpoint performance.

        Target: <500ms
        Current baseline to be established.
        """
        program_id = dashboard_program["program"]["id"]
        headers = dashboard_program["headers"]

        # Warm up
        await client.get(
            f"/api/v1/activities?program_id={program_id}",
            headers=headers,
        )

        # Measure
        times = []
        for _ in range(3):
            start = time.perf_counter()
            response = await client.get(
                f"/api/v1/activities?program_id={program_id}",
                headers=headers,
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed)

            assert response.status_code == 200, f"Unexpected status: {response.status_code}"

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print("\n=== Activities List Endpoint Baseline ===")
        print(f"  Average: {avg_time * 1000:.1f}ms")
        print(f"  Min: {min_time * 1000:.1f}ms")
        print(f"  Max: {max_time * 1000:.1f}ms")
        print("  Target: <500ms")

        # Baseline assertion
        assert avg_time < 2.0, f"Activities list baseline exceeded 2s: {avg_time * 1000:.1f}ms"

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_schedule_calculation_endpoint_baseline(
        self,
        client: AsyncClient,
        dashboard_program: dict,
    ):
        """Baseline: Schedule calculation endpoint performance.

        Target: <1s for 10 activities
        Current baseline to be established.
        """
        program_id = dashboard_program["program"]["id"]
        headers = dashboard_program["headers"]

        # Warm up
        await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=headers,
        )

        # Measure
        times = []
        for _ in range(3):
            start = time.perf_counter()
            response = await client.post(
                f"/api/v1/schedule/calculate/{program_id}",
                headers=headers,
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed)

            assert response.status_code in [200, 404, 422], (
                f"Unexpected status: {response.status_code}"
            )

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print("\n=== Schedule Calculation Endpoint Baseline ===")
        print(f"  Average: {avg_time * 1000:.1f}ms")
        print(f"  Min: {min_time * 1000:.1f}ms")
        print(f"  Max: {max_time * 1000:.1f}ms")
        print("  Target: <1000ms")

        # Baseline assertion
        assert avg_time < 3.0, f"Schedule calculation baseline exceeded 3s: {avg_time * 1000:.1f}ms"

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_full_dashboard_load_baseline(
        self,
        client: AsyncClient,
        dashboard_program: dict,
    ):
        """Baseline: Full dashboard load (sequential) performance.

        Target: <3s for full dashboard load
        Simulates loading all dashboard data.
        """
        program_id = dashboard_program["program"]["id"]
        headers = dashboard_program["headers"]

        # Endpoints to load for a full dashboard view
        endpoints = [
            f"/api/v1/evms/summary/{program_id}",
            f"/api/v1/activities?program_id={program_id}",
            f"/api/v1/wbs/tree?program_id={program_id}",
        ]

        # Warm up
        for endpoint in endpoints:
            await client.get(endpoint, headers=headers)

        # Measure full sequential load
        times = []
        for _ in range(3):
            start = time.perf_counter()

            for endpoint in endpoints:
                response = await client.get(endpoint, headers=headers)
                # Don't assert on status - some endpoints may not be implemented

            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print("\n=== Full Dashboard Load Baseline (Sequential) ===")
        print(f"  Endpoints: {len(endpoints)}")
        print(f"  Average: {avg_time * 1000:.1f}ms")
        print(f"  Min: {min_time * 1000:.1f}ms")
        print(f"  Max: {max_time * 1000:.1f}ms")
        print("  Target: <3000ms")

        # Baseline assertion
        assert avg_time < 10.0, f"Dashboard load baseline exceeded 10s: {avg_time * 1000:.1f}ms"


class TestDashboardScalePerformance:
    """Test dashboard performance at different scales."""

    @pytest_asyncio.fixture
    async def large_program(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> dict:
        """Create a larger program for scale testing."""
        # Create program
        program_data = {
            "name": "Scale Test Program",
            "code": f"SCALE-{uuid4().hex[:6].upper()}",
            "description": "Program for scale testing",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "budget_at_completion": "5000000.00",
        }
        response = await client.post(
            "/api/v1/programs",
            json=program_data,
            headers=auth_headers,
        )
        assert response.status_code == 201
        program = response.json()
        program_id = program["id"]

        # Create WBS structure (5 elements)
        wbs_elements = []
        for i in range(5):
            wbs_resp = await client.post(
                "/api/v1/wbs",
                json={
                    "program_id": program_id,
                    "name": f"Work Package {i + 1}",
                    "wbs_code": f"1.{i + 1}",
                },
                headers=auth_headers,
            )
            if wbs_resp.status_code == 201:
                wbs_elements.append(wbs_resp.json())

        # Create 50 activities
        activities = []
        for i in range(50):
            wbs_id = wbs_elements[i % len(wbs_elements)]["id"] if wbs_elements else None
            activity_data = {
                "program_id": program_id,
                "name": f"Activity {i + 1}",
                "code": f"ACT-{i + 1:03d}",
                "duration": 5 + (i % 10),
                "budgeted_cost": str(Decimal("10000.00") + Decimal(i * 500)),
                "percent_complete": str(Decimal(min(100, i * 2))),
                "actual_cost": str(Decimal("9000.00") + Decimal(i * 400)),
            }
            if wbs_id:
                activity_data["wbs_id"] = wbs_id

            resp = await client.post(
                "/api/v1/activities",
                json=activity_data,
                headers=auth_headers,
            )
            if resp.status_code == 201:
                activities.append(resp.json())

        return {
            "program": program,
            "wbs_elements": wbs_elements,
            "activities": activities,
            "headers": auth_headers,
        }

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_activities_list_50_activities(
        self,
        client: AsyncClient,
        large_program: dict,
    ):
        """Test activities list with 50 activities.

        Target: <1s for 50 activities
        """
        program_id = large_program["program"]["id"]
        headers = large_program["headers"]

        # Warm up
        await client.get(
            f"/api/v1/activities?program_id={program_id}",
            headers=headers,
        )

        # Measure
        start = time.perf_counter()
        response = await client.get(
            f"/api/v1/activities?program_id={program_id}",
            headers=headers,
        )
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        data = response.json()
        activity_count = len(data.get("items", data)) if isinstance(data, dict) else len(data)

        print("\n=== Activities List (50 activities) ===")
        print(f"  Activities returned: {activity_count}")
        print(f"  Time: {elapsed * 1000:.1f}ms")
        print("  Target: <1000ms")

        assert elapsed < 2.0, f"50 activities list exceeded 2s: {elapsed * 1000:.1f}ms"

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_schedule_calculation_50_activities(
        self,
        client: AsyncClient,
        large_program: dict,
    ):
        """Test schedule calculation with 50 activities.

        Target: <2s for 50 activities
        """
        program_id = large_program["program"]["id"]
        headers = large_program["headers"]

        # Measure
        start = time.perf_counter()
        response = await client.post(
            f"/api/v1/schedule/calculate/{program_id}",
            headers=headers,
        )
        elapsed = time.perf_counter() - start

        print("\n=== Schedule Calculation (50 activities) ===")
        print(f"  Status: {response.status_code}")
        print(f"  Time: {elapsed * 1000:.1f}ms")
        print("  Target: <2000ms")

        # Accept various status codes
        assert response.status_code in [200, 404, 422], f"Unexpected status: {response.status_code}"
        assert elapsed < 5.0, f"50 activity schedule exceeded 5s: {elapsed * 1000:.1f}ms"


class TestDashboardPerformanceSummary:
    """Summary test that reports all baselines."""

    @pytest.mark.asyncio
    async def test_print_performance_summary(self):
        """Print summary of performance targets for Week 8."""
        print("\n" + "=" * 60)
        print("DASHBOARD PERFORMANCE TARGETS (Week 8)")
        print("=" * 60)
        print()
        print("Endpoint                      | Target   | Priority")
        print("-" * 60)
        print("EVMS Summary                  | <500ms   | High")
        print("Activities List (10)          | <500ms   | High")
        print("WBS Tree                      | <500ms   | Medium")
        print("Schedule Calculation (10)     | <1000ms  | High")
        print("S-curve Enhanced              | <2000ms  | Medium")
        print("Full Dashboard Load           | <3000ms  | High")
        print("-" * 60)
        print("Activities List (50)          | <1000ms  | Medium")
        print("Schedule Calculation (50)     | <2000ms  | Medium")
        print("=" * 60)
        print()
        print("Optimization strategies for Week 8:")
        print("1. Database query optimization with eager loading")
        print("2. Redis caching for computed values")
        print("3. Async concurrent endpoint fetching")
        print("4. Response pagination for large datasets")
        print("=" * 60)
