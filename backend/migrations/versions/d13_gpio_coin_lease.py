"""Add owner-bound heartbeat fields to coin reservations.

Revision ID: d13_gpio_coin_lease
Revises: c24c32020e4c
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d13_gpio_coin_lease"
down_revision: Union[str, Sequence[str], None] = "c24c32020e4c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("coin_reservations")}
    with op.batch_alter_table("coin_reservations") as batch:
        if "lease_id" not in columns:
            batch.add_column(sa.Column("lease_id", sa.String(length=64), nullable=True))
        if "owner_ip" not in columns:
            batch.add_column(sa.Column("owner_ip", sa.String(length=45), nullable=True))
        if "last_heartbeat_at" not in columns:
            batch.add_column(sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("coin_reservations") as batch:
        batch.drop_column("last_heartbeat_at")
        batch.drop_column("owner_ip")
        batch.drop_column("lease_id")
