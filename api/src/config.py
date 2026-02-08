"""Application configuration using pydantic-settings."""

import secrets
from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def generate_secret_key() -> str:
    """Generate a cryptographically secure secret key."""
    return secrets.token_urlsafe(32)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via environment variables or a .env file.
    Required settings without defaults will raise an error if not provided.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Defense PM Tool"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database settings for PostgreSQL
    DATABASE_URL: PostgresDsn = "postgresql://dev_user:dev_password@localhost:5432/defense_pm_dev"  # type: ignore[assignment]
    DATABASE_POOL_MIN_SIZE: int = 5
    DATABASE_POOL_MAX_SIZE: int = 20
    DATABASE_POOL_RECYCLE: int = 3600  # Recycle connections after 1 hour
    DATABASE_ECHO: bool = False  # Log SQL queries (useful for debugging)

    # Redis
    REDIS_URL: RedisDsn = "redis://localhost:6379/0"  # type: ignore[assignment]

    # Authentication - SECRET_KEY is required in production
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    BCRYPT_ROUNDS: int = 12

    # Encryption - Salt for token encryption (Jira API tokens, etc.)
    # Override via ENCRYPTION_SALT env var in production
    ENCRYPTION_SALT: str = "defense-pm-tool-encryption-salt"

    @model_validator(mode="after")
    def validate_encryption_salt(self) -> "Settings":
        """Require a custom ENCRYPTION_SALT in production."""
        if (
            self.ENVIRONMENT == "production"
            and self.ENCRYPTION_SALT == "defense-pm-tool-encryption-salt"
        ):
            raise ValueError(
                "ENCRYPTION_SALT must be overridden in production. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(16))"'
            )
        return self

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Security Headers
    CSP_ENABLED: bool = True
    HSTS_ENABLED: bool = False

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        """
        Validate and set SECRET_KEY.

        In development, generates a random key if not provided.
        In production, requires an explicit key to be set.
        """
        if not self.SECRET_KEY:
            if self.ENVIRONMENT == "production":
                raise ValueError(
                    "SECRET_KEY must be explicitly set in production environment. "
                    'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
                )
            # Generate a random key for development/staging
            object.__setattr__(self, "SECRET_KEY", generate_secret_key())
        elif len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return self

    @model_validator(mode="after")
    def validate_database_pool(self) -> "Settings":
        """Validate database pool configuration."""
        if self.DATABASE_POOL_MIN_SIZE > self.DATABASE_POOL_MAX_SIZE:
            raise ValueError("DATABASE_POOL_MIN_SIZE cannot be greater than DATABASE_POOL_MAX_SIZE")
        return self

    @property
    def database_url_async(self) -> str:
        """Get async database URL with asyncpg driver."""
        url = str(self.DATABASE_URL)
        # Replace postgresql:// with postgresql+asyncpg://
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()


# Global settings instance
settings = get_settings()
