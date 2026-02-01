"""Unit tests for FastAPI dependencies."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.core.deps import (
    get_current_user,
    get_current_user_optional,
    get_current_user_or_api_key,
    require_active_user,
    require_role,
)
from src.core.exceptions import AuthenticationError
from src.models.enums import UserRole


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_valid_token(self):
        """Test with valid token returns user."""
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = True

        mock_payload = MagicMock()
        mock_payload.type = "access"
        mock_payload.sub = str(user_id)

        mock_db = AsyncMock()

        with patch("src.core.deps.decode_token") as mock_decode, patch(
            "src.core.deps.UserRepository"
        ) as mock_repo_class:
            mock_decode.return_value = mock_payload
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo

            result = await get_current_user("valid_token", mock_db)

            assert result == mock_user

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        """Test with invalid token raises 401."""
        mock_db = AsyncMock()

        with patch("src.core.deps.decode_token") as mock_decode:
            mock_decode.side_effect = AuthenticationError("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("invalid_token", mock_db)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_token_type(self):
        """Test with non-access token raises 401."""
        mock_payload = MagicMock()
        mock_payload.type = "refresh"  # Wrong type

        mock_db = AsyncMock()

        with patch("src.core.deps.decode_token") as mock_decode:
            mock_decode.return_value = mock_payload

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("refresh_token", mock_db)

            assert exc_info.value.status_code == 401
            assert "Invalid token type" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_token_subject(self):
        """Test with invalid user ID in token raises 401."""
        mock_payload = MagicMock()
        mock_payload.type = "access"
        mock_payload.sub = "not-a-uuid"

        mock_db = AsyncMock()

        with patch("src.core.deps.decode_token") as mock_decode:
            mock_decode.return_value = mock_payload

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("token", mock_db)

            assert exc_info.value.status_code == 401
            assert "Invalid token subject" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_user_not_found(self):
        """Test with user not in database raises 401."""
        user_id = uuid4()
        mock_payload = MagicMock()
        mock_payload.type = "access"
        mock_payload.sub = str(user_id)

        mock_db = AsyncMock()

        with patch("src.core.deps.decode_token") as mock_decode, patch(
            "src.core.deps.UserRepository"
        ) as mock_repo_class:
            mock_decode.return_value = mock_payload
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("token", mock_db)

            assert exc_info.value.status_code == 401
            assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_inactive_user(self):
        """Test with inactive user raises 401."""
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = False

        mock_payload = MagicMock()
        mock_payload.type = "access"
        mock_payload.sub = str(user_id)

        mock_db = AsyncMock()

        with patch("src.core.deps.decode_token") as mock_decode, patch(
            "src.core.deps.UserRepository"
        ) as mock_repo_class:
            mock_decode.return_value = mock_payload
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("token", mock_db)

            assert exc_info.value.status_code == 401
            assert "deactivated" in exc_info.value.detail


class TestGetCurrentUserOptional:
    """Tests for get_current_user_optional dependency."""

    @pytest.mark.asyncio
    async def test_no_token_returns_none(self):
        """Test with no token returns None."""
        mock_db = AsyncMock()

        result = await get_current_user_optional(None, mock_db)

        assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        """Test with valid token returns user."""
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = True

        mock_payload = MagicMock()
        mock_payload.type = "access"
        mock_payload.sub = str(user_id)

        mock_db = AsyncMock()

        with patch("src.core.deps.decode_token") as mock_decode, patch(
            "src.core.deps.UserRepository"
        ) as mock_repo_class:
            mock_decode.return_value = mock_payload
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo

            result = await get_current_user_optional("valid_token", mock_db)

            assert result == mock_user

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self):
        """Test with invalid token returns None instead of raising."""
        mock_db = AsyncMock()

        with patch("src.core.deps.decode_token") as mock_decode:
            mock_decode.side_effect = AuthenticationError("Invalid")

            result = await get_current_user_optional("bad_token", mock_db)

            assert result is None


class TestRequireRole:
    """Tests for require_role dependency factory."""

    def test_returns_function(self):
        """Test that require_role returns a callable."""
        checker = require_role(UserRole.ADMIN)
        assert callable(checker)

    def test_user_has_required_role(self):
        """Test user with required role is returned."""
        mock_user = MagicMock()
        mock_user.has_role.return_value = True

        checker = require_role(UserRole.ANALYST)
        result = checker(mock_user)

        assert result == mock_user
        mock_user.has_role.assert_called_once_with(UserRole.ANALYST)

    def test_user_lacks_required_role(self):
        """Test user without required role raises 403."""
        mock_user = MagicMock()
        mock_user.has_role.return_value = False

        checker = require_role(UserRole.ADMIN)

        with pytest.raises(HTTPException) as exc_info:
            checker(mock_user)

        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail.lower()

    def test_different_roles(self):
        """Test with different role requirements."""
        for role in [UserRole.VIEWER, UserRole.SCHEDULER, UserRole.PROGRAM_MANAGER]:
            mock_user = MagicMock()
            mock_user.has_role.return_value = True

            checker = require_role(role)
            result = checker(mock_user)

            assert result == mock_user


class TestRequireActiveUser:
    """Tests for require_active_user dependency factory."""

    def test_returns_function(self):
        """Test that require_active_user returns a callable."""
        checker = require_active_user()
        assert callable(checker)

    def test_active_user_is_returned(self):
        """Test active user is returned."""
        mock_user = MagicMock()
        mock_user.is_active = True

        checker = require_active_user()
        result = checker(mock_user)

        assert result == mock_user

    def test_inactive_user_raises_403(self):
        """Test inactive user raises 403."""
        mock_user = MagicMock()
        mock_user.is_active = False

        checker = require_active_user()

        with pytest.raises(HTTPException) as exc_info:
            checker(mock_user)

        assert exc_info.value.status_code == 403
        assert "deactivated" in exc_info.value.detail


class TestGetCurrentUserOrApiKey:
    """Tests for get_current_user_or_api_key dependency."""

    @pytest.mark.asyncio
    async def test_valid_api_key(self):
        """Test with valid API key returns user."""
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = True

        mock_api_key = MagicMock()
        mock_api_key.user_id = str(user_id)
        mock_api_key.key_prefix = "test"

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "valid_api_key"

        mock_db = AsyncMock()

        with patch(
            "src.services.api_key_service.APIKeyService"
        ) as mock_service_class, patch(
            "src.core.deps.UserRepository"
        ) as mock_repo_class:
            mock_service = MagicMock()
            mock_service.verify_key = AsyncMock(return_value=mock_api_key)
            mock_service_class.return_value = mock_service

            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo

            result = await get_current_user_or_api_key(mock_request, mock_db, None)

            assert result == mock_user

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Test with invalid API key raises 401."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "invalid_key"

        mock_db = AsyncMock()

        with patch(
            "src.services.api_key_service.APIKeyService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.verify_key = AsyncMock(return_value=None)
            mock_service_class.return_value = mock_service

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_or_api_key(mock_request, mock_db, None)

            assert exc_info.value.status_code == 401
            assert "Invalid or expired API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_api_key_inactive_user(self):
        """Test with API key for inactive user raises 401."""
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = False

        mock_api_key = MagicMock()
        mock_api_key.user_id = str(user_id)
        mock_api_key.key_prefix = "test"

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "api_key"

        mock_db = AsyncMock()

        with patch(
            "src.services.api_key_service.APIKeyService"
        ) as mock_service_class, patch(
            "src.core.deps.UserRepository"
        ) as mock_repo_class:
            mock_service = MagicMock()
            mock_service.verify_key = AsyncMock(return_value=mock_api_key)
            mock_service_class.return_value = mock_service

            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_or_api_key(mock_request, mock_db, None)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_fallback_to_jwt_token(self):
        """Test fallback to JWT when no API key provided."""
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = True

        mock_payload = MagicMock()
        mock_payload.type = "access"
        mock_payload.sub = str(user_id)

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None  # No API key

        mock_db = AsyncMock()

        with patch("src.core.deps.decode_token") as mock_decode, patch(
            "src.core.deps.UserRepository"
        ) as mock_repo_class:
            mock_decode.return_value = mock_payload
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo

            result = await get_current_user_or_api_key(
                mock_request, mock_db, "valid_jwt_token"
            )

            assert result == mock_user

    @pytest.mark.asyncio
    async def test_no_auth_provided(self):
        """Test with neither API key nor JWT token raises 401."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_or_api_key(mock_request, mock_db, None)

        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_api_key_user_not_found(self):
        """Test with API key but user not found raises 401."""
        user_id = uuid4()

        mock_api_key = MagicMock()
        mock_api_key.user_id = str(user_id)
        mock_api_key.key_prefix = "test"

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "api_key"

        mock_db = AsyncMock()

        with patch(
            "src.services.api_key_service.APIKeyService"
        ) as mock_service_class, patch(
            "src.core.deps.UserRepository"
        ) as mock_repo_class:
            mock_service = MagicMock()
            mock_service.verify_key = AsyncMock(return_value=mock_api_key)
            mock_service_class.return_value = mock_service

            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_or_api_key(mock_request, mock_db, None)

            assert exc_info.value.status_code == 401
