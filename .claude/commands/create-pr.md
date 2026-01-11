Create a pull request for: $ARGUMENTS

Follow this workflow to prepare and create a high-quality pull request.

## Phase 1: Pre-PR Verification

1. **Ensure all changes are committed**:
   ```bash
   git status
   # Should show "nothing to commit, working tree clean"
   ```

2. **Run the full verification ladder**:
   ```bash
   cd api
   
   # Static analysis
   ruff check src tests --fix
   ruff format src tests
   
   # Type checking
   mypy src --ignore-missing-imports
   
   # Unit tests
   pytest tests/unit -v
   
   # Integration tests
   pytest tests/integration -v
   
   # Coverage check
   pytest --cov=src --cov-report=term-missing --cov-fail-under=60
   ```

3. **Fix any issues** before proceeding. Do NOT create a PR with failing checks.

## Phase 2: Review Your Changes

4. **List all changed files**:
   ```bash
   git diff main..HEAD --name-only
   ```

5. **Review the diff**:
   ```bash
   git diff main..HEAD
   ```

6. **Check for common issues**:
   ```bash
   # No print statements
   grep -rn "print(" api/src/ --include="*.py"
   
   # No hardcoded secrets
   grep -rn "password\|secret\|api_key" api/src/ --include="*.py"
   
   # No TODO/FIXME (should be issues)
   grep -rn "TODO\|FIXME" api/src/ --include="*.py"
   
   # No commented-out code
   grep -rn "^#.*def \|^#.*class " api/src/ --include="*.py"
   ```

## Phase 3: Prepare PR Description

7. **Gather information for PR**:

   **Type of Change** (check one):
   - [ ] 🐛 Bug fix (non-breaking change fixing an issue)
   - [ ] ✨ New feature (non-breaking change adding functionality)
   - [ ] 💥 Breaking change (fix or feature causing existing functionality to change)
   - [ ] 📝 Documentation update
   - [ ] ♻️ Refactoring (no functional changes)
   - [ ] 🧪 Test update

   **Changes Made**:
   - List each significant change
   - Reference files modified
   - Explain why changes were made

   **Testing Done**:
   - List tests added/modified
   - Note manual testing performed

## Phase 4: Create the PR

8. **Push to remote**:
   ```bash
   git push -u origin <branch-name>
   ```

9. **Create PR using GitHub CLI** (if available):
   ```bash
   gh pr create --title "<type>(<scope>): <description>" \
     --body-file .github/PULL_REQUEST_TEMPLATE.md \
     --base main
   ```

   Or **create PR via GitHub web**:
   - Go to: https://github.com/<org>/<repo>/compare/<branch>
   - Fill in the PR template

## Phase 5: PR Template Content

Fill in this template for the PR description:

```markdown
## Description
<!-- Brief description of changes and why they're needed -->
<description>

## Type of Change
<!-- Check the relevant option -->
- [ ] 🐛 Bug fix (non-breaking change fixing an issue)
- [ ] ✨ New feature (non-breaking change adding functionality)
- [ ] 💥 Breaking change (fix or feature causing existing functionality to change)
- [ ] 📝 Documentation update
- [ ] ♻️ Refactoring (no functional changes)
- [ ] 🧪 Test update

## Related Issues
<!-- Link to related issues -->
Closes #<issue_number>

## Changes Made
<!-- List the specific changes made -->
- <change 1>
- <change 2>
- <change 3>

## Testing
<!-- Describe how this was tested -->

### Tests Added/Modified
- `tests/unit/test_<module>.py::test_<name>` - <what it tests>
- `tests/integration/test_<feature>.py::test_<name>` - <what it tests>

### Test Commands Run
```bash
pytest tests/unit/test_<module>.py -v
pytest tests/integration/test_<feature>.py -v
pytest --cov=src/<module> --cov-report=term-missing
```

### Manual Testing
- [ ] <manual test 1>
- [ ] <manual test 2>

## Verification Checklist

### Code Quality
- [ ] `ruff check src tests` passes with no errors
- [ ] `mypy src` passes with no errors
- [ ] Code follows project style guide (see CLAUDE.md)
- [ ] No hardcoded values (use constants/config)
- [ ] No commented-out code
- [ ] No TODO comments (create issues instead)

### Testing
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Coverage meets project targets (60%+ overall, 80%+ for new code)

### Documentation
- [ ] Docstrings added for public functions/classes
- [ ] README updated (if needed)
- [ ] API documentation updated (if endpoints changed)

### Security
- [ ] No secrets or credentials committed
- [ ] Input validation in place for user data
- [ ] Error messages don't leak sensitive info

## Database Changes
<!-- Does this require migrations? -->
- [ ] No database changes
- [ ] Migration added and tested
- [ ] Migration is reversible (downgrade works)

## Screenshots (if applicable)
<!-- Add screenshots for UI changes -->

## Notes for Reviewers
<!-- Point out specific areas that need careful review -->
<notes>
```

## Phase 6: Post-PR Actions

10. **Monitor CI/CD**:
    - Watch for automated checks to complete
    - Fix any failures immediately

11. **Respond to review feedback**:
    - Address all comments
    - Make requested changes
    - Re-request review when ready

12. **Merge when approved**:
    ```bash
    # If using squash merge
    gh pr merge --squash
    
    # Or via GitHub web interface
    ```

13. **Clean up**:
    ```bash
    # Switch back to main
    git checkout main
    git pull
    
    # Delete local branch
    git branch -d <branch-name>
    ```

---

## Quick PR Checklist

Before creating PR:
- [ ] All verification ladder checks pass
- [ ] No print statements or debug code
- [ ] No hardcoded secrets or credentials
- [ ] No TODO/FIXME comments
- [ ] All new code has tests
- [ ] All new functions have docstrings
- [ ] Commit messages follow convention
- [ ] Branch is up to date with main

---

## Commit Message Reference

```
feat(scope): add new feature
fix(scope): fix bug description
refactor(scope): refactor code
test(scope): add/update tests
docs(scope): update documentation
chore(scope): maintenance task
perf(scope): performance improvement
```

**Scopes**: `cpm`, `evms`, `auth`, `api`, `models`, `schemas`, `frontend`, `deps`, `config`
