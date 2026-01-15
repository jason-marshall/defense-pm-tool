# Load Project Context for New Session

Read and internalize the project context to provide high-quality assistance for this defense program management tool development session.

## Step 1: Read Core Documentation

Read these files in order to understand the project:

```bash
# Primary context file (MOST IMPORTANT - read this first)
cat CLAUDE.md

# Architecture and design decisions
cat docs/ARCHITECTURE.md

# Current development plan and progress
cat docs/TDD_PLAN.md

# Risk mitigation strategies
cat docs/RISK_PLAYBOOK.md
```

## Step 2: Understand Current Codebase State

```bash
# Check project structure
find . -type f -name "*.py" | grep -v __pycache__ | grep -v ".venv" | head -50

# Check recent git activity
git log --oneline -15

# Check current branch and status
git branch -a
git status

# Check for any uncommitted work
git diff --stat
```

## Step 3: Review Key Implementation Files

```bash
# Models - understand data structures
ls -la api/src/models/
cat api/src/models/activity.py
cat api/src/models/dependency.py

# Core services - understand business logic
ls -la api/src/services/
head -100 api/src/services/cpm.py
head -100 api/src/services/evms.py

# API endpoints - understand current routes
ls -la api/src/api/v1/endpoints/
cat api/src/api/v1/router.py

# Schemas - understand API contracts
ls -la api/src/schemas/
```

## Step 4: Check Test Coverage and Health

```bash
cd api

# Check what tests exist
find tests -name "*.py" -type f | head -20

# Run tests to see current state (quick mode)
pytest tests/unit -q --tb=no 2>/dev/null || echo "Unit tests need attention"
pytest tests/integration -q --tb=no 2>/dev/null || echo "Integration tests need attention"

# Check coverage if available
pytest --cov=src --cov-report=term-missing --cov-fail-under=0 -q 2>/dev/null | tail -20 || echo "Coverage check skipped"

cd ..
```

## Step 5: Check Environment Health

```bash
# Verify Docker containers are running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "Docker not running"

# Check database connectivity
docker exec defense-pm-tool-postgres pg_isready -U dev_user 2>/dev/null || echo "Database not ready"

# Check Redis connectivity  
docker exec defense-pm-tool-redis redis-cli ping 2>/dev/null || echo "Redis not ready"

# Check Python environment
cd api
python --version
pip list | grep -E "fastapi|sqlalchemy|pydantic|pytest|ruff" 2>/dev/null || echo "Check Python deps"
cd ..
```

## Step 6: Identify Current Work Items

```bash
# Check for any TODO/FIXME comments
grep -r "TODO\|FIXME\|HACK\|XXX" api/src --include="*.py" 2>/dev/null | head -10

# Check for any failing tests or known issues
grep -r "pytest.mark.skip\|@pytest.mark.xfail" api/tests --include="*.py" 2>/dev/null

# Look for any WIP branches
git branch | grep -E "feature|bugfix|hotfix|wip" 2>/dev/null
```

## Step 7: Summarize Context

After reading all the above, provide a summary covering:

1. **Project Overview**: What is this project and what stage is it at?

2. **Current Week/Sprint**: What development phase are we in?

3. **Completed Work**: What major features are done?

4. **In Progress**: What's currently being worked on?

5. **Known Issues**: Any bugs, tech debt, or blockers?

6. **Next Steps**: What should be tackled next based on the TDD plan?

7. **Environment Status**: Are Docker, DB, Redis all healthy?

8. **Test Status**: Are tests passing? What's the coverage?

## Quick Context Summary Template

After loading context, respond with:

```
## 🎯 Session Context Loaded

**Project**: Defense Program Management Tool
**Phase**: Week [X] of Month [Y]
**Branch**: [current branch]

### ✅ Completed
- [List major completed features]

### 🔶 In Progress  
- [Current work items]

### ⏭️ Next Priority
- [Based on TDD_PLAN.md]

### ⚠️ Known Issues
- [Any blockers or tech debt]

### 🏥 Environment Health
- Docker: [Running/Down]
- PostgreSQL: [Connected/Error]
- Redis: [Connected/Error]
- Tests: [Passing/Failing] ([X]% coverage)

### 📋 Ready to Help With
1. [Suggested task based on plan]
2. [Alternative task]
3. [Or ask what you'd like to work on]
```

---

## Alternative: Minimal Context Load (30 seconds)

If you need quick context without full analysis:

```bash
# Essential files only
cat CLAUDE.md
git log --oneline -5
git status
cd api && pytest -q --tb=no 2>/dev/null; cd ..
```

---

## Usage Notes

- Run this prompt at the **start of every new Claude Code session**
- If files are missing, note them but continue with available context
- If tests fail, note the failures but don't block on fixing them immediately
- Prioritize understanding the **current development phase** from TDD_PLAN.md
- Check CLAUDE.md's "Current Development Status" section for quick orientation

## After Context is Loaded

Ask the user:
> "I've loaded the project context. What would you like to work on today? 
> Based on the current plan, the next priority appears to be [X]. 
> Should we continue with that, or do you have something else in mind?"
