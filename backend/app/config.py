import json
import os
from pydantic_settings import BaseSettings
from functools import lru_cache

ADMIN_SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "admin_settings.json")

# Track file modification time for change detection across workers
_admin_settings_mtime: float = 0.0


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

    # Token limits (high default for million-context models)
    MAX_TOKENS: int = 65536
    MAX_TOKENS_DEFAULT: int = 16384

    # Thinking mode (DeepSeek / compatible models)
    AI_THINKING_ENABLED: bool = True
    AI_THINKING_EFFORT: str = "high"  # high / max

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


# Admin-overridable fields on the Settings class
ADMIN_SETTINGS_FIELDS = {
    "AI_PROVIDER", "AI_API_KEY", "AI_BASE_URL",
    "AI_MODEL_DEFAULT", "AI_MODEL_PREMIUM",
    "MAX_TOKENS", "MAX_TOKENS_DEFAULT",
    "AI_THINKING_ENABLED", "AI_THINKING_EFFORT",
}

# Prompt fields (stored in admin_settings.json, NOT on Settings class)
ADMIN_PROMPT_FIELDS = {
    "PROMPT_PARSE_STORY", "PROMPT_EVALUATE_ACTION",
    "PROMPT_GENERATE_NARRATIVE", "PROMPT_EVALUATE_COOPERATION",
    "PROMPT_COMPRESS_MEMORY",
}

# All admin-overridable fields
ADMIN_FIELDS = ADMIN_SETTINGS_FIELDS | ADMIN_PROMPT_FIELDS


def load_admin_overrides() -> dict:
    """Load admin settings from JSON file."""
    if not os.path.exists(ADMIN_SETTINGS_PATH):
        return {}
    try:
        with open(ADMIN_SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_admin_overrides(overrides: dict) -> None:
    """Save admin settings to JSON file."""
    os.makedirs(os.path.dirname(ADMIN_SETTINGS_PATH), exist_ok=True)
    with open(ADMIN_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(overrides, f, indent=2, ensure_ascii=False)


def apply_admin_overrides() -> None:
    """Apply admin overrides to the cached Settings instance."""
    global _admin_settings_mtime
    settings = get_settings()
    overrides = load_admin_overrides()
    for key, value in overrides.items():
        if key in ADMIN_SETTINGS_FIELDS:
            object.__setattr__(settings, key, value)
    try:
        _admin_settings_mtime = os.path.getmtime(ADMIN_SETTINGS_PATH)
    except OSError:
        _admin_settings_mtime = 0.0


def refresh_settings_if_changed() -> None:
    """Check if admin_settings.json changed on disk and reload if so.

    With multi-worker uvicorn, each worker has its own Settings singleton.
    When one worker saves new admin settings, other workers need to detect
    the file change and reload. This function should be called once per
    request (via middleware) so all workers stay in sync.
    """
    global _admin_settings_mtime
    try:
        current_mtime = os.path.getmtime(ADMIN_SETTINGS_PATH)
    except OSError:
        return

    if current_mtime != _admin_settings_mtime:
        apply_admin_overrides()


def update_admin_settings(updates: dict) -> dict:
    """Update admin settings, persist, and apply to runtime."""
    current = load_admin_overrides()
    settings = get_settings()

    for key, value in updates.items():
        if key not in ADMIN_FIELDS:
            continue
        if value is None:
            continue
        # Skip empty strings for prompt fields - they should fall back to defaults
        if key in ADMIN_PROMPT_FIELDS and value == "":
            # Remove override so default takes effect
            current.pop(key, None)
            continue
        current[key] = value
        if key in ADMIN_SETTINGS_FIELDS:
            object.__setattr__(settings, key, value)

    save_admin_overrides(current)
    return get_current_admin_settings()


def get_current_admin_settings() -> dict:
    """Get current effective values for admin-overridable fields."""
    from app.services.ai_service import get_default_prompts
    settings = get_settings()
    overrides = load_admin_overrides()
    defaults = get_default_prompts()
    result = {}
    for key in ADMIN_FIELDS:
        if key in ADMIN_SETTINGS_FIELDS:
            result[key] = getattr(settings, key)
        else:
            # Prompt fields: return override or default value
            result[key] = overrides.get(key, defaults.get(key, ""))
    return result


@lru_cache()
def get_settings() -> Settings:
    return Settings()
