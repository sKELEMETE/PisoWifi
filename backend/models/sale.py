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


class PaymentMethod(str, Enum):
    COIN = "COIN"
    VOUCHER = "VOUCHER"


class Sale(Base):
    __tablename__ = "sales"

    __table_args__ = (
        Index("ix_sales_created_at", "created_at"),
        Index("ix_sales_payment_method", "payment_method"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id"),
        nullable=False,
    )

    rate_id: Mapped[int] = mapped_column(
        ForeignKey("rates.id"),
        nullable=False,
    )

    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    payment_method: Mapped[PaymentMethod] = mapped_column(
        SqlEnum(PaymentMethod),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    session: Mapped["Session"] = relationship(
        back_populates="sales",
    )

    rate: Mapped["Rate"] = relationship(
        back_populates="sales",
    )
