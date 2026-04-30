"""Add memory compression fields to games table

Revision ID: 006
Revises: 005
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('games', sa.Column('compressed_memory', sa.Text(), nullable=True))
    op.add_column('games', sa.Column('memory_event_count', sa.Integer(), server_default='0'))
    op.add_column('games', sa.Column('last_memory_compress_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('games', 'last_memory_compress_at')
    op.drop_column('games', 'memory_event_count')
    op.drop_column('games', 'compressed_memory')
