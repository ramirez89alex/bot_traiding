import time
from pathlib import Path

import ccxt
import pandas as pd

from src.logger import get_logger

log = get_logger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    since_ms: int | None = None,
    limit: int = 1000,
    max_candles: int = 5000,
) -> pd.DataFrame:
    """Descarga velas históricas públicas de Binance (no requiere API key)."""
    exchange = ccxt.binance({"enableRateLimit": True})
    all_rows: list[list] = []

    if since_ms is None:
        # Sin `since`, Binance solo devuelve las velas MÁS RECIENTES: paginar hacia
        # adelante desde ahí no trae más historial. Para juntar `max_candles` velas
        # hay que arrancar suficientemente atrás en el tiempo.
        timeframe_ms = exchange.parse_timeframe(timeframe) * 1000
        since_ms = exchange.milliseconds() - max_candles * timeframe_ms

    while len(all_rows) < max_candles:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=limit)
        if not batch:
            break
        all_rows.extend(batch)
        since_ms = batch[-1][0] + 1
        log.info("Descargadas %d velas de %s (%s)", len(all_rows), symbol, timeframe)
        if len(batch) < limit:
            break
        time.sleep(exchange.rateLimit / 1000)

    df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.drop_duplicates(subset="timestamp").reset_index(drop=True)
    return df.tail(max_candles).reset_index(drop=True)


def cache_path(symbol: str, timeframe: str) -> Path:
    safe_symbol = symbol.replace("/", "-")
    return DATA_DIR / f"{safe_symbol}_{timeframe}.csv"


def load_or_fetch(symbol: str, timeframe: str, max_candles: int = 5000, force_refresh: bool = False) -> pd.DataFrame:
    path = cache_path(symbol, timeframe)
    if path.exists() and not force_refresh:
        log.info("Cargando datos desde caché: %s", path)
        return pd.read_csv(path, parse_dates=["timestamp"])

    df = fetch_ohlcv(symbol, timeframe, max_candles=max_candles)
    DATA_DIR.mkdir(exist_ok=True)
    df.to_csv(path, index=False)
    log.info("Datos guardados en %s", path)
    return df
