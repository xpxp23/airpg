"""Add game_mode to games table

Revision ID: 005
Revises: 004
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('games', sa.Column('game_mode', sa.String(20), server_default='waiting'))


def downgrade() -> None:
    op.drop_column('games', 'game_mode')
