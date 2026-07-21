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
