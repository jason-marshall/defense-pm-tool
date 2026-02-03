# Security Controls

> **Last Updated**: March 2026
> **Version**: 1.2.0
> **Audit Status**: OWASP Top 10 2021 Compliant

---

## OWASP Top 10 2021 Compliance

This document outlines the security controls implemented in the Defense PM Tool API to address the OWASP Top 10 2021 vulnerabilities.

---

### A01: Broken Access Control

**Status**: Implemented

| Control | Implementation | Location |
|---------|----------------|----------|
| JWT Authentication | All API endpoints require valid JWT token | `src/core/deps.py:get_current_user` |
| Resource Ownership | Users can only access their own programs/resources | `src/api/v1/endpoints/*.py` |
| Role Verification | Admin actions require admin role | `src/core/deps.py` |

**Verification**:
- Unauthorized requests return 401
- Access to other users' resources returns 403/404
- All endpoints checked in `tests/security/test_owasp_audit.py`

---

### A02: Cryptographic Failures

**Status**: Implemented

| Control | Implementation | Location |
|---------|----------------|----------|
| Password Hashing | bcrypt with cost factor 12 | `src/core/auth.py:get_password_hash` |
| JWT Signing | HS256 algorithm with secret key | `src/core/auth.py:create_access_token` |
| Token Encryption | Fernet (AES-128) for Jira tokens | `src/services/jira_client.py` |
| API Key Hashing | SHA-256 hash for API key storage | `src/core/api_key.py` |
| No Sensitive Data in Logs | Passwords/tokens never logged | All logging calls |

**Verification**:
- Passwords not returned in API responses
- Tokens stored encrypted in database
- JWT tokens have expiration claims

---

### A03: Injection

**Status**: Implemented

| Control | Implementation | Location |
|---------|----------------|----------|
| SQL Injection Prevention | SQLAlchemy ORM with parameterized queries | `src/repositories/*.py` |
| Input Validation | Pydantic v2 schemas validate all input | `src/schemas/*.py` |
| XSS Prevention | HTML sanitization with bleach | Schema validators |
| Output Encoding | JSON responses properly encoded | FastAPI default |

**Verification**:
- SQL injection attempts safely handled
- XSS payloads sanitized or rejected
- Invalid input returns 422

---

### A04: Insecure Design

**Status**: Implemented

| Control | Implementation | Location |
|---------|----------------|----------|
| Defense in Depth | Multiple validation layers | Throughout codebase |
| Explicit Confirmation | Destructive ops require confirm=true | `scenarios.py:apply_scenario_changes` |
| Rate Limiting | All endpoints rate limited | `src/core/rate_limit.py` |
| Soft Deletes | Data preserved with deleted_at | `src/models/base.py` |

**Verification**:
- Apply scenario requires `confirm=true`
- Rate limits enforced (429 responses)
- Deleted data recoverable

---

### A05: Security Misconfiguration

**Status**: Implemented

| Control | Implementation | Location |
|---------|----------------|----------|
| Debug Mode Control | ENVIRONMENT variable controls debug | `src/core/config.py` |
| CORS Configuration | Allowed origins only | `src/main.py` |
| Error Handling | No stack traces in production | Exception handlers |
| Secure Headers | Security headers in responses | FastAPI middleware |

**Verification**:
- 404/500 errors don't leak stack traces
- CORS preflight works correctly
- Production environment has debug=false

---

### A06: Vulnerable and Outdated Components

**Status**: Partially Implemented

| Control | Implementation | Location |
|---------|----------------|----------|
| Dependency Pinning | Versions pinned in requirements.txt | `requirements.txt` |
| Dependency Scanning | Run pip-audit regularly | CI/CD pipeline |

**Recommendations**:
```bash
# Scan for vulnerabilities
pip install pip-audit
pip-audit

# Update dependencies
pip install --upgrade -r requirements.txt
```

**Current Dependencies** (key security-related):
- `pyjwt>=2.8.0` - JWT handling
- `bcrypt>=4.1.0` - Password hashing
- `cryptography>=42.0.0` - Token encryption
- `pydantic>=2.5.0` - Input validation

---

### A07: Identification and Authentication Failures

**Status**: Implemented

| Control | Implementation | Location |
|---------|----------------|----------|
| Auth Rate Limiting | 10 requests/minute on login | `src/core/rate_limit.py` |
| Token Expiration | 30 minute default (configurable) | `src/core/config.py` |
| Password Requirements | Minimum length enforced | `src/schemas/user.py` |
| Session Management | Stateless JWT (no session fixation) | `src/core/auth.py` |

**Verification**:
- Brute force attempts blocked after 10 tries
- Expired tokens rejected with 401
- Invalid credentials don't reveal user existence

---

### A08: Software and Data Integrity Failures

**Status**: Implemented

| Control | Implementation | Location |
|---------|----------------|----------|
| Baseline Immutability | Promoted scenarios locked | `src/services/scenario_promotion.py` |
| Audit Trail | created_at/updated_at on all records | `src/models/base.py` |
| Report Checksums | Report audit with checksums | `src/models/report_audit.py` |
| Change Tracking | Scenario changes tracked | `src/models/scenario.py` |

**Verification**:
- Promoted scenarios return 422 on modification attempts
- All records have timestamps
- Reports have audit trail

---

### A09: Security Logging and Monitoring Failures

**Status**: Implemented

| Control | Implementation | Location |
|---------|----------------|----------|
| Structured Logging | structlog with context | `src/core/logging.py` |
| Auth Event Logging | Login success/failure logged | `src/api/v1/endpoints/auth.py` |
| Sync Audit Logging | Jira sync operations logged | `src/models/jira_integration.py` |
| Error Logging | All exceptions logged | Exception handlers |

**Log Events Captured**:
- Authentication attempts (success/failure)
- Resource access attempts
- Data modifications
- External API calls (Jira)
- System errors

---

### A10: Server-Side Request Forgery (SSRF)

**Status**: Implemented

| Control | Implementation | Location |
|---------|----------------|----------|
| URL Validation | Jira base URL validated | `src/services/jira_client.py` |
| No Arbitrary Fetching | URLs must match configured base | `JiraClient.__init__` |
| Webhook Validation | Jira webhooks validated | `src/services/jira_webhook_processor.py` |

**Verification**:
- Only configured Jira instance accessible
- Arbitrary URLs rejected
- Webhook signatures validated

---

## Security Testing

### Running Security Tests

```bash
cd api

# Run OWASP security tests
pytest tests/security -v

# Run with coverage
pytest tests/security --cov=src --cov-report=term-missing

# Run specific category
pytest tests/security/test_owasp_audit.py::TestA03Injection -v
```

### Automated Security Scanning

```bash
# Dependency vulnerability scan
pip install pip-audit
pip-audit

# Static analysis
bandit -r src/

# Secret scanning
pip install detect-secrets
detect-secrets scan
```

---

## Security Configuration

### Environment Variables

| Variable | Description | Default | Security Note |
|----------|-------------|---------|---------------|
| `SECRET_KEY` | JWT signing key | Required | Use strong random value |
| `DATABASE_URL` | DB connection | Required | Use SSL in production |
| `REDIS_URL` | Cache connection | Optional | Use TLS in production |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | true | Keep enabled in production |
| `ENVIRONMENT` | Runtime environment | development | Set to "production" |
| `CORS_ORIGINS` | Allowed origins | localhost | Configure for your domain |

### Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Set strong `SECRET_KEY` (32+ random bytes)
- [ ] Configure `CORS_ORIGINS` for your domain only
- [ ] Enable `RATE_LIMIT_ENABLED=true`
- [ ] Use HTTPS only
- [ ] Configure database with SSL
- [ ] Set up log aggregation
- [ ] Enable security headers
- [ ] Run pip-audit before deployment

---

## Incident Response

### Security Contact

Report security vulnerabilities to: security@example.com

### Response Process

1. **Acknowledge** - Confirm receipt within 24 hours
2. **Assess** - Evaluate severity and impact
3. **Remediate** - Fix vulnerability
4. **Disclose** - Coordinate responsible disclosure

---

## Audit History

| Date | Auditor | Findings | Status |
|------|---------|----------|--------|
| January 2026 | Automated | 0 Critical, 0 High | PASS |
| March 2026 | Automated (v1.2.0) | 0 Critical, 0 High | PASS |

---

*This document is part of the Defense PM Tool security documentation.*
*Last security audit: March 2026 (v1.2.0)*
