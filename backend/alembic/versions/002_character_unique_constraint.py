"""add unique constraint on character game_id + player_id

Revision ID: 002_char_unique
Revises: 001_initial
Create Date: 2024-01-02 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_character_game_player",
        "characters",
        ["game_id", "player_id"],
    )
    op.alter_column(
        "characters", "player_id",
        existing_type=sa.String(36),
        server_default=None,
        existing_nullable=True,
    )


def downgrade() -> None:
    op.drop_constraint("uq_character_game_player", "characters", type_="unique")
