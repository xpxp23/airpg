import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Integer, Text, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class ActionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"


class ActionType(str, enum.Enum):
    NORMAL = "normal"
    COOPERATION = "cooperation"  # Changed from "rescue" to "cooperation"
    INTERACTION = "interaction"


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    game_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("characters.id"), nullable=False
    )
    player_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    action_type: Mapped[ActionType] = mapped_column(
        Enum(ActionType), default=ActionType.NORMAL, nullable=False
    )
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    public_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    wait_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finish_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_effects: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    risk: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_cooperation: Mapped[bool] = mapped_column(Boolean, default=False)
    cooperation_target_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("actions.id"), nullable=True
    )
    modifiers: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus), default=ActionStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    game = relationship("Game", back_populates="actions")
    character = relationship("Character", back_populates="actions", foreign_keys=[character_id])
    player = relationship("User", back_populates="actions")
    cooperation_target = relationship("Action", remote_side=[id], foreign_keys=[cooperation_target_id])
