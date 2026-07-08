from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from database import Base


class Rate(Base):
    __tablename__ = "rates"

    __table_args__ = (
        Index("ix_rates_enabled", "enabled"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    coin_value: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False,
    )

    minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
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

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="rate",
    )

    sales: Mapped[list["Sale"]] = relationship(
        back_populates="rate",
    )
