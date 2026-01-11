"""Unit tests for authentication functions."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from src.config import settings
from src.core.auth import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from src.core.exceptions import AuthenticationError


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_string(self):
        """hash_password should return a string."""
        password = "MySecurePassword123!"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_is_different_from_plain(self):
        """Hashed password should be different from plain text."""
        password = "MySecurePassword123!"
        hashed = hash_password(password)
        assert hashed != password

    def test_hash_password_is_unique_each_time(self):
        """Same password should produce different hashes (due to salt)."""
        password = "MySecurePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """verify_password should return True for correct password."""
        password = "MySecurePassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password should return False for incorrect password."""
        password = "MySecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """verify_password should handle empty password."""
        password = ""
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password("notempty", hashed) is False


class TestAccessToken:
    """Tests for access token creation and validation."""

    def test_create_access_token_returns_string(self):
        """create_access_token should return a JWT string."""
        user_id = str(uuid4())
        token = create_access_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_is_valid_jwt(self):
        """Created token should be a valid JWT."""
        user_id = str(uuid4())
        token = create_access_token(user_id)
        # Should be able to decode without verification
        payload = jwt.decode(token, options={"verify_signature": False})
        assert "sub" in payload
        assert payload["sub"] == user_id

    def test_create_access_token_has_correct_type(self):
        """Access token should have type 'access'."""
        user_id = str(uuid4())
        token = create_access_token(user_id)
        payload = decode_token(token)
        assert payload.type == "access"

    def test_create_access_token_with_extra_claims(self):
        """create_access_token should include extra claims."""
        user_id = str(uuid4())
        extra = {"role": "admin", "custom": "value"}
        token = create_access_token(user_id, extra_claims=extra)
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["role"] == "admin"
        assert payload["custom"] == "value"

    def test_access_token_expiration(self):
        """Access token should expire after configured time."""
        user_id = str(uuid4())
        token = create_access_token(user_id)
        payload = jwt.decode(token, options={"verify_signature": False})

        # Check expiration is approximately correct (within 1 minute)
        expected_exp = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        actual_exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        diff = abs((expected_exp - actual_exp).total_seconds())
        assert diff < 60  # Within 1 minute


class TestRefreshToken:
    """Tests for refresh token creation and validation."""

    def test_create_refresh_token_returns_string(self):
        """create_refresh_token should return a JWT string."""
        user_id = str(uuid4())
        token = create_refresh_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token_has_correct_type(self):
        """Refresh token should have type 'refresh'."""
        user_id = str(uuid4())
        token = create_refresh_token(user_id)
        payload = decode_token(token)
        assert payload.type == "refresh"

    def test_refresh_token_expiration(self):
        """Refresh token should expire after configured days."""
        user_id = str(uuid4())
        token = create_refresh_token(user_id)
        payload = jwt.decode(token, options={"verify_signature": False})

        # Check expiration is approximately correct (within 1 hour)
        expected_exp = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        actual_exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        diff = abs((expected_exp - actual_exp).total_seconds())
        assert diff < 3600  # Within 1 hour


class TestTokenPair:
    """Tests for token pair creation."""

    def test_create_token_pair_returns_both_tokens(self):
        """create_token_pair should return both access and refresh tokens."""
        user_id = str(uuid4())
        pair = create_token_pair(user_id)
        assert pair.access_token is not None
        assert pair.refresh_token is not None
        assert pair.token_type == "bearer"

    def test_create_token_pair_tokens_are_different(self):
        """Access and refresh tokens should be different."""
        user_id = str(uuid4())
        pair = create_token_pair(user_id)
        assert pair.access_token != pair.refresh_token

    def test_create_token_pair_same_subject(self):
        """Both tokens should have the same subject."""
        user_id = str(uuid4())
        pair = create_token_pair(user_id)

        access_payload = decode_token(pair.access_token)
        refresh_payload = decode_token(pair.refresh_token)

        assert access_payload.sub == user_id
        assert refresh_payload.sub == user_id


class TestDecodeToken:
    """Tests for token decoding and validation."""

    def test_decode_valid_access_token(self):
        """decode_token should successfully decode valid access token."""
        user_id = str(uuid4())
        token = create_access_token(user_id)
        payload = decode_token(token)

        assert isinstance(payload, TokenPayload)
        assert payload.sub == user_id
        assert payload.type == "access"

    def test_decode_valid_refresh_token(self):
        """decode_token should successfully decode valid refresh token."""
        user_id = str(uuid4())
        token = create_refresh_token(user_id)
        payload = decode_token(token)

        assert isinstance(payload, TokenPayload)
        assert payload.sub == user_id
        assert payload.type == "refresh"

    def test_decode_invalid_token_raises_error(self):
        """decode_token should raise AuthenticationError for invalid token."""
        with pytest.raises(AuthenticationError) as exc_info:
            decode_token("invalid.token.here")
        assert exc_info.value.code == "INVALID_TOKEN"

    def test_decode_tampered_token_raises_error(self):
        """decode_token should raise error for tampered token."""
        user_id = str(uuid4())
        token = create_access_token(user_id)
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"

        with pytest.raises(AuthenticationError) as exc_info:
            decode_token(tampered)
        assert exc_info.value.code == "INVALID_TOKEN"

    def test_decode_expired_token_raises_error(self):
        """decode_token should raise AuthenticationError for expired token."""
        user_id = str(uuid4())
        # Create a token that expired 1 hour ago
        now = datetime.now(UTC)
        expire = now - timedelta(hours=1)

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": now - timedelta(hours=2),
            "type": "access",
        }

        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        with pytest.raises(AuthenticationError) as exc_info:
            decode_token(token)
        assert exc_info.value.code == "TOKEN_EXPIRED"

    def test_decode_token_wrong_algorithm(self):
        """decode_token should reject token signed with wrong algorithm."""
        user_id = str(uuid4())
        now = datetime.now(UTC)
        expire = now + timedelta(hours=1)

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
            "type": "access",
        }

        # Sign with different algorithm
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS384")

        with pytest.raises(AuthenticationError) as exc_info:
            decode_token(token)
        assert exc_info.value.code == "INVALID_TOKEN"


class TestTokenPayload:
    """Tests for TokenPayload model."""

    def test_token_payload_from_dict(self):
        """TokenPayload should be constructable from dict."""
        now = datetime.now(UTC)
        data = {
            "sub": "user-123",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "access",
        }
        payload = TokenPayload(**data)
        assert payload.sub == "user-123"
        assert payload.type == "access"

    def test_token_payload_has_required_fields(self):
        """TokenPayload should require all fields."""
        # Missing 'type' field
        with pytest.raises(Exception):
            TokenPayload(
                sub="user-123",
                exp=datetime.now(UTC),
                iat=datetime.now(UTC),
            )
