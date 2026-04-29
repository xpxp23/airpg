from pydantic import BaseModel
from datetime import datetime


class CharacterCreate(BaseModel):
    name: str
    description: str | None = None
    background: str | None = None
    preset_id: str | None = None


class CharacterResponse(BaseModel):
    id: str
    game_id: str
    player_id: str | None = None
    name: str
    description: str | None = None
    background: str | None = None
    status_effects: dict = {}
    location: str | None = None
    is_alive: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class CharacterListResponse(BaseModel):
    characters: list[CharacterResponse]
