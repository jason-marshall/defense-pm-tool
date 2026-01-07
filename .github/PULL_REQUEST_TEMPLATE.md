## Description
<!-- Brief description of changes and why they're needed -->

## Type of Change
- [ ] 🐛 Bug fix (non-breaking change fixing an issue)
- [ ] ✨ New feature (non-breaking change adding functionality)
- [ ] 💥 Breaking change (fix or feature causing existing functionality to change)
- [ ] 📝 Documentation update
- [ ] ♻️ Refactoring (no functional changes)
- [ ] 🧪 Test update

## Related Issues
<!-- Link to related issues: Fixes #123, Relates to #456 -->

## Changes Made
<!-- List the specific changes made -->
- 
- 

## Testing
<!-- Describe how this was tested -->

### Test Coverage
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] Edge cases covered

### Test Commands Run
```bash
# List the test commands you ran
pytest tests/unit/test_<module>.py -v
```

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
- [ ] Coverage meets project targets (90% CPM, 85% EVMS, 80% overall)

### Documentation
- [ ] Docstrings added for public functions/classes
- [ ] README updated (if needed)
- [ ] API documentation updated (if endpoints changed)

### Security
- [ ] No secrets or credentials committed
- [ ] Input validation in place for user data
- [ ] Error messages don't leak sensitive info

## Screenshots (if applicable)
<!-- Add screenshots for UI changes -->

## Performance Impact
<!-- Does this change affect performance? If so, describe benchmarks -->
- [ ] No significant performance impact
- [ ] Performance tested (describe results below)

## Database Changes
<!-- Does this require migrations? -->
- [ ] No database changes
- [ ] Migration added and tested
- [ ] Migration is reversible (downgrade works)

## Deployment Notes
<!-- Any special deployment considerations? -->

## Notes for Reviewers
<!-- Point out specific areas that need careful review -->

---

### Reviewer Checklist
<!-- For the code reviewer -->
- [ ] Code is readable and well-structured
- [ ] Logic is correct and handles edge cases
- [ ] Tests are meaningful and comprehensive
- [ ] No obvious security vulnerabilities
- [ ] Performance is acceptable
- [ ] Documentation is clear and accurate
