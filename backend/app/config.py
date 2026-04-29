from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://gameuser:gamepass@localhost:5432/gamedb"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Configuration - Unified Interface
    AI_PROVIDER: str = "openai"  # openai / anthropic / local / custom
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL_DEFAULT: str = "gpt-4o-mini"      # For evaluation, compression, etc.
    AI_MODEL_PREMIUM: str = "gpt-4o"           # For narrative generation, etc.

    # Claude (Anthropic) Configuration (optional)
    ANTHROPIC_API_KEY: str = ""

    # Fallback API (optional, for failover)
    AI_FALLBACK_API_KEY: str = ""
    AI_FALLBACK_BASE_URL: str = ""
    AI_FALLBACK_MODEL: str = ""

    # Legacy OpenAI fields (for backward compatibility)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL_GPT4O: str = "gpt-4o-2024-08-06"
    OPENAI_MODEL_MINI: str = "gpt-4o-mini-2024-07-18"

    # JWT
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    # App
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
