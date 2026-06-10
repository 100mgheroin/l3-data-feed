import asyncio
import time
from datetime import datetime, timezone
from this import d
from typing import Any

import orjson
from loguru import logger
from picows import (
    WSError,
    WSFrame,
    WSListener,
    WSMsgType,
    WSTransport,
    picows,
    ws_connect,
)

from .database import Database


async def run_websocket(url: str, symbols: list[str], database: Database):
    while True:
        try:
            logger.info(f"Connecting to {url}...")

            transport, protocol = await ws_connect(
                lambda: BybitWSHandler(symbols=symbols, database=database), url
            )

            logger.info("Connected!")

            await transport.wait_disconnected()
            logger.info("Connection closed.")

        except (ConnectionRefusedError, OSError, WSError) as e:
            print(f"Connection failed: {e}. Retrying in 5s...")

        await asyncio.sleep(5)


class BybitWSHandler(WSListener):
    def __init__(self, symbols, database: Database):
        self.symbols: list[str] = symbols
        self.ob_topic: list[str] = [f"orderbook.50.{s}" for s in symbols]
        self.trade_topic: list[str] = [f"publicTrade.{s}" for s in symbols]
        self.database: Database = database
        self.asks: dict[str, Any] = {}
        self.bids: dict[str, Any] = {}
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self.cooldown: dict[str, int] = {}

    def on_ws_connected(self, transport: WSTransport):
        subscribe_msg = {"op": "subscribe", "args": self.ob_topic + self.trade_topic}

        transport.send(WSMsgType.TEXT, orjson.dumps(subscribe_msg))

        logger.info(f"Subscribed to {self.symbols}")

    def _update_book(self, side_dict: dict[str, Any], data: list[tuple[str, str]]):
        for price, size in data:
            if float(size) == 0:
                side_dict.pop(price, None)
            else:
                side_dict[price] = size

    def _serialize_l2(self, side_dict: dict[str, Any], reverse: bool = False):
        sorted_prices = sorted(side_dict.keys(), key=float, reverse=reverse)

        return ";".join([f"{p}:{side_dict[p]}" for p in sorted_prices])

    def on_ws_frame(self, transport: WSTransport, frame: WSFrame):
        try:
            msg = orjson.loads(frame.get_payload_as_ascii_text())
            topic: str | None = msg.get("topic")

            if topic is None:
                return

            if topic.startswith("publicTrade."):
                symbol: str = topic.replace("publicTrade.", "")
                symbol.replace(".", "")

                self.loop.create_task(self._handle_trade(symbol, msg))

            if topic.startswith("orderbook.50."):
                symbol = topic.replace("orderbook.50.", "")
                symbol.replace(".", "")

                self.loop.create_task(self._handle_orderbook(symbol, msg))

        except Exception as e:
            logger.error(f"Error: {e}")

    async def _handle_orderbook(self, symbol: str, msg: dict[str, Any]):
        current_time: int = time.time_ns() // 1_000_000

        data: dict[str, Any] = msg.get("data", {})
        m_type: str | None = msg.get("type")
        u_id: int | None = data.get("u")

        if m_type == "snapshot" or u_id == 1:
            self.asks[symbol] = {item[0]: item[1] for item in data.get("a", [])}
            self.bids[symbol] = {item[0]: item[1] for item in data.get("b", [])}
        else:
            self._update_book(self.asks[symbol], data.get("a", []))
            self._update_book(self.bids[symbol], data.get("b", []))

        if current_time - self.cooldown.get(symbol, 0) < 1000:
            return

        if self.asks[symbol] and self.bids[symbol]:
            s_ask = sorted(self.asks[symbol].keys(), key=float)
            s_bid = sorted(self.bids[symbol].keys(), key=float, reverse=True)
            b_ask, b_bid = float(s_ask[0]), float(s_bid[0])

            row: dict[str, Any] = {
                "ts_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
                "mid": round((b_bid + b_ask) / 2, 2),
                "best_bid": round(b_bid, 2),
                "best_ask": round(b_ask, 2),
                "bid_sz": float(self.bids[symbol][s_bid[0]]),
                "ask_sz": float(self.asks[symbol][s_ask[0]]),
                "bid": self._serialize_l2(self.bids[symbol], reverse=True),
                "ask": self._serialize_l2(self.asks[symbol], reverse=False),
                "spread": round(b_ask - b_bid, 2),
                "exchange_ts": msg.get("cts", 0),
                "update_count": u_id,
                "symbol": symbol,
            }

            self.cooldown[symbol] = current_time

            await self.database.save_orderbook(row)

    async def _handle_trade(self, symbol, msg):
        for t in msg.get("data", []):
            side = t.get("S")

            row: dict[str, Any] = {
                "ts_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
                "price": float(t.get("p")),
                "size": float(t.get("v")),
                "is_bid": side == "Buy",
                "is_otc": side == "Sell",
                "symbol": symbol,
            }

            await self.database.save_tradebook(row)
