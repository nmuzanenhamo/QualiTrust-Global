"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Qualification Verification System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./qualification_verification.db"

    # JWT
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 1440

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Anthropic (config-only for now; not yet wired into extraction/analysis)
    ANTHROPIC_API_KEY: str = ""

    # Fernet key used to encrypt API keys stored in the database.
    # If unset, a warning is logged and DB-stored keys cannot be used.
    ENCRYPTION_KEY: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
