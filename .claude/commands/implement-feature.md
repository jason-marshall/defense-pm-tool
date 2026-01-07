Implement feature using Test-Driven Development: $ARGUMENTS

Follow this workflow strictly:

## Phase 1: Research & Plan (DO NOT WRITE CODE YET)

1. **Read the relevant files** in the codebase to understand:
   - Existing patterns and conventions
   - Related functionality
   - Data models involved

2. **Create a plan** with:
   - What tests need to be written
   - What code changes are needed
   - What files will be modified or created

3. **Show the plan** and wait for approval before proceeding.

## Phase 2: Write Failing Tests First (RED)

4. **Write test cases** for the feature including:
   - Happy path tests
   - Edge cases (empty input, invalid data, boundary conditions)
   - Error conditions

5. **Run the tests** to confirm they fail:
   ```bash
   pytest tests/unit/test_<module>.py -v
   ```

6. **Commit the tests** (if requested):
   ```bash
   git add tests/
   git commit -m "test(<scope>): add tests for <feature>"
   ```

## Phase 3: Implement Minimum Code (GREEN)

7. **Write the minimum code** to make tests pass
   - Do NOT over-engineer
   - Focus only on passing the current tests

8. **Run tests** to confirm they pass:
   ```bash
   pytest tests/unit/test_<module>.py -v
   ```

9. **Run type checking and linting**:
   ```bash
   ruff check src tests
   mypy src
   ```

## Phase 4: Refactor

10. **Refactor** the implementation:
    - Improve code clarity
    - Remove duplication
    - Add docstrings
    - Ensure consistent naming

11. **Run all tests again** to ensure nothing broke:
    ```bash
    pytest -v
    ```

## Phase 5: Verify

12. **Run the verification ladder**:
    - [ ] `ruff check` passes
    - [ ] `mypy` passes  
    - [ ] All tests pass
    - [ ] Coverage meets targets
    - [ ] No hardcoded values
    - [ ] Docstrings on public functions

13. **Commit the implementation**:
    ```bash
    git add .
    git commit -m "feat(<scope>): implement <feature>"
    ```

## Important Rules

- NEVER skip writing tests first
- NEVER write implementation before tests fail
- NEVER modify tests to make them pass (modify implementation instead)
- Ask clarifying questions if the feature requirements are unclear
- If you encounter unexpected issues, explain them before proceeding
