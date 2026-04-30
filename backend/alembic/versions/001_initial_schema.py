"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("push_token", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Games
    op.create_table(
        "games",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("creator_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("uploaded_story", sa.Text, nullable=False),
        sa.Column("duration_hint", sa.String(100), nullable=True),
        sa.Column("target_duration_minutes", sa.Integer, nullable=True),
        sa.Column(
            "status",
            sa.Enum("lobby", "active", "paused", "finished", "abandoned", name="gamestatus"),
            nullable=False,
            server_default="lobby",
        ),
        sa.Column("ai_summary", JSONB, nullable=True),
        sa.Column("current_chapter", sa.Integer, server_default="1"),
        sa.Column("max_players", sa.Integer, server_default="6"),
        sa.Column("is_public", sa.Boolean, server_default="false"),
        sa.Column("invite_code", sa.String(8), unique=True, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Characters
    op.create_table(
        "characters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "game_id",
            sa.String(36),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("player_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("background", sa.Text, nullable=True),
        sa.Column("status_effects", JSONB, server_default="{}"),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("is_alive", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Actions
    op.create_table(
        "actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "game_id",
            sa.String(36),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("character_id", sa.String(36), sa.ForeignKey("characters.id"), nullable=False),
        sa.Column("player_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "action_type",
            sa.Enum("normal", "cooperation", "interaction", name="actiontype"),
            nullable=False,
            server_default="normal",
        ),
        sa.Column("input_text", sa.Text, nullable=False),
        sa.Column("public_snippet", sa.Text, nullable=True),
        sa.Column("wait_seconds", sa.Integer, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finish_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_narrative", sa.Text, nullable=True),
        sa.Column("result_effects", JSONB, nullable=True),
        sa.Column("difficulty", sa.String(20), nullable=True),
        sa.Column("risk", sa.String(20), nullable=True),
        sa.Column("is_cooperation", sa.Boolean, server_default="false"),
        sa.Column(
            "cooperation_target_id",
            sa.String(36),
            sa.ForeignKey("actions.id"),
            nullable=True,
        ),
        sa.Column("modifiers", JSONB, server_default="[]"),
        sa.Column(
            "status",
            sa.Enum("pending", "completed", "interrupted", "cancelled", name="actionstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Events
    op.create_table(
        "events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "game_id",
            sa.String(36),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "type",
            sa.Enum(
                "game_start",
                "game_end",
                "player_join",
                "player_leave",
                "action_start",
                "action_result",
                "cooperation_start",
                "cooperation_result",
                "scene_change",
                "chapter_advance",
                "system_message",
                "ai_narrative",
                name="eventtype",
            ),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("data", JSONB, nullable=False),
        sa.Column("is_visible", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("events")
    op.drop_table("actions")
    op.drop_table("characters")
    op.drop_table("games")
    op.drop_table("users")
    sa.Enum(name="eventtype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="actionstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="actiontype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="gamestatus").drop(op.get_bind(), checkfirst=True)
