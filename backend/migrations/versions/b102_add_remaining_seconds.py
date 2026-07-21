"""add_remaining_seconds_to_sessions

Revision ID: b102_add_remaining_seconds
Revises: a8d29f42b101
Create Date: 2026-07-20 19:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b102_add_remaining_seconds'
down_revision: Union[str, Sequence[str], None] = 'a8d29f42b101'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('sessions')]
    
    if 'remaining_seconds' not in columns:
        op.add_column('sessions', sa.Column('remaining_seconds', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    op.drop_column('sessions', 'remaining_seconds')
