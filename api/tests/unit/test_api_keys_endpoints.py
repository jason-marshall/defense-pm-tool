"""Unit tests for API key management endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.v1.endpoints.api_keys import (
    create_api_key,
    get_api_key,
    list_api_keys,
    revoke_api_key,
)


class TestCreateAPIKey:
    """Tests for create_api_key endpoint."""

    @pytest.mark.asyncio
    async def test_create_api_key_success(self):
        """Should create API key successfully."""
        from src.schemas.api_key import APIKeyCreate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        key_id = uuid4()
        plain_key = "dpmt_test1234567890abcdef"
        now = datetime.now(UTC)

        mock_api_key = MagicMock()
        mock_api_key.id = key_id
        mock_api_key.name = "Test Key"
        mock_api_key.key_prefix = "dpmt_test"
        mock_api_key.expires_at = now
        mock_api_key.created_at = now

        data = APIKeyCreate(
            name="Test Key",
            description="A test API key",
            scopes=["read", "write"],
            expires_in_days=30,
        )

        with patch("src.api.v1.endpoints.api_keys.APIKeyService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_key = AsyncMock(return_value=(mock_api_key, plain_key))
            mock_service_class.return_value = mock_service

            result = await create_api_key(data, mock_db, mock_user)

            assert result.id == key_id
            assert result.name == "Test Key"
            assert result.key == plain_key
            assert result.key_prefix == "dpmt_test"
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_api_key_with_no_scopes(self):
        """Should create API key with no scopes (full access)."""
        from src.schemas.api_key import APIKeyCreate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        key_id = uuid4()
        plain_key = "dpmt_full1234567890abcdef"
        now = datetime.now(UTC)

        mock_api_key = MagicMock()
        mock_api_key.id = key_id
        mock_api_key.name = "Full Access Key"
        mock_api_key.key_prefix = "dpmt_full"
        mock_api_key.expires_at = now
        mock_api_key.created_at = now

        data = APIKeyCreate(
            name="Full Access Key",
            description=None,
            scopes=None,
            expires_in_days=365,
        )

        with patch("src.api.v1.endpoints.api_keys.APIKeyService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_key = AsyncMock(return_value=(mock_api_key, plain_key))
            mock_service_class.return_value = mock_service

            result = await create_api_key(data, mock_db, mock_user)

            assert result.id == key_id
            assert result.name == "Full Access Key"
            mock_service.create_key.assert_called_once_with(
                user_id=mock_user.id,
                name="Full Access Key",
                description=None,
                scopes=None,
                expires_in_days=365,
            )

    @pytest.mark.asyncio
    async def test_create_api_key_no_expiration(self):
        """Should create API key with no expiration."""
        from src.schemas.api_key import APIKeyCreate

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        key_id = uuid4()
        plain_key = "dpmt_perm1234567890abcdef"
        now = datetime.now(UTC)

        mock_api_key = MagicMock()
        mock_api_key.id = key_id
        mock_api_key.name = "Permanent Key"
        mock_api_key.key_prefix = "dpmt_perm"
        mock_api_key.expires_at = None
        mock_api_key.created_at = now

        data = APIKeyCreate(
            name="Permanent Key",
            expires_in_days=None,
        )

        with patch("src.api.v1.endpoints.api_keys.APIKeyService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_key = AsyncMock(return_value=(mock_api_key, plain_key))
            mock_service_class.return_value = mock_service

            result = await create_api_key(data, mock_db, mock_user)

            assert result.expires_at is None
            assert "securely" in result.message.lower()


class TestListAPIKeys:
    """Tests for list_api_keys endpoint."""

    @pytest.mark.asyncio
    async def test_list_api_keys_success(self):
        """Should list all user API keys."""
        from src.schemas.api_key import APIKeyResponse

        mock_db = AsyncMock()
        mock_user = MagicMock()
        user_id = uuid4()
        mock_user.id = user_id

        now = datetime.now(UTC)
        key1_id = uuid4()
        key2_id = uuid4()

        # Mock APIKeyResponse items
        mock_response1 = MagicMock(spec=APIKeyResponse)
        mock_response2 = MagicMock(spec=APIKeyResponse)

        with patch("src.api.v1.endpoints.api_keys.APIKeyService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.list_keys = AsyncMock(return_value=[MagicMock(), MagicMock()])
            mock_service_class.return_value = mock_service

            with patch("src.api.v1.endpoints.api_keys.APIKeyResponse") as mock_api_key_response:
                mock_api_key_response.model_validate.side_effect = [mock_response1, mock_response2]

                with patch("src.api.v1.endpoints.api_keys.APIKeyListResponse") as mock_list_response:
                    mock_result = MagicMock()
                    mock_result.total = 2
                    mock_result.items = [mock_response1, mock_response2]
                    mock_list_response.return_value = mock_result

                    result = await list_api_keys(mock_db, mock_user)

                    assert result.total == 2
                    assert len(result.items) == 2
                    mock_service.list_keys.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_list_api_keys_empty(self):
        """Should return empty list when no API keys exist."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        with patch("src.api.v1.endpoints.api_keys.APIKeyService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.list_keys = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            result = await list_api_keys(mock_db, mock_user)

            assert result.total == 0
            assert len(result.items) == 0


class TestGetAPIKey:
    """Tests for get_api_key endpoint."""

    @pytest.mark.asyncio
    async def test_get_api_key_success(self):
        """Should return API key details."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        key_id = uuid4()
        now = datetime.now(UTC)

        mock_key = MagicMock()
        mock_key.id = key_id
        mock_key.name = "My Key"
        mock_key.key_prefix = "dpmt_myke"
        mock_key.description = "My description"
        mock_key.scopes = ["read", "write"]
        mock_key.expires_at = now
        mock_key.last_used_at = now
        mock_key.created_at = now

        with patch("src.api.v1.endpoints.api_keys.APIKeyService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_key_by_id = AsyncMock(return_value=mock_key)
            mock_service_class.return_value = mock_service

            with patch("src.schemas.api_key.APIKeyResponse.model_validate") as mock_validate:
                mock_response = MagicMock()
                mock_response.id = key_id
                mock_response.name = "My Key"
                mock_validate.return_value = mock_response

                result = await get_api_key(key_id, mock_db, mock_user)

                assert result.id == key_id
                assert result.name == "My Key"
                mock_service.get_key_by_id.assert_called_once_with(key_id, mock_user.id)

    @pytest.mark.asyncio
    async def test_get_api_key_not_found(self):
        """Should raise NotFoundError when key doesn't exist."""
        from src.core.exceptions import NotFoundError

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        key_id = uuid4()

        with patch("src.api.v1.endpoints.api_keys.APIKeyService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_key_by_id = AsyncMock(return_value=None)
            mock_service_class.return_value = mock_service

            with pytest.raises(NotFoundError) as exc_info:
                await get_api_key(key_id, mock_db, mock_user)

            assert exc_info.value.code == "API_KEY_NOT_FOUND"


class TestRevokeAPIKey:
    """Tests for revoke_api_key endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self):
        """Should revoke API key successfully."""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        key_id = uuid4()

        with patch("src.api.v1.endpoints.api_keys.APIKeyService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.revoke_key = AsyncMock(return_value=True)
            mock_service_class.return_value = mock_service

            result = await revoke_api_key(key_id, mock_db, mock_user)

            assert result is None
            mock_service.revoke_key.assert_called_once_with(key_id, mock_user.id)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(self):
        """Should raise NotFoundError when key doesn't exist."""
        from src.core.exceptions import NotFoundError

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        key_id = uuid4()

        with patch("src.api.v1.endpoints.api_keys.APIKeyService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.revoke_key = AsyncMock(return_value=False)
            mock_service_class.return_value = mock_service

            with pytest.raises(NotFoundError) as exc_info:
                await revoke_api_key(key_id, mock_db, mock_user)

            assert exc_info.value.code == "API_KEY_NOT_FOUND"
            mock_db.commit.assert_not_called()
