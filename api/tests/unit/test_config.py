"""Unit tests for configuration module."""

import pytest

from src.config import Settings, generate_secret_key


class TestGenerateSecretKey:
    """Tests for generate_secret_key function."""

    def test_generates_string(self) -> None:
        """Should generate a string."""
        key = generate_secret_key()
        assert isinstance(key, str)

    def test_generates_sufficient_length(self) -> None:
        """Should generate a key of at least 32 characters."""
        key = generate_secret_key()
        assert len(key) >= 32

    def test_generates_unique_keys(self) -> None:
        """Should generate unique keys each time."""
        key1 = generate_secret_key()
        key2 = generate_secret_key()
        assert key1 != key2


class TestSettings:
    """Tests for Settings class."""

    def test_default_app_name(self) -> None:
        """Should have default app name."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            SECRET_KEY="a" * 32,
        )
        assert settings.APP_NAME == "Defense PM Tool"

    def test_default_environment(self) -> None:
        """Should default to development environment."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            SECRET_KEY="a" * 32,
        )
        assert settings.ENVIRONMENT == "development"

    def test_is_development_property(self) -> None:
        """is_development should return True for development environment."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            SECRET_KEY="a" * 32,
            ENVIRONMENT="development",
        )
        assert settings.is_development is True
        assert settings.is_production is False

    def test_is_production_property(self) -> None:
        """is_production should return True for production environment."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            SECRET_KEY="a" * 32,
            ENCRYPTION_SALT="custom-production-salt",
            ENVIRONMENT="production",
        )
        assert settings.is_production is True
        assert settings.is_development is False

    def test_database_url_async_postgresql(self) -> None:
        """Should convert postgresql:// to postgresql+asyncpg://."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            SECRET_KEY="a" * 32,
        )
        assert settings.database_url_async.startswith("postgresql+asyncpg://")

    def test_database_url_async_postgres(self) -> None:
        """Should convert postgres:// to postgresql+asyncpg://."""
        settings = Settings(
            DATABASE_URL="postgres://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            SECRET_KEY="a" * 32,
        )
        assert settings.database_url_async.startswith("postgresql+asyncpg://")

    def test_secret_key_auto_generated_in_dev(self) -> None:
        """Should auto-generate secret key in development."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            ENVIRONMENT="development",
        )
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) >= 32

    def test_secret_key_required_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should require explicit secret key in production."""
        from pydantic import ValidationError as PydanticValidationError

        # Clear any SECRET_KEY from environment to ensure test isolation
        monkeypatch.delenv("SECRET_KEY", raising=False)

        with pytest.raises(PydanticValidationError):
            Settings(
                DATABASE_URL="postgresql://user:pass@localhost:5432/db",
                REDIS_URL="redis://localhost:6379/0",
                ENVIRONMENT="production",
                SECRET_KEY="",  # Explicitly empty to trigger validation
            )

    def test_secret_key_minimum_length(self) -> None:
        """Should require secret key of at least 32 characters."""
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            Settings(
                DATABASE_URL="postgresql://user:pass@localhost:5432/db",
                REDIS_URL="redis://localhost:6379/0",
                SECRET_KEY="too_short",
            )

    def test_database_pool_validation(self) -> None:
        """Should validate database pool size configuration."""
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            Settings(
                DATABASE_URL="postgresql://user:pass@localhost:5432/db",
                REDIS_URL="redis://localhost:6379/0",
                SECRET_KEY="a" * 32,
                DATABASE_POOL_MIN_SIZE=20,
                DATABASE_POOL_MAX_SIZE=5,
            )

    def test_encryption_salt_required_in_production(self) -> None:
        """Should require custom ENCRYPTION_SALT in production."""
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            Settings(
                DATABASE_URL="postgresql://user:pass@localhost:5432/db",
                REDIS_URL="redis://localhost:6379/0",
                SECRET_KEY="a" * 32,
                ENVIRONMENT="production",
                # Uses default salt, should fail in production
            )

    def test_encryption_salt_custom_in_production(self) -> None:
        """Should accept custom ENCRYPTION_SALT in production."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            SECRET_KEY="a" * 32,
            ENCRYPTION_SALT="my-custom-production-salt",
            ENVIRONMENT="production",
        )
        assert settings.ENCRYPTION_SALT == "my-custom-production-salt"

    def test_cors_origins_from_string(self) -> None:
        """Should parse CORS origins from comma-separated string."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            SECRET_KEY="a" * 32,
            CORS_ORIGINS="http://localhost:3000,http://localhost:5000",
        )
        assert len(settings.CORS_ORIGINS) == 2
        assert "http://localhost:3000" in settings.CORS_ORIGINS
        assert "http://localhost:5000" in settings.CORS_ORIGINS

    def test_cors_origins_from_list(self) -> None:
        """Should accept CORS origins as list."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            SECRET_KEY="a" * 32,
            CORS_ORIGINS=["http://localhost:3000"],
        )
        assert settings.CORS_ORIGINS == ["http://localhost:3000"]

    def test_csp_enabled_default(self) -> None:
        """CSP_ENABLED should default to True."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            SECRET_KEY="a" * 32,
        )
        assert settings.CSP_ENABLED is True

    def test_hsts_enabled_default(self) -> None:
        """HSTS_ENABLED should default to False."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            SECRET_KEY="a" * 32,
        )
        assert settings.HSTS_ENABLED is False

    def test_hsts_enabled_override(self) -> None:
        """HSTS_ENABLED should be overridable."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            SECRET_KEY="a" * 32,
            HSTS_ENABLED=True,
        )
        assert settings.HSTS_ENABLED is True

    def test_csp_disabled_override(self) -> None:
        """CSP_ENABLED should be overridable to False."""
        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            SECRET_KEY="a" * 32,
            CSP_ENABLED=False,
        )
        assert settings.CSP_ENABLED is False
