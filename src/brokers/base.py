from abc import ABC, abstractmethod

import pandas as pd


class BrokerClient(ABC):
    """Interfaz común para cualquier bróker/exchange (cripto o TradFi).

    Permite que el screener y el trader operen sobre distintos brókers
    (Binance, Alpaca, ...) sin conocer sus detalles internos.
    """

    name: str

    @abstractmethod
    def fetch_ohlcv_df(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        """Devuelve un DataFrame con columnas timestamp, open, high, low, close, volume."""

    @abstractmethod
    def fetch_available_cash(self) -> float:
        """Efectivo disponible para operar, en la moneda base de la cuenta (USDT, USD, ...)."""

    @abstractmethod
    def create_market_buy(self, symbol: str, qty: float):
        ...

    @abstractmethod
    def create_market_sell(self, symbol: str, qty: float):
        ...
