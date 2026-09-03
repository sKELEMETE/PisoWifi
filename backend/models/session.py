from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from database import Base


from sqlalchemy import CheckConstraint, String

class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"


class Session(Base):
    __tablename__ = "sessions"

    __table_args__ = (
        Index("ix_sessions_status", "status"),
        Index("ix_sessions_client", "client_id"),
        Index("ix_sessions_end_time", "end_time"),
        Index("ix_sessions_status_end_time", "status", "end_time"),
        Index("ix_sessions_status_paused_at", "status", "paused_at"),
        CheckConstraint("remaining_seconds >= 0", name="chk_sessions_remaining_seconds_non_negative"),
        CheckConstraint("purchased_minutes >= 0", name="chk_sessions_purchased_minutes_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id"),
        nullable=False,
    )

    rate_id: Mapped[int] = mapped_column(
        ForeignKey("rates.id"),
        nullable=False,
    )

    status: Mapped[SessionStatus] = mapped_column(
        SqlEnum(SessionStatus),
        default=SessionStatus.ACTIVE,
        nullable=False,
    )

    purchased_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    remaining_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    remaining_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=0,
    )

    start_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    end_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    paused_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    pause_allowed: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    last_accounted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    client: Mapped["Client"] = relationship(
        back_populates="sessions",
    )

    rate: Mapped["Rate"] = relationship(
        back_populates="sessions",
    )

    sales: Mapped[list["Sale"]] = relationship(
        back_populates="session",
    )


class ClientLiveSession(Base):
    __tablename__ = "client_live_sessions"

    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        primary_key=True,
    )

    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
