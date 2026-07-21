from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from database import Base


class VoucherStatus(str, Enum):
    UNUSED = "UNUSED"
    USED = "USED"
    EXPIRED = "EXPIRED"


class Voucher(Base):
    __tablename__ = "vouchers"

    __table_args__ = (
        Index("ix_vouchers_status", "status"),
        Index("ix_vouchers_expiration", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )

    minutes: Mapped[int] = mapped_column(
        nullable=False,
    )

    status: Mapped[VoucherStatus] = mapped_column(
        SqlEnum(VoucherStatus),
        default=VoucherStatus.UNUSED,
        nullable=False,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    used_by_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id"),
        nullable=True,
    )

    created_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        String(255),
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

    used_by_client: Mapped["Client | None"] = relationship(
        back_populates="redeemed_vouchers",
    )
