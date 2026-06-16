"""
Application configuration using pydantic-settings.

Reads settings from environment variables and .env file.
"""

import logging
import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    DATABASE_URL: str = "sqlite+aiosqlite:///./license.db"
    SECRET_KEY: str = ""
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    APP_NAME: str = "License Key Manager"

    def model_post_init(self, __context: object) -> None:
        """Generate a random secret key if none was provided and log a warning."""
        if not self.SECRET_KEY:
            generated = secrets.token_urlsafe(64)
            object.__setattr__(self, "SECRET_KEY", generated)
            logger.warning(
                "No SECRET_KEY configured — using a randomly generated key. "
                "Sessions will NOT survive restarts. Set SECRET_KEY in your "
                "environment or .env file for production use."
            )

        # Normalise DATABASE_URL for async drivers
             # Normalise DATABASE_URL for async drivers
        url = self.DATABASE_URL
        if url.startswith("postgres://") and not url.startswith("postgresql://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            object.__setattr__(self, "DATABASE_URL", url)
            logger.info("Converted postgres:// to use asyncpg driver.")
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            object.__setattr__(self, "DATABASE_URL", url)
            logger.info("Converted postgresql:// to use asyncpg driver.")



settings = Settings()
