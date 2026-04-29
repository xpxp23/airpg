from pydantic import BaseModel
from datetime import datetime


class EventResponse(BaseModel):
    id: str
    game_id: str
    type: str
    timestamp: datetime
    data: dict
    is_visible: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    events: list[EventResponse]
    has_more: bool = False
