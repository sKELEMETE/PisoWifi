from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from database import Base


class ClientStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class Client(Base):
    __tablename__ = "clients"

    __table_args__ = (
        Index("ix_clients_current_ip", "current_ip"),
        Index("ix_clients_last_seen", "last_seen"),
        Index("ix_clients_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    mac_address: Mapped[str] = mapped_column(
        String(17),
        unique=True,
        nullable=False,
    )

    current_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    hostname: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    first_seen: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    status: Mapped[ClientStatus] = mapped_column(
        SqlEnum(ClientStatus),
        default=ClientStatus.OFFLINE,
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

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
    )

    redeemed_vouchers: Mapped[list["Voucher"]] = relationship(
        back_populates="used_by_client",
    )
