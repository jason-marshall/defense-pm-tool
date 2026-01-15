# Increase Test Coverage to Target Percentage

Analyze the current test coverage, identify gaps, write tests to increase coverage to the target percentage, and fix any bugs discovered during testing.

**Target Coverage: $ARGUMENTS** (e.g., "80" for 80%)

If no target specified, default to 80%.

---

## Phase 1: Assess Current Coverage State

### Step 1.1: Run Coverage Analysis

```bash
cd api

# Generate detailed coverage report
pytest --cov=src --cov-report=term-missing --cov-report=html --cov-report=json -q

# Display summary
echo ""
echo "=== COVERAGE SUMMARY ==="
python -c "
import json
with open('coverage.json', 'r') as f:
    data = json.load(f)
    total = data['totals']['percent_covered']
    print(f'Current Coverage: {total:.1f}%')
    print(f'Target Coverage: \$TARGET%')
    print(f'Gap: {max(0, \$TARGET - total):.1f}%')
"
```

### Step 1.2: Identify Lowest Coverage Files

```bash
cd api

# List files by coverage (lowest first)
python -c "
import json
with open('coverage.json', 'r') as f:
    data = json.load(f)
    files = []
    for filepath, info in data['files'].items():
        if 'src/' in filepath and '__pycache__' not in filepath:
            pct = info['summary']['percent_covered']
            missing = info['summary']['missing_lines']
            files.append((filepath, pct, missing))
    
    files.sort(key=lambda x: x[1])
    print('Files needing coverage (sorted by coverage %):')
    print('-' * 70)
    for f, pct, missing in files[:15]:
        short_path = f.replace('/home/claude/api/', '')
        print(f'{pct:5.1f}%  ({missing:3d} lines missing)  {short_path}')
"
```

### Step 1.3: Identify Untested Functions

```bash
cd api

# Find functions/methods with no coverage
grep -n "def " src/**/*.py 2>/dev/null | head -50

# Check which lines are missing coverage (from HTML report)
echo ""
echo "Open htmlcov/index.html in browser for detailed line-by-line coverage"
```

---

## Phase 2: Prioritize Test Writing

Based on coverage analysis, prioritize in this order:

### Priority 1: Core Business Logic (MUST have 90%+ coverage)
- `src/services/cpm.py` - Critical Path calculations
- `src/services/evms.py` - Earned Value calculations
- `src/core/auth.py` - Authentication logic

### Priority 2: API Endpoints (MUST have 80%+ coverage)
- `src/api/v1/endpoints/*.py` - All route handlers

### Priority 3: Repositories (Should have 75%+ coverage)
- `src/repositories/*.py` - Data access layer

### Priority 4: Models & Schemas (Should have 70%+ coverage)
- `src/models/*.py` - SQLAlchemy models
- `src/schemas/*.py` - Pydantic schemas

### Priority 5: Utilities & Config (Can be lower)
- `src/core/config.py`
- `src/core/database.py`

---

## Phase 3: Write Missing Tests

For each file needing coverage, follow this pattern:

### Step 3.1: Analyze Missing Lines

```bash
cd api

# For a specific file, see what's not covered
pytest --cov=src/path/to/file.py --cov-report=term-missing tests/ -q

# Or view in HTML report
# Lines in RED need tests
```

### Step 3.2: Write Unit Tests for Uncovered Code

For each uncovered function, create tests following this template:

```python
# api/tests/unit/test_<module>.py
"""Unit tests for <module> - Coverage improvement."""

import pytest
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

# Import the module being tested
from src.<module> import <functions_to_test>


class Test<FunctionName>:
    """Tests for <function_name>."""

    def test_happy_path(self):
        """Should return expected result with valid input."""
        # Arrange
        input_data = ...
        expected = ...
        
        # Act
        result = function_under_test(input_data)
        
        # Assert
        assert result == expected

    def test_edge_case_empty_input(self):
        """Should handle empty input gracefully."""
        result = function_under_test([])
        assert result == expected_for_empty

    def test_edge_case_none_input(self):
        """Should handle None input."""
        with pytest.raises(ValueError):
            function_under_test(None)

    def test_boundary_condition(self):
        """Should handle boundary values correctly."""
        # Test min/max values, zero, negative numbers, etc.
        pass

    @pytest.mark.parametrize("input_val,expected", [
        (1, "one"),
        (2, "two"),
        (0, "zero"),
        (-1, "negative"),
    ])
    def test_multiple_inputs(self, input_val, expected):
        """Should handle various inputs correctly."""
        result = function_under_test(input_val)
        assert result == expected
```

### Step 3.3: Write Integration Tests for Uncovered Endpoints

```python
# api/tests/integration/test_<feature>_api.py
"""Integration tests for <feature> API - Coverage improvement."""

import pytest
from httpx import AsyncClient
from uuid import uuid4

pytestmark = pytest.mark.asyncio


class Test<Feature>APICoverage:
    """Additional tests to improve <feature> API coverage."""

    async def test_endpoint_with_invalid_uuid(self, client: AsyncClient, auth_headers: dict):
        """Should return 422 for invalid UUID format."""
        response = await client.get(
            "/api/v1/<resource>/not-a-uuid",
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_endpoint_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent resource."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/<resource>/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_endpoint_unauthorized(self, client: AsyncClient):
        """Should return 401 without auth token."""
        response = await client.get("/api/v1/<resource>")
        assert response.status_code == 401

    async def test_endpoint_forbidden(self, client: AsyncClient, other_user_headers: dict):
        """Should return 403 when accessing another user's resource."""
        response = await client.get(
            "/api/v1/<resource>/<other_users_resource_id>",
            headers=other_user_headers,
        )
        assert response.status_code == 403

    async def test_endpoint_validation_error(self, client: AsyncClient, auth_headers: dict):
        """Should return 422 for invalid request body."""
        response = await client.post(
            "/api/v1/<resource>",
            headers=auth_headers,
            json={"invalid_field": "value"},  # Missing required fields
        )
        assert response.status_code == 422

    async def test_endpoint_duplicate_conflict(self, client: AsyncClient, auth_headers: dict):
        """Should return 409 for duplicate resource."""
        # Create first
        await client.post("/api/v1/<resource>", headers=auth_headers, json={...})
        # Try duplicate
        response = await client.post("/api/v1/<resource>", headers=auth_headers, json={...})
        assert response.status_code == 409
```

---

## Phase 4: Fix Discovered Bugs

During test writing, you may discover bugs. Handle them as follows:

### Step 4.1: Document the Bug

```python
def test_bug_discovered_<description>(self):
    """
    BUG DISCOVERED: <description of the bug>
    
    Expected: <what should happen>
    Actual: <what currently happens>
    
    This test will fail until the bug is fixed.
    """
    # Test that exposes the bug
    result = buggy_function(input)
    assert result == expected  # Currently fails
```

### Step 4.2: Fix the Bug

1. Ensure the test fails (confirms bug exists)
2. Fix the code
3. Ensure the test passes
4. Run full test suite to check for regressions

### Step 4.3: Commit Bug Fix Separately

```bash
git add src/path/to/fixed_file.py tests/path/to/test.py
git commit -m "fix(<scope>): <description of bug fix>

Bug: <what was wrong>
Cause: <root cause>
Fix: <what was changed>

Added regression test to prevent recurrence."
```

---

## Phase 5: Iterate Until Target Reached

### Step 5.1: Re-run Coverage After Each Batch

```bash
cd api

# Quick coverage check
pytest --cov=src --cov-fail-under=$TARGET -q

# If it passes, you've reached the target!
# If it fails, continue writing tests
```

### Step 5.2: Focus on High-Impact Files

Calculate impact per test:

```bash
cd api

python -c "
import json
with open('coverage.json', 'r') as f:
    data = json.load(f)
    total_statements = data['totals']['num_statements']
    target = $TARGET
    current = data['totals']['percent_covered']
    
    needed_lines = int((target - current) * total_statements / 100)
    print(f'Need to cover approximately {needed_lines} more lines')
    print('')
    print('Best files to target (most missing lines):')
    
    files = []
    for filepath, info in data['files'].items():
        if 'src/' in filepath:
            missing = info['summary']['missing_lines']
            if missing > 0:
                files.append((filepath, missing))
    
    files.sort(key=lambda x: -x[1])
    for f, missing in files[:10]:
        print(f'  {missing:3d} lines: {f.split(\"src/\")[-1]}')
"
```

### Step 5.3: Verify No Regressions

```bash
cd api

# Full test suite
pytest -v

# All tests must pass before considering coverage target met
```

---

## Phase 6: Final Verification & Commit

### Step 6.1: Final Coverage Check

```bash
cd api

# Generate final report
pytest --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=$TARGET

echo ""
echo "=== FINAL COVERAGE ==="
pytest --cov=src --cov-report=term -q 2>/dev/null | tail -5
```

### Step 6.2: Run Full Verification Ladder

```bash
cd api

# Lint
ruff check src tests --fix
ruff format src tests

# Type check
mypy src --ignore-missing-imports

# All tests
pytest -v

# Coverage gate
pytest --cov=src --cov-fail-under=$TARGET -q
```

### Step 6.3: Commit Coverage Improvements

```bash
git add tests/
git commit -m "test: increase coverage to $TARGET%

Coverage improvements:
- Added unit tests for <modules>
- Added integration tests for <endpoints>
- Added edge case tests for <functions>

Previous coverage: <X>%
New coverage: $TARGET%"
```

### Step 6.4: If Bugs Were Fixed, Create Separate Commits

Ensure bug fixes are in separate commits from test additions for clean git history.

---

## Common Coverage Gaps to Check

### 1. Exception Handlers
```python
# Often untested - add tests that trigger exceptions
try:
    risky_operation()
except SpecificError:
    handle_error()  # <- This branch needs a test
```

### 2. Conditional Branches
```python
# Both branches need tests
if condition:
    do_something()  # <- Test with condition=True
else:
    do_other()      # <- Test with condition=False
```

### 3. Early Returns
```python
def function(data):
    if not data:
        return None  # <- Test with empty/None input
    # ... rest of function
```

### 4. Default Parameters
```python
def function(param=default_value):
    # Test with explicit param AND with default
```

### 5. Error Response Codes
```python
# Test all HTTP status codes your endpoints can return
# 200, 201, 204, 400, 401, 403, 404, 409, 422, 500
```

---

## Quick Commands Reference

```bash
# Current coverage
pytest --cov=src -q

# Coverage for specific file
pytest --cov=src/services/cpm.py --cov-report=term-missing -q

# Run tests for specific module
pytest tests/unit/test_cpm.py -v

# Run with coverage threshold (fails if below)
pytest --cov=src --cov-fail-under=80

# Generate HTML report
pytest --cov=src --cov-report=html
# Then open htmlcov/index.html

# See uncovered lines for a file
pytest --cov=src/module.py --cov-report=term-missing tests/
```

---

## Expected Outcome

After completing this prompt:

1. ✅ Test coverage meets or exceeds target percentage
2. ✅ All critical business logic has 90%+ coverage
3. ✅ All API endpoints have 80%+ coverage
4. ✅ Any discovered bugs are fixed with regression tests
5. ✅ All tests pass
6. ✅ Verification ladder passes (lint, types, tests)
7. ✅ Clean commits with descriptive messages
