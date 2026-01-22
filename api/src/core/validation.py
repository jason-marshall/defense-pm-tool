"""Input validation utilities for security hardening.

Provides validators and sanitizers for user inputs:
- Text sanitization (XSS prevention)
- SQL injection pattern detection
- Length enforcement
- Format validation

Per OWASP guidelines, all user inputs must be validated.
"""

from __future__ import annotations

import re
from typing import Any

import bleach

# Allowed HTML tags for rich text fields (minimal set)
ALLOWED_TAGS = ["b", "i", "u", "p", "br", "ul", "ol", "li", "strong", "em"]
ALLOWED_ATTRIBUTES: dict[str, list[str]] = {}

# SQL injection patterns to detect
# These patterns look for SQL-specific syntax rather than just keywords
SQL_INJECTION_PATTERNS = [
    r"(\bSELECT\b\s+(\*|[\w,\s]+)\s+\bFROM\b)",  # SELECT * FROM or SELECT col FROM
    r"(\bDELETE\b\s+\bFROM\b)",  # DELETE FROM table
    r"(\bINSERT\b\s+\bINTO\b)",  # INSERT INTO table
    r"(\bUPDATE\b\s+\w+\s+\bSET\b)",  # UPDATE table SET
    r"(\bDROP\b\s+(TABLE|DATABASE|INDEX)\b)",  # DROP TABLE/DATABASE/INDEX
    r"(\bALTER\b\s+TABLE\b)",  # ALTER TABLE
    r"(\bCREATE\b\s+(TABLE|DATABASE|INDEX)\b)",  # CREATE TABLE/DATABASE/INDEX
    r"(\bTRUNCATE\b\s+TABLE\b)",  # TRUNCATE TABLE
    r"(--|\/\*|\*\/)",  # SQL comments
    r"(\bOR\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?)",  # OR 1=1
    r"(\bAND\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?)",  # AND 1=1
    r"('[\s]*;)",  # Quote followed by semicolon
    r"(;\s*(SELECT|INSERT|UPDATE|DELETE|DROP))",  # Chained SQL statements
    r"(\bUNION\b\s+\bSELECT\b)",  # UNION SELECT injection
]


class ValidationError(Exception):
    """Validation error with field details."""

    def __init__(self, field: str, message: str, value: Any = None) -> None:
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"{field}: {message}")


def sanitize_html(text: str | None) -> str | None:
    """
    Sanitize HTML to prevent XSS attacks.

    Strips all tags except allowed whitelist.

    Args:
        text: Input text that may contain HTML

    Returns:
        Sanitized text with only allowed tags
    """
    if text is None:
        return None

    result: str = bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )
    return result


def sanitize_text(text: str | None) -> str | None:
    """
    Sanitize plain text by stripping all HTML.

    Args:
        text: Input text that may contain HTML

    Returns:
        Plain text with all HTML removed
    """
    if text is None:
        return None

    result: str = bleach.clean(text, tags=[], strip=True)
    return result


def detect_sql_injection(text: str) -> bool:
    """
    Detect potential SQL injection patterns.

    Args:
        text: Input text to check

    Returns:
        True if suspicious patterns found
    """
    if not text:
        return False

    text_upper = text.upper()
    return any(re.search(pattern, text_upper, re.IGNORECASE) for pattern in SQL_INJECTION_PATTERNS)


def validate_text_field(
    value: str | None,
    field_name: str,
    max_length: int = 1000,
    min_length: int = 0,
    required: bool = False,
    allow_html: bool = False,
    check_sql_injection: bool = True,
) -> str | None:
    """
    Validate and sanitize a text field.

    Args:
        value: Input value
        field_name: Name for error messages
        max_length: Maximum allowed length
        min_length: Minimum required length
        required: Whether field is required
        allow_html: Allow limited HTML tags
        check_sql_injection: Check for SQL injection patterns

    Returns:
        Sanitized value

    Raises:
        ValidationError: If validation fails
    """
    if value is None or value == "":
        if required:
            raise ValidationError(field_name, "Field is required")
        return None

    # Length checks
    if len(value) > max_length:
        raise ValidationError(
            field_name,
            f"Must be at most {max_length} characters",
            f"length={len(value)}",
        )

    if len(value) < min_length:
        raise ValidationError(
            field_name,
            f"Must be at least {min_length} characters",
            f"length={len(value)}",
        )

    # SQL injection check
    if check_sql_injection and detect_sql_injection(value):
        raise ValidationError(
            field_name,
            "Invalid characters detected",
        )

    # Sanitize
    if allow_html:
        return sanitize_html(value)
    return sanitize_text(value)


def validate_code_field(
    value: str | None,
    field_name: str,
    max_length: int = 50,
    pattern: str | None = r"^[A-Za-z0-9_\-\.]+$",
) -> str | None:
    """
    Validate a code/identifier field.

    Codes are restricted to alphanumeric + limited special chars.

    Args:
        value: Input code value
        field_name: Name for error messages
        max_length: Maximum length
        pattern: Regex pattern for validation

    Returns:
        Validated code

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        return None

    # Sanitize first
    value = sanitize_text(value)

    if not value:
        return None

    if len(value) > max_length:
        raise ValidationError(
            field_name,
            f"Must be at most {max_length} characters",
        )

    if pattern and not re.match(pattern, value):
        raise ValidationError(
            field_name,
            "Contains invalid characters. Use only letters, numbers, "
            "underscores, hyphens, and periods.",
        )

    return value


def validate_url(
    value: str | None,
    field_name: str,
    required: bool = False,
    allowed_schemes: list[str] | None = None,
) -> str | None:
    """
    Validate a URL field.

    Args:
        value: URL to validate
        field_name: Name for error messages
        required: Whether URL is required
        allowed_schemes: Allowed URL schemes (default: http, https)

    Returns:
        Validated URL

    Raises:
        ValidationError: If validation fails
    """
    if allowed_schemes is None:
        allowed_schemes = ["http", "https"]

    if value is None or value == "":
        if required:
            raise ValidationError(field_name, "URL is required")
        return None

    # Check if URL has a scheme
    if "://" not in value:
        raise ValidationError(field_name, "Invalid URL format")

    # Check scheme
    scheme = value.split("://")[0].lower()
    if scheme not in allowed_schemes:
        raise ValidationError(
            field_name,
            f"URL must use one of: {', '.join(allowed_schemes)}",
        )

    # Basic URL structure validation
    url_pattern = r"^[a-z]+://[^\s/$.?#].[^\s]*$"
    if not re.match(url_pattern, value, re.IGNORECASE):
        raise ValidationError(field_name, "Invalid URL format")

    return value


def validate_email(
    value: str | None,
    field_name: str,
    required: bool = False,
) -> str | None:
    """
    Validate an email address.

    Args:
        value: Email to validate
        field_name: Name for error messages
        required: Whether email is required

    Returns:
        Validated and lowercased email

    Raises:
        ValidationError: If validation fails
    """
    if value is None or value == "":
        if required:
            raise ValidationError(field_name, "Email is required")
        return None

    # RFC 5322 simplified pattern
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, value):
        raise ValidationError(field_name, "Invalid email format")

    return value.lower()


def validate_positive_number(
    value: int | float | None,
    field_name: str,
    required: bool = False,
    min_value: int | float = 0,
    max_value: int | float | None = None,
) -> int | float | None:
    """
    Validate a positive number.

    Args:
        value: Number to validate
        field_name: Name for error messages
        required: Whether number is required
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Returns:
        Validated number

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if required:
            raise ValidationError(field_name, "Value is required")
        return None

    if value < min_value:
        raise ValidationError(
            field_name,
            f"Must be at least {min_value}",
        )

    if max_value is not None and value > max_value:
        raise ValidationError(
            field_name,
            f"Must be at most {max_value}",
        )

    return value
