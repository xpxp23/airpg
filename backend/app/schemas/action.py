from pydantic import BaseModel
from datetime import datetime


class ActionCreate(BaseModel):
    character_id: str
    action_text: str


class CooperationCreate(BaseModel):
    helper_character_id: str
    target_action_id: str
    cooperation_text: str


class ActionResponse(BaseModel):
    id: str
    game_id: str
    character_id: str
    player_id: str
    action_type: str
    input_text: str
    public_snippet: str | None = None
    wait_seconds: int
    started_at: datetime
    finish_at: datetime
    completed_at: datetime | None = None
    result_narrative: str | None = None
    result_effects: dict | None = None
    difficulty: str | None = None
    risk: str | None = None
    is_cooperation: bool = False
    cooperation_target_id: str | None = None
    modifiers: list = []
    status: str
    created_at: datetime
    remaining_seconds: float | None = None

    class Config:
        from_attributes = True


class ActionListResponse(BaseModel):
    actions: list[ActionResponse]


class CooperationResponse(BaseModel):
    cooperation_action_id: str
    helper_wait_seconds: int
    target_time_reduction_percent: float
    target_new_finish_at: datetime
    public_snippet: str
