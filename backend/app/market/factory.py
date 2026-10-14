"""Factory for creating market data sources."""

from __future__ import annotations

import logging
import os

from .cache import PriceCache
from .interface import MarketDataSource
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)


def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Create the appropriate market data source based on environment variables.

    - YFINANCE_ENABLED=true → YFinanceDataSource (real Yahoo Finance data, free, no API key)
    - Otherwise → SimulatorDataSource (GBM simulation, default, recommended)

    Returns an unstarted source. Caller must await source.start(tickers).
    """
    yfinance_enabled = os.environ.get("YFINANCE_ENABLED", "").strip().lower() in ("true", "1", "yes")

    if yfinance_enabled:
        from .yfinance_client import YFinanceDataSource  # lazy import — yfinance is optional
        logger.info("Market data source: Yahoo Finance via yfinance (real data)")
        return YFinanceDataSource(price_cache=price_cache)
    else:
        logger.info("Market data source: GBM Simulator")
        return SimulatorDataSource(price_cache=price_cache)
