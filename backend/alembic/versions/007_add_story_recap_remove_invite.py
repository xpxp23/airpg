"""Add story_recap, remove invite_code

Revision ID: 007
Revises: 006
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('games', sa.Column('story_recap', sa.Text(), nullable=True))
    op.drop_column('games', 'invite_code')


def downgrade() -> None:
    op.add_column('games', sa.Column('invite_code', sa.String(8), unique=True, nullable=True))
    op.drop_column('games', 'story_recap')
