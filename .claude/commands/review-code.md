Review the code changes for: $ARGUMENTS

Perform a thorough code review covering the following areas:

## 1. Correctness
- Does the code do what it's supposed to do?
- Are there any logic errors?
- Are edge cases handled properly?
- Could any inputs cause crashes or unexpected behavior?

## 2. Code Quality
- Is the code readable and well-organized?
- Are variable/function names descriptive?
- Is there unnecessary complexity?
- Is there code duplication that should be extracted?
- Are there any "code smells"?

## 3. Testing
- Are there sufficient tests?
- Do tests cover edge cases?
- Are tests meaningful (not just for coverage)?
- Could any tests be flaky?

## 4. Type Safety
Run type checking:
```bash
mypy src --strict
```

Report any type errors or places where types could be more specific.

## 5. Style & Conventions
Run linting:
```bash
ruff check src tests
```

Check adherence to project conventions in CLAUDE.md:
- Import order correct?
- Docstrings present on public functions?
- Naming conventions followed?

## 6. Security
- Is user input validated?
- Are there any injection vulnerabilities?
- Are secrets properly handled?
- Are error messages safe (don't leak sensitive info)?

## 7. Performance
- Are there any obvious performance issues?
- N+1 query problems?
- Unnecessary loops or computations?
- Missing indexes (for database queries)?

## 8. Documentation
- Are public functions documented?
- Is the documentation accurate?
- Would a new developer understand this code?

## Output Format

Provide your review in this format:

### Summary
Brief overall assessment (1-2 sentences)

### Critical Issues 🚨
Must be fixed before merge:
- Issue 1
- Issue 2

### Suggestions 💡
Recommended improvements:
- Suggestion 1
- Suggestion 2

### Minor Notes 📝
Optional improvements:
- Note 1
- Note 2

### Positive Feedback ✅
What was done well:
- Good thing 1
- Good thing 2
