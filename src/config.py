from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes")


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


@dataclass(frozen=True)
class Config:
    api_key: str
    api_secret: str
    symbol: str
    timeframe: str
    sandbox: bool

    initial_balance: float
    risk_per_trade: float
    max_daily_loss: float
    atr_multiplier: float
    reward_risk_ratio: float

    fast_ma: int
    slow_ma: int
    rsi_period: int
    rsi_oversold: float
    rsi_overbought: float

    loop_interval_seconds: int


def load_config() -> Config:
    return Config(
        api_key=os.getenv("BINANCE_API_KEY", ""),
        api_secret=os.getenv("BINANCE_API_SECRET", ""),
        symbol=os.getenv("SYMBOL", "BTC/USDT"),
        timeframe=os.getenv("TIMEFRAME", "15m"),
        sandbox=_bool("SANDBOX", True),
        initial_balance=_float("INITIAL_BALANCE", 1000),
        risk_per_trade=_float("RISK_PER_TRADE", 0.01),
        max_daily_loss=_float("MAX_DAILY_LOSS", 0.03),
        atr_multiplier=_float("ATR_MULTIPLIER", 2.0),
        reward_risk_ratio=_float("REWARD_RISK_RATIO", 1.5),
        fast_ma=_int("FAST_MA", 20),
        slow_ma=_int("SLOW_MA", 50),
        rsi_period=_int("RSI_PERIOD", 14),
        rsi_oversold=_float("RSI_OVERSOLD", 35),
        rsi_overbought=_float("RSI_OVERBOUGHT", 65),
        loop_interval_seconds=_int("LOOP_INTERVAL_SECONDS", 60),
    )
