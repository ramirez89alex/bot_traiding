import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from src.brokers.base import BrokerClient
from src.logger import get_logger

log = get_logger(__name__)

_UNIT_MAP = {"m": TimeFrameUnit.Minute, "h": TimeFrameUnit.Hour, "d": TimeFrameUnit.Day}


def parse_timeframe(timeframe: str) -> TimeFrame:
    """Convierte strings tipo '15m', '1h', '1d' al TimeFrame de alpaca-py."""
    tf = timeframe.strip().lower()
    digits = "".join(ch for ch in tf if ch.isdigit()) or "1"
    letters = "".join(ch for ch in tf if ch.isalpha())
    unit = _UNIT_MAP.get(letters[:1], TimeFrameUnit.Day)
    return TimeFrame(int(digits), unit)


class AlpacaBroker(BrokerClient):
    """Bróker TradFi (acciones/ETFs de EE.UU.) vía Alpaca. `paper=True` opera
    contra el entorno de pruebas de Alpaca (dinero ficticio)."""

    name = "alpaca"

    def __init__(self, api_key: str, secret_key: str, paper: bool = True):
        self.trading = TradingClient(api_key, secret_key, paper=paper)
        self.data = StockHistoricalDataClient(api_key, secret_key)
        self.paper = paper

    def fetch_ohlcv_df(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        request = StockBarsRequest(symbol_or_symbols=symbol, timeframe=parse_timeframe(timeframe), limit=limit)
        bars = self.data.get_stock_bars(request).df.reset_index()
        if "symbol" in bars.columns:
            bars = bars[bars["symbol"] == symbol]
        bars = bars.rename(columns={"timestamp": "timestamp"})
        return bars[["timestamp", "open", "high", "low", "close", "volume"]].tail(limit).reset_index(drop=True)

    def fetch_available_cash(self) -> float:
        account = self.trading.get_account()
        return float(account.cash)

    def create_market_buy(self, symbol: str, qty: float):
        log.info("Orden MARKET BUY %s qty=%s (alpaca paper=%s)", symbol, qty, self.paper)
        order = MarketOrderRequest(symbol=symbol, qty=round(qty, 4), side=OrderSide.BUY, time_in_force=TimeInForce.DAY)
        return self.trading.submit_order(order)

    def create_market_sell(self, symbol: str, qty: float):
        log.info("Orden MARKET SELL %s qty=%s (alpaca paper=%s)", symbol, qty, self.paper)
        order = MarketOrderRequest(symbol=symbol, qty=round(qty, 4), side=OrderSide.SELL, time_in_force=TimeInForce.DAY)
        return self.trading.submit_order(order)
