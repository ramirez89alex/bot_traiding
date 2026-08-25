from dataclasses import dataclass

import pandas as pd

from src.indicators import rsi, sma


@dataclass
class StrategyParams:
    fast_ma: int = 20
    slow_ma: int = 50
    rsi_period: int = 14
    rsi_oversold: float = 35
    rsi_overbought: float = 65


class SmaRsiStrategy:
    """Cruce de medias móviles (SMA rápida/lenta) filtrado por RSI.

    Señal de compra: la SMA rápida cruza por encima de la SMA lenta
    y el RSI no está en sobrecompra.
    Señal de venta: la SMA rápida cruza por debajo de la SMA lenta,
    o el RSI entra en sobrecompra.
    """

    def __init__(self, params: StrategyParams | None = None):
        self.params = params or StrategyParams()

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["sma_fast"] = sma(out["close"], self.params.fast_ma)
        out["sma_slow"] = sma(out["close"], self.params.slow_ma)
        out["rsi"] = rsi(out["close"], self.params.rsi_period)
        return out

    def generate_signal(self, df: pd.DataFrame) -> str:
        """Devuelve 'buy', 'sell' u 'hold' evaluando las dos últimas velas cerradas de df."""
        if len(df) < max(self.params.slow_ma, self.params.rsi_period) + 2:
            return "hold"

        enriched = self.add_indicators(df)
        prev, last = enriched.iloc[-2], enriched.iloc[-1]

        if pd.isna(last["sma_slow"]) or pd.isna(prev["sma_slow"]):
            return "hold"

        crossed_up = prev["sma_fast"] <= prev["sma_slow"] and last["sma_fast"] > last["sma_slow"]
        crossed_down = prev["sma_fast"] >= prev["sma_slow"] and last["sma_fast"] < last["sma_slow"]

        if crossed_up and last["rsi"] < self.params.rsi_overbought:
            return "buy"
        if crossed_down or last["rsi"] > self.params.rsi_overbought:
            return "sell"
        return "hold"
