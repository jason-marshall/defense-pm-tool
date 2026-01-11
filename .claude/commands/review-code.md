Review the code changes for: $ARGUMENTS

Perform a thorough code review covering all areas below.

## 1. Identify Changed Files

```bash
# If reviewing a branch
git diff main..HEAD --name-only

# If reviewing recent commits
git diff HEAD~3 --name-only

# If reviewing specific files
git diff HEAD -- <file1> <file2>
```

## 2. Correctness Review

### Logic
- [ ] Does the code do what it's supposed to do?
- [ ] Are there any logic errors or off-by-one mistakes?
- [ ] Are all code paths reachable and tested?
- [ ] Are edge cases handled properly?

### Common Issues to Check
```python
# 1. None checks
value.attribute  # Could value be None?

# 2. Empty collection checks
items[0]  # Could items be empty?

# 3. Async/await
result = async_func()  # Missing await?

# 4. Type mismatches
str_value + int_value  # Type error?

# 5. Resource cleanup
file = open(...)  # Using context manager?

# 6. Exception handling
except Exception:  # Too broad? Swallowing errors?
```

## 3. Code Quality Review

### Readability
- [ ] Are variable/function names descriptive and consistent?
- [ ] Is the code self-documenting?
- [ ] Are there unnecessary comments that just repeat the code?
- [ ] Is there dead code or commented-out code?

### Complexity
- [ ] Are functions too long (>50 lines)?
- [ ] Is there deep nesting (>3 levels)?
- [ ] Are there complex conditionals that could be simplified?
- [ ] Is there code duplication that should be extracted?

### Code Smells
- [ ] Magic numbers/strings (should be constants)
- [ ] God objects (classes doing too much)
- [ ] Feature envy (accessing other object's data excessively)
- [ ] Long parameter lists (>5 parameters)

## 4. Testing Review

### Coverage
- [ ] Are there sufficient unit tests for new code?
- [ ] Are edge cases tested?
- [ ] Are error conditions tested?
- [ ] Do integration tests cover the API endpoints?

### Test Quality
- [ ] Do tests follow AAA pattern (Arrange, Act, Assert)?
- [ ] Are test names descriptive?
- [ ] Are tests independent (no shared state)?
- [ ] Could any tests be flaky (timing, external deps)?

### Run Tests
```bash
# Run tests for changed files
pytest tests/unit/test_<changed_module>.py -v
pytest tests/integration/test_<changed_feature>.py -v

# Check coverage
pytest --cov=src/<changed_module> --cov-report=term-missing
```

## 5. Type Safety Review

### Run Type Checker
```bash
mypy src --ignore-missing-imports
```

### Check for Issues
- [ ] All function parameters have type hints
- [ ] All return types are specified
- [ ] Optional types properly handled (Optional[T] or T | None)
- [ ] Generic types used correctly (list[T], dict[K, V])

## 6. Style & Conventions Review

### Run Linting
```bash
ruff check src tests
ruff format src tests --check
```

### Project Conventions (from CLAUDE.md)
- [ ] Import order correct (stdlib, third-party, local)?
- [ ] Docstrings on all public functions/classes?
- [ ] Naming conventions followed?
- [ ] Line length <= 100 characters?
- [ ] Double quotes for strings?

## 7. Security Review

### Input Validation
- [ ] Is all user input validated?
- [ ] Are Pydantic models used for request validation?
- [ ] Are file uploads sanitized?

### Authentication & Authorization
- [ ] Do protected endpoints require authentication?
- [ ] Are authorization checks in place?
- [ ] Are sensitive operations logged?

### Data Safety
- [ ] No secrets or credentials in code?
- [ ] Error messages don't leak sensitive info?
- [ ] SQL injection prevented (using ORM)?
- [ ] XSS prevented (output escaping)?

## 8. Performance Review

### Database
- [ ] Are there N+1 query issues?
- [ ] Are appropriate indexes in place?
- [ ] Are queries using select_related/joinedload?
- [ ] Are large result sets paginated?

### Computation
- [ ] Any O(n²) or worse algorithms that could be optimized?
- [ ] Are expensive operations cached?
- [ ] Are async operations used for I/O?

## 9. Documentation Review

### Code Documentation
- [ ] Are public functions documented?
- [ ] Is the documentation accurate?
- [ ] Would a new developer understand this code?

### External Documentation
- [ ] Is docs/api.md updated for new endpoints?
- [ ] Is README updated if needed?
- [ ] Are there any architectural changes that need docs?

## 10. Database Migration Review (if applicable)

```bash
# Check migration file
cat api/alembic/versions/<migration>.py

# Verify migration
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

- [ ] Migration is reversible (downgrade works)?
- [ ] No data loss in migration?
- [ ] Indexes added for frequently queried columns?

---

## Output Format

### Summary
Brief overall assessment (1-2 sentences)

### Critical Issues 🚨
**Must be fixed before merge:**
1. Issue description + file:line + suggested fix
2. ...

### Suggestions 💡
**Recommended improvements:**
1. Suggestion + reasoning
2. ...

### Minor Notes 📝
**Optional improvements:**
1. Note
2. ...

### Positive Feedback ✅
**What was done well:**
1. Good practice observed
2. ...

### Verification Status
```
[ ] ruff check passes
[ ] mypy passes
[ ] All tests pass
[ ] Coverage meets targets
[ ] Documentation updated
```

---

## Quick Review Commands

```bash
# View diff with context
git diff main..HEAD

# View specific file changes
git diff main..HEAD -- api/src/<file>

# Check for large files
git diff --stat main..HEAD

# Find TODO/FIXME
grep -rn "TODO\|FIXME" api/src/

# Find print statements (shouldn't be committed)
grep -rn "print(" api/src/

# Find hardcoded values
grep -rn "localhost\|127.0.0.1\|password" api/src/
```
