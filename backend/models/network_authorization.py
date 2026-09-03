from __future__ import annotations

from datetime import datetime
from enum import Enum
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class NetworkAuthState(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    BLOCKED = "BLOCKED"
    THROTTLED = "THROTTLED"
    ISOLATED = "ISOLATED"


class NetworkAuthorization(Base):
    __tablename__ = "network_authorizations"

    __table_args__ = (
        Index("ix_netauth_mac", "mac_address"),
        Index("ix_netauth_desired", "desired_state"),
        Index("ix_netauth_applied", "applied_state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    mac_address: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    desired_state: Mapped[str] = mapped_column(
        String(20),
        default=NetworkAuthState.BLOCKED.value,
        nullable=False,
    )

    applied_state: Mapped[str] = mapped_column(
        String(20),
        default=NetworkAuthState.BLOCKED.value,
        nullable=False,
    )

    last_applied_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    failure_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    last_error: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    retry_after: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    reconciliation_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
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

    client = relationship("Client")
    session = relationship("Session")
