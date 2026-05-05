import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class EventType(str, enum.Enum):
    GAME_START = "GAME_START"
    GAME_END = "GAME_END"
    PLAYER_JOIN = "PLAYER_JOIN"
    PLAYER_LEAVE = "PLAYER_LEAVE"
    ACTION_START = "ACTION_START"
    ACTION_RESULT = "ACTION_RESULT"
    COOPERATION_START = "COOPERATION_START"
    COOPERATION_RESULT = "COOPERATION_RESULT"
    SCENE_CHANGE = "SCENE_CHANGE"
    CHAPTER_ADVANCE = "CHAPTER_ADVANCE"
    SYSTEM_MESSAGE = "SYSTEM_MESSAGE"
    AI_NARRATIVE = "AI_NARRATIVE"
    MIDGAME_JOIN = "MIDGAME_JOIN"


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
