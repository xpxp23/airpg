import uuid
import enum
from datetime import datetime, timedelta
from sqlalchemy import String, DateTime, Boolean, Integer, Text, Enum, ForeignKey, func, Interval
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class GameStatus(str, enum.Enum):
    LOBBY = "lobby"
    ACTIVE = "active"
    PAUSED = "paused"
    FINISHED = "finished"
    ABANDONED = "abandoned"


class ParseStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Game(Base):
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    creator_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    uploaded_story: Mapped[str] = mapped_column(Text, nullable=False)
    duration_hint: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[GameStatus] = mapped_column(
        Enum(GameStatus), default=GameStatus.LOBBY, nullable=False
    )
    ai_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    parse_status: Mapped[ParseStatus] = mapped_column(
        Enum(ParseStatus), default=ParseStatus.PENDING, nullable=False
    )
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_chapter: Mapped[int] = mapped_column(Integer, default=1)
    max_players: Mapped[int] = mapped_column(Integer, default=6)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    game_mode: Mapped[str] = mapped_column(String(20), default="waiting")
    invite_code: Mapped[str | None] = mapped_column(String(8), unique=True, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    creator = relationship("User", back_populates="created_games", foreign_keys=[creator_id])
    characters = relationship("Character", back_populates="game", cascade="all, delete-orphan")
    actions = relationship("Action", back_populates="game", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="game", cascade="all, delete-orphan")
