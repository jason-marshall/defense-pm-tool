"""Security audit utilities for OWASP compliance verification.

This module provides utilities for tracking security findings,
generating audit reports, and verifying OWASP Top 10 2021 compliance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class OWASPCategory(str, Enum):
    """OWASP Top 10 2021 categories."""

    A01_BROKEN_ACCESS_CONTROL = "A01:2021"
    A02_CRYPTOGRAPHIC_FAILURES = "A02:2021"
    A03_INJECTION = "A03:2021"
    A04_INSECURE_DESIGN = "A04:2021"
    A05_SECURITY_MISCONFIGURATION = "A05:2021"
    A06_VULNERABLE_COMPONENTS = "A06:2021"
    A07_AUTH_FAILURES = "A07:2021"
    A08_DATA_INTEGRITY_FAILURES = "A08:2021"
    A09_LOGGING_FAILURES = "A09:2021"
    A10_SSRF = "A10:2021"


class Severity(str, Enum):
    """Security finding severity levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class FindingStatus(str, Enum):
    """Security finding status."""

    OPEN = "OPEN"
    FIXED = "FIXED"
    ACCEPTED = "ACCEPTED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


@dataclass
class SecurityFinding:
    """Security audit finding.

    Attributes:
        category: OWASP Top 10 category
        severity: Finding severity level
        title: Short title describing the finding
        description: Detailed description of the vulnerability
        location: File/endpoint where finding was identified
        remediation: Recommended fix
        status: Current status of the finding
        cwe_id: Common Weakness Enumeration ID (optional)
        evidence: Supporting evidence (optional)
    """

    category: OWASPCategory
    severity: Severity
    title: str
    description: str
    location: str
    remediation: str
    status: FindingStatus = FindingStatus.OPEN
    cwe_id: str | None = None
    evidence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "remediation": self.remediation,
            "status": self.status.value,
            "cwe_id": self.cwe_id,
            "evidence": self.evidence,
        }


@dataclass
class SecurityControl:
    """Security control implementation.

    Attributes:
        category: OWASP Top 10 category this control addresses
        name: Control name
        description: What the control does
        implemented: Whether control is implemented
        location: Where the control is implemented
        verification: How to verify the control works
    """

    category: OWASPCategory
    name: str
    description: str
    implemented: bool
    location: str
    verification: str

    def to_dict(self) -> dict[str, Any]:
        """Convert control to dictionary."""
        return {
            "category": self.category.value,
            "name": self.name,
            "description": self.description,
            "implemented": self.implemented,
            "location": self.location,
            "verification": self.verification,
        }


@dataclass
class SecurityAuditReport:
    """Complete security audit report.

    Attributes:
        findings: List of security findings
        controls: List of security controls
        passed_checks: List of checks that passed
        audit_date: Date of the audit
        auditor: Who performed the audit
        version: Application version audited
    """

    findings: list[SecurityFinding] = field(default_factory=list)
    controls: list[SecurityControl] = field(default_factory=list)
    passed_checks: list[str] = field(default_factory=list)
    audit_date: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    auditor: str = "Automated"
    version: str = "1.0.0"

    @property
    def critical_count(self) -> int:
        """Count of critical findings."""
        return len([f for f in self.findings if f.severity == Severity.CRITICAL])

    @property
    def high_count(self) -> int:
        """Count of high severity findings."""
        return len([f for f in self.findings if f.severity == Severity.HIGH])

    @property
    def medium_count(self) -> int:
        """Count of medium severity findings."""
        return len([f for f in self.findings if f.severity == Severity.MEDIUM])

    @property
    def low_count(self) -> int:
        """Count of low severity findings."""
        return len([f for f in self.findings if f.severity == Severity.LOW])

    @property
    def open_findings(self) -> list[SecurityFinding]:
        """Get all open findings."""
        return [f for f in self.findings if f.status == FindingStatus.OPEN]

    @property
    def is_release_ready(self) -> bool:
        """Check if safe to release (no critical/high open findings)."""
        open_critical_high = [
            f for f in self.open_findings if f.severity in [Severity.CRITICAL, Severity.HIGH]
        ]
        return len(open_critical_high) == 0

    def add_finding(self, finding: SecurityFinding) -> None:
        """Add a security finding."""
        self.findings.append(finding)

    def add_control(self, control: SecurityControl) -> None:
        """Add a security control."""
        self.controls.append(control)

    def add_passed_check(self, check: str) -> None:
        """Add a passed check."""
        self.passed_checks.append(check)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "audit_date": self.audit_date,
            "auditor": self.auditor,
            "version": self.version,
            "summary": {
                "total_findings": len(self.findings),
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "open": len(self.open_findings),
                "release_ready": self.is_release_ready,
            },
            "findings": [f.to_dict() for f in self.findings],
            "controls": [c.to_dict() for c in self.controls],
            "passed_checks": self.passed_checks,
        }


def get_owasp_controls() -> list[SecurityControl]:
    """Get all implemented security controls.

    Returns:
        List of security controls implemented in the application.
    """
    return [
        # A01: Broken Access Control
        SecurityControl(
            category=OWASPCategory.A01_BROKEN_ACCESS_CONTROL,
            name="JWT Authentication",
            description="All API endpoints require valid JWT token",
            implemented=True,
            location="src/core/deps.py:get_current_user",
            verification="Unauthorized requests return 401",
        ),
        SecurityControl(
            category=OWASPCategory.A01_BROKEN_ACCESS_CONTROL,
            name="Resource Ownership Verification",
            description="Users can only access their own resources",
            implemented=True,
            location="src/api/v1/endpoints/*.py",
            verification="Access to other users' resources returns 403/404",
        ),
        # A02: Cryptographic Failures
        SecurityControl(
            category=OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
            name="Password Hashing",
            description="Passwords hashed with bcrypt (cost factor 12)",
            implemented=True,
            location="src/core/auth.py:get_password_hash",
            verification="Passwords not stored in plaintext",
        ),
        SecurityControl(
            category=OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
            name="JWT Token Signing",
            description="JWT tokens signed with HS256 algorithm",
            implemented=True,
            location="src/core/auth.py:create_access_token",
            verification="Tokens cannot be forged",
        ),
        SecurityControl(
            category=OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
            name="API Token Encryption",
            description="Jira API tokens encrypted with Fernet (AES-128)",
            implemented=True,
            location="src/services/jira_client.py",
            verification="Tokens stored encrypted in database",
        ),
        # A03: Injection
        SecurityControl(
            category=OWASPCategory.A03_INJECTION,
            name="SQL Injection Prevention",
            description="SQLAlchemy ORM with parameterized queries",
            implemented=True,
            location="src/repositories/*.py",
            verification="SQL injection attempts safely handled",
        ),
        SecurityControl(
            category=OWASPCategory.A03_INJECTION,
            name="Input Validation",
            description="Pydantic schemas validate all input",
            implemented=True,
            location="src/schemas/*.py",
            verification="Invalid input rejected with 422",
        ),
        SecurityControl(
            category=OWASPCategory.A03_INJECTION,
            name="XSS Prevention",
            description="HTML sanitization for user input",
            implemented=True,
            location="src/schemas/*.py (validators)",
            verification="Script tags stripped from input",
        ),
        # A04: Insecure Design
        SecurityControl(
            category=OWASPCategory.A04_INSECURE_DESIGN,
            name="Explicit Confirmation",
            description="Destructive operations require confirmation",
            implemented=True,
            location="src/api/v1/endpoints/scenarios.py:apply_scenario_changes",
            verification="Apply requires confirm=true",
        ),
        SecurityControl(
            category=OWASPCategory.A04_INSECURE_DESIGN,
            name="Rate Limiting",
            description="Rate limiting on all endpoints",
            implemented=True,
            location="src/core/rate_limit.py",
            verification="Excessive requests return 429",
        ),
        # A05: Security Misconfiguration
        SecurityControl(
            category=OWASPCategory.A05_SECURITY_MISCONFIGURATION,
            name="Debug Mode Control",
            description="Debug mode controlled by ENVIRONMENT variable",
            implemented=True,
            location="src/core/config.py",
            verification="Production has debug disabled",
        ),
        SecurityControl(
            category=OWASPCategory.A05_SECURITY_MISCONFIGURATION,
            name="CORS Configuration",
            description="CORS configured for allowed origins only",
            implemented=True,
            location="src/main.py",
            verification="Cross-origin requests validated",
        ),
        # A06: Vulnerable Components
        SecurityControl(
            category=OWASPCategory.A06_VULNERABLE_COMPONENTS,
            name="Dependency Tracking",
            description="Dependencies pinned in requirements.txt",
            implemented=True,
            location="requirements.txt",
            verification="Run pip-audit for vulnerability scan",
        ),
        # A07: Authentication Failures
        SecurityControl(
            category=OWASPCategory.A07_AUTH_FAILURES,
            name="Auth Rate Limiting",
            description="Login endpoint rate limited (10/minute)",
            implemented=True,
            location="src/core/rate_limit.py:RATE_LIMIT_AUTH",
            verification="Brute force attempts blocked",
        ),
        SecurityControl(
            category=OWASPCategory.A07_AUTH_FAILURES,
            name="Token Expiration",
            description="JWT tokens expire (configurable, default 30 min)",
            implemented=True,
            location="src/core/config.py:ACCESS_TOKEN_EXPIRE_MINUTES",
            verification="Expired tokens rejected",
        ),
        # A08: Data Integrity Failures
        SecurityControl(
            category=OWASPCategory.A08_DATA_INTEGRITY_FAILURES,
            name="Baseline Immutability",
            description="Baseline snapshots cannot be modified",
            implemented=True,
            location="src/services/scenario_promotion.py",
            verification="Promoted scenarios locked",
        ),
        SecurityControl(
            category=OWASPCategory.A08_DATA_INTEGRITY_FAILURES,
            name="Audit Trail",
            description="All changes tracked with timestamps and user",
            implemented=True,
            location="src/models/base.py:created_at, updated_at",
            verification="Report audit table tracks changes",
        ),
        # A09: Logging Failures
        SecurityControl(
            category=OWASPCategory.A09_LOGGING_FAILURES,
            name="Structured Logging",
            description="Structured logging with structlog",
            implemented=True,
            location="src/core/logging.py",
            verification="All events logged with context",
        ),
        SecurityControl(
            category=OWASPCategory.A09_LOGGING_FAILURES,
            name="Auth Event Logging",
            description="Authentication failures logged",
            implemented=True,
            location="src/api/v1/endpoints/auth.py",
            verification="Failed logins appear in logs",
        ),
        # A10: SSRF
        SecurityControl(
            category=OWASPCategory.A10_SSRF,
            name="URL Validation",
            description="Jira URLs validated against configured base URL",
            implemented=True,
            location="src/services/jira_client.py",
            verification="Arbitrary URLs rejected",
        ),
    ]


def run_security_audit() -> SecurityAuditReport:
    """Run a security audit and generate report.

    Returns:
        SecurityAuditReport with all findings and controls.
    """
    report = SecurityAuditReport()

    # Add all implemented controls
    for control in get_owasp_controls():
        report.add_control(control)
        if control.implemented:
            report.add_passed_check(f"{control.category.value}: {control.name}")

    # Note: Actual vulnerability scanning would be done by security tests
    # This function provides the framework for tracking findings

    return report
