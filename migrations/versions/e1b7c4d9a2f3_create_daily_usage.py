"""create daily usage

Revision ID: e1b7c4d9a2f3
Revises: b7e4a1c2d9f3
Create Date: 2026-11-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e1b7c4d9a2f3'
down_revision: Union[str, Sequence[str], None] = 'b7e4a1c2d9f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'daily_usage',
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('requests', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_tokens', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('day', name=op.f('pk_daily_usage')),
    )


def downgrade() -> None:
    op.drop_table('daily_usage')
