import hmac
import hashlib
import time
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_current_admin_settings, update_admin_settings, get_settings, get_admin_password_raw, set_admin_password
from app.services.ai_service import get_default_prompts
from app.database import get_db
from app.models.game import Game, GameStatus
from app.models.character import Character
from app.models.event import Event, EventType

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

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

    # Try with current password
    current_password = get_admin_password_raw()
    payload = f"{current_password}:{expires}"
    expected = hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    if hmac.compare_digest(sig, expected):
        return True

    # If password was changed, also try the hardcoded default
    # (for tokens issued before the password change)
    if current_password != "rpgadmin":
        payload_old = f"rpgadmin:{expires}"
        expected_old = hmac.new(
            settings.JWT_SECRET_KEY.encode(),
            payload_old.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(sig, expected_old)

    return False


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
    # Memory compression
    MEMORY_COMPRESS_EVENT_THRESHOLD: int | None = None
    MEMORY_COMPRESS_CHAR_THRESHOLD: int | None = None
    MEMORY_COMPRESS_KEEP_RECENT: int | None = None
    # Prompt overrides
    PROMPT_PARSE_STORY: str | None = None
    PROMPT_EVALUATE_ACTION: str | None = None
    PROMPT_GENERATE_NARRATIVE: str | None = None
    PROMPT_EVALUATE_COOPERATION: str | None = None
    PROMPT_COMPRESS_MEMORY: str | None = None


class AdminPasswordChange(BaseModel):
    old_password: str
    new_password: str


class AdminGameInfo(BaseModel):
    id: str
    title: str | None = None
    status: str
    creator_id: str
    player_count: int
    current_chapter: int
    created_at: str
    started_at: str | None = None


# --- Dependency ---

def _require_admin(x_admin_token: str = Header(..., alias="X-Admin-Token")):
    """FastAPI dependency: verify admin token from header."""
    if not _verify_admin_token(x_admin_token):
        raise HTTPException(status_code=401, detail="Invalid or expired admin token")


# --- Endpoints ---

@router.post("/verify", response_model=AdminVerifyResponse)
async def admin_verify(data: AdminVerifyRequest):
    """Verify admin password and return a session token."""
    current_password = get_admin_password_raw()
    if data.password != current_password:
        raise HTTPException(status_code=403, detail="Incorrect password")
    token, expires = _make_admin_token(current_password)
    return AdminVerifyResponse(token=token, expires_at=expires)


@router.get("/settings")
async def get_settings_endpoint(_: None = None):
    """Get current admin-configurable settings. No auth required for reading."""
    return get_current_admin_settings()


@router.get("/prompts/defaults")
async def get_default_prompts_endpoint():
    """Get default prompt texts. No auth required."""
    return get_default_prompts()


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


@router.put("/password")
async def change_admin_password(
    data: AdminPasswordChange,
    _: None = Depends(_require_admin),
):
    """Change admin password. Requires current admin token."""
    current_password = get_admin_password_raw()
    if data.old_password != current_password:
        raise HTTPException(status_code=403, detail="当前密码不正确")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="密码长度不能少于6位")
    set_admin_password(data.new_password)
    return {"message": "密码修改成功，请重新登录"}


@router.get("/games", response_model=list[AdminGameInfo])
async def admin_list_games(
    _: None = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all games with player counts. Admin only."""
    count_subq = (
        select(Character.game_id, func.count(Character.id).label("cnt"))
        .where(Character.player_id.isnot(None))
        .group_by(Character.game_id)
        .subquery()
    )
    result = await db.execute(
        select(Game, func.coalesce(count_subq.c.cnt, 0).label("player_count"))
        .outerjoin(count_subq, Game.id == count_subq.c.game_id)
        .order_by(Game.created_at.desc())
    )
    rows = result.all()
    return [
        AdminGameInfo(
            id=game.id,
            title=game.title,
            status=game.status.value if hasattr(game.status, "value") else game.status,
            creator_id=game.creator_id,
            player_count=cnt,
            current_chapter=game.current_chapter or 1,
            created_at=game.created_at.isoformat() if game.created_at else "",
            started_at=game.started_at.isoformat() if game.started_at else None,
        )
        for game, cnt in rows
    ]


@router.post("/games/{game_id}/close")
async def admin_close_game(
    game_id: str,
    _: None = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Force-end a game. Admin only."""
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.status in (GameStatus.FINISHED, GameStatus.ABANDONED):
        raise HTTPException(status_code=400, detail="Game is already ended")

    if game.status == GameStatus.LOBBY:
        game.status = GameStatus.ABANDONED
        event = Event(
            id=str(uuid.uuid4()),
            game_id=game_id,
            type=EventType.GAME_END,
            data={"reason": "管理员关闭了房间"},
        )
        db.add(event)
    else:
        game.status = GameStatus.FINISHED
        game.finished_at = datetime.now(timezone.utc)
        event = Event(
            id=str(uuid.uuid4()),
            game_id=game_id,
            type=EventType.GAME_END,
            data={"reason": "管理员强制结束了游戏"},
        )
        db.add(event)

    await db.commit()
    return {"message": "房间已关闭"}


@router.delete("/games/{game_id}", status_code=204)
async def admin_delete_game(
    game_id: str,
    _: None = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Abandon/delete a game. Admin only."""
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.status in (GameStatus.FINISHED, GameStatus.ABANDONED):
        raise HTTPException(status_code=400, detail="Game is already ended")

    game.status = GameStatus.ABANDONED
    game.finished_at = datetime.now(timezone.utc)

    event = Event(
        id=str(uuid.uuid4()),
        game_id=game_id,
        type=EventType.GAME_END,
        data={"reason": "管理员废弃了房间"},
    )
    db.add(event)
    await db.commit()
