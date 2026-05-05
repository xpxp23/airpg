"""Add midgame_join to eventtype enum

Revision ID: 008
Revises: 007
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'midgame_join'")


def downgrade() -> None:
    pass
