Implement feature using Test-Driven Development: $ARGUMENTS

Follow this workflow strictly. Do NOT skip any phase.

## Phase 1: Research & Plan (NO CODE YET)

1. **Read the relevant files** to understand:
   - Existing patterns and conventions in the codebase
   - Related functionality that might be affected
   - Data models and schemas involved
   - Current test coverage

2. **Identify affected components**:
   ```bash
   # Search for related code
   grep -r "relevant_term" api/src/
   grep -r "relevant_term" api/tests/
   ```

3. **Create implementation plan** including:
   - What tests need to be written (unit + integration)
   - What files will be created or modified
   - Database migration requirements
   - API endpoint changes
   - Schema updates needed

4. **Show the plan and wait for approval** before writing any code.

## Phase 2: Write Failing Tests First (RED)

5. **Create unit test file** (if new feature):
   ```python
   # api/tests/unit/test_<feature>.py
   """Unit tests for <feature>."""
   
   import pytest
   from uuid import uuid4
   
   
   class Test<Feature>:
       """Tests for <feature> functionality."""
       
       def test_<happy_path>(self):
           """Should <expected behavior>."""
           # Arrange
           <setup>
           
           # Act
           result = <action>
           
           # Assert
           assert result == <expected>
       
       def test_<edge_case>(self):
           """Should handle <edge case>."""
           pass
       
       def test_<error_case>(self):
           """Should raise <error> when <condition>."""
           with pytest.raises(ExpectedError):
               <action that fails>
   ```

6. **Create integration test file** (if API endpoint):
   ```python
   # api/tests/integration/test_<feature>_api.py
   """Integration tests for <feature> API."""
   
   import pytest
   from httpx import AsyncClient
   
   pytestmark = pytest.mark.asyncio
   
   
   class Test<Feature>API:
       """Integration tests for /api/v1/<feature> endpoints."""
       
       async def test_endpoint_requires_auth(self, client: AsyncClient):
           """Should return 401 without authentication."""
           response = await client.get("/api/v1/<endpoint>")
           assert response.status_code == 401
       
       async def test_endpoint_success(self, client: AsyncClient, auth_headers: dict):
           """Should return expected data."""
           response = await client.get("/api/v1/<endpoint>", headers=auth_headers)
           assert response.status_code == 200
   ```

7. **Run tests to confirm they fail**:
   ```bash
   cd api
   pytest tests/unit/test_<feature>.py -v
   pytest tests/integration/test_<feature>_api.py -v
   ```

8. **Commit tests only**:
   ```bash
   git add tests/
   git commit -m "test(<scope>): add tests for <feature>"
   ```

## Phase 3: Implement Minimum Code (GREEN)

9. **Create/update models** (if needed):
   - Add fields to existing models
   - Create new models following Base pattern
   - Add relationships and indexes

10. **Create/update schemas** (if needed):
    - Create request schemas
    - Response schemas
    - Update existing schemas

11. **Create/update repository** (if needed):
    - Add query methods
    - Follow BaseRepository pattern

12. **Create/update endpoints** (if needed):
    - Add route handlers
    - Include authentication
    - Add to router

13. **Create migration** (if database changes):
    ```bash
    alembic revision --autogenerate -m "<description>"
    alembic upgrade head
    ```

14. **Run tests to confirm they pass**:
    ```bash
    pytest tests/unit/test_<feature>.py -v
    pytest tests/integration/test_<feature>_api.py -v
    ```

## Phase 4: Refactor & Polish

15. **Improve code quality**:
    - Add/improve docstrings
    - Remove duplication
    - Ensure consistent naming
    - Add type hints if missing

16. **Run full verification ladder**:
    ```bash
    # Static analysis
    ruff check src tests --fix
    ruff format src tests
    
    # Type checking
    mypy src --ignore-missing-imports
    
    # All tests
    pytest -v
    
    # Coverage
    pytest --cov=src --cov-report=term-missing
    ```

## Phase 5: Document & Commit

17. **Update documentation** (if needed):
    - Update docs/api.md for new endpoints
    - Update README if user-facing changes
    - Add inline comments for complex logic

18. **Create final commit**:
    ```bash
    git add .
    git commit -m "feat(<scope>): implement <feature>
    
    - Add <component 1>
    - Add <component 2>
    - Update <component 3>
    
    Closes #<issue_number>"
    ```

19. **Push and create PR**:
    ```bash
    git push -u origin feature/<feature-name>
    ```
    
    Then create PR with template from `.github/PULL_REQUEST_TEMPLATE.md`

## Important Rules

- **NEVER skip writing tests first** - this is non-negotiable
- **NEVER modify tests to make them pass** - modify implementation instead
- **NEVER commit without running verification ladder**
- **ALWAYS ask clarifying questions** if requirements are unclear
- **ALWAYS explain reasoning** at each major step
- If you encounter unexpected issues, **explain them before proceeding**

## Verification Checklist

Before marking complete:
- [ ] All new code has type hints
- [ ] All public functions have docstrings
- [ ] All tests pass
- [ ] Coverage meets targets (80%+ for new code)
- [ ] No hardcoded values
- [ ] No TODO comments (create issues instead)
- [ ] ruff check passes
- [ ] mypy passes
- [ ] Documentation updated
