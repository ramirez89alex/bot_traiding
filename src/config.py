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


def _list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Config:
    # Binance (cripto)
    api_key: str
    api_secret: str
    symbol: str
    timeframe: str
    crypto_watchlist: list[str]
    sandbox: bool

    # Alpaca (TradFi: acciones/ETFs)
    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_paper: bool
    stock_watchlist: list[str]
    stock_timeframe: str

    initial_balance: float
    risk_per_trade: float
    max_daily_loss: float
    atr_multiplier: float
    reward_risk_ratio: float
    max_open_positions: int

    fast_ma: int
    slow_ma: int
    rsi_period: int
    rsi_oversold: float
    rsi_overbought: float

    loop_interval_seconds: int


def load_config() -> Config:
    symbol = os.getenv("SYMBOL", "BTC/USDT")
    return Config(
        api_key=os.getenv("BINANCE_API_KEY", ""),
        api_secret=os.getenv("BINANCE_API_SECRET", ""),
        symbol=symbol,
        timeframe=os.getenv("TIMEFRAME", "15m"),
        crypto_watchlist=_list("CRYPTO_WATCHLIST") or [symbol],
        sandbox=_bool("SANDBOX", True),
        alpaca_api_key=os.getenv("ALPACA_API_KEY", ""),
        alpaca_secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
        alpaca_paper=_bool("ALPACA_PAPER", True),
        stock_watchlist=_list("STOCK_WATCHLIST"),
        stock_timeframe=os.getenv("STOCK_TIMEFRAME", "1d"),
        initial_balance=_float("INITIAL_BALANCE", 1000),
        risk_per_trade=_float("RISK_PER_TRADE", 0.01),
        max_daily_loss=_float("MAX_DAILY_LOSS", 0.03),
        atr_multiplier=_float("ATR_MULTIPLIER", 2.0),
        reward_risk_ratio=_float("REWARD_RISK_RATIO", 1.5),
        max_open_positions=_int("MAX_OPEN_POSITIONS", 3),
        fast_ma=_int("FAST_MA", 20),
        slow_ma=_int("SLOW_MA", 50),
        rsi_period=_int("RSI_PERIOD", 14),
        rsi_oversold=_float("RSI_OVERSOLD", 35),
        rsi_overbought=_float("RSI_OVERBOUGHT", 65),
        loop_interval_seconds=_int("LOOP_INTERVAL_SECONDS", 60),
    )
