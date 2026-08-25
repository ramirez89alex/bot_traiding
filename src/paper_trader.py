import time
from dataclasses import dataclass

from src.config import Config
from src.exchange import ExchangeClient
from src.indicators import atr as atr_series
from src.logger import get_logger
from src.risk import RiskManager
from src.strategy import SmaRsiStrategy, StrategyParams

log = get_logger(__name__)


@dataclass
class OpenPosition:
    entry_price: float
    qty: float
    stop_loss: float
    take_profit: float


class PaperTrader:
    """Bucle de trading contra Binance Testnet (paper trading con dinero ficticio).

    IMPORTANTE: mientras `config.sandbox` sea True, todas las órdenes se ejecutan
    en el entorno de pruebas de Binance, no con dinero real.
    """

    def __init__(self, config: Config):
        if not config.sandbox:
            raise RuntimeError(
                "PaperTrader solo debe usarse con SANDBOX=true. "
                "Pasar a trading real es una decisión aparte, fuera de este script."
            )

        self.config = config
        self.client = ExchangeClient(config.api_key, config.api_secret, sandbox=True)
        self.strategy = SmaRsiStrategy(
            StrategyParams(
                fast_ma=config.fast_ma,
                slow_ma=config.slow_ma,
                rsi_period=config.rsi_period,
                rsi_oversold=config.rsi_oversold,
                rsi_overbought=config.rsi_overbought,
            )
        )
        self.risk_manager = RiskManager(
            risk_per_trade=config.risk_per_trade,
            max_daily_loss=config.max_daily_loss,
            atr_multiplier=config.atr_multiplier,
            reward_risk_ratio=config.reward_risk_ratio,
        )
        self.position: OpenPosition | None = None
        self.quote_asset = config.symbol.split("/")[1]

    def run_once(self) -> None:
        df = self.client.fetch_ohlcv_df(self.config.symbol, self.config.timeframe, limit=max(200, self.config.slow_ma + 20))
        df["atr"] = atr_series(df)
        last = df.iloc[-1]

        if self.position is not None:
            self._manage_open_position(last)
            return

        balance = self.client.fetch_quote_balance(self.quote_asset)
        if not self.risk_manager.can_open_new_trade(balance):
            log.warning("Límite de pérdida diaria alcanzado. No se abren nuevas operaciones hoy.")
            return

        signal = self.strategy.generate_signal(df)

        if signal == "buy" and last["atr"] > 0:
            entry_price = float(last["close"])
            qty = self.risk_manager.position_size(balance, entry_price, float(last["atr"]))
            if qty <= 0:
                log.info("Señal de compra pero tamaño calculado es 0 (balance insuficiente).")
                return

            self.client.create_market_buy(self.config.symbol, qty)
            self.position = OpenPosition(
                entry_price=entry_price,
                qty=qty,
                stop_loss=self.risk_manager.stop_loss_price(entry_price, float(last["atr"])),
                take_profit=self.risk_manager.take_profit_price(entry_price, float(last["atr"])),
            )
            log.info(
                "Posición abierta: entrada=%.2f qty=%.6f stop=%.2f take_profit=%.2f",
                entry_price, qty, self.position.stop_loss, self.position.take_profit,
            )
        else:
            log.info("Sin señal de entrada (signal=%s).", signal)

    def _manage_open_position(self, last_bar) -> None:
        price = float(last_bar["close"])
        pos = self.position

        hit_stop = price <= pos.stop_loss
        hit_tp = price >= pos.take_profit

        if not (hit_stop or hit_tp):
            log.info("Posición abierta sin cambios. precio=%.2f stop=%.2f tp=%.2f", price, pos.stop_loss, pos.take_profit)
            return

        self.client.create_market_sell(self.config.symbol, pos.qty)
        pnl = (price - pos.entry_price) * pos.qty
        self.risk_manager.register_trade_result(pnl)
        reason = "stop_loss" if hit_stop else "take_profit"
        log.info("Posición cerrada (%s). precio=%.2f pnl=%.2f pnl_diario=%.2f", reason, price, pnl, self.risk_manager.daily_pnl)
        self.position = None

    def run_forever(self) -> None:
        log.info(
            "Iniciando paper trading: symbol=%s timeframe=%s sandbox=%s",
            self.config.symbol, self.config.timeframe, self.config.sandbox,
        )
        while True:
            try:
                self.run_once()
            except Exception:
                log.exception("Error en la iteración del bot; se continúa en el siguiente ciclo.")
            time.sleep(self.config.loop_interval_seconds)
