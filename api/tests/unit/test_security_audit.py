"""Unit tests for security audit module."""

import pytest

from src.core.security_audit import (
    FindingStatus,
    OWASPCategory,
    SecurityAuditReport,
    SecurityControl,
    SecurityFinding,
    Severity,
    get_owasp_controls,
    run_security_audit,
)


class TestOWASPCategory:
    """Tests for OWASPCategory enum."""

    def test_all_categories_exist(self):
        """All OWASP Top 10 2021 categories should exist."""
        assert OWASPCategory.A01_BROKEN_ACCESS_CONTROL.value == "A01:2021"
        assert OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES.value == "A02:2021"
        assert OWASPCategory.A03_INJECTION.value == "A03:2021"
        assert OWASPCategory.A04_INSECURE_DESIGN.value == "A04:2021"
        assert OWASPCategory.A05_SECURITY_MISCONFIGURATION.value == "A05:2021"
        assert OWASPCategory.A06_VULNERABLE_COMPONENTS.value == "A06:2021"
        assert OWASPCategory.A07_AUTH_FAILURES.value == "A07:2021"
        assert OWASPCategory.A08_DATA_INTEGRITY_FAILURES.value == "A08:2021"
        assert OWASPCategory.A09_LOGGING_FAILURES.value == "A09:2021"
        assert OWASPCategory.A10_SSRF.value == "A10:2021"

    def test_category_count(self):
        """Should have 10 categories."""
        assert len(OWASPCategory) == 10


class TestSeverity:
    """Tests for Severity enum."""

    def test_all_severities(self):
        """All severity levels should exist."""
        assert Severity.CRITICAL.value == "CRITICAL"
        assert Severity.HIGH.value == "HIGH"
        assert Severity.MEDIUM.value == "MEDIUM"
        assert Severity.LOW.value == "LOW"
        assert Severity.INFO.value == "INFO"

    def test_severity_count(self):
        """Should have 5 severity levels."""
        assert len(Severity) == 5


class TestFindingStatus:
    """Tests for FindingStatus enum."""

    def test_all_statuses(self):
        """All statuses should exist."""
        assert FindingStatus.OPEN.value == "OPEN"
        assert FindingStatus.FIXED.value == "FIXED"
        assert FindingStatus.ACCEPTED.value == "ACCEPTED"
        assert FindingStatus.FALSE_POSITIVE.value == "FALSE_POSITIVE"

    def test_status_count(self):
        """Should have 4 statuses."""
        assert len(FindingStatus) == 4


class TestSecurityFinding:
    """Tests for SecurityFinding dataclass."""

    def test_finding_creation(self):
        """Test basic finding creation."""
        finding = SecurityFinding(
            category=OWASPCategory.A03_INJECTION,
            severity=Severity.HIGH,
            title="SQL Injection Vulnerability",
            description="User input not sanitized in query",
            location="src/api/v1/endpoints/users.py:45",
            remediation="Use parameterized queries",
        )

        assert finding.category == OWASPCategory.A03_INJECTION
        assert finding.severity == Severity.HIGH
        assert finding.title == "SQL Injection Vulnerability"
        assert finding.status == FindingStatus.OPEN  # Default

    def test_finding_with_optional_fields(self):
        """Test finding with optional fields."""
        finding = SecurityFinding(
            category=OWASPCategory.A01_BROKEN_ACCESS_CONTROL,
            severity=Severity.CRITICAL,
            title="Missing Auth Check",
            description="Endpoint lacks authentication",
            location="src/api/v1/endpoints/admin.py:10",
            remediation="Add authentication decorator",
            cwe_id="CWE-862",
            evidence="curl -X GET /api/admin returns 200",
        )

        assert finding.cwe_id == "CWE-862"
        assert finding.evidence is not None

    def test_finding_to_dict(self):
        """Test converting finding to dictionary."""
        finding = SecurityFinding(
            category=OWASPCategory.A07_AUTH_FAILURES,
            severity=Severity.MEDIUM,
            title="Weak Password Policy",
            description="Passwords require only 6 characters",
            location="src/schemas/user.py",
            remediation="Require minimum 8 characters with complexity",
            status=FindingStatus.FIXED,
        )

        result = finding.to_dict()

        assert result["category"] == "A07:2021"
        assert result["severity"] == "MEDIUM"
        assert result["status"] == "FIXED"
        assert result["title"] == "Weak Password Policy"

    def test_finding_with_fixed_status(self):
        """Test finding with fixed status."""
        finding = SecurityFinding(
            category=OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
            severity=Severity.HIGH,
            title="Hardcoded Secret",
            description="Secret key in source code",
            location="src/core/config.py",
            remediation="Use environment variable",
            status=FindingStatus.FIXED,
        )

        assert finding.status == FindingStatus.FIXED


class TestSecurityControl:
    """Tests for SecurityControl dataclass."""

    def test_control_creation(self):
        """Test basic control creation."""
        control = SecurityControl(
            category=OWASPCategory.A01_BROKEN_ACCESS_CONTROL,
            name="JWT Authentication",
            description="All endpoints require valid JWT",
            implemented=True,
            location="src/core/deps.py",
            verification="401 returned without token",
        )

        assert control.category == OWASPCategory.A01_BROKEN_ACCESS_CONTROL
        assert control.name == "JWT Authentication"
        assert control.implemented is True

    def test_control_not_implemented(self):
        """Test control marked as not implemented."""
        control = SecurityControl(
            category=OWASPCategory.A10_SSRF,
            name="URL Allowlist",
            description="Only allow specific external URLs",
            implemented=False,
            location="src/services/webhook.py",
            verification="N/A - not yet implemented",
        )

        assert control.implemented is False

    def test_control_to_dict(self):
        """Test converting control to dictionary."""
        control = SecurityControl(
            category=OWASPCategory.A03_INJECTION,
            name="Input Validation",
            description="Pydantic validates all input",
            implemented=True,
            location="src/schemas/*.py",
            verification="Invalid input returns 422",
        )

        result = control.to_dict()

        assert result["category"] == "A03:2021"
        assert result["name"] == "Input Validation"
        assert result["implemented"] is True


class TestSecurityAuditReport:
    """Tests for SecurityAuditReport dataclass."""

    def test_empty_report(self):
        """Test empty report creation."""
        report = SecurityAuditReport()

        assert len(report.findings) == 0
        assert len(report.controls) == 0
        assert len(report.passed_checks) == 0
        assert report.auditor == "Automated"
        assert report.version == "1.0.0"

    def test_report_with_custom_values(self):
        """Test report with custom auditor and version."""
        report = SecurityAuditReport(
            auditor="Security Team",
            version="1.2.0",
        )

        assert report.auditor == "Security Team"
        assert report.version == "1.2.0"

    def test_add_finding(self):
        """Test adding findings to report."""
        report = SecurityAuditReport()
        finding = SecurityFinding(
            category=OWASPCategory.A03_INJECTION,
            severity=Severity.HIGH,
            title="Test Finding",
            description="Description",
            location="test.py",
            remediation="Fix it",
        )

        report.add_finding(finding)

        assert len(report.findings) == 1
        assert report.findings[0].title == "Test Finding"

    def test_add_control(self):
        """Test adding controls to report."""
        report = SecurityAuditReport()
        control = SecurityControl(
            category=OWASPCategory.A01_BROKEN_ACCESS_CONTROL,
            name="Test Control",
            description="Description",
            implemented=True,
            location="test.py",
            verification="Test",
        )

        report.add_control(control)

        assert len(report.controls) == 1
        assert report.controls[0].name == "Test Control"

    def test_add_passed_check(self):
        """Test adding passed checks."""
        report = SecurityAuditReport()
        report.add_passed_check("A01:2021: JWT Authentication")
        report.add_passed_check("A03:2021: SQL Injection Prevention")

        assert len(report.passed_checks) == 2

    def test_critical_count(self):
        """Test counting critical findings."""
        report = SecurityAuditReport()

        # Add findings with different severities
        for severity in [Severity.CRITICAL, Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM]:
            report.add_finding(
                SecurityFinding(
                    category=OWASPCategory.A03_INJECTION,
                    severity=severity,
                    title=f"{severity.value} Finding",
                    description="Test",
                    location="test.py",
                    remediation="Fix",
                )
            )

        assert report.critical_count == 2

    def test_high_count(self):
        """Test counting high severity findings."""
        report = SecurityAuditReport()

        report.add_finding(
            SecurityFinding(
                category=OWASPCategory.A01_BROKEN_ACCESS_CONTROL,
                severity=Severity.HIGH,
                title="High 1",
                description="Test",
                location="test.py",
                remediation="Fix",
            )
        )
        report.add_finding(
            SecurityFinding(
                category=OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
                severity=Severity.HIGH,
                title="High 2",
                description="Test",
                location="test.py",
                remediation="Fix",
            )
        )
        report.add_finding(
            SecurityFinding(
                category=OWASPCategory.A03_INJECTION,
                severity=Severity.MEDIUM,
                title="Medium 1",
                description="Test",
                location="test.py",
                remediation="Fix",
            )
        )

        assert report.high_count == 2

    def test_medium_count(self):
        """Test counting medium severity findings."""
        report = SecurityAuditReport()

        for i in range(3):
            report.add_finding(
                SecurityFinding(
                    category=OWASPCategory.A04_INSECURE_DESIGN,
                    severity=Severity.MEDIUM,
                    title=f"Medium {i}",
                    description="Test",
                    location="test.py",
                    remediation="Fix",
                )
            )

        assert report.medium_count == 3

    def test_low_count(self):
        """Test counting low severity findings."""
        report = SecurityAuditReport()

        report.add_finding(
            SecurityFinding(
                category=OWASPCategory.A09_LOGGING_FAILURES,
                severity=Severity.LOW,
                title="Low Finding",
                description="Test",
                location="test.py",
                remediation="Fix",
            )
        )

        assert report.low_count == 1

    def test_open_findings(self):
        """Test getting open findings."""
        report = SecurityAuditReport()

        # Add open finding
        report.add_finding(
            SecurityFinding(
                category=OWASPCategory.A03_INJECTION,
                severity=Severity.HIGH,
                title="Open Finding",
                description="Test",
                location="test.py",
                remediation="Fix",
                status=FindingStatus.OPEN,
            )
        )

        # Add fixed finding
        report.add_finding(
            SecurityFinding(
                category=OWASPCategory.A03_INJECTION,
                severity=Severity.HIGH,
                title="Fixed Finding",
                description="Test",
                location="test.py",
                remediation="Fix",
                status=FindingStatus.FIXED,
            )
        )

        assert len(report.open_findings) == 1
        assert report.open_findings[0].title == "Open Finding"

    def test_is_release_ready_true(self):
        """Test release ready when no critical/high open."""
        report = SecurityAuditReport()

        # Add medium open finding
        report.add_finding(
            SecurityFinding(
                category=OWASPCategory.A05_SECURITY_MISCONFIGURATION,
                severity=Severity.MEDIUM,
                title="Medium Issue",
                description="Test",
                location="test.py",
                remediation="Fix",
            )
        )

        # Add fixed high finding
        report.add_finding(
            SecurityFinding(
                category=OWASPCategory.A03_INJECTION,
                severity=Severity.HIGH,
                title="Fixed High",
                description="Test",
                location="test.py",
                remediation="Fix",
                status=FindingStatus.FIXED,
            )
        )

        assert report.is_release_ready is True

    def test_is_release_ready_false_critical(self):
        """Test not release ready with open critical."""
        report = SecurityAuditReport()

        report.add_finding(
            SecurityFinding(
                category=OWASPCategory.A01_BROKEN_ACCESS_CONTROL,
                severity=Severity.CRITICAL,
                title="Critical Issue",
                description="Test",
                location="test.py",
                remediation="Fix",
                status=FindingStatus.OPEN,
            )
        )

        assert report.is_release_ready is False

    def test_is_release_ready_false_high(self):
        """Test not release ready with open high."""
        report = SecurityAuditReport()

        report.add_finding(
            SecurityFinding(
                category=OWASPCategory.A02_CRYPTOGRAPHIC_FAILURES,
                severity=Severity.HIGH,
                title="High Issue",
                description="Test",
                location="test.py",
                remediation="Fix",
                status=FindingStatus.OPEN,
            )
        )

        assert report.is_release_ready is False

    def test_to_dict(self):
        """Test converting report to dictionary."""
        report = SecurityAuditReport(auditor="Test", version="2.0.0")

        report.add_finding(
            SecurityFinding(
                category=OWASPCategory.A03_INJECTION,
                severity=Severity.MEDIUM,
                title="Test Finding",
                description="Test",
                location="test.py",
                remediation="Fix",
            )
        )

        report.add_control(
            SecurityControl(
                category=OWASPCategory.A01_BROKEN_ACCESS_CONTROL,
                name="Test Control",
                description="Desc",
                implemented=True,
                location="test.py",
                verification="Test",
            )
        )

        report.add_passed_check("Test check passed")

        result = report.to_dict()

        assert result["auditor"] == "Test"
        assert result["version"] == "2.0.0"
        assert result["summary"]["total_findings"] == 1
        assert result["summary"]["medium"] == 1
        assert result["summary"]["release_ready"] is True
        assert len(result["findings"]) == 1
        assert len(result["controls"]) == 1
        assert len(result["passed_checks"]) == 1


class TestGetOWASPControls:
    """Tests for get_owasp_controls function."""

    def test_returns_controls(self):
        """Test that controls are returned."""
        controls = get_owasp_controls()

        assert len(controls) > 0
        assert all(isinstance(c, SecurityControl) for c in controls)

    def test_all_categories_covered(self):
        """Test that all OWASP categories have at least one control."""
        controls = get_owasp_controls()
        categories = {c.category for c in controls}

        # Check we have controls for each OWASP category
        for cat in OWASPCategory:
            assert cat in categories, f"Missing control for {cat}"

    def test_controls_are_implemented(self):
        """Test that all returned controls are marked as implemented."""
        controls = get_owasp_controls()

        # All controls should be implemented (this is the security posture)
        assert all(c.implemented for c in controls)

    def test_jwt_auth_control_exists(self):
        """Test JWT authentication control exists."""
        controls = get_owasp_controls()
        jwt_control = next((c for c in controls if "JWT" in c.name), None)

        assert jwt_control is not None
        assert jwt_control.category == OWASPCategory.A01_BROKEN_ACCESS_CONTROL

    def test_sql_injection_control_exists(self):
        """Test SQL injection prevention control exists."""
        controls = get_owasp_controls()
        sql_control = next((c for c in controls if "SQL" in c.name), None)

        assert sql_control is not None
        assert sql_control.category == OWASPCategory.A03_INJECTION

    def test_rate_limiting_control_exists(self):
        """Test rate limiting control exists."""
        controls = get_owasp_controls()
        rate_control = next((c for c in controls if "Rate" in c.name), None)

        assert rate_control is not None


class TestRunSecurityAudit:
    """Tests for run_security_audit function."""

    def test_returns_report(self):
        """Test that audit returns a report."""
        report = run_security_audit()

        assert isinstance(report, SecurityAuditReport)

    def test_report_has_controls(self):
        """Test that report contains controls."""
        report = run_security_audit()

        assert len(report.controls) > 0

    def test_report_has_passed_checks(self):
        """Test that report contains passed checks."""
        report = run_security_audit()

        assert len(report.passed_checks) > 0

    def test_passed_checks_match_implemented_controls(self):
        """Test passed checks match implemented controls."""
        report = run_security_audit()

        # Count of passed checks should match implemented controls
        implemented = [c for c in report.controls if c.implemented]
        assert len(report.passed_checks) == len(implemented)

    def test_audit_date_set(self):
        """Test audit date is set."""
        report = run_security_audit()

        assert report.audit_date is not None
        assert len(report.audit_date) > 0

    def test_default_auditor(self):
        """Test default auditor is 'Automated'."""
        report = run_security_audit()

        assert report.auditor == "Automated"
