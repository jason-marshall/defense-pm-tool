# Defense PM Tool - API Guide

A comprehensive API guide for system integrators and developers using the Defense Program Management Tool v1.1.0.

## Table of Contents

1. [Authentication](#authentication)
2. [Programs API](#programs-api)
3. [WBS API](#wbs-api)
4. [Activities API](#activities-api)
5. [Dependencies API](#dependencies-api)
6. [Schedule Calculation (CPM)](#schedule-calculation-cpm)
7. [EVMS API](#evms-api)
8. [Resource Management](#resource-management)
9. [Baselines API](#baselines-api)
10. [Monte Carlo Simulation](#monte-carlo-simulation)
11. [Scenario Planning](#scenario-planning)
12. [Reports API](#reports-api)
13. [Jira Integration](#jira-integration)
14. [Error Handling](#error-handling)
15. [Rate Limiting](#rate-limiting)

---

## Authentication

### Base URL

```
Production: https://api.defense-pm-tool.com/api/v1
Development: http://localhost:8000/api/v1
```

### Option 1: JWT Token (Interactive Use)

Best for: Web applications, interactive sessions, short-lived access.

```bash
# Step 1: Login to get tokens
curl -X POST https://api.defense-pm-tool.com/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your@email.com&password=yourpassword"

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}

# Step 2: Use token in requests
curl https://api.defense-pm-tool.com/api/v1/programs \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Step 3: Refresh token before expiry
curl -X POST https://api.defense-pm-tool.com/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

### Option 2: API Key (Service Accounts)

Best for: CI/CD pipelines, automated scripts, long-running integrations.

```bash
# Step 1: Create API key (requires JWT authentication first)
curl -X POST https://api.defense-pm-tool.com/api/v1/api-keys \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CI/CD Pipeline - Jenkins",
    "description": "Automated schedule updates from Jenkins",
    "scopes": ["programs:read", "activities:write"],
    "expires_in_days": 365
  }'

# Response - SAVE THE KEY IMMEDIATELY (shown only once!)
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "CI/CD Pipeline - Jenkins",
  "key": "dpm_a1b2c3d4_f7e8d9c0b1a2...",
  "key_prefix": "dpm_a1b2c3d4",
  "expires_at": "2027-01-24T00:00:00Z",
  "message": "Store this key securely - it cannot be retrieved again."
}

# Step 2: Use API key in requests
curl https://api.defense-pm-tool.com/api/v1/programs \
  -H "X-API-Key: dpm_a1b2c3d4_f7e8d9c0b1a2..."
```

### API Key Scopes

| Scope | Description |
|-------|-------------|
| `programs:read` | Read program data |
| `programs:write` | Create/update programs |
| `activities:read` | Read activities |
| `activities:write` | Create/update activities |
| `evms:read` | Read EVMS data |
| `reports:generate` | Generate reports |
| *(none)* | Full access (when no scopes specified) |

### API Key Management

```bash
# List your API keys
curl https://api.defense-pm-tool.com/api/v1/api-keys \
  -H "Authorization: Bearer $TOKEN"

# Get specific key details
curl https://api.defense-pm-tool.com/api/v1/api-keys/$KEY_ID \
  -H "Authorization: Bearer $TOKEN"

# Revoke an API key
curl -X DELETE https://api.defense-pm-tool.com/api/v1/api-keys/$KEY_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

## Programs API

### List Programs

```bash
curl https://api.defense-pm-tool.com/api/v1/programs \
  -H "Authorization: Bearer $TOKEN"
```

### Create Program

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/programs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "F-35 Block 4 Development",
    "code": "F35-BLK4",
    "description": "Block 4 capability development program",
    "start_date": "2026-01-01",
    "end_date": "2028-12-31",
    "budget_at_completion": "5000000000.00",
    "contract_number": "FA8615-21-C-0001",
    "contract_type": "CPFF"
  }'
```

### Get Program

```bash
curl https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID \
  -H "Authorization: Bearer $TOKEN"
```

### Update Program

```bash
curl -X PATCH https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "budget_at_completion": "5500000000.00",
    "end_date": "2029-06-30"
  }'
```

### Delete Program

```bash
curl -X DELETE https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

## WBS API

### Create WBS Element

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/wbs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "1.1",
    "name": "Air Vehicle",
    "description": "Complete air vehicle system",
    "level": 2,
    "parent_id": null,
    "budget_at_completion": "2000000000.00",
    "is_control_account": false
  }'
```

### Create Child WBS Element

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/wbs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "1.1.1",
    "name": "Airframe",
    "level": 3,
    "parent_id": "uuid-of-parent-wbs",
    "budget_at_completion": "500000000.00",
    "is_control_account": true
  }'
```

### Get WBS Tree

```bash
curl https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/wbs/tree \
  -H "Authorization: Bearer $TOKEN"
```

### List WBS Elements

```bash
curl https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/wbs \
  -H "Authorization: Bearer $TOKEN"
```

---

## Activities API

### Create Activity

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/activities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "A-001",
    "name": "Preliminary Design Review",
    "description": "PDR for Block 4 capabilities",
    "wbs_id": "uuid-of-wbs-element",
    "duration": 10,
    "budgeted_cost": "150000.00",
    "ev_method": "milestone",
    "is_milestone": true
  }'
```

### List Activities

```bash
# All activities for a program
curl "https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/activities" \
  -H "Authorization: Bearer $TOKEN"

# Filter by WBS
curl "https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/activities?wbs_id=$WBS_ID" \
  -H "Authorization: Bearer $TOKEN"

# Filter critical path only
curl "https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/activities?is_critical=true" \
  -H "Authorization: Bearer $TOKEN"
```

### Get Activity

```bash
curl https://api.defense-pm-tool.com/api/v1/activities/$ACTIVITY_ID \
  -H "Authorization: Bearer $TOKEN"
```

### Update Activity

```bash
curl -X PATCH https://api.defense-pm-tool.com/api/v1/activities/$ACTIVITY_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "percent_complete": "75.00",
    "actual_cost": "120000.00"
  }'
```

### Earned Value Methods

| Method | Code | Description |
|--------|------|-------------|
| Percent Complete | `percent_complete` | Manual % entry |
| Milestone | `milestone` | 0% until complete, then 100% |
| 50/50 | `fifty_fifty` | 50% at start, 100% at finish |
| 0/100 | `zero_hundred` | 0% until 100% complete |
| Level of Effort | `loe` | Spreads evenly over time |
| Apportioned | `apportioned` | Based on reference activity |

---

## Dependencies API

### Create Dependency

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/dependencies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "predecessor_id": "uuid-of-predecessor-activity",
    "successor_id": "uuid-of-successor-activity",
    "dependency_type": "FS",
    "lag": 5
  }'
```

### Dependency Types

| Type | Name | Description |
|------|------|-------------|
| `FS` | Finish-to-Start | Successor starts after predecessor finishes |
| `SS` | Start-to-Start | Both start together |
| `FF` | Finish-to-Finish | Both finish together |
| `SF` | Start-to-Finish | Successor finishes when predecessor starts |

### List Dependencies

```bash
curl https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/dependencies \
  -H "Authorization: Bearer $TOKEN"
```

### Delete Dependency

```bash
curl -X DELETE https://api.defense-pm-tool.com/api/v1/dependencies/$DEPENDENCY_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

## Schedule Calculation (CPM)

### Calculate Schedule

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/calculate \
  -H "Authorization: Bearer $TOKEN"
```

### Response

```json
{
  "program_id": "uuid",
  "calculated_at": "2026-01-24T12:00:00Z",
  "project_duration": 450,
  "critical_path_activities": ["A-001", "A-005", "A-012", "A-025"],
  "activities": [
    {
      "id": "uuid",
      "code": "A-001",
      "early_start": 0,
      "early_finish": 10,
      "late_start": 0,
      "late_finish": 10,
      "total_float": 0,
      "free_float": 0,
      "is_critical": true
    }
  ]
}
```

### Constraint Types

| Constraint | Code | Description |
|------------|------|-------------|
| As Soon As Possible | `ASAP` | Default - schedule earliest |
| As Late As Possible | `ALAP` | Schedule as late as possible |
| Start No Earlier Than | `SNET` | Cannot start before date |
| Start No Later Than | `SNLT` | Must start by date |
| Finish No Earlier Than | `FNET` | Cannot finish before date |
| Finish No Later Than | `FNLT` | Must finish by date |
| Must Start On | `MSO` | Fixed start date |
| Must Finish On | `MFO` | Fixed finish date |

---

## EVMS API

### Get EVMS Dashboard

```bash
curl https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/evms/dashboard \
  -H "Authorization: Bearer $TOKEN"
```

### Response

```json
{
  "program_id": "uuid",
  "as_of_date": "2026-01-24",
  "bac": "5000000000.00",
  "bcws": "1250000000.00",
  "bcwp": "1125000000.00",
  "acwp": "1300000000.00",
  "sv": "-125000000.00",
  "cv": "-175000000.00",
  "spi": "0.90",
  "cpi": "0.87",
  "eac": "5747126436.78",
  "etc": "4447126436.78",
  "vac": "-747126436.78",
  "tcpi": "1.05",
  "percent_complete": "22.50",
  "percent_spent": "26.00"
}
```

### Get EAC Methods

```bash
curl https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/evms/eac-methods \
  -H "Authorization: Bearer $TOKEN"
```

### EVMS Formulas

| Metric | Formula | Description |
|--------|---------|-------------|
| SV | BCWP - BCWS | Schedule Variance |
| CV | BCWP - ACWP | Cost Variance |
| SPI | BCWP / BCWS | Schedule Performance Index |
| CPI | BCWP / ACWP | Cost Performance Index |
| EAC | BAC / CPI | Estimate at Completion |
| ETC | EAC - ACWP | Estimate to Complete |
| VAC | BAC - EAC | Variance at Completion |
| TCPI | (BAC - BCWP) / (BAC - ACWP) | To-Complete Performance Index |

---

## Resource Management

### Resource Types

| Type | Code | Description |
|------|------|-------------|
| Labor | `LABOR` | Human resources (engineers, technicians, managers) |
| Equipment | `EQUIPMENT` | Machinery and tools (CNC machines, test equipment) |
| Material | `MATERIAL` | Consumable materials and supplies |

### Create Resource

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/resources \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "program_id": "uuid-of-program",
    "name": "Senior Systems Engineer",
    "code": "ENG-001",
    "resource_type": "LABOR",
    "capacity_per_day": "8.0",
    "cost_rate": "175.00",
    "is_active": true
  }'
```

### Response

```json
{
  "id": "uuid",
  "program_id": "uuid",
  "name": "Senior Systems Engineer",
  "code": "ENG-001",
  "resource_type": "LABOR",
  "capacity_per_day": "8.0",
  "cost_rate": "175.00",
  "is_active": true,
  "created_at": "2026-01-24T12:00:00Z",
  "updated_at": "2026-01-24T12:00:00Z"
}
```

### List Resources

```bash
# All resources for a program
curl "https://api.defense-pm-tool.com/api/v1/resources?program_id=$PROGRAM_ID" \
  -H "Authorization: Bearer $TOKEN"

# Filter by resource type
curl "https://api.defense-pm-tool.com/api/v1/resources?program_id=$PROGRAM_ID&resource_type=LABOR" \
  -H "Authorization: Bearer $TOKEN"

# Filter by active status
curl "https://api.defense-pm-tool.com/api/v1/resources?program_id=$PROGRAM_ID&is_active=true" \
  -H "Authorization: Bearer $TOKEN"
```

### Get Resource

```bash
curl https://api.defense-pm-tool.com/api/v1/resources/$RESOURCE_ID \
  -H "Authorization: Bearer $TOKEN"
```

### Update Resource

```bash
curl -X PUT https://api.defense-pm-tool.com/api/v1/resources/$RESOURCE_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Lead Systems Engineer",
    "cost_rate": "200.00"
  }'
```

### Delete Resource

```bash
curl -X DELETE https://api.defense-pm-tool.com/api/v1/resources/$RESOURCE_ID \
  -H "Authorization: Bearer $TOKEN"
```

### Assign Resource to Activity

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/resources/$RESOURCE_ID/assignments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resource_id": "uuid-of-resource",
    "activity_id": "uuid-of-activity",
    "units": "1.0",
    "start_date": "2026-02-01",
    "finish_date": "2026-02-15"
  }'
```

### Assignment Response

```json
{
  "id": "uuid",
  "resource_id": "uuid",
  "activity_id": "uuid",
  "units": "1.0",
  "start_date": "2026-02-01",
  "finish_date": "2026-02-15",
  "created_at": "2026-01-24T12:00:00Z"
}
```

### List Resource Assignments

```bash
curl "https://api.defense-pm-tool.com/api/v1/resources/$RESOURCE_ID/assignments" \
  -H "Authorization: Bearer $TOKEN"
```

### Manage Resource Calendar

```bash
# Bulk create calendar entries
curl -X POST https://api.defense-pm-tool.com/api/v1/resources/$RESOURCE_ID/calendar \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resource_id": "uuid-of-resource",
    "entries": [
      {"calendar_date": "2026-02-01", "available_hours": "8.0", "is_working_day": true},
      {"calendar_date": "2026-02-02", "available_hours": "8.0", "is_working_day": true},
      {"calendar_date": "2026-02-03", "available_hours": "0.0", "is_working_day": false}
    ]
  }'

# Get calendar range
curl "https://api.defense-pm-tool.com/api/v1/resources/$RESOURCE_ID/calendar?start_date=2026-02-01&end_date=2026-02-28" \
  -H "Authorization: Bearer $TOKEN"
```

### Calendar Range Response

```json
{
  "resource_id": "uuid",
  "start_date": "2026-02-01",
  "end_date": "2026-02-28",
  "working_days": 20,
  "total_hours": "160.0",
  "entries": [
    {"calendar_date": "2026-02-01", "available_hours": "8.0", "is_working_day": true},
    {"calendar_date": "2026-02-02", "available_hours": "8.0", "is_working_day": true}
  ]
}
```

### Delete Calendar Range

```bash
curl -X DELETE "https://api.defense-pm-tool.com/api/v1/resources/$RESOURCE_ID/calendar?start_date=2026-02-01&end_date=2026-02-28" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Resource Leveling

Resource leveling resolves over-allocations by delaying activities when resources are assigned beyond their capacity.

### Detect Over-allocations

Check a resource's histogram to identify over-allocated periods:

```bash
curl "https://api.defense-pm-tool.com/api/v1/resources/$RESOURCE_ID/histogram?start_date=2026-01-01&end_date=2026-03-31" \
  -H "Authorization: Bearer $TOKEN"
```

### Histogram Response

```json
{
  "resource_id": "uuid",
  "resource_code": "ENG-001",
  "resource_name": "Senior Engineer",
  "resource_type": "labor",
  "start_date": "2026-01-01",
  "end_date": "2026-03-31",
  "data_points": [
    {
      "date": "2026-01-15",
      "available_hours": "8.00",
      "assigned_hours": "12.00",
      "utilization_percent": "150.00",
      "is_overallocated": true
    }
  ],
  "peak_utilization": "150.00",
  "peak_date": "2026-01-15",
  "average_utilization": "85.50",
  "overallocated_days": 5,
  "total_available_hours": "480.00",
  "total_assigned_hours": "410.40"
}
```

### Program-wide Histogram

Get histogram data for all resources in a program:

```bash
curl "https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/histogram?start_date=2026-01-01&end_date=2026-03-31" \
  -H "Authorization: Bearer $TOKEN"
```

### Program Histogram Response

```json
{
  "summary": {
    "program_id": "uuid",
    "start_date": "2026-01-01",
    "end_date": "2026-03-31",
    "resource_count": 5,
    "total_overallocated_days": 12,
    "resources_with_overallocation": 2
  },
  "histograms": [
    { "resource_id": "uuid", "resource_code": "ENG-001", "..." : "..." }
  ]
}
```

### Preview Resource Leveling

Preview leveling without applying changes:

```bash
curl "https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/level/preview?preserve_critical_path=true&level_within_float=true" \
  -H "Authorization: Bearer $TOKEN"
```

### Run Resource Leveling

Execute the leveling algorithm:

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/level \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "preserve_critical_path": true,
    "max_iterations": 100,
    "level_within_float": true,
    "target_resources": null
  }'
```

### Leveling Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `preserve_critical_path` | bool | true | Never delay critical path activities |
| `max_iterations` | int | 100 | Maximum leveling iterations |
| `level_within_float` | bool | true | Only delay within total float |
| `target_resources` | list | null | Specific resources to level (null = all) |

### Leveling Response

```json
{
  "program_id": "uuid",
  "success": true,
  "iterations_used": 15,
  "activities_shifted": 3,
  "shifts": [
    {
      "activity_id": "uuid",
      "activity_code": "A-005",
      "original_start": "2026-01-15",
      "original_finish": "2026-01-25",
      "new_start": "2026-01-22",
      "new_finish": "2026-02-01",
      "delay_days": 7,
      "reason": "Resource ENG-001 overallocated"
    }
  ],
  "remaining_overallocations": 0,
  "new_project_finish": "2026-06-15",
  "original_project_finish": "2026-06-01",
  "schedule_extension_days": 14,
  "warnings": []
}
```

### Apply Leveling Shifts

Apply selected shifts to update activity dates:

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/level/apply \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "shifts": ["activity-uuid-1", "activity-uuid-2", "activity-uuid-3"]
  }'
```

### Apply Response

```json
{
  "applied_count": 3,
  "skipped_count": 0,
  "new_project_finish": "2026-06-15"
}
```

### Leveling Workflow Example

```python
import requests

BASE_URL = "https://api.defense-pm-tool.com/api/v1"
headers = {"Authorization": f"Bearer {token}"}

# 1. Check for over-allocations
histogram = requests.get(
    f"{BASE_URL}/programs/{program_id}/histogram",
    headers=headers
).json()

if histogram["summary"]["resources_with_overallocation"] > 0:
    print(f"Found {histogram['summary']['total_overallocated_days']} overallocated days")

    # 2. Preview leveling
    preview = requests.get(
        f"{BASE_URL}/programs/{program_id}/level/preview",
        headers=headers,
        params={"preserve_critical_path": True}
    ).json()

    print(f"Leveling would shift {preview['activities_shifted']} activities")
    print(f"Schedule extension: {preview['schedule_extension_days']} days")

    # 3. Run leveling
    result = requests.post(
        f"{BASE_URL}/programs/{program_id}/level",
        headers=headers,
        json={"preserve_critical_path": True}
    ).json()

    if result["success"]:
        # 4. Apply shifts
        shift_ids = [s["activity_id"] for s in result["shifts"]]
        applied = requests.post(
            f"{BASE_URL}/programs/{program_id}/level/apply",
            headers=headers,
            json={"shifts": shift_ids}
        ).json()

        print(f"Applied {applied['applied_count']} shifts")
        print(f"New project finish: {applied['new_project_finish']}")
```

---

## Baselines API

### Create Baseline

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/baselines \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "PMB v1.0",
    "description": "Initial Performance Measurement Baseline",
    "baseline_type": "pmb"
  }'
```

### List Baselines

```bash
curl https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/baselines \
  -H "Authorization: Bearer $TOKEN"
```

### Compare Baselines

```bash
curl "https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/baselines/compare?baseline_id=$ID1&compare_to=$ID2" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Monte Carlo Simulation

### Configure Activity Distributions

```bash
curl -X PATCH https://api.defense-pm-tool.com/api/v1/activities/$ACTIVITY_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "duration_optimistic": 8,
    "duration_most_likely": 10,
    "duration_pessimistic": 15,
    "distribution_type": "pert",
    "cost_optimistic": "120000.00",
    "cost_most_likely": "150000.00",
    "cost_pessimistic": "200000.00"
  }'
```

### Distribution Types

| Type | Description |
|------|-------------|
| `triangular` | Simple 3-point estimate |
| `pert` | Beta-PERT (weighted toward most likely) |
| `normal` | Gaussian distribution |
| `uniform` | Equal probability in range |

### Run Simulation

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/monte-carlo \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "iterations": 10000,
    "seed": 42,
    "include_cost": true,
    "correlation_enabled": true
  }'
```

### Simulation Response

```json
{
  "simulation_id": "uuid",
  "iterations": 10000,
  "duration_results": {
    "min": 420,
    "max": 510,
    "mean": 458.3,
    "median": 456,
    "std_dev": 18.5,
    "p50": 456,
    "p70": 468,
    "p80": 475,
    "p90": 485,
    "p95": 495
  },
  "cost_results": {
    "min": "4800000000.00",
    "max": "5800000000.00",
    "mean": "5250000000.00",
    "p80": "5450000000.00"
  },
  "sensitivity": [
    {"activity": "A-012", "correlation": 0.72},
    {"activity": "A-025", "correlation": 0.58}
  ]
}
```

---

## Scenario Planning

### Create Scenario

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/scenarios \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "program_id": "uuid",
    "name": "Schedule Acceleration Option",
    "description": "Evaluate adding second shift to critical path activities"
  }'
```

### Add Changes to Scenario

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/scenarios/$SCENARIO_ID/changes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "activity",
    "entity_id": "uuid-of-activity",
    "change_type": "update",
    "field_name": "duration",
    "old_value": {"value": 60},
    "new_value": {"value": 45}
  }'
```

### Simulate Scenario

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/scenarios/$SCENARIO_ID/simulate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "iterations": 1000,
    "compare_to_baseline": true
  }'
```

### Promote Scenario to Baseline

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/scenarios/$SCENARIO_ID/promote \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "baseline_name": "PMB v2.0 - Accelerated Schedule",
    "baseline_description": "Approved schedule with second shift added",
    "apply_to_program": true
  }'
```

---

## Reports API

### CPR Format 1 - WBS Summary

```bash
curl https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/reports/cpr/format1 \
  -H "Authorization: Bearer $TOKEN"
```

### CPR Format 3 - Baseline Changes

```bash
curl https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/reports/cpr/format3 \
  -H "Authorization: Bearer $TOKEN"
```

### CPR Format 5 - EVMS Summary

```bash
curl https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/reports/cpr/format5 \
  -H "Authorization: Bearer $TOKEN"
```

### Export to PDF

```bash
curl https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/reports/cpr/format5/pdf \
  -H "Authorization: Bearer $TOKEN" \
  -o cpr_format5_report.pdf
```

### S-Curve Export

```bash
# PNG image
curl https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/reports/scurve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: image/png" \
  -o scurve.png

# CSV data
curl https://api.defense-pm-tool.com/api/v1/programs/$PROGRAM_ID/reports/scurve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: text/csv" \
  -o scurve.csv
```

---

## Jira Integration

### Configure Integration

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/jira/integrations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "program_id": "uuid",
    "jira_url": "https://yourcompany.atlassian.net",
    "project_key": "F35",
    "email": "integration@company.com",
    "api_token": "your-jira-api-token",
    "sync_direction": "bidirectional"
  }'
```

### Trigger Manual Sync

```bash
curl -X POST https://api.defense-pm-tool.com/api/v1/jira/integrations/$INTEGRATION_ID/sync \
  -H "Authorization: Bearer $TOKEN"
```

### Sync Directions

| Direction | Description |
|-----------|-------------|
| `jira_to_dpm` | Jira issues update DPM activities |
| `dpm_to_jira` | DPM activities update Jira issues |
| `bidirectional` | Changes sync both ways |

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {"field": "duration", "message": "Must be positive integer"}
    ]
  }
}
```

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 400 | Bad Request | Invalid JSON, missing required fields |
| 401 | Unauthorized | Invalid/expired token, missing auth |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate entry, constraint violation |
| 422 | Validation Error | Invalid field values |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Server Error | Internal error, contact support |

### Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Input validation failed |
| `NOT_FOUND` | Resource not found |
| `UNAUTHORIZED` | Authentication required |
| `FORBIDDEN` | Permission denied |
| `CONFLICT` | Duplicate or constraint error |
| `CIRCULAR_DEPENDENCY` | Circular reference detected |
| `RATE_LIMITED` | Too many requests |

---

## Rate Limiting

### Limits

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Authentication | 5 | 1 minute |
| Read operations | 100 | 1 minute |
| Write operations | 30 | 1 minute |
| Simulations | 10 | 1 minute |
| Report generation | 5 | 1 minute |

### Rate Limit Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1706097600
```

### Handling Rate Limits

When rate limited (HTTP 429):

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests",
    "retry_after": 45
  }
}
```

Implement exponential backoff:

```python
import time
import requests

def api_request_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            time.sleep(retry_after)
            continue
        return response
    raise Exception("Max retries exceeded")
```

---

## API Reference

Full interactive API documentation:

- **Swagger UI**: https://api.defense-pm-tool.com/docs
- **ReDoc**: https://api.defense-pm-tool.com/redoc
- **OpenAPI JSON**: https://api.defense-pm-tool.com/openapi.json

---

*Defense PM Tool v1.1.0 - API Guide*
*Last Updated: February 2026*
