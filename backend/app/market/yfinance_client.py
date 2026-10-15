"""Yahoo Finance market data client using yfinance (free, no API key required)."""

from __future__ import annotations

import asyncio
import logging
import time

import yfinance as yf

from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)

_DEFAULT_POLL_INTERVAL = 15.0  # seconds — respects Yahoo Finance rate limits


class YFinanceDataSource(MarketDataSource):
    """MarketDataSource backed by Yahoo Finance via the yfinance library.

    Free, no API key needed. Works on corporate networks (standard HTTPS to Yahoo).
    Polls on a ~15s interval during market hours; returns previous close outside hours.
    """

    def __init__(self, price_cache: PriceCache, poll_interval: float = _DEFAULT_POLL_INTERVAL) -> None:
        self._cache = price_cache
        self._interval = poll_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        self._tickers = list(tickers)
        await self._poll_once()
        self._task = asyncio.create_task(self._poll_loop(), name="yfinance-poller")
        logger.info("yfinance poller started: %d tickers, %.1fs interval", len(tickers), self._interval)

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("yfinance poller stopped")

    async def add_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        if ticker not in self._tickers:
            self._tickers.append(ticker)
            logger.info("yfinance: added ticker %s", ticker)

    async def remove_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        self._tickers = [t for t in self._tickers if t != ticker]
        self._cache.remove(ticker)
        logger.info("yfinance: removed ticker %s", ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    async def _poll_loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            await self._poll_once()

    async def _poll_once(self) -> None:
        if not self._tickers:
            return
        try:
            prices = await asyncio.to_thread(self._fetch_prices)
            for ticker, price in prices.items():
                self._cache.update(ticker=ticker, price=price, timestamp=time.time())
            logger.debug("yfinance poll: updated %d/%d tickers", len(prices), len(self._tickers))
        except Exception as e:
            logger.error("yfinance poll failed: %s", e)

    def _fetch_prices(self) -> dict[str, float]:
        """Fetch latest prices synchronously. Runs in a thread pool."""
        tickers = list(self._tickers)  # snapshot to avoid mid-fetch mutations
        if not tickers:
            return {}
        data = yf.download(" ".join(tickers), period="1d", interval="5m", progress=False, auto_adjust=True)
        if data.empty:
            return {}

        prices: dict[str, float] = {}
        close = data["Close"]

        if len(tickers) == 1:
            series = close.dropna()
            if not series.empty:
                prices[tickers[0]] = float(series.iloc[-1])
        else:
            for ticker in tickers:
                if ticker in close.columns:
                    series = close[ticker].dropna()
                    if not series.empty:
                        prices[ticker] = float(series.iloc[-1])

        return prices
