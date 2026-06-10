from sqlalchemy import BigInteger, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from data.database.base import Base


class TradeBook(Base):
    __tablename__ = "tradebook"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    ts_ms: Mapped[int] = mapped_column(BigInteger)

    price: Mapped[float] = mapped_column(Float)

    size: Mapped[float] = mapped_column(Float)

    is_bid: Mapped[bool] = mapped_column(Boolean)

    is_otc: Mapped[bool] = mapped_column(Boolean)

    symbol: Mapped[str] = mapped_column()