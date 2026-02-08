"""Unit tests for API Key service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.api_key import APIKey, generate_api_key, generate_api_key_prefix
from src.services.api_key_service import APIKeyService


class TestAPIKeyGeneration:
    """Tests for API key generation functions."""

    def test_generate_api_key_prefix_format(self) -> None:
        """API key prefix should have correct format."""
        prefix = generate_api_key_prefix()

        # Should start with 'dpm_'
        assert prefix.startswith("dpm_")

        # Should be dpm_ + 8 hex chars
        assert len(prefix) == 12

    def test_generate_api_key_prefix_uniqueness(self) -> None:
        """Each generated prefix should be unique."""
        prefixes = {generate_api_key_prefix() for _ in range(100)}
        assert len(prefixes) == 100

    def test_generate_api_key_format(self) -> None:
        """Full API key should have correct format."""
        key = generate_api_key()

        # Should have two underscores (dpm_prefix_secret)
        parts = key.split("_")
        assert len(parts) == 3
        assert parts[0] == "dpm"
        assert len(parts[1]) == 8  # hex prefix
        assert len(parts[2]) >= 32  # secret part

    def test_generate_api_key_uniqueness(self) -> None:
        """Each generated key should be unique."""
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100


class TestAPIKeyModel:
    """Tests for APIKey model."""

    def test_is_expired_with_no_expiration(self) -> None:
        """Key with no expiration should not be expired."""
        api_key = APIKey(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Key",
            key_prefix="dpm_test1234",
            key_hash="somehash",
            expires_at=None,
        )
        assert not api_key.is_expired()

    def test_is_expired_with_future_expiration(self) -> None:
        """Key with future expiration should not be expired."""
        api_key = APIKey(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Key",
            key_prefix="dpm_test1234",
            key_hash="somehash",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        assert not api_key.is_expired()

    def test_is_expired_with_past_expiration(self) -> None:
        """Key with past expiration should be expired."""
        api_key = APIKey(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Key",
            key_prefix="dpm_test1234",
            key_hash="somehash",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        assert api_key.is_expired()

    def test_is_valid_active_not_expired(self) -> None:
        """Active key with no expiration should be valid."""
        api_key = APIKey(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Key",
            key_prefix="dpm_test1234",
            key_hash="somehash",
            is_active=True,
            expires_at=None,
        )
        assert api_key.is_valid()

    def test_is_valid_inactive(self) -> None:
        """Inactive key should not be valid."""
        api_key = APIKey(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Key",
            key_prefix="dpm_test1234",
            key_hash="somehash",
            is_active=False,
            expires_at=None,
        )
        assert not api_key.is_valid()

    def test_get_scopes_empty(self) -> None:
        """Key with no scopes should return empty list."""
        api_key = APIKey(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Key",
            key_prefix="dpm_test1234",
            key_hash="somehash",
            scopes=None,
        )
        assert api_key.get_scopes() == []

    def test_get_scopes_with_values(self) -> None:
        """Key with scopes should return list."""
        api_key = APIKey(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Key",
            key_prefix="dpm_test1234",
            key_hash="somehash",
            scopes="programs:read,activities:read",
        )
        assert api_key.get_scopes() == ["programs:read", "activities:read"]

    def test_has_scope_with_no_scopes(self) -> None:
        """Key with no scopes should have all scopes (full access)."""
        api_key = APIKey(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Key",
            key_prefix="dpm_test1234",
            key_hash="somehash",
            scopes=None,
        )
        assert api_key.has_scope("any:scope")

    def test_has_scope_with_matching_scope(self) -> None:
        """Key should have matching scope."""
        api_key = APIKey(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Key",
            key_prefix="dpm_test1234",
            key_hash="somehash",
            scopes="programs:read,activities:read",
        )
        assert api_key.has_scope("programs:read")

    def test_has_scope_without_matching_scope(self) -> None:
        """Key should not have non-matching scope."""
        api_key = APIKey(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Key",
            key_prefix="dpm_test1234",
            key_hash="somehash",
            scopes="programs:read",
        )
        assert not api_key.has_scope("activities:write")


class TestAPIKeyServiceHashKey:
    """Tests for APIKeyService.hash_key."""

    def test_hash_key_deterministic(self) -> None:
        """Same key should produce same hash."""
        key = "dpm_test1234_secretvalue"
        hash1 = APIKeyService.hash_key(key)
        hash2 = APIKeyService.hash_key(key)
        assert hash1 == hash2

    def test_hash_key_different_keys(self) -> None:
        """Different keys should produce different hashes."""
        hash1 = APIKeyService.hash_key("dpm_test1234_secret1")
        hash2 = APIKeyService.hash_key("dpm_test1234_secret2")
        assert hash1 != hash2

    def test_hash_key_length(self) -> None:
        """Hash should be 64 characters (SHA-256 hex)."""
        key_hash = APIKeyService.hash_key("any_key")
        assert len(key_hash) == 64


class TestAPIKeyServiceExtractPrefix:
    """Tests for APIKeyService.extract_prefix."""

    def test_extract_prefix_standard_format(self) -> None:
        """Should extract prefix from standard key format."""
        key = "dpm_a1b2c3d4_secretparthere"
        prefix = APIKeyService.extract_prefix(key)
        assert prefix == "dpm_a1b2c3d4"

    def test_extract_prefix_short_key(self) -> None:
        """Should handle short keys gracefully."""
        key = "shortkey"
        prefix = APIKeyService.extract_prefix(key)
        assert prefix == "shortkey"[:12]


class TestAPIKeyServiceCreateKey:
    """Tests for APIKeyService.create_key."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock async session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_create_key_basic(self, mock_session: AsyncMock) -> None:
        """Should create key with basic parameters."""
        service = APIKeyService(mock_session)
        user_id = uuid4()

        api_key, plain_key = await service.create_key(
            user_id=user_id,
            name="Test Key",
        )

        # Verify key was added to session
        mock_session.add.assert_called_once()

        # Verify returned data
        assert api_key.name == "Test Key"
        assert api_key.user_id == str(user_id)
        assert plain_key.startswith("dpm_")

        # Verify hash matches
        assert api_key.key_hash == APIKeyService.hash_key(plain_key)

    @pytest.mark.asyncio
    async def test_create_key_with_scopes(self, mock_session: AsyncMock) -> None:
        """Should create key with scopes."""
        service = APIKeyService(mock_session)

        api_key, _ = await service.create_key(
            user_id=uuid4(),
            name="Scoped Key",
            scopes=["programs:read", "activities:read"],
        )

        assert api_key.scopes == "programs:read,activities:read"

    @pytest.mark.asyncio
    async def test_create_key_with_expiration(self, mock_session: AsyncMock) -> None:
        """Should create key with expiration."""
        service = APIKeyService(mock_session)

        api_key, _ = await service.create_key(
            user_id=uuid4(),
            name="Expiring Key",
            expires_in_days=30,
        )

        assert api_key.expires_at is not None
        # Should expire in approximately 30 days
        expected = datetime.now(UTC) + timedelta(days=30)
        diff = abs((api_key.expires_at - expected).total_seconds())
        assert diff < 5  # Within 5 seconds

    @pytest.mark.asyncio
    async def test_create_key_no_expiration(self, mock_session: AsyncMock) -> None:
        """Should create key without expiration."""
        service = APIKeyService(mock_session)

        api_key, _ = await service.create_key(
            user_id=uuid4(),
            name="Permanent Key",
            expires_in_days=None,
        )

        assert api_key.expires_at is None


class TestAPIKeyServiceVerifyKey:
    """Tests for APIKeyService.verify_key."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock async session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_verify_key_not_found(self, mock_session: AsyncMock) -> None:
        """Should return None for non-existent key."""
        # Mock no result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = APIKeyService(mock_session)
        result = await service.verify_key("dpm_notfound_secret")

        assert result is None

    @pytest.mark.asyncio
    async def test_verify_key_invalid_hash(self, mock_session: AsyncMock) -> None:
        """Should return None for invalid hash."""
        # Create key with different hash
        api_key = APIKey(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Key",
            key_prefix="dpm_test1234",
            key_hash="different_hash",
            is_active=True,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_session.execute.return_value = mock_result

        service = APIKeyService(mock_session)
        result = await service.verify_key("dpm_test1234_wrongsecret")

        assert result is None

    @pytest.mark.asyncio
    async def test_verify_key_expired(self, mock_session: AsyncMock) -> None:
        """Should return None for expired key."""
        plain_key = "dpm_test1234_correctsecret"
        api_key = APIKey(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Key",
            key_prefix="dpm_test1234",
            key_hash=APIKeyService.hash_key(plain_key),
            is_active=True,
            expires_at=datetime.now(UTC) - timedelta(days=1),  # Expired
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_session.execute.return_value = mock_result

        service = APIKeyService(mock_session)
        result = await service.verify_key(plain_key)

        assert result is None

    @pytest.mark.asyncio
    async def test_verify_key_valid(self, mock_session: AsyncMock) -> None:
        """Should return key for valid key."""
        plain_key = "dpm_test1234_correctsecret"
        api_key = APIKey(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Key",
            key_prefix="dpm_test1234",
            key_hash=APIKeyService.hash_key(plain_key),
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_session.execute.return_value = mock_result

        service = APIKeyService(mock_session)
        result = await service.verify_key(plain_key)

        assert result == api_key
        assert result.last_used_at is not None

    @pytest.mark.asyncio
    async def test_verify_key_uses_constant_time_comparison(self, mock_session: AsyncMock) -> None:
        """Should use hmac.compare_digest for constant-time hash comparison."""
        plain_key = "dpm_test1234_correctsecret"
        api_key = APIKey(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Key",
            key_prefix="dpm_test1234",
            key_hash=APIKeyService.hash_key(plain_key),
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_session.execute.return_value = mock_result

        service = APIKeyService(mock_session)
        with patch(
            "src.services.api_key_service.hmac.compare_digest", return_value=True
        ) as mock_compare:
            await service.verify_key(plain_key)
            mock_compare.assert_called_once()


class TestAPIKeyServiceRevokeKey:
    """Tests for APIKeyService.revoke_key."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock async session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_revoke_key_not_found(self, mock_session: AsyncMock) -> None:
        """Should return False for non-existent key."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = APIKeyService(mock_session)
        result = await service.revoke_key(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_key_success(self, mock_session: AsyncMock) -> None:
        """Should deactivate key and return True."""
        api_key = APIKey(
            id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Key",
            key_prefix="dpm_test1234",
            key_hash="somehash",
            is_active=True,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key
        mock_session.execute.return_value = mock_result

        service = APIKeyService(mock_session)
        result = await service.revoke_key(uuid4())

        assert result is True
        assert api_key.is_active is False


class TestAPIKeyServiceListKeys:
    """Tests for APIKeyService.list_keys."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock async session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_list_keys_empty(self, mock_session: AsyncMock) -> None:
        """Should return empty list when no keys."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        service = APIKeyService(mock_session)
        result = await service.list_keys(uuid4())

        assert result == []

    @pytest.mark.asyncio
    async def test_list_keys_with_results(self, mock_session: AsyncMock) -> None:
        """Should return list of keys."""
        keys = [
            APIKey(
                id=str(uuid4()),
                user_id=str(uuid4()),
                name="Key 1",
                key_prefix="dpm_key1",
                key_hash="hash1",
            ),
            APIKey(
                id=str(uuid4()),
                user_id=str(uuid4()),
                name="Key 2",
                key_prefix="dpm_key2",
                key_hash="hash2",
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = keys
        mock_session.execute.return_value = mock_result

        service = APIKeyService(mock_session)
        result = await service.list_keys(uuid4())

        assert len(result) == 2
