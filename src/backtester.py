from dataclasses import dataclass, field

import pandas as pd

from src.indicators import atr as atr_series
from src.risk import RiskManager
from src.strategy import SmaRsiStrategy


@dataclass
class Trade:
    entry_time: pd.Timestamp
    entry_price: float
    qty: float
    stop_loss: float
    take_profit: float
    exit_time: pd.Timestamp | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    pnl: float = 0.0


@dataclass
class BacktestResult:
    trades: list[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    final_balance: float = 0.0

    @property
    def metrics(self) -> dict:
        if not self.trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_return_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "profit_factor": 0.0,
            }

        pnls = [t.pnl for t in self.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        initial = self.equity_curve.iloc[0]
        final = self.equity_curve.iloc[-1]
        running_max = self.equity_curve.cummax()
        drawdown = (self.equity_curve - running_max) / running_max
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))

        return {
            "total_trades": len(self.trades),
            "win_rate": len(wins) / len(self.trades),
            "total_return_pct": (final - initial) / initial * 100,
            "max_drawdown_pct": drawdown.min() * 100,
            "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else float("inf"),
        }


class Backtester:
    """Simula la estrategia sobre datos OHLCV históricos, vela a vela.

    Solo abre posiciones largas (compra -> vende), sin apalancamiento ni ventas
    en corto, replicando cómo operaría el bot en un spot exchange como Binance.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        strategy: SmaRsiStrategy,
        risk_manager: RiskManager,
        initial_balance: float = 1000.0,
        fee_rate: float = 0.001,
    ):
        self.df = df.reset_index(drop=True)
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.balance = initial_balance
        self.fee_rate = fee_rate
        self.df["atr"] = atr_series(self.df)

    def run(self, warmup: int = 60) -> BacktestResult:
        result = BacktestResult()
        equity = []
        position: Trade | None = None

        for i in range(warmup, len(self.df)):
            window = self.df.iloc[: i + 1]
            bar = self.df.iloc[i]
            equity.append(self.balance if position is None else self.balance + position.qty * bar["close"])

            if position is not None:
                hit_stop = bar["low"] <= position.stop_loss
                hit_tp = bar["high"] >= position.take_profit
                signal = self.strategy.generate_signal(window)

                exit_price, reason = None, None
                if hit_stop:
                    exit_price, reason = position.stop_loss, "stop_loss"
                elif hit_tp:
                    exit_price, reason = position.take_profit, "take_profit"
                elif signal == "sell":
                    exit_price, reason = bar["close"], "signal"

                if exit_price is not None:
                    proceeds = position.qty * exit_price * (1 - self.fee_rate)
                    cost = position.qty * position.entry_price
                    position.pnl = proceeds - cost
                    position.exit_time = bar.get("timestamp", i)
                    position.exit_price = exit_price
                    position.exit_reason = reason
                    self.balance += proceeds
                    self.risk_manager.register_trade_result(position.pnl)
                    result.trades.append(position)
                    position = None
                continue

            if not self.risk_manager.can_open_new_trade(self.balance):
                continue

            signal = self.strategy.generate_signal(window)
            if signal != "buy" or pd.isna(bar["atr"]) or bar["atr"] <= 0:
                continue

            entry_price = bar["close"]
            qty = self.risk_manager.position_size(self.balance, entry_price, bar["atr"])
            if qty <= 0:
                continue

            cost = qty * entry_price * (1 + self.fee_rate)
            if cost > self.balance:
                continue

            self.balance -= cost
            position = Trade(
                entry_time=bar.get("timestamp", i),
                entry_price=entry_price,
                qty=qty,
                stop_loss=self.risk_manager.stop_loss_price(entry_price, bar["atr"]),
                take_profit=self.risk_manager.take_profit_price(entry_price, bar["atr"]),
            )

        result.equity_curve = pd.Series(equity)
        result.final_balance = self.balance if position is None else self.balance + position.qty * self.df.iloc[-1]["close"]
        return result
