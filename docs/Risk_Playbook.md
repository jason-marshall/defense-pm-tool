# Risk Mitigation Playbook

**Defense Program Management Tool**

*Fast Decisions Under Pressure*

> **January 2026 | Version 1.0**

---

> ℹ️ **PURPOSE**: Pre-planned decisions to enable fast action when risks materialize. Reference this document BEFORE making decisions under pressure.

---

## Table of Contents

1. [Schedule Risk Triggers & Responses](#1-schedule-risk-triggers--responses)
2. [Technical Risk Decision Trees](#2-technical-risk-decision-trees)
3. [Scope Negotiation Framework](#3-scope-negotiation-framework)
4. [Technical Fallback Options](#4-technical-fallback-options)
5. [Daily/Weekly Health Checks](#5-dailyweekly-health-checks)
6. ["Break Glass" Emergency Procedures](#6-break-glass-emergency-procedures)
7. [Success Metrics Dashboard](#7-success-metrics-dashboard)
8. [Quick Reference Card](#quick-reference-card)

---

## 1. Schedule Risk Triggers & Responses

Monitor these indicators weekly. Take action immediately when Yellow triggers appear. Escalate to scope decisions when Red triggers appear.

### 1.1 Month 1: Schedule Foundation

#### Week 1: Project Setup & Database

| Status | Indicator | Metric | Action |
|--------|-----------|--------|--------|
| 🟢 GREEN | Repo, Docker, DB schema complete | 5/5 Day 1-2 tasks done | Continue as planned |
| 🟡 YELLOW | Docker or DB issues taking >4 hours | 1+ day tasks incomplete | Skip optional features, use SQLite temporarily |
| 🔴 RED | Auth not working by Day 5 | <60% Week 1 tasks done | Use basic API key auth, defer JWT to Week 3 |

#### Week 2: CPM Engine Core

| Status | Indicator | Metric | Action |
|--------|-----------|--------|--------|
| 🟢 GREEN | Forward/backward pass working | CPM tests 85%+ coverage, <500ms | Continue as planned |
| 🟡 YELLOW | Only FS dependencies working by Day 8 | 2+ edge case tests failing | Defer SS/FF/SF to Week 3, focus on FS only |
| 🔴 RED | Forward pass not working by Day 10 | CPM tests <60% coverage | **STOP.** Execute Decision Tree 2a |

#### Week 3: API & MS Project Import

| Status | Indicator | Metric | Action |
|--------|-----------|--------|--------|
| 🟢 GREEN | All CRUD endpoints working, import parses | API tests pass, sample XML imports | Continue as planned |
| 🟡 YELLOW | MS Project import has edge cases | 2+ real-world files fail import | Limit to basic import, manual data entry as backup |
| 🔴 RED | CRUD endpoints incomplete by Day 13 | <70% API coverage | Cut MS Project import, manual entry only |

#### Week 4: Frontend & Gantt

| Status | Indicator | Metric | Action |
|--------|-----------|--------|--------|
| 🟢 GREEN | Gantt displays, drag-drop works | E2E test passes, <2s load time | Month 1 MVP complete ✓ |
| 🟡 YELLOW | Gantt displays but no interaction | Read-only Gantt only | Defer drag-drop to Month 2 |
| 🔴 RED | Gantt library not rendering by Day 18 | No visual schedule by Day 19 | Use AG Grid table view, defer Gantt |

### 1.2 Month 2: EVMS Integration

| Week | 🟢 Green Target | 🟡 Yellow Trigger | 🔴 Red Trigger | Fallback |
|------|-----------------|-------------------|----------------|----------|
| Week 5 | BCWS/BCWP calculations working | Only % complete method works | No EV calculations by Day 25 | Manual EV entry |
| Week 6 | SPI/CPI/EAC correct vs reference | 2+ edge cases failing | Calculations off by >1% | Decision Tree 2d |
| Week 7 | Monte Carlo runs <5s for 1000 sim | Monte Carlo >30s | Monte Carlo crashes | Reduce to 100 sim |
| Week 8 | S-curve dashboard complete | Dashboard slow >3s | No working dashboard | Static charts only |

### 1.3 Month 3: Compliance & Polish

| Week | 🟢 Green Target | 🟡 Yellow Trigger | 🔴 Red Trigger | Fallback |
|------|-----------------|-------------------|----------------|----------|
| Week 9 | CPR Format 1,3,5 generating | Only Format 1 working | No reports generating | Excel export only |
| Week 10 | Jira integration syncing | Jira read-only | Jira not connecting | Manual sync |
| Week 11 | What-if scenarios working | Scenarios slow >10s | Scenarios corrupting baseline | Read-only analysis |
| Week 12 | Security hardened, 80% coverage | Coverage 70-79% | Security vulnerabilities found | Fix vulns, defer features |

---

## 2. Technical Risk Decision Trees

When a risk materializes, find the relevant decision tree and follow it. Make decisions within the time threshold—do not deliberate longer.

### 2a. CPM Engine Taking 2x Longer Than Planned

> 🚨 **TIME THRESHOLD**: Make decision within 4 hours of recognizing the pattern

**TRIGGER**: Forward pass not working after 3 days of effort, OR backward pass fails after forward pass took 2x estimate

| Option | When to Choose | Action |
|--------|----------------|--------|
| **A: Push Through** | Root cause identified, fix is clear, <2 days work remaining | Continue implementation, extend Week 2 by 2 days max, compress Week 3 |
| **B: Simplify** | FS dependencies work but others don't, OR lag handling is the issue | Ship FS-only CPM, add SS/FF/SF in Month 2, document limitation |
| **C: Alternative** | Fundamental architecture problem, OR NetworkX not suitable | Use pm4py library (has CPM built-in), OR call external scheduling API |

### 2b. MS Project XML Import Fails for Real Files

> ⚠️ **TIME THRESHOLD**: Make decision within 2 hours of third file failure

**TRIGGER**: Parser works for test XML but fails for 2+ real-world MS Project files from customer

| Option | When to Choose | Action |
|--------|----------------|--------|
| **A: Push Through** | Failures are in specific edge cases (resources, calendars), core tasks import | Import tasks/dependencies only, log warnings for skipped fields |
| **B: Simplify** | XML structure varies significantly between MS Project versions | Support only MS Project 2019+ format, require CSV export as backup |
| **C: Alternative** | XML parsing fundamentally unreliable, customer files are corrupt | Use mpxj library (Java, but has Python bindings), OR manual entry with Excel template |

### 2c. Gantt Library Performance Issues

> ⚠️ **TIME THRESHOLD**: Make decision within 1 day of performance testing

**TRIGGER**: Gantt chart takes >3s to render 500 activities, OR drag-drop causes visible lag

| Option | When to Choose | Action |
|--------|----------------|--------|
| **A: Push Through** | Virtualization not enabled, clear optimization path exists | Enable row virtualization, limit visible date range, lazy load |
| **B: Simplify** | Library fundamentally slow, but acceptable for <200 activities | Implement pagination (show 100 at a time), add 'load more' button |
| **C: Alternative** | Frappe Gantt unsuitable, need commercial-grade performance | Switch to DHTMLX Gantt ($599 license), OR Bryntum Gantt ($499), OR table-only view |

### 2d. EVMS Calculations Don't Match Reference Data

> 🚨 **TIME THRESHOLD**: Make decision within 4 hours—EVMS accuracy is compliance-critical

**TRIGGER**: SPI/CPI calculations differ from reference spreadsheet by >0.5%, OR EAC is wrong

| Option | When to Choose | Action |
|--------|----------------|--------|
| **A: Push Through** | Rounding difference identified, OR reference data has known error | Document rounding rules explicitly, match reference exactly, add unit tests |
| **B: Simplify** | Advanced EAC methods (3-point, regression) are wrong, basic works | Ship mathematical EAC only (BAC/CPI), defer advanced methods |
| **C: Alternative** | Formula interpretation differs from industry standard | Get EVMS expert review (contractor support), use validated spreadsheet as backend |

### 2e. Database Queries Too Slow for 1000 Activities

> ⚠️ **TIME THRESHOLD**: Make decision within 2 hours of benchmark failure

**TRIGGER**: Schedule load takes >2s, OR CPM recalculation takes >1s, OR dashboard queries timeout

| Option | When to Choose | Action |
|--------|----------------|--------|
| **A: Push Through** | Missing indexes identified, N+1 query found, clear fix | Add indexes, use eager loading, add EXPLAIN ANALYZE to tests |
| **B: Simplify** | WBS hierarchy queries are slow despite ltree | Denormalize rolled-up metrics, use materialized views, cache in Redis |
| **C: Alternative** | PostgreSQL fundamentally too slow for this access pattern | Add read replica, implement CQRS pattern, OR pre-compute all metrics on write |

---

## 3. Scope Negotiation Framework

Use this framework when risks force scope decisions. Share with stakeholders proactively.

### 3.1 Feature Priority Classification

| Priority | Features | Criteria | If Cut |
|----------|----------|----------|--------|
| 🔴 **NON-NEGOTIABLE** | • CPM calculation (ES/EF/LS/LF) • Activity CRUD • WBS hierarchy • Basic Gantt display • User authentication | Cannot ship without these. Users cannot do their job. | Project fails. Do not ship. |
| 🟡 **SHOULD-HAVE** | • All 4 dependency types • MS Project import • EVMS calculations • Drag-drop Gantt editing • CPR report generation | Important for adoption. Can work around temporarily. | Document limitation. Deliver in next release. |
| 🟢 **NICE-TO-HAVE** | • Resource leveling • Monte Carlo simulation • Jira integration • What-if scenarios • Mobile responsive | Enhances value. Users can live without. | Move to backlog. No apology needed. |

### 3.2 Stakeholder Communication Templates

#### Template A: Early Warning (Yellow Status)

```
Subject: [Project Name] Week X Status - Monitoring Risk

Hi [Stakeholder],

Quick status update: We're tracking a potential risk with [component].

• Current status: [specific issue]
• Impact if unresolved: [feature] may be simplified or delayed
• Mitigation in progress: [what you're doing]
• Decision point: [date] - I'll update you by then

No action needed from you yet. I'll escalate if this becomes critical.

[Your name]
```

#### Template B: Scope Decision Required (Red Status)

```
Subject: [Project Name] - Scope Decision Needed by [Date]

Hi [Stakeholder],

I need your input on a scope decision.

SITUATION:
[Component] is taking longer than planned due to [root cause].

OPTIONS:
A) [Push through] - Delivers [X], delays overall by [Y days]
B) [Simplify] - Delivers [reduced X], stays on schedule
C) [Alternative] - Delivers [different approach], [trade-off]

MY RECOMMENDATION: Option [X] because [reasoning]

Please confirm by [date/time] so I can proceed. If I don't hear back, 
I'll proceed with Option [X].

[Your name]
```

#### Template C: Feature Deferral Notice

```
Subject: [Project Name] - [Feature] Moved to Phase 2

Hi [Stakeholder],

To ensure we deliver a solid MVP on schedule, I've moved [feature] to Phase 2.

WHAT'S CHANGING:
• [Feature] will not be in the initial release
• Workaround: [how users accomplish this without the feature]
• Expected delivery: [Month X]

WHY:
[Brief explanation - 1-2 sentences]

WHAT'S STILL ON TRACK:
• [List of features still delivering]

Let me know if you have concerns.

[Your name]
```

---

## 4. Technical Fallback Options

Pre-researched alternatives for major components. Switching cost estimates assume fallback is exercised early.

| Component | Plan A (Current) | Plan B (Fallback) | Switch Cost | Trigger |
|-----------|------------------|-------------------|-------------|---------|
| **CPM Engine** | Custom implementation with NetworkX | pm4py library (MIT license, has CPM) OR python-gantt | 2-3 days | Day 10 |
| **Gantt Chart** | Frappe Gantt (open source) | DHTMLX Gantt ($599) OR AG Grid table view (free) | 1-2 days | Day 18 |
| **EVMS Calc** | Custom Decimal-based calculator | Validated Excel as calculation engine (xlwings) | 1 day | Day 28 |
| **MS Project Import** | Custom XML parser with lxml | mpxj library (Java, Python bindings) OR CSV import only | 1 day | Day 15 |
| **Database** | PostgreSQL with ltree | PostgreSQL with adjacency list + CTE OR SQLite for single-user | 2 days | Day 5 |
| **Caching** | Redis | In-memory Python cache (cachetools) OR PostgreSQL materialized views | 0.5 days | Any |
| **Auth** | JWT with refresh tokens | Session-based auth with Redis OR API keys only | 1 day | Day 5 |
| **Reports** | PDF generation with reportlab | Excel export with openpyxl OR HTML print view | 0.5 days | Day 45 |

---

## 5. Daily/Weekly Health Checks

### 5.1 Daily Health Check (5 minutes)

Run every morning before starting work:

- [ ] Git status clean? No uncommitted work from yesterday?
- [ ] All tests passing? Run: `pytest tests/unit -q`
- [ ] Any blockers identified yesterday still unresolved?
- [ ] Today's tasks clear? Check against weekly plan
- [ ] Anything taking >4 hours? Flag for potential Yellow status

> ℹ️ If 2+ items fail, stop and address before starting new work

### 5.2 Weekly Health Check (30 minutes)

Complete every Friday afternoon:

| Metric | Target | This Week |
|--------|--------|-----------|
| Tasks completed vs planned | ≥80% | [ ] / [ ] |
| Test coverage (overall) | ≥80% | [ ]% |
| Test coverage (CPM engine) | ≥90% | [ ]% |
| Open blockers | 0 | [ ] |
| Longest task duration (hours) | <8 | [ ] |
| Technical debt items added | <3 | [ ] |
| Dependencies updated this week | If security fix | Y / N |

**Weekly Status Classification:**

- 🟢 **GREEN**: All targets met, no blockers
- 🟡 **YELLOW**: 1-2 targets missed OR 1 blocker >2 days
- 🔴 **RED**: 3+ targets missed OR blocker >4 days OR behind schedule

### 5.3 Milestone Go/No-Go Criteria

#### Month 1 Milestone: Schedule Foundation Complete

| Criterion | Required | Status |
|-----------|----------|--------|
| User can create program and WBS hierarchy | YES | ☐ |
| User can add activities with dependencies | YES | ☐ |
| CPM calculates correct ES/EF/LS/LF (verified vs reference) | YES | ☐ |
| Gantt chart displays schedule | YES | ☐ |
| MS Project XML imports basic schedule | PREFERRED | ☐ |
| Test coverage ≥80% overall, ≥90% CPM | YES | ☐ |
| No critical security vulnerabilities | YES | ☐ |

> 🚨 **GO**: All YES criteria met. **NO-GO**: Any YES criterion failed—do not proceed to Month 2 features until resolved.

---

## 6. "Break Glass" Emergency Procedures

Procedures for low-probability, high-impact events. Execute immediately without deliberation.

### 6.1 Developer Unavailable for 1+ Week

> 🚨 **IMMEDIATE ACTIONS** (within 2 hours of confirmed unavailability):

1. Push all local changes to Git (if accessible)
2. Notify stakeholders: "Development paused due to [illness/emergency]"
3. Document current state: What's done, what's in progress, what's blocked
4. If >2 weeks: Engage backup contractor (pre-identified, see contacts)

**Pre-requisite:** Maintain updated CLAUDE.md and architecture docs so backup can onboard quickly.

### 6.2 Critical Bug in Production

> 🚨 **IMMEDIATE ACTIONS** (within 30 minutes of report):

1. Assess severity: Data loss? Security breach? Blocking all users?
2. If data loss/security: Take system offline immediately
3. Notify stakeholders: "System issue identified, investigating"
4. Reproduce bug locally, write failing test
5. Fix, test, deploy hotfix (bypass normal review if <10 lines)
6. Post-mortem within 24 hours: root cause, prevention

### 6.3 Security Vulnerability Found

> 🚨 **IMMEDIATE ACTIONS** (within 1 hour of discovery):

1. Classify: Critical (RCE, auth bypass, data exposure) vs High vs Medium
2. If Critical: Disable affected feature immediately, notify stakeholders
3. Check if already exploited: Review logs for suspicious activity
4. Fix vulnerability (all current work stops until resolved)
5. Add regression test for vulnerability
6. Document in security log for compliance audit trail

### 6.4 Major Scope Change Request

> ⚠️ **IMMEDIATE ACTIONS** (within 4 hours of request):

1. Acknowledge request: "Received, assessing impact"
2. **DO NOT** agree to anything immediately, even if pressured
3. Estimate: Effort in days, what must be cut to accommodate, risks
4. Present trade-off: "We can do X, but Y must be deferred"
5. Get written approval for scope change AND what's being cut
6. Update project documentation to reflect new scope

> ℹ️ **NEVER** accept scope additions without corresponding scope reductions or timeline extension

---

## 7. Success Metrics Dashboard

Track these metrics weekly. Visualize trends to catch issues early.

### 7.1 Key Metrics & Thresholds

| Metric | 🟢 Green | 🟡 Yellow | 🔴 Red | Action if Red |
|--------|----------|-----------|--------|---------------|
| Velocity (tasks/week) | ≥80% plan | 60-79% | <60% | Re-estimate or cut scope |
| Test Coverage (overall) | ≥80% | 70-79% | <70% | Stop features, write tests |
| Test Coverage (CPM) | ≥90% | 85-89% | <85% | **STOP.** CPM must be correct |
| Bug Escape Rate | 0 bugs in prod | 1-2 low severity | 3+ or any high | Review test strategy |
| Blocker Duration | <4 hours | 4-8 hours | >8 hours | Escalate or pivot |
| Tech Debt Items | <5 total | 5-10 | >10 | Dedicate 20% to debt |
| API Response Time (p95) | <200ms | 200-500ms | >500ms | Optimize queries/cache |
| CPM Calc Time (1000 act) | <500ms | 500ms-1s | >1s | Profile and optimize |

### 7.2 Weekly Tracking Template

Copy this table each week and fill in actuals:

| Week | Velocity | Coverage | Blockers | Tech Debt | Status |
|------|----------|----------|----------|-----------|--------|
| Week 1 | | | | | |
| Week 2 | | | | | |
| Week 3 | | | | | |
| Week 4 | | | | | |
| Week 5 | | | | | |
| Week 6 | | | | | |
| Week 7 | | | | | |
| Week 8 | | | | | |
| Week 9 | | | | | |
| Week 10 | | | | | |
| Week 11 | | | | | |
| Week 12 | | | | | |

### 7.3 Trend Interpretation

- **Velocity declining 2+ weeks**: Burnout, hidden complexity, or scope creep—investigate root cause
- **Coverage declining**: Technical debt accumulating—schedule debt payment sprint
- **Blockers increasing**: Architecture issue or missing knowledge—consider pairing/consulting
- **Tech debt growing**: Cut scope to make room for refactoring

> ✅ **HEALTHY PROJECT**: Green metrics, declining blockers, stable or improving velocity trend

---

## Quick Reference Card

*Print this page and keep visible during development.*

### Decision Time Thresholds

| Situation | Decide Within |
|-----------|---------------|
| CPM implementation stuck | 4 hours |
| Library/tool not working | 2 hours |
| Test failures on edge cases | 4 hours |
| Performance not meeting targets | 1 day |
| Scope change request | 4 hours to respond, 1 day to decide |
| Security vulnerability | 1 hour |
| Production bug | 30 minutes to assess |

### Emergency Contacts

| Role | Name | Contact |
|------|------|---------|
| Project Stakeholder | [Name] | [Email/Phone] |
| Backup Developer | [Name] | [Email/Phone] |
| EVMS Subject Matter Expert | [Name] | [Email/Phone] |
| Security Contact | [Name] | [Email/Phone] |

### Key Reminders

> ⚠️ Never deliberate longer than the time threshold—make a decision and move forward

> ℹ️ Document all scope decisions in writing—verbal agreements don't count

> ✅ When in doubt, choose the option that keeps the project moving

> 🚨 If security or data integrity is at risk, stop everything else and fix it

---

*Document Version: 1.0*
*Last Updated: January 2026*
