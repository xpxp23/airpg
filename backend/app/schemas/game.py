from pydantic import BaseModel
from datetime import datetime


class GameCreate(BaseModel):
    story_text: str
    duration_hint: str | None = None
    title: str | None = None
    max_players: int = 6
    is_public: bool = False


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
    invite_code: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    player_count: int = 0

    class Config:
        from_attributes = True


class GameDetailResponse(GameResponse):
    uploaded_story: str
    ai_summary: dict | None = None
    duration_hint: str | None = None
    target_duration_minutes: int | None = None


class GameStart(BaseModel):
    pass
