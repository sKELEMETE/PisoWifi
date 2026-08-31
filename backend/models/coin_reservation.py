from datetime import datetime
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from database import Base
from utils.time_utils import get_utc_now


class CoinReservation(Base):
    __tablename__ = "coin_reservations"

    mac: Mapped[str] = mapped_column(String(50), primary_key=True)
    reserved_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    lease_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    owner_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PendingCoin(Base):
    __tablename__ = "pending_coins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mac: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)
