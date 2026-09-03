"""Production Hardening Phase F - Database CHECK Constraints

Revision ID: g16_production_hardening_phase_f
Revises: f15_production_hardening_phase_b
Create Date: 2026-09-03 12:22:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision: str = 'g16_production_hardening_phase_f'
down_revision: Union[str, None] = 'f15_production_hardening_phase_b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    if dialect_name in ("mysql", "mariadb"):
        # Add CHECK constraint on sessions.remaining_seconds >= 0
        try:
            op.create_check_constraint(
                "chk_sessions_remaining_seconds_nonnegative",
                "sessions",
                "remaining_seconds >= 0"
            )
        except Exception:
            pass

        # Add CHECK constraint on sales
        try:
            op.create_check_constraint(
                "chk_sales_amount",
                "sales",
                "amount >= 0 AND (payment_method != 'COIN' OR amount > 0)"
            )
        except Exception:
            pass


def downgrade() -> None:
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    if dialect_name in ("mysql", "mariadb"):
        try:
            op.drop_constraint("chk_sessions_remaining_seconds_nonnegative", "sessions", type_="check")
        except Exception:
            pass
        try:
            op.drop_constraint("chk_sales_amount_positive", "sales", type_="check")
        except Exception:
            pass
