# Defense PM Tool - API Reference

Complete REST API documentation for the Defense Program Management Tool.

## Base URL

All API endpoints are prefixed with `/api/v1`.

**Development**: `http://localhost:8000/api/v1`
**Production**: `https://your-domain.com/api/v1`

## Authentication

Authentication uses JWT tokens. Include the token in the Authorization header:

```
Authorization: Bearer <access_token>
```

### Auth Endpoints

#### Register User
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securePassword123!",
  "full_name": "John Doe"
}
```

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securePassword123!
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "refresh_token": "eyJhbGciOiJIUzI1...",
  "token_type": "bearer"
}
```

#### Refresh Token
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1..."
}
```

#### Get Current User
```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

---

## Programs

### List Programs
```http
GET /api/v1/programs?page=1&page_size=20
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| page_size | int | 20 | Items per page (max 100) |

### Get Program
```http
GET /api/v1/programs/{program_id}
```

### Create Program
```http
POST /api/v1/programs
Content-Type: application/json

{
  "name": "F-35 Modernization",
  "code": "F35-MOD-001",
  "description": "F-35 Block 4 upgrade program",
  "planned_start_date": "2024-01-01",
  "planned_end_date": "2026-12-31",
  "budget_at_completion": "500000000.00",
  "contract_number": "FA8650-21-C-1234",
  "contract_type": "CPIF"
}
```

**Contract Types:** `FFP`, `CPFF`, `CPIF`, `CPAF`, `T&M`, `FPI`

### Update Program
```http
PATCH /api/v1/programs/{program_id}
Content-Type: application/json

{
  "name": "Updated Program Name"
}
```

### Delete Program
```http
DELETE /api/v1/programs/{program_id}
```

---

## WBS (Work Breakdown Structure)

WBS elements use PostgreSQL ltree for efficient hierarchy queries.

### List WBS Elements
```http
GET /api/v1/wbs?program_id={uuid}
```

### Get WBS Tree
```http
GET /api/v1/wbs/tree?program_id={uuid}
```

Returns WBS elements as a hierarchical tree structure with nested children.

### Get WBS Element
```http
GET /api/v1/wbs/{element_id}
```

### Create WBS Element
```http
POST /api/v1/wbs
Content-Type: application/json

{
  "program_id": "uuid",
  "name": "Systems Engineering",
  "wbs_code": "1.1",
  "parent_id": "uuid",  // Optional - null for root elements
  "description": "Systems engineering activities"
}
```

### Update WBS Element
```http
PATCH /api/v1/wbs/{element_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "description": "Updated description"
}
```

### Delete WBS Element
```http
DELETE /api/v1/wbs/{element_id}
```

Deletes the element and all its children.

---

## Activities

### List Activities
```http
GET /api/v1/activities?program_id={uuid}&page=1&page_size=50
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| program_id | uuid | required | Filter by program |
| page | int | 1 | Page number |
| page_size | int | 50 | Items per page (max 100) |

### Get Activity
```http
GET /api/v1/activities/{activity_id}
```

### Create Activity
```http
POST /api/v1/activities
Content-Type: application/json

{
  "program_id": "uuid",
  "name": "Design Review",
  "code": "DR-001",
  "duration": 10,
  "budgeted_cost": "50000.00",
  "wbs_element_id": "uuid",  // Optional
  "is_milestone": false,
  "constraint_type": "ASAP",  // ASAP, SNET, SNLT, FNET, FNLT, MSO, MFO
  "constraint_date": null
}
```

### Update Activity
```http
PATCH /api/v1/activities/{activity_id}
Content-Type: application/json

{
  "duration": 15,
  "budgeted_cost": "75000.00"
}
```

### Delete Activity
```http
DELETE /api/v1/activities/{activity_id}
```

---

## Dependencies

### List Dependencies for Activity
```http
GET /api/v1/dependencies/activity/{activity_id}
```

### Create Dependency
```http
POST /api/v1/dependencies
Content-Type: application/json

{
  "predecessor_id": "uuid",
  "successor_id": "uuid",
  "dependency_type": "FS",
  "lag": 0
}
```

**Dependency Types:**
| Type | Name | Description |
|------|------|-------------|
| FS | Finish-to-Start | Successor starts when predecessor finishes (most common) |
| SS | Start-to-Start | Successor starts when predecessor starts |
| FF | Finish-to-Finish | Successor finishes when predecessor finishes |
| SF | Start-to-Finish | Successor finishes when predecessor starts (rare) |

**Lag:** Positive = delay, Negative = lead time (overlap)

### Update Dependency
```http
PATCH /api/v1/dependencies/{dependency_id}
Content-Type: application/json

{
  "lag": 2
}
```

### Delete Dependency
```http
DELETE /api/v1/dependencies/{dependency_id}
```

---

## Schedule (CPM Engine)

### Calculate Schedule
```http
POST /api/v1/schedule/calculate/{program_id}?force_recalculate=false
```

Performs Critical Path Method (CPM) calculation including:
- Forward pass (Early Start/Early Finish)
- Backward pass (Late Start/Late Finish)
- Float calculation
- Critical path identification

Results are cached in Redis (1 hour TTL). Use `force_recalculate=true` to bypass cache.

**Response:**
```json
[
  {
    "activity_id": "uuid",
    "early_start": 0,
    "early_finish": 10,
    "late_start": 0,
    "late_finish": 10,
    "total_float": 0,
    "free_float": 0,
    "is_critical": true
  }
]
```

### Get Critical Path
```http
GET /api/v1/schedule/critical-path/{program_id}
```

Returns list of activities on the critical path (zero total float).

### Get Project Duration
```http
GET /api/v1/schedule/duration/{program_id}
```

Returns the total project duration in days.

---

## EVMS (Earned Value Management System)

### Get EVMS Summary Dashboard
```http
GET /api/v1/evms/summary/{program_id}
```

Returns comprehensive EVMS metrics including:
- Current period values (BCWS, BCWP, ACWP)
- Cumulative values
- Variance analysis (CV, SV)
- Performance indices (CPI, SPI)
- Estimates (EAC, ETC, VAC, TCPI)
- Trend data for charts

**Response (truncated):**
```json
{
  "program_id": "uuid",
  "program_name": "F-35 Modernization",
  "period_name": "January 2024",
  "current_period": {
    "bcws": "1000000.00",
    "bcwp": "950000.00",
    "acwp": "1020000.00"
  },
  "cumulative": {
    "bcws": "5000000.00",
    "bcwp": "4750000.00",
    "acwp": "5100000.00"
  },
  "variances": {
    "cv": "-350000.00",
    "cv_percent": "-7.37",
    "sv": "-250000.00",
    "sv_percent": "-5.00"
  },
  "indices": {
    "cpi": "0.93",
    "spi": "0.95"
  },
  "estimates": {
    "bac": "50000000.00",
    "eac": "53763441.00",
    "etc": "48663441.00",
    "vac": "-3763441.00",
    "tcpi": "1.08"
  },
  "trends": {
    "periods": ["Oct 2023", "Nov 2023", "Dec 2023", "Jan 2024"],
    "cpi_values": ["0.98", "0.96", "0.94", "0.93"],
    "spi_values": ["0.99", "0.97", "0.96", "0.95"]
  }
}
```

### List EVMS Periods
```http
GET /api/v1/evms/periods/{program_id}
```

### Create EVMS Period
```http
POST /api/v1/evms/periods
Content-Type: application/json

{
  "program_id": "uuid",
  "period_name": "January 2024",
  "period_start": "2024-01-01",
  "period_end": "2024-01-31"
}
```

### Get Period Data
```http
GET /api/v1/evms/periods/{period_id}/data
```

### Update Period Data
```http
PUT /api/v1/evms/periods/{period_id}/data
Content-Type: application/json

{
  "data": [
    {
      "wbs_element_id": "uuid",
      "bcws": "100000.00",
      "bcwp": "95000.00",
      "acwp": "102000.00"
    }
  ]
}
```

### Approve Period
```http
POST /api/v1/evms/periods/{period_id}/approve
```

---

## Import/Export

### Import MS Project XML
```http
POST /api/v1/import/msproject/{program_id}?preview=false
Content-Type: multipart/form-data

file: <MS Project XML file>
```

**Supported formats:** MS Project 2010-2021 XML export (.xml)

**Imported data:**
- Tasks (as activities)
- Predecessor links (as dependencies)
- WBS structure
- Milestones
- Constraints

**Not imported (logged as warnings):**
- Resources and assignments
- Calendars
- Custom fields
- Cost data

**Preview mode:** Set `preview=true` to parse and preview without saving.

**Preview Response:**
```json
{
  "preview": true,
  "project_name": "Sample Project",
  "start_date": "2024-01-01",
  "finish_date": "2024-12-31",
  "task_count": 150,
  "tasks": [
    {
      "name": "Design Phase",
      "wbs": "1.1",
      "duration_hours": 240,
      "is_milestone": false,
      "predecessors": 1
    }
  ],
  "warnings": ["Resources not imported", "Calendars not imported"]
}
```

**Import Response:**
```json
{
  "success": true,
  "program_id": "uuid",
  "tasks_imported": 150,
  "dependencies_imported": 200,
  "wbs_elements_created": 25,
  "warnings": ["3 tasks had unsupported constraint types"],
  "errors": []
}
```

### Export CSV (Coming Soon)
```http
GET /api/v1/import/export/{program_id}/csv
```

---

## Reports

### Get Report Summary
```http
GET /api/v1/reports/summary/{program_id}
```

Returns available reports and periods for a program.

### Generate CPR Format 1 (JSON)
```http
GET /api/v1/reports/cpr/{program_id}?period_id={uuid}
```

Generates Contract Performance Report Format 1 (WBS Summary).

If `period_id` is not specified, uses the latest approved period.

### Generate CPR Format 1 (HTML)
```http
GET /api/v1/reports/cpr/{program_id}/html?period_id={uuid}
```

Returns printable HTML report.

---

## Health & Status

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development"
}
```

### Root
```http
GET /
```

**Response:**
```json
{
  "name": "Defense PM Tool API",
  "version": "0.1.0",
  "docs": "/docs",
  "health": "/health"
}
```

### OpenAPI Documentation
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

---

## Error Responses

All errors return a consistent JSON structure:

```json
{
  "detail": "Human-readable error message",
  "code": "MACHINE_READABLE_CODE"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 422 | Invalid input data |
| NOT_FOUND | 404 | Resource not found |
| CONFLICT | 409 | Resource conflict (duplicate) |
| CIRCULAR_DEPENDENCY | 400 | Circular dependency in schedule |
| SCHEDULE_CALCULATION_ERROR | 400 | Error during CPM calculation |
| AUTHENTICATION_ERROR | 401 | Invalid or missing credentials |
| AUTHORIZATION_ERROR | 403 | Insufficient permissions |
| INTERNAL_SERVER_ERROR | 500 | Unexpected server error |

### HTTP Status Codes

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful deletion) |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict (duplicate) |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

## Rate Limiting

Authentication endpoints are rate limited:
- `/auth/login`: 5 requests per minute per IP
- `/auth/register`: 10 requests per hour per IP

---

## Pagination

List endpoints support pagination with consistent parameters:

```http
GET /api/v1/programs?page=1&page_size=20
```

**Response:**
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "pages": 8
}
```

---

## Versioning

The API is versioned in the URL path (`/api/v1`). Breaking changes will be introduced in new API versions.

---

*Last updated: January 2026*
