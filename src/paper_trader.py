import time
from dataclasses import dataclass

import pandas as pd

from src.brokers.alpaca_broker import AlpacaBroker
from src.brokers.base import BrokerClient
from src.brokers.binance_broker import BinanceBroker
from src.config import Config
from src.indicators import atr as atr_series
from src.logger import get_logger
from src.risk import RiskManager
from src.screener import scan_watchlist
from src.strategy import SmaRsiStrategy, StrategyParams

log = get_logger(__name__)


@dataclass
class OpenPosition:
    broker_name: str
    symbol: str
    entry_price: float
    qty: float
    stop_loss: float
    take_profit: float


class MultiAssetTrader:
    """Bucle de paper trading que evalúa una watchlist de varios símbolos —
    criptomonedas (Binance Testnet) y, opcionalmente, acciones/ETFs (Alpaca
    paper trading) — y decide en cuáles entrar según el score del screener.

    IMPORTANTE: solo corre en modo sandbox/paper. No ejecuta órdenes con
    dinero real.
    """

    def __init__(self, config: Config):
        if not config.sandbox:
            raise RuntimeError(
                "MultiAssetTrader solo debe usarse con SANDBOX=true. "
                "Pasar a trading real es una decisión aparte, fuera de este script."
            )

        self.config = config
        self.strategy = SmaRsiStrategy(
            StrategyParams(
                fast_ma=config.fast_ma,
                slow_ma=config.slow_ma,
                rsi_period=config.rsi_period,
                rsi_oversold=config.rsi_oversold,
                rsi_overbought=config.rsi_overbought,
            )
        )

        self.brokers: dict[str, BrokerClient] = {}
        self.risk_managers: dict[str, RiskManager] = {}
        self.timeframes: dict[str, str] = {}
        self.watchlist: list[tuple[BrokerClient, str, str]] = []
        self.positions: dict[tuple[str, str], OpenPosition] = {}

        self._setup_crypto()
        self._setup_stocks()

        if not self.watchlist:
            raise RuntimeError("La watchlist está vacía. Configura CRYPTO_WATCHLIST y/o STOCK_WATCHLIST en .env.")

    def _new_risk_manager(self) -> RiskManager:
        return RiskManager(
            risk_per_trade=self.config.risk_per_trade,
            max_daily_loss=self.config.max_daily_loss,
            atr_multiplier=self.config.atr_multiplier,
            reward_risk_ratio=self.config.reward_risk_ratio,
        )

    def _setup_crypto(self) -> None:
        if not self.config.crypto_watchlist:
            return
        binance = BinanceBroker(self.config.api_key, self.config.api_secret, sandbox=True)
        self.brokers["binance"] = binance
        self.risk_managers["binance"] = self._new_risk_manager()
        self.timeframes["binance"] = self.config.timeframe
        for symbol in self.config.crypto_watchlist:
            self.watchlist.append((binance, symbol, self.config.timeframe))

    def _setup_stocks(self) -> None:
        if not self.config.stock_watchlist:
            return
        if not self.config.alpaca_api_key or not self.config.alpaca_secret_key:
            log.warning(
                "STOCK_WATCHLIST configurado pero faltan ALPACA_API_KEY/ALPACA_SECRET_KEY; "
                "se omite el bloque TradFi."
            )
            return
        alpaca = AlpacaBroker(self.config.alpaca_api_key, self.config.alpaca_secret_key, paper=self.config.alpaca_paper)
        self.brokers["alpaca"] = alpaca
        self.risk_managers["alpaca"] = self._new_risk_manager()
        self.timeframes["alpaca"] = self.config.stock_timeframe
        for symbol in self.config.stock_watchlist:
            self.watchlist.append((alpaca, symbol, self.config.stock_timeframe))

    def run_once(self) -> None:
        self._manage_open_positions()

        open_slots = self.config.max_open_positions - len(self.positions)
        if open_slots <= 0:
            log.info("Máximo de posiciones abiertas alcanzado (%d).", self.config.max_open_positions)
            return

        candidates = scan_watchlist(self.watchlist, self.strategy)
        buys = [c for c in candidates if c.signal == "buy" and (c.broker, c.symbol) not in self.positions]

        if not buys:
            best = candidates[0] if candidates else None
            log.info("Sin candidatos de compra. Mejor señal actual: %s", best)
            return

        for candidate in buys[:open_slots]:
            self._try_open(candidate.broker, candidate.symbol, candidate.last_price)

    def _try_open(self, broker_name: str, symbol: str, last_price: float) -> None:
        broker = self.brokers[broker_name]
        risk_manager = self.risk_managers[broker_name]

        balance = broker.fetch_available_cash()
        if not risk_manager.can_open_new_trade(balance):
            log.warning("[%s] Límite de pérdida diaria alcanzado; se omite %s.", broker_name, symbol)
            return

        df = broker.fetch_ohlcv_df(symbol, self.timeframes[broker_name], limit=max(200, self.config.slow_ma + 20))
        atr_value = float(atr_series(df).iloc[-1])
        if pd.isna(atr_value) or atr_value <= 0:
            return

        qty = risk_manager.position_size(balance, last_price, atr_value)
        if qty <= 0:
            log.info("[%s] %s: señal de compra pero tamaño calculado es 0 (saldo insuficiente).", broker_name, symbol)
            return

        broker.create_market_buy(symbol, qty)
        position = OpenPosition(
            broker_name=broker_name,
            symbol=symbol,
            entry_price=last_price,
            qty=qty,
            stop_loss=risk_manager.stop_loss_price(last_price, atr_value),
            take_profit=risk_manager.take_profit_price(last_price, atr_value),
        )
        self.positions[(broker_name, symbol)] = position
        log.info(
            "Posición abierta [%s] %s qty=%.6f entrada=%.2f stop=%.2f take_profit=%.2f",
            broker_name, symbol, qty, last_price, position.stop_loss, position.take_profit,
        )

    def _manage_open_positions(self) -> None:
        for key, position in list(self.positions.items()):
            broker_name, symbol = key
            broker = self.brokers[broker_name]
            try:
                df = broker.fetch_ohlcv_df(symbol, self.timeframes[broker_name], limit=5)
                price = float(df.iloc[-1]["close"])
            except Exception:
                log.exception("[%s] Error consultando precio de %s.", broker_name, symbol)
                continue

            hit_stop = price <= position.stop_loss
            hit_tp = price >= position.take_profit
            if not (hit_stop or hit_tp):
                continue

            broker.create_market_sell(symbol, position.qty)
            pnl = (price - position.entry_price) * position.qty
            self.risk_managers[broker_name].register_trade_result(pnl)
            reason = "stop_loss" if hit_stop else "take_profit"
            log.info(
                "Posición cerrada [%s] %s (%s) precio=%.2f pnl=%.2f pnl_diario=%.2f",
                broker_name, symbol, reason, price, pnl, self.risk_managers[broker_name].daily_pnl,
            )
            del self.positions[key]

    def run_forever(self) -> None:
        watchlist_desc = [f"{symbol}[{broker.name}]" for broker, symbol, _ in self.watchlist]
        log.info(
            "Iniciando paper trading multi-activo. Watchlist=%s max_open_positions=%d",
            watchlist_desc, self.config.max_open_positions,
        )
        while True:
            try:
                self.run_once()
            except Exception:
                log.exception("Error en la iteración del bot; se continúa en el siguiente ciclo.")
            time.sleep(self.config.loop_interval_seconds)
