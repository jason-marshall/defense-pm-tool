# API Documentation

## Base URL

All API endpoints are prefixed with `/api/v1`.

## Authentication

Authentication uses JWT tokens. Include the token in the Authorization header:

```
Authorization: Bearer <access_token>
```

## Programs

### List Programs
```http
GET /api/v1/programs?page=1&page_size=20
```

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

## Activities

### List Activities
```http
GET /api/v1/activities?program_id={uuid}&page=1&page_size=50
```

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
  "budgeted_cost": "50000.00"
}
```

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

## Schedule

### Calculate Schedule
```http
POST /api/v1/schedule/calculate/{program_id}
```

### Get Critical Path
```http
GET /api/v1/schedule/critical-path/{program_id}
```

### Get Project Duration
```http
GET /api/v1/schedule/duration/{program_id}
```

## Error Responses

All errors return a consistent JSON structure:

```json
{
  "detail": "Human-readable error message",
  "code": "MACHINE_READABLE_CODE"
}
```

### HTTP Status Codes

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful deletion) |
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | Not Found |
| 409 | Conflict (duplicate) |
| 422 | Validation Error |
| 500 | Internal Server Error |
