from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)

    buy_order_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    sell_order_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)

    symbol: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    executed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    blockchain_tx_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
