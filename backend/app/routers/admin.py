import hmac
import hashlib
import time
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.config import get_current_admin_settings, update_admin_settings, get_settings

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

ADMIN_PASSWORD = "rpgadmin"
TOKEN_EXPIRE_SECONDS = 3600  # 1 hour


def _make_admin_token(password: str) -> tuple[str, float]:
    """Create an HMAC-based admin token."""
    settings = get_settings()
    expires = time.time() + TOKEN_EXPIRE_SECONDS
    payload = f"{password}:{expires}"
    sig = hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    token = f"{expires}:{sig}"
    return token, expires


def _verify_admin_token(token: str) -> bool:
    """Verify an admin token is valid and not expired."""
    settings = get_settings()
    try:
        expires_str, sig = token.split(":", 1)
        expires = float(expires_str)
    except (ValueError, AttributeError):
        return False

    if time.time() > expires:
        return False

    payload = f"{ADMIN_PASSWORD}:{expires}"
    expected = hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(sig, expected)


# --- Schemas ---

class AdminVerifyRequest(BaseModel):
    password: str


class AdminVerifyResponse(BaseModel):
    token: str
    expires_at: float


class AdminSettingsUpdate(BaseModel):
    AI_PROVIDER: str | None = None
    AI_API_KEY: str | None = None
    AI_BASE_URL: str | None = None
    AI_MODEL_DEFAULT: str | None = None
    AI_MODEL_PREMIUM: str | None = None
    MAX_TOKENS: int | None = None
    MAX_TOKENS_DEFAULT: int | None = None
    AI_THINKING_ENABLED: bool | None = None
    AI_THINKING_EFFORT: str | None = None


# --- Dependency ---

def _require_admin(x_admin_token: str = Header(..., alias="X-Admin-Token")):
    """FastAPI dependency: verify admin token from header."""
    if not _verify_admin_token(x_admin_token):
        raise HTTPException(status_code=401, detail="Invalid or expired admin token")


# --- Endpoints ---

@router.post("/verify", response_model=AdminVerifyResponse)
async def admin_verify(data: AdminVerifyRequest):
    """Verify admin password and return a session token."""
    if data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Incorrect password")
    token, expires = _make_admin_token(data.password)
    return AdminVerifyResponse(token=token, expires_at=expires)


@router.get("/settings")
async def get_settings_endpoint(_: None = None):
    """Get current admin-configurable settings. No auth required for reading."""
    return get_current_admin_settings()


@router.put("/settings")
async def update_settings_endpoint(
    data: AdminSettingsUpdate,
    x_admin_token: str = Header(..., alias="X-Admin-Token"),
):
    """Update admin settings. Requires valid admin token."""
    if not _verify_admin_token(x_admin_token):
        raise HTTPException(status_code=401, detail="Invalid or expired admin token")

    updates = data.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No settings to update")

    result = update_admin_settings(updates)
    return result
