import ccxt
import pandas as pd

from src.logger import get_logger

log = get_logger(__name__)


class ExchangeClient:
    """Envoltorio delgado sobre ccxt.binance. `sandbox=True` apunta a Binance Testnet
    (testnet.binance.vision) para operar con dinero ficticio."""

    def __init__(self, api_key: str, api_secret: str, sandbox: bool = True):
        self.exchange = ccxt.binance(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            }
        )
        if sandbox:
            self.exchange.set_sandbox_mode(True)
        self.sandbox = sandbox

    def fetch_ohlcv_df(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        raw = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df

    def fetch_quote_balance(self, quote_asset: str) -> float:
        balance = self.exchange.fetch_balance()
        return float(balance.get("free", {}).get(quote_asset, 0.0))

    def create_market_buy(self, symbol: str, amount: float):
        log.info("Orden MARKET BUY %s qty=%s (sandbox=%s)", symbol, amount, self.sandbox)
        return self.exchange.create_order(symbol, "market", "buy", amount)

    def create_market_sell(self, symbol: str, amount: float):
        log.info("Orden MARKET SELL %s qty=%s (sandbox=%s)", symbol, amount, self.sandbox)
        return self.exchange.create_order(symbol, "market", "sell", amount)
