"""Rolling in-memory price history buffer for sparkline initial data."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class PricePoint:
    price: float
    timestamp: float


class PriceHistory:
    """Keeps the last N price points per ticker for sparkline seeding."""

    def __init__(self, max_points: int = 100) -> None:
        self._max = max_points
        self._data: dict[str, deque[PricePoint]] = {}

    def record(self, ticker: str, price: float, timestamp: float | None = None) -> None:
        if ticker not in self._data:
            self._data[ticker] = deque(maxlen=self._max)
        self._data[ticker].append(PricePoint(price=price, timestamp=timestamp or time.time()))

    def get(self, ticker: str) -> list[dict]:
        pts = self._data.get(ticker, [])
        return [{"price": p.price, "timestamp": p.timestamp} for p in pts]

    def tickers(self) -> list[str]:
        return list(self._data.keys())


def attach_history_to_cache(price_cache, price_history: PriceHistory) -> None:
    """Monkey-patch the cache's update method to also feed the history buffer."""
    original_update = price_cache.update

    def update_with_history(ticker: str, price: float, timestamp: float | None = None):
        result = original_update(ticker=ticker, price=price, timestamp=timestamp)
        price_history.record(ticker=ticker, price=price, timestamp=timestamp)
        return result

    price_cache.update = update_with_history
