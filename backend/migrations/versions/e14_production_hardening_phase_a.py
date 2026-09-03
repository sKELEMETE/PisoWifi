"""Production Hardening Phase A - Coin events, client live session invariant, last accounted at

Revision ID: e14_production_hardening_phase_a
Revises: d13_gpio_coin_lease
Create Date: 2026-09-03 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision: str = 'e14_production_hardening_phase_a'
down_revision: Union[str, Sequence[str], None] = 'd13_gpio_coin_lease'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. Add last_accounted_at to sessions table
    session_columns = [col['name'] for col in inspector.get_columns('sessions')]
    if 'last_accounted_at' not in session_columns:
        with op.batch_alter_table('sessions') as batch:
            batch.add_column(sa.Column('last_accounted_at', sa.DateTime(), nullable=True))

    # Clean up any corrupt negative values before enforcing constraints
    conn.execute(text("UPDATE sessions SET remaining_seconds = 0 WHERE remaining_seconds < 0"))
    conn.execute(text("UPDATE sessions SET purchased_minutes = 0 WHERE purchased_minutes < 0"))

    # 2. Create coin_events table
    if 'coin_events' not in existing_tables:
        op.create_table(
            'coin_events',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('event_id', sa.String(length=64), nullable=False, unique=True),
            sa.Column('source', sa.String(length=32), nullable=False, server_default='serial'),
            sa.Column('denomination', sa.Integer(), nullable=False),
            sa.Column('pulse_count', sa.Integer(), nullable=True),
            sa.Column('lease_id', sa.String(length=64), nullable=True),
            sa.Column('mac', sa.String(length=50), nullable=True),
            sa.Column('received_at', sa.DateTime(), nullable=False),
            sa.Column('persisted_at', sa.DateTime(), nullable=False),
            sa.Column('processed_at', sa.DateTime(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='RECEIVED'),
            sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('failure_reason', sa.String(length=255), nullable=True),
        )
        op.create_index('ix_coin_events_event_id', 'coin_events', ['event_id'])
        op.create_index('ix_coin_events_status', 'coin_events', ['status'])
        op.create_index('ix_coin_events_lease_id', 'coin_events', ['lease_id'])
        op.create_index('ix_coin_events_mac', 'coin_events', ['mac'])

    # 3. Create client_live_sessions table (enforces DB invariant: exactly 1 live session per client)
    if 'client_live_sessions' not in existing_tables:
        op.create_table(
            'client_live_sessions',
            sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id', ondelete='CASCADE'), unique=True, nullable=False),
            sa.Column('status', sa.String(length=16), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

        # 4. Migrate and reconcile existing data into client_live_sessions
        # If any client has multiple ACTIVE or PAUSED sessions, keep the most recent,
        # merge any remaining purchased time from duplicates into the surviving session,
        # and expire the duplicates so customer time is never destroyed.
        active_or_paused = conn.execute(
            text("SELECT id, client_id, status, remaining_seconds, remaining_minutes, purchased_minutes FROM sessions WHERE status IN ('ACTIVE', 'PAUSED') ORDER BY client_id, id DESC")
        ).fetchall()

        seen_clients = {}
        for row in active_or_paused:
            s_id, c_id, s_status = row[0], row[1], str(row[2])
            rem_sec = row[3] or ((row[4] or 0) * 60)
            purchased_min = row[5] or 0
            if c_id not in seen_clients:
                seen_clients[c_id] = s_id
                conn.execute(
                    text("INSERT INTO client_live_sessions (client_id, session_id, status, updated_at) VALUES (:c, :s, :st, CURRENT_TIMESTAMP)"),
                    {"c": c_id, "s": s_id, "st": s_status}
                )
            else:
                # Merge duplicate time into the surviving primary session
                primary_sid = seen_clients[c_id]
                if rem_sec > 0 or purchased_min > 0:
                    conn.execute(
                        text("""
                            UPDATE sessions 
                            SET remaining_seconds = COALESCE(remaining_seconds, 0) + :sec,
                                remaining_minutes = (COALESCE(remaining_seconds, 0) + :sec) / 60,
                                purchased_minutes = COALESCE(purchased_minutes, 0) + :pm
                            WHERE id = :psid
                        """),
                        {"sec": rem_sec, "pm": purchased_min, "psid": primary_sid}
                    )
                # Mark duplicate as EXPIRED with 0 remaining
                conn.execute(
                    text("UPDATE sessions SET status = 'EXPIRED', remaining_seconds = 0, remaining_minutes = 0 WHERE id = :s"),
                    {"s": s_id}
                )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'client_live_sessions' in existing_tables:
        op.drop_table('client_live_sessions')

    if 'coin_events' in existing_tables:
        op.drop_table('coin_events')

    session_columns = [col['name'] for col in inspector.get_columns('sessions')]
    if 'last_accounted_at' in session_columns:
        with op.batch_alter_table('sessions') as batch:
            batch.drop_column('last_accounted_at')
