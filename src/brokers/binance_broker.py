import pandas as pd

from src.brokers.base import BrokerClient
from src.exchange import ExchangeClient


class BinanceBroker(BrokerClient):
    """Adapta ExchangeClient (ccxt/Binance) a la interfaz común BrokerClient."""

    name = "binance"

    def __init__(self, api_key: str, api_secret: str, sandbox: bool = True, quote_asset: str = "USDT"):
        self.client = ExchangeClient(api_key, api_secret, sandbox=sandbox)
        self.quote_asset = quote_asset

    def fetch_ohlcv_df(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        return self.client.fetch_ohlcv_df(symbol, timeframe, limit=limit)

    def fetch_available_cash(self) -> float:
        return self.client.fetch_quote_balance(self.quote_asset)

    def create_market_buy(self, symbol: str, qty: float):
        return self.client.create_market_buy(symbol, qty)

    def create_market_sell(self, symbol: str, qty: float):
        return self.client.create_market_sell(symbol, qty)
