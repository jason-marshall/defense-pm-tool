Fix the bug: $ARGUMENTS

Follow this systematic debugging workflow:

## Phase 1: Understand the Bug

1. **Read the bug report/description** carefully
2. **Reproduce the bug** if possible:
   - What are the exact steps to reproduce?
   - What is the expected behavior?
   - What is the actual behavior?

3. **Locate relevant code** by searching the codebase:
   ```bash
   grep -r "relevant_term" src/
   ```

4. **Explain your understanding** of the bug before proceeding.

## Phase 2: Write a Failing Test

5. **Write a test that reproduces the bug**:
   ```python
   def test_bug_description():
       """Regression test for bug: <description>."""
       # Arrange
       <setup that triggers the bug>
       
       # Act
       result = <code that has the bug>
       
       # Assert
       assert result == <expected_correct_behavior>
   ```

6. **Run the test to confirm it fails**:
   ```bash
   pytest tests/unit/test_<module>.py::test_bug_description -v
   ```

## Phase 3: Fix the Bug

7. **Make the minimal change** to fix the bug
   - Don't refactor unrelated code
   - Don't add features
   - Just fix the bug

8. **Run the new test** to confirm it passes:
   ```bash
   pytest tests/unit/test_<module>.py::test_bug_description -v
   ```

9. **Run all related tests** to ensure no regressions:
   ```bash
   pytest tests/ -v
   ```

## Phase 4: Verify the Fix

10. **Run the full verification ladder**:
    ```bash
    ruff check src tests
    mypy src
    pytest -v
    ```

11. **Manually verify** the fix works as expected (if applicable)

## Phase 5: Document

12. **Add a comment** in the code if the fix is non-obvious:
    ```python
    # Fix for bug #123: Handle edge case where X is None
    ```

13. **Prepare commit message**:
    ```
    fix(<scope>): <brief description>
    
    <What was the bug?>
    <What caused it?>
    <How was it fixed?>
    
    Fixes #<issue_number>
    ```

## Important Rules

- ALWAYS write a regression test before fixing
- NEVER skip the test step
- Keep the fix minimal and focused
- Explain your reasoning at each step
- If the root cause is unclear, investigate further before fixing
