import numpy as np
import pandas as pd

from src.brokers.base import BrokerClient
from src.screener import scan_watchlist
from src.strategy import SmaRsiStrategy, StrategyParams


class FakeBroker(BrokerClient):
    """Bróker de prueba: devuelve una serie de precios fija, sin red."""

    def __init__(self, name: str, closes: list[float]):
        self.name = name
        self.closes = closes

    def fetch_ohlcv_df(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        n = len(self.closes)
        return pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h"),
                "open": self.closes,
                "high": [c * 1.001 for c in self.closes],
                "low": [c * 0.999 for c in self.closes],
                "close": self.closes,
                "volume": [100] * n,
            }
        )

    def fetch_available_cash(self) -> float:
        return 1000.0

    def create_market_buy(self, symbol, qty):
        raise NotImplementedError

    def create_market_sell(self, symbol, qty):
        raise NotImplementedError


def _uptrend(n=100, start=100.0, step=0.8, noise=0.05, seed=1):
    rng = np.random.default_rng(seed)
    return list(start + np.arange(n) * step + rng.normal(0, noise, n))


def _flat(n=100, level=100.0, noise=0.05, seed=2):
    rng = np.random.default_rng(seed)
    return list(level + rng.normal(0, noise, n))


def test_scan_watchlist_ranks_buy_signals_first():
    strategy = SmaRsiStrategy(StrategyParams(fast_ma=5, slow_ma=15, rsi_period=14))

    strong_uptrend = FakeBroker("brokerA", _uptrend(n=100, step=1.2, seed=1))
    flat = FakeBroker("brokerA", _flat(n=100, seed=2))

    watchlist = [
        (flat, "FLAT", "1h"),
        (strong_uptrend, "UP", "1h"),
    ]

    results = scan_watchlist(watchlist, strategy)

    assert len(results) == 2
    # Cualquier señal de compra debe aparecer antes que las que no lo son.
    buy_results = [c for c in results if c.signal == "buy"]
    non_buy_results = [c for c in results if c.signal != "buy"]
    assert results[: len(buy_results)] == buy_results
    assert results[len(buy_results):] == non_buy_results


def test_scan_watchlist_skips_symbols_with_insufficient_data():
    strategy = SmaRsiStrategy(StrategyParams(fast_ma=5, slow_ma=50, rsi_period=14))
    short_history = FakeBroker("brokerA", _uptrend(n=10))

    results = scan_watchlist([(short_history, "SHORT", "1h")], strategy)

    assert results == []
