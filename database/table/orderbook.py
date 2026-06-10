from sqlalchemy import BigInteger, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


# Add index = True if we want to sort by parameter
class OrderBook(Base):
    __tablename__ = "orderbook"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    ts_ms: Mapped[int] = mapped_column(BigInteger)

    mid: Mapped[float] = mapped_column(Float(precision=2))

    best_bid: Mapped[float] = mapped_column(Float(precision=2))

    best_ask: Mapped[float] = mapped_column(Float(precision=2))

    bid_sz: Mapped[float] = mapped_column(Float)

    ask_sz: Mapped[float] = mapped_column(Float)

    bid: Mapped[str] = mapped_column(String)

    ask: Mapped[str] = mapped_column(String)

    spread: Mapped[float] = mapped_column(Float)

    exchange_ts: Mapped[int] = mapped_column(BigInteger)

    update_count: Mapped[int] = mapped_column(BigInteger)

    symbol: Mapped[str] = mapped_column()
