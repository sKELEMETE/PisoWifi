from datetime import datetime
from enum import Enum
from sqlalchemy import String, Integer, DateTime, func, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from database import Base
from utils.time_utils import get_utc_now


class CoinEventStatus(str, Enum):
    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    ORPHANED = "ORPHANED"


class CoinEvent(Base):
    __tablename__ = "coin_events"

    __table_args__ = (
        Index("ix_coin_events_status", "status"),
        Index("ix_coin_events_lease_id", "lease_id"),
        Index("ix_coin_events_mac", "mac"),
        CheckConstraint("denomination > 0", name="chk_coin_events_denomination_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="serial")
    denomination: Mapped[int] = mapped_column(Integer, nullable=False)
    pulse_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lease_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mac: Mapped[str | None] = mapped_column(String(50), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)
    persisted_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=CoinEventStatus.RECEIVED.value, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
