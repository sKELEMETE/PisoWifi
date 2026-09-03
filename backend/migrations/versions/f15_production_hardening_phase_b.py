"""Production Hardening Phase B - Transactional Network Authorization Table

Revision ID: f15_production_hardening_phase_b
Revises: e14_production_hardening_phase_a
Create Date: 2026-09-03 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision: str = 'f15_production_hardening_phase_b'
down_revision: Union[str, Sequence[str], None] = 'e14_production_hardening_phase_a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'network_authorizations' not in existing_tables:
        op.create_table(
            'network_authorizations',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id', ondelete='CASCADE'), unique=True, nullable=False),
            sa.Column('mac_address', sa.String(length=50), nullable=False),
            sa.Column('ip_address', sa.String(length=50), nullable=True),
            sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id', ondelete='SET NULL'), nullable=True),
            sa.Column('desired_state', sa.String(length=20), nullable=False, server_default='BLOCKED'),
            sa.Column('applied_state', sa.String(length=20), nullable=False, server_default='BLOCKED'),
            sa.Column('last_applied_at', sa.DateTime(), nullable=True),
            sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('last_error', sa.String(length=255), nullable=True),
            sa.Column('retry_after', sa.DateTime(), nullable=True),
            sa.Column('reconciliation_version', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_netauth_mac', 'network_authorizations', ['mac_address'])
        op.create_index('ix_netauth_desired', 'network_authorizations', ['desired_state'])
        op.create_index('ix_netauth_applied', 'network_authorizations', ['applied_state'])

        # Seed network_authorizations from existing live sessions
        rows = conn.execute(text(
            "SELECT cls.client_id, cls.session_id, cls.status, c.mac_address, c.current_ip "
            "FROM client_live_sessions cls "
            "JOIN clients c ON c.id = cls.client_id"
        )).fetchall()

        for row in rows:
            c_id, s_id, status, mac, ip = row[0], row[1], str(row[2]), str(row[3]), row[4]
            desired = "AUTHORIZED" if status == "ACTIVE" else "BLOCKED"
            conn.execute(text(
                "INSERT INTO network_authorizations "
                "(client_id, mac_address, ip_address, session_id, desired_state, applied_state, created_at, updated_at) "
                "VALUES (:c, :m, :ip, :s, :d, 'BLOCKED', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ), {"c": c_id, "m": mac, "ip": ip, "s": s_id, "d": desired})


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'network_authorizations' in existing_tables:
        op.drop_table('network_authorizations')
