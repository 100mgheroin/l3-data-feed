from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from database.base import Base
from database.table.orderbook import OrderBook
from database.table.tradebook import TradeBook
from exceptions import DatabaseNotConnectedException

SQL_ROOT = Path(__file__).resolve().parent / "queries"


def load_sql(name: str) -> str:
    if name.endswith(".sql"):
        sql_path = SQL_ROOT / name
    else:
        sql_path = SQL_ROOT / f"{name}.sql"
    return sql_path.read_text(encoding="utf-8")


class Database:
    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.async_session: async_sessionmaker[AsyncSession] | None = None

    async def connect(
        self, username: str, password: str, hostname: str, port: int, db_name: str
    ) -> None:
        logger.info("Connecting to database...")

        url = f"postgresql+asyncpg://{username}:{password}@{hostname}:{port}/{db_name}"

        self.engine = create_async_engine(
            url,
            echo=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            pool_pre_ping=True,
        )

        self.async_session = async_sessionmaker(
            bind=self.engine, expire_on_commit=False
        )

        await self._create_tables()

        logger.info("Connected to database!")

    async def _create_tables(self) -> None:
        if not self.engine:
            raise DatabaseNotConnectedException()

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def clear_all_orderbooks(self) -> None:
        if not self.async_session:
            raise DatabaseNotConnectedException()

        async with self.async_session() as session:
            await session.execute(text(load_sql("maintenance/truncate_orderbook")))

    async def save_orderbook(self, rows: dict[str, Any]) -> None:
        if not rows:
            return

        if not self.async_session:
            raise DatabaseNotConnectedException()

        async with self.async_session() as session:
            async with session.begin():
                await session.execute(insert(OrderBook), rows)

    async def save_tradebook(self, rows: dict[str, Any]) -> None:
        if not rows:
            return

        if not self.async_session:
            raise DatabaseNotConnectedException()

        async with self.async_session() as session:
            async with session.begin():
                await session.execute(insert(TradeBook), rows)

    async def get_tradebook_bins(
        self,
        symbol: str,
        start_ts: int,
        end_ts: int,
        time_agg_ms: int,
        price_bin_size: float,
    ) -> list[dict[str, Any]]:
        if price_bin_size <= 0.0:
            raise ValueError("price_bin_size must be greater than zero")

        if time_agg_ms <= 0:
            raise ValueError("time_agg_ms must be greater than zero")

        if not self.async_session:
            raise DatabaseNotConnectedException()

        sql_query = text(
            load_sql("analytics/postgres_tradebook_bins").format(
                symbol_filter="symbol = :symbol"
            )
        )

        params = {
            "symbol": symbol,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "time_agg_ms": time_agg_ms,
            "price_bin_size": price_bin_size,
        }

        async with self.async_session() as session:
            result = await session.execute(sql_query, params)
            return [dict(row) for row in result.mappings().all()]

    async def disconnect(self) -> None:
        if self.engine:
            await self.engine.dispose()
