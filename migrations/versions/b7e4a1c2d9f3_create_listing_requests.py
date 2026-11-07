"""create listing requests

Revision ID: b7e4a1c2d9f3
Revises: cc2bec3c0b60
Create Date: 2026-11-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b7e4a1c2d9f3'
down_revision: Union[str, Sequence[str], None] = 'cc2bec3c0b60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('listing_requests',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('conversation_id', sa.UUID(), nullable=True),
    sa.Column('external_user_id', sa.String(length=64), nullable=False),
    sa.Column('category_id', sa.String(length=64), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('city', sa.String(length=64), nullable=False),
    sa.Column('area', sa.String(length=64), nullable=True),
    sa.Column('budget_label', sa.String(length=64), nullable=True),
    sa.Column('contact_phone', sa.String(length=15), nullable=False),
    sa.Column('status', sa.String(length=16), server_default=sa.text("'review'"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('review', 'submitted', 'rejected')", name=op.f('ck_listing_requests_status')),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], name=op.f('fk_listing_requests_conversation_id_conversations'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_listing_requests'))
    )
    op.create_index('ix_listing_requests_user', 'listing_requests', ['external_user_id', sa.literal_column('created_at DESC')], unique=False)


def downgrade() -> None:
    op.drop_index('ix_listing_requests_user', table_name='listing_requests')
    op.drop_table('listing_requests')
