from pydantic import BaseModel
from datetime import datetime


class GameCreate(BaseModel):
    story_text: str
    duration_hint: str | None = None
    title: str | None = None
    max_players: int = 6
    is_public: bool = True
    game_mode: str = "waiting"


class GameJoin(BaseModel):
    character_id: str | None = None
    custom_character: str | None = None


class GameResponse(BaseModel):
    id: str
    creator_id: str
    title: str | None = None
    status: str
    current_chapter: int
    max_players: int
    is_public: bool
    game_mode: str = "waiting"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    player_count: int = 0
    parse_status: str = "pending"

    class Config:
        from_attributes = True


class GameDetailResponse(GameResponse):
    uploaded_story: str
    ai_summary: dict | None = None
    parse_status: str = "pending"
    parse_error: str | None = None
    duration_hint: str | None = None
    target_duration_minutes: int | None = None
    story_recap: str | None = None


class GameStart(BaseModel):
    pass
