# Lint Codebase and Create Pull Request

Run a comprehensive lint pass on the entire codebase, fix all errors and warnings, and create a pull request with the changes.

## Step 1: Create Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b chore/lint-cleanup-$(date +%Y%m%d)
```

## Step 2: Run Linting on Backend (Python)

```bash
cd api

# Check current state (don't fix yet, just see what's there)
echo "=== Current Ruff Errors ==="
ruff check src tests --output-format=grouped

echo "=== Current Ruff Format Issues ==="
ruff format src tests --check --diff
```

## Step 3: Auto-Fix All Fixable Issues

```bash
cd api

# Fix all auto-fixable lint errors
ruff check src tests --fix --unsafe-fixes

# Format all files
ruff format src tests

# Run again to see remaining issues that need manual fixes
echo "=== Remaining Issues (require manual fix) ==="
ruff check src tests --output-format=grouped
```

## Step 4: Fix Remaining Manual Issues

For any remaining issues that couldn't be auto-fixed:

1. Read each error message carefully
2. Navigate to the file and line number
3. Apply the appropriate fix following these patterns:

**Common Manual Fixes:**

```python
# F401: Unused import - Remove the import or add to __all__
# F841: Unused variable - Remove or prefix with underscore: _unused_var
# E501: Line too long - Break into multiple lines or simplify
# B006: Mutable default argument - Use None and set in function body
# B007: Loop variable not used - Prefix with underscore: for _i in range()
# PLR0913: Too many arguments - Consider using dataclass or config object
```

## Step 5: Run Type Checking

```bash
cd api

# Check for type errors
mypy src --ignore-missing-imports

# If there are errors, fix them:
# - Add missing type hints
# - Fix incompatible types
# - Add # type: ignore comments only as last resort (with explanation)
```

## Step 6: Verify All Tests Still Pass

```bash
cd api

# Run all tests to ensure fixes didn't break anything
pytest tests/unit -v
pytest tests/integration -v

# If any tests fail, fix them before proceeding
```

## Step 7: Check Frontend (if applicable)

```bash
# Only if web/ directory has code
if [ -d "web/src" ] && [ "$(ls -A web/src 2>/dev/null)" ]; then
    cd web
    
    # Run ESLint
    npm run lint --fix 2>/dev/null || npx eslint src --fix
    
    # Run Prettier
    npx prettier --write "src/**/*.{ts,tsx,js,jsx,css,json}"
    
    # Type check
    npx tsc --noEmit
    
    cd ..
fi
```

## Step 8: Final Verification

```bash
cd api

# Complete verification ladder
echo "=== Final Lint Check ==="
ruff check src tests
echo "Exit code: $?"

echo "=== Final Format Check ==="
ruff format src tests --check
echo "Exit code: $?"

echo "=== Type Check ==="
mypy src --ignore-missing-imports
echo "Exit code: $?"

echo "=== Tests ==="
pytest -q
echo "Exit code: $?"
```

All checks should pass (exit code 0) before proceeding.

## Step 9: Commit Changes

```bash
# Stage all changes
git add -A

# Create commit with detailed message
git commit -m "chore(lint): fix all linting errors and warnings

Changes made:
- Auto-fixed ruff lint errors
- Applied ruff formatting to all Python files
- Fixed type hints for mypy compliance
- [Add any manual fixes you made]

Verification:
- All ruff checks pass
- All mypy checks pass
- All tests pass"
```

## Step 10: Push and Create Pull Request

```bash
# Push to remote
git push -u origin $(git branch --show-current)
```

Then create the PR with this description:

---

**PR Title:** `chore(lint): Fix all linting errors and format codebase`

**PR Body:**

```markdown
## Description

Comprehensive lint cleanup pass on the entire codebase to ensure code quality and consistency.

## Type of Change

- [ ] 🐛 Bug fix
- [ ] ✨ New feature
- [x] ♻️ Refactoring (no functional changes)
- [ ] 📝 Documentation update
- [ ] 🧪 Test update

## Changes Made

### Python (Backend)
- Fixed all `ruff` lint errors and warnings
- Applied consistent formatting with `ruff format`
- Resolved `mypy` type checking issues
- [List specific manual fixes if any]

### TypeScript (Frontend)
- [If applicable: Fixed ESLint errors]
- [If applicable: Applied Prettier formatting]

## Verification

```bash
# All checks pass:
ruff check src tests           # ✅ 0 errors
ruff format src tests --check  # ✅ 0 changes needed
mypy src                       # ✅ 0 errors
pytest                         # ✅ All tests pass
```

## Testing

- [x] All existing unit tests pass
- [x] All existing integration tests pass
- [x] No functional changes, only formatting/style fixes

## Notes for Reviewers

This is a code quality PR with no functional changes. All modifications are:
- Import ordering
- Line length fixes
- Formatting consistency
- Type hint additions
- Unused import/variable removal

Safe to merge after CI passes.
```

---

## Troubleshooting

### If ruff finds unfixable errors:

```bash
# See detailed explanation of each rule
ruff rule <RULE_CODE>

# Example:
ruff rule F401  # Explains unused import rule
```

### If tests fail after lint fixes:

```bash
# Check what changed
git diff

# Run specific failing test with verbose output
pytest tests/path/to/test.py::test_name -v -s

# If lint removed something needed, restore it
git checkout -- path/to/file.py
```

### If mypy has many errors:

```bash
# Focus on one file at a time
mypy src/specific/file.py --ignore-missing-imports

# Or temporarily ignore a file (add to pyproject.toml)
# [tool.mypy]
# exclude = ["src/problematic/"]
```

## Expected Outcome

After completing this prompt:

1. ✅ All Python files pass `ruff check` with 0 errors
2. ✅ All Python files are formatted with `ruff format`
3. ✅ All Python files pass `mypy` type checking
4. ✅ All tests pass
5. ✅ A clean PR is ready for review
6. ✅ No functional changes to the codebase
