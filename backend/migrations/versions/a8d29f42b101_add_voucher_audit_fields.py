"""add_voucher_audit_fields

Revision ID: a8d29f42b101
Revises: fffa6e27566e
Create Date: 2026-07-20 18:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a8d29f42b101'
down_revision: Union[str, Sequence[str], None] = 'fffa6e27566e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('vouchers')]
    
    if 'created_by' not in columns:
        op.add_column('vouchers', sa.Column('created_by', sa.String(length=255), nullable=True))
    if 'notes' not in columns:
        op.add_column('vouchers', sa.Column('notes', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('vouchers', 'notes')
    op.drop_column('vouchers', 'created_by')
