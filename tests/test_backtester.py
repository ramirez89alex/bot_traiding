import numpy as np
import pandas as pd

from src.backtester import Backtester
from src.risk import RiskManager
from src.strategy import SmaRsiStrategy, StrategyParams


def make_synthetic_df(n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(seed=42)
    trend = np.linspace(100, 160, n)
    noise = np.cumsum(rng.normal(0, 0.5, n))
    close = trend + noise
    high = close + rng.uniform(0.1, 1.0, n)
    low = close - rng.uniform(0.1, 1.0, n)
    open_ = close + rng.uniform(-0.5, 0.5, n)

    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="15min"),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.uniform(10, 100, n),
        }
    )


def test_backtester_runs_and_returns_metrics():
    df = make_synthetic_df()
    strategy = SmaRsiStrategy(StrategyParams(fast_ma=10, slow_ma=30, rsi_period=14))
    risk_manager = RiskManager(risk_per_trade=0.01, max_daily_loss=0.03)

    backtester = Backtester(df, strategy, risk_manager, initial_balance=1000.0)
    result = backtester.run(warmup=35)

    assert result.final_balance > 0
    assert len(result.equity_curve) > 0

    metrics = result.metrics
    assert "total_trades" in metrics
    assert "win_rate" in metrics
    assert "max_drawdown_pct" in metrics
    assert metrics["total_trades"] == len(result.trades)


def test_backtester_never_exceeds_available_balance():
    df = make_synthetic_df()
    strategy = SmaRsiStrategy(StrategyParams(fast_ma=5, slow_ma=15, rsi_period=14))
    risk_manager = RiskManager(risk_per_trade=0.5, max_daily_loss=1.0)

    backtester = Backtester(df, strategy, risk_manager, initial_balance=1000.0)
    backtester.run(warmup=20)

    assert backtester.balance >= 0
