"""add_missing_indexes

Revision ID: c24c32020e4c
Revises: b102_add_remaining_seconds
Create Date: 2026-07-21 18:31:40.717957

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c24c32020e4c'
down_revision: Union[str, Sequence[str], None] = 'b102_add_remaining_seconds'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Add index on coin_reservations.expires_at (queried by every coin operation)
    existing = [idx['name'] for idx in inspector.get_indexes('coin_reservations')]
    if 'ix_coin_reservations_expires_at' not in existing:
        op.create_index('ix_coin_reservations_expires_at', 'coin_reservations', ['expires_at'])

    # Add index on sessions.paused_at (used in stale session cleanup)
    existing = [idx['name'] for idx in inspector.get_indexes('sessions')]
    if 'ix_sessions_paused_at' not in existing:
        op.create_index('ix_sessions_paused_at', 'sessions', ['paused_at'])


def downgrade() -> None:
    op.drop_index('ix_coin_reservations_expires_at', table_name='coin_reservations')
    op.drop_index('ix_sessions_paused_at', table_name='sessions')
