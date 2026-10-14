"""Tests for market data source factory."""

import os
from unittest.mock import patch

from app.market.cache import PriceCache
from app.market.factory import create_market_data_source
from app.market.simulator import SimulatorDataSource
from app.market.yfinance_client import YFinanceDataSource


class TestFactory:
    """Tests for create_market_data_source factory."""

    def test_creates_simulator_when_yfinance_not_set(self):
        """Simulator is default when YFINANCE_ENABLED is absent."""
        cache = PriceCache()
        with patch.dict(os.environ, {}, clear=True):
            source = create_market_data_source(cache)
        assert isinstance(source, SimulatorDataSource)

    def test_creates_simulator_when_yfinance_false(self):
        """Simulator is used when YFINANCE_ENABLED=false."""
        cache = PriceCache()
        with patch.dict(os.environ, {"YFINANCE_ENABLED": "false"}, clear=True):
            source = create_market_data_source(cache)
        assert isinstance(source, SimulatorDataSource)

    def test_creates_simulator_when_yfinance_empty(self):
        """Simulator is used when YFINANCE_ENABLED is empty string."""
        cache = PriceCache()
        with patch.dict(os.environ, {"YFINANCE_ENABLED": ""}, clear=True):
            source = create_market_data_source(cache)
        assert isinstance(source, SimulatorDataSource)

    def test_creates_yfinance_when_enabled(self):
        """YFinanceDataSource is created when YFINANCE_ENABLED=true."""
        cache = PriceCache()
        with patch.dict(os.environ, {"YFINANCE_ENABLED": "true"}, clear=True):
            source = create_market_data_source(cache)
        assert isinstance(source, YFinanceDataSource)

    def test_creates_yfinance_when_enabled_uppercase(self):
        """YFINANCE_ENABLED is case-insensitive."""
        cache = PriceCache()
        with patch.dict(os.environ, {"YFINANCE_ENABLED": "TRUE"}, clear=True):
            source = create_market_data_source(cache)
        assert isinstance(source, YFinanceDataSource)

    def test_simulator_receives_cache(self):
        """Simulator receives the cache reference."""
        cache = PriceCache()
        with patch.dict(os.environ, {}, clear=True):
            source = create_market_data_source(cache)
        assert isinstance(source, SimulatorDataSource)
        assert source._cache is cache

    def test_yfinance_receives_cache(self):
        """YFinanceDataSource receives the cache reference."""
        cache = PriceCache()
        with patch.dict(os.environ, {"YFINANCE_ENABLED": "true"}, clear=True):
            source = create_market_data_source(cache)
        assert isinstance(source, YFinanceDataSource)
        assert source._cache is cache
