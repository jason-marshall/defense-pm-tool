Fix the bug: $ARGUMENTS

Follow this systematic debugging workflow. Do NOT skip any phase.

## Phase 1: Understand the Bug

1. **Read the bug report carefully**:
   - What is the expected behavior?
   - What is the actual behavior?
   - What are the steps to reproduce?
   - What error messages are shown?

2. **Gather context**:
   ```bash
   # Search for related code
   grep -r "relevant_term" api/src/
   
   # Check git history for recent changes
   git log --oneline -20 -- api/src/<relevant_path>
   
   # Check if there are existing tests
   grep -r "test.*relevant" api/tests/
   ```

3. **Reproduce the bug** (if possible):
   ```bash
   # Start the API server
   cd api && uvicorn src.main:app --reload
   
   # Make the request that triggers the bug
   curl -X GET "http://localhost:8000/api/v1/<endpoint>"
   
   # Or run specific test
   pytest tests/<path>::<test> -v
   ```

4. **Explain your understanding** of the bug before proceeding:
   - What component is affected?
   - What is the root cause hypothesis?
   - What is the fix approach?

## Phase 2: Write a Failing Test (REQUIRED)

5. **Create a regression test** that reproduces the bug:
   ```python
   # api/tests/unit/test_<module>.py or api/tests/integration/test_<feature>.py
   
   def test_bug_<issue_number>_<brief_description>(self):
       """
       Regression test for bug #<issue_number>: <description>.
       
       Bug: <What was happening>
       Fix: <What should happen>
       """
       # Arrange - Setup that triggers the bug
       <setup_code>
       
       # Act - The action that was failing
       result = <code_that_had_bug>
       
       # Assert - What the correct behavior should be
       assert result == <expected_correct_value>
   ```

6. **Run the test to confirm it fails**:
   ```bash
   pytest tests/<path>::test_bug_<issue_number>_<description> -v
   ```
   
   The test MUST fail before you fix the bug. This proves:
   - The test actually catches the bug
   - Your fix will be verified

7. **If the test passes unexpectedly**:
   - The bug may already be fixed
   - The test doesn't capture the bug correctly
   - Investigate further before proceeding

## Phase 3: Fix the Bug

8. **Make the minimal change** to fix the bug:
   - Do NOT refactor unrelated code
   - Do NOT add features
   - Do NOT "improve" other parts
   - ONLY fix the specific bug

9. **Common fix patterns**:
   ```python
   # Off-by-one error
   for i in range(len(items)):  # Bug: should be range(len(items) - 1)
   
   # None check missing
   return value.attribute  # Bug: value could be None
   # Fix: return value.attribute if value else None
   
   # Wrong comparison
   if value == other:  # Bug: should use 'is' for None/bool
   
   # Async issue
   result = func()  # Bug: missing await
   # Fix: result = await func()
   
   # Type coercion
   if value:  # Bug: empty string/0 treated as False
   # Fix: if value is not None:
   ```

10. **Run the regression test** to confirm it passes:
    ```bash
    pytest tests/<path>::test_bug_<issue_number>_<description> -v
    ```

## Phase 4: Verify No Regressions

11. **Run all related tests**:
    ```bash
    # Run tests for the affected module
    pytest tests/unit/test_<module>.py -v
    pytest tests/integration/test_<feature>.py -v
    ```

12. **Run the full test suite**:
    ```bash
    pytest -v
    ```

13. **Run the verification ladder**:
    ```bash
    # Static analysis
    ruff check src tests --fix
    ruff format src tests
    
    # Type checking
    mypy src --ignore-missing-imports
    
    # All tests with coverage
    pytest --cov=src --cov-report=term-missing
    ```

## Phase 5: Document the Fix

14. **Add a comment** if the fix is non-obvious:
    ```python
    # Fix for bug #123: Handle edge case where X is None
    # See: https://github.com/org/repo/issues/123
    if x is None:
        return default_value
    ```

15. **Update tests** if the bug revealed a gap in coverage

16. **Prepare commit message**:
    ```bash
    git add .
    git commit -m "fix(<scope>): <brief description>

    Bug: <What was the bug?>
    Cause: <What caused it?>
    Fix: <How was it fixed?>

    Adds regression test to prevent recurrence.

    Fixes #<issue_number>"
    ```

17. **Push and create PR**:
    ```bash
    git push -u origin bugfix/<issue>-<description>
    ```

## Important Rules

- **ALWAYS write a regression test** before fixing
- **NEVER skip the test step** - it proves the fix works
- **KEEP the fix minimal** - don't add features or refactor
- **EXPLAIN your reasoning** at each step
- If the root cause is unclear, **investigate further** before fixing
- If fixing reveals a larger issue, **create a new issue** for it

## Verification Checklist

Before marking complete:
- [ ] Bug is understood and documented
- [ ] Regression test written and initially fails
- [ ] Fix is minimal and targeted
- [ ] Regression test now passes
- [ ] All existing tests still pass
- [ ] ruff check passes
- [ ] mypy passes
- [ ] Commit message follows format
- [ ] PR created with bug description

## Quick Debug Commands

```bash
# Check recent changes to a file
git log --oneline -10 -- <file>
git diff HEAD~5 -- <file>

# Find where a function is defined
grep -rn "def function_name" api/src/

# Find where a function is called
grep -rn "function_name(" api/src/

# Check Python path issues
python -c "import sys; print('\n'.join(sys.path))"

# Check database state
docker exec defense-pm-tool-postgres psql -U dev_user -d defense_pm_dev -c "SELECT * FROM <table> LIMIT 5"

# Check logs
docker-compose logs -f api
```
