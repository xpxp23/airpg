import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class EventType(str, enum.Enum):
    GAME_START = "game_start"
    GAME_END = "game_end"
    PLAYER_JOIN = "player_join"
    PLAYER_LEAVE = "player_leave"
    ACTION_START = "action_start"
    ACTION_RESULT = "action_result"
    COOPERATION_START = "cooperation_start"
    COOPERATION_RESULT = "cooperation_result"
    SCENE_CHANGE = "scene_change"
    CHAPTER_ADVANCE = "chapter_advance"
    SYSTEM_MESSAGE = "system_message"
    AI_NARRATIVE = "ai_narrative"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    game_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    game = relationship("Game", back_populates="events")
