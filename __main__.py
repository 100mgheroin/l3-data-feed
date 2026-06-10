import asyncio
import sys

from asyncpg import ConnectionDoesNotExistError
from loguru import logger

from .config.app import get_settings
from .config.log import LogConfig
from .database import Database
from .websocket import BybitWSHandler
from .websocket.collector.bybit import run_websocket


async def main():
    logconfig = LogConfig()

    logconfig.setup()

    symbols = ["SOLUSDT", "BTCUSDT", "ETHUSDT", "XRPUSDT", "XAUTUSDT"]
    url = "wss://stream.bybit.com/v5/public/linear"

    database = Database()

    settings = get_settings()

    try:
        await database.connect(
            username=settings.DB_USER,
            password=settings.DB_PASSWORD,
            hostname=settings.DB_HOST,
            port=settings.DB_PORT,
            db_name=settings.DB_NAME,
        )

    except (ConnectionRefusedError, ConnectionDoesNotExistError):
        logger.critical("Connection to database failed...")
        logger.critical("Stopping app...")
        sys.exit(1)

    await run_websocket(url=url, symbols=symbols, database=database)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
