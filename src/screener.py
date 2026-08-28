from dataclasses import dataclass

from src.brokers.base import BrokerClient
from src.logger import get_logger
from src.strategy import SmaRsiStrategy

log = get_logger(__name__)


@dataclass
class Candidate:
    broker: str
    symbol: str
    signal: str
    score: float
    last_price: float


def evaluate_symbol(broker: BrokerClient, symbol: str, timeframe: str, strategy: SmaRsiStrategy) -> Candidate | None:
    try:
        df = broker.fetch_ohlcv_df(symbol, timeframe, limit=max(200, strategy.params.slow_ma + 20))
    except Exception:
        log.exception("No se pudo obtener datos de %s en %s; se omite del escaneo.", symbol, broker.name)
        return None

    if len(df) < strategy.params.slow_ma + 2:
        return None

    signal = strategy.generate_signal(df)
    enriched = strategy.add_indicators(df)
    last = enriched.iloc[-1]

    if last["sma_slow"] in (0, None) or last["sma_slow"] != last["sma_slow"]:  # NaN check sin depender de pandas aquí
        return None

    momentum = (last["sma_fast"] - last["sma_slow"]) / last["sma_slow"]
    rsi_headroom = (strategy.params.rsi_overbought - last["rsi"]) / strategy.params.rsi_overbought
    score = momentum * max(rsi_headroom, 0.0)

    return Candidate(
        broker=broker.name,
        symbol=symbol,
        signal=signal,
        score=score,
        last_price=float(last["close"]),
    )


def scan_watchlist(
    entries: list[tuple[BrokerClient, str, str]],
    strategy: SmaRsiStrategy,
) -> list[Candidate]:
    """Evalúa cada (broker, símbolo, timeframe) de la watchlist y devuelve los
    resultados ordenados: primero las señales de compra, de mayor a menor score."""
    candidates = []
    for broker, symbol, timeframe in entries:
        candidate = evaluate_symbol(broker, symbol, timeframe, strategy)
        if candidate is not None:
            candidates.append(candidate)

    candidates.sort(key=lambda c: (c.signal == "buy", c.score), reverse=True)
    return candidates
