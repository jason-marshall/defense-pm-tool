"""Unit tests for input validation utilities.

Tests cover:
- HTML sanitization (XSS prevention)
- SQL injection detection
- Text field validation
- Code field validation
- URL validation
- Email validation
- Number validation
"""

from __future__ import annotations

import pytest

from src.core.validation import (
    ValidationError,
    detect_sql_injection,
    sanitize_html,
    sanitize_text,
    validate_code_field,
    validate_email,
    validate_positive_number,
    validate_text_field,
    validate_url,
)

# =============================================================================
# Test: sanitize_html
# =============================================================================


class TestSanitizeHtml:
    """Tests for HTML sanitization."""

    def test_allows_safe_tags(self):
        """Should allow whitelisted tags."""
        input_html = "<b>Bold</b> and <i>italic</i>"
        result = sanitize_html(input_html)
        assert "<b>" in result
        assert "<i>" in result

    def test_allows_paragraph_tags(self):
        """Should allow paragraph tags."""
        input_html = "<p>Paragraph text</p>"
        result = sanitize_html(input_html)
        assert "<p>" in result

    def test_allows_list_tags(self):
        """Should allow list tags."""
        input_html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = sanitize_html(input_html)
        assert "<ul>" in result
        assert "<li>" in result

    def test_strips_script_tags(self):
        """Should strip script tags."""
        input_html = "<script>alert('xss')</script>Hello"
        result = sanitize_html(input_html)
        assert "<script>" not in result
        # Note: bleach strips tags but preserves content, which is expected
        assert "Hello" in result

    def test_strips_onclick(self):
        """Should strip onclick attributes."""
        input_html = '<div onclick="evil()">Click</div>'
        result = sanitize_html(input_html)
        assert "onclick" not in result

    def test_strips_onerror(self):
        """Should strip onerror attributes."""
        input_html = '<img onerror="evil()" src="x">'
        result = sanitize_html(input_html)
        assert "onerror" not in result

    def test_strips_javascript_url(self):
        """Should strip javascript: URLs."""
        input_html = '<a href="javascript:evil()">Link</a>'
        result = sanitize_html(input_html)
        assert "javascript:" not in result

    def test_handles_none(self):
        """Should handle None input."""
        assert sanitize_html(None) is None

    def test_handles_empty_string(self):
        """Should handle empty string."""
        assert sanitize_html("") == ""


# =============================================================================
# Test: sanitize_text
# =============================================================================


class TestSanitizeText:
    """Tests for plain text sanitization."""

    def test_strips_all_html(self):
        """Should strip all HTML tags."""
        input_text = "<b>Bold</b> and <script>bad</script>"
        result = sanitize_text(input_text)
        assert "<" not in result
        assert ">" not in result
        assert "Bold" in result

    def test_preserves_text_content(self):
        """Should preserve text content."""
        input_text = "Hello <b>World</b>!"
        result = sanitize_text(input_text)
        assert "Hello" in result
        assert "World" in result
        assert "!" in result

    def test_handles_none(self):
        """Should handle None input."""
        assert sanitize_text(None) is None


# =============================================================================
# Test: detect_sql_injection
# =============================================================================


class TestDetectSqlInjection:
    """Tests for SQL injection detection."""

    def test_detects_select(self):
        """Should detect SELECT statements."""
        assert detect_sql_injection("1; SELECT * FROM users")

    def test_detects_union(self):
        """Should detect UNION injection."""
        assert detect_sql_injection("' UNION SELECT password FROM users")

    def test_detects_drop(self):
        """Should detect DROP statements."""
        assert detect_sql_injection("'; DROP TABLE users;")

    def test_detects_comment(self):
        """Should detect SQL comments."""
        assert detect_sql_injection("admin'--")

    def test_detects_or_equals(self):
        """Should detect OR = injection pattern."""
        assert detect_sql_injection("' OR '1'='1")

    def test_allows_normal_text(self):
        """Should allow normal text."""
        assert not detect_sql_injection("Hello, world!")
        assert not detect_sql_injection("Project deadline is next week")

    def test_allows_technical_text(self):
        """Should allow technical text that's not injection."""
        # Normal sentences that might contain keywords
        assert not detect_sql_injection("Please select the option")
        assert not detect_sql_injection("Update your profile settings")
        assert not detect_sql_injection("Delete this item from the list")
        assert not detect_sql_injection("The union of these sets")
        assert not detect_sql_injection("Insert your name here")

    def test_handles_empty_string(self):
        """Should handle empty string."""
        assert not detect_sql_injection("")

    def test_case_insensitive(self):
        """Should detect regardless of case."""
        assert detect_sql_injection("select * from users")
        assert detect_sql_injection("SELECT * FROM users")
        assert detect_sql_injection("SeLeCt * FrOm users")


# =============================================================================
# Test: validate_text_field
# =============================================================================


class TestValidateTextField:
    """Tests for text field validation."""

    def test_enforces_max_length(self):
        """Should reject text exceeding max length."""
        with pytest.raises(ValidationError) as exc:
            validate_text_field("x" * 101, "test", max_length=100)
        assert "at most 100" in exc.value.message

    def test_enforces_min_length(self):
        """Should reject text below min length."""
        with pytest.raises(ValidationError) as exc:
            validate_text_field("ab", "test", min_length=5)
        assert "at least 5" in exc.value.message

    def test_required_field(self):
        """Should require non-empty for required fields."""
        with pytest.raises(ValidationError) as exc:
            validate_text_field(None, "test", required=True)
        assert "required" in exc.value.message

    def test_required_field_empty_string(self):
        """Should reject empty string for required fields."""
        with pytest.raises(ValidationError) as exc:
            validate_text_field("", "test", required=True)
        assert "required" in exc.value.message

    def test_optional_field_none(self):
        """Should allow None for optional fields."""
        result = validate_text_field(None, "test", required=False)
        assert result is None

    def test_sanitizes_output(self):
        """Should sanitize the output."""
        result = validate_text_field("<script>x</script>Hello", "test")
        assert "<script>" not in (result or "")
        assert "Hello" in (result or "")

    def test_allows_html_when_enabled(self):
        """Should allow limited HTML when allow_html=True."""
        result = validate_text_field("<b>Bold</b>", "test", allow_html=True)
        assert "<b>" in (result or "")

    def test_detects_sql_injection(self):
        """Should detect SQL injection by default."""
        with pytest.raises(ValidationError) as exc:
            validate_text_field("'; DROP TABLE users;", "test")
        assert "Invalid characters" in exc.value.message

    def test_skip_sql_injection_check(self):
        """Should skip SQL injection check when disabled."""
        # This is for cases where we know the content is safe
        result = validate_text_field(
            "SELECT option from menu",
            "test",
            check_sql_injection=False,
        )
        assert result is not None


# =============================================================================
# Test: validate_code_field
# =============================================================================


class TestValidateCodeField:
    """Tests for code field validation."""

    def test_accepts_alphanumeric(self):
        """Should accept alphanumeric codes."""
        result = validate_code_field("ABC123", "code")
        assert result == "ABC123"

    def test_accepts_underscore(self):
        """Should accept underscores."""
        result = validate_code_field("ABC_123", "code")
        assert result == "ABC_123"

    def test_accepts_hyphen(self):
        """Should accept hyphens."""
        result = validate_code_field("ABC-123", "code")
        assert result == "ABC-123"

    def test_accepts_period(self):
        """Should accept periods."""
        result = validate_code_field("ABC.123", "code")
        assert result == "ABC.123"

    def test_rejects_special_chars(self):
        """Should reject special characters."""
        with pytest.raises(ValidationError) as exc:
            validate_code_field("ABC@123", "code")
        assert "invalid characters" in exc.value.message.lower()

    def test_rejects_spaces(self):
        """Should reject spaces."""
        with pytest.raises(ValidationError) as exc:
            validate_code_field("ABC 123", "code")
        assert "invalid characters" in exc.value.message.lower()

    def test_enforces_max_length(self):
        """Should enforce max length."""
        with pytest.raises(ValidationError) as exc:
            validate_code_field("A" * 51, "code", max_length=50)
        assert "at most 50" in exc.value.message

    def test_handles_none(self):
        """Should handle None input."""
        result = validate_code_field(None, "code")
        assert result is None


# =============================================================================
# Test: validate_url
# =============================================================================


class TestValidateUrl:
    """Tests for URL validation."""

    def test_accepts_https(self):
        """Should accept HTTPS URLs."""
        result = validate_url("https://example.com", "url")
        assert result == "https://example.com"

    def test_accepts_http(self):
        """Should accept HTTP URLs."""
        result = validate_url("http://example.com", "url")
        assert result == "http://example.com"

    def test_accepts_url_with_path(self):
        """Should accept URLs with paths."""
        result = validate_url("https://example.com/path/to/resource", "url")
        assert result == "https://example.com/path/to/resource"

    def test_accepts_url_with_query(self):
        """Should accept URLs with query strings."""
        result = validate_url("https://example.com?foo=bar", "url")
        assert result == "https://example.com?foo=bar"

    def test_rejects_ftp(self):
        """Should reject FTP by default."""
        with pytest.raises(ValidationError):
            validate_url("ftp://example.com", "url")

    def test_rejects_invalid_format(self):
        """Should reject invalid URL format."""
        with pytest.raises(ValidationError):
            validate_url("not-a-url", "url")

    def test_rejects_javascript(self):
        """Should reject javascript: URLs."""
        with pytest.raises(ValidationError):
            validate_url("javascript:alert(1)", "url")

    def test_required_url(self):
        """Should require URL when required=True."""
        with pytest.raises(ValidationError) as exc:
            validate_url(None, "url", required=True)
        assert "required" in exc.value.message

    def test_optional_url(self):
        """Should allow None when not required."""
        result = validate_url(None, "url", required=False)
        assert result is None

    def test_custom_schemes(self):
        """Should allow custom schemes."""
        result = validate_url(
            "ftp://example.com",
            "url",
            allowed_schemes=["http", "https", "ftp"],
        )
        assert result == "ftp://example.com"


# =============================================================================
# Test: validate_email
# =============================================================================


class TestValidateEmail:
    """Tests for email validation."""

    def test_accepts_valid_email(self):
        """Should accept valid email."""
        result = validate_email("user@example.com", "email")
        assert result == "user@example.com"

    def test_accepts_email_with_subdomain(self):
        """Should accept email with subdomain."""
        result = validate_email("user@mail.example.com", "email")
        assert result == "user@mail.example.com"

    def test_accepts_email_with_plus(self):
        """Should accept email with plus sign."""
        result = validate_email("user+tag@example.com", "email")
        assert result == "user+tag@example.com"

    def test_lowercases_email(self):
        """Should lowercase email."""
        result = validate_email("User@EXAMPLE.COM", "email")
        assert result == "user@example.com"

    def test_rejects_invalid_email(self):
        """Should reject invalid email."""
        with pytest.raises(ValidationError):
            validate_email("not-an-email", "email")

    def test_rejects_missing_at(self):
        """Should reject email without @."""
        with pytest.raises(ValidationError):
            validate_email("userexample.com", "email")

    def test_rejects_missing_domain(self):
        """Should reject email without domain."""
        with pytest.raises(ValidationError):
            validate_email("user@", "email")

    def test_required_email(self):
        """Should require email when required=True."""
        with pytest.raises(ValidationError) as exc:
            validate_email(None, "email", required=True)
        assert "required" in exc.value.message

    def test_optional_email(self):
        """Should allow None when not required."""
        result = validate_email(None, "email", required=False)
        assert result is None


# =============================================================================
# Test: validate_positive_number
# =============================================================================


class TestValidatePositiveNumber:
    """Tests for positive number validation."""

    def test_accepts_positive(self):
        """Should accept positive numbers."""
        result = validate_positive_number(42, "value")
        assert result == 42

    def test_accepts_zero(self):
        """Should accept zero by default."""
        result = validate_positive_number(0, "value")
        assert result == 0

    def test_accepts_float(self):
        """Should accept floats."""
        result = validate_positive_number(3.14, "value")
        assert result == 3.14

    def test_rejects_negative(self):
        """Should reject negative numbers."""
        with pytest.raises(ValidationError) as exc:
            validate_positive_number(-5, "value")
        assert "at least" in exc.value.message

    def test_enforces_min_value(self):
        """Should enforce minimum value."""
        with pytest.raises(ValidationError) as exc:
            validate_positive_number(5, "value", min_value=10)
        assert "at least 10" in exc.value.message

    def test_enforces_max_value(self):
        """Should enforce maximum value."""
        with pytest.raises(ValidationError) as exc:
            validate_positive_number(100, "value", max_value=50)
        assert "at most 50" in exc.value.message

    def test_required_value(self):
        """Should require value when required=True."""
        with pytest.raises(ValidationError) as exc:
            validate_positive_number(None, "value", required=True)
        assert "required" in exc.value.message

    def test_optional_value(self):
        """Should allow None when not required."""
        result = validate_positive_number(None, "value", required=False)
        assert result is None


# =============================================================================
# Test: ValidationError
# =============================================================================


class TestValidationError:
    """Tests for ValidationError class."""

    def test_stores_field_and_message(self):
        """Should store field name and message."""
        error = ValidationError("email", "Invalid format", "bad@")
        assert error.field == "email"
        assert error.message == "Invalid format"
        assert error.value == "bad@"

    def test_string_representation(self):
        """Should have useful string representation."""
        error = ValidationError("email", "Invalid format")
        assert "email" in str(error)
        assert "Invalid format" in str(error)

    def test_default_value(self):
        """Should default value to None."""
        error = ValidationError("email", "Invalid format")
        assert error.value is None
