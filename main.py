import argparse

from src.backtester import Backtester
from src.brokers.alpaca_broker import AlpacaBroker
from src.brokers.binance_broker import BinanceBroker
from src.config import load_config
from src.data_fetcher import load_or_fetch
from src.logger import get_logger
from src.paper_trader import MultiAssetTrader
from src.risk import RiskManager
from src.screener import scan_watchlist
from src.strategy import SmaRsiStrategy, StrategyParams

log = get_logger("main")


def _build_strategy(config) -> SmaRsiStrategy:
    return SmaRsiStrategy(
        StrategyParams(
            fast_ma=config.fast_ma,
            slow_ma=config.slow_ma,
            rsi_period=config.rsi_period,
            rsi_oversold=config.rsi_oversold,
            rsi_overbought=config.rsi_overbought,
        )
    )


def _build_risk_manager(config) -> RiskManager:
    return RiskManager(
        risk_per_trade=config.risk_per_trade,
        max_daily_loss=config.max_daily_loss,
        atr_multiplier=config.atr_multiplier,
        reward_risk_ratio=config.reward_risk_ratio,
    )


def _run_single_backtest(symbol: str, timeframe: str, args: argparse.Namespace, config) -> dict:
    df = load_or_fetch(symbol, timeframe, max_candles=args.candles, force_refresh=args.refresh)
    strategy = _build_strategy(config)
    risk_manager = _build_risk_manager(config)

    backtester = Backtester(df, strategy, risk_manager, initial_balance=args.balance)
    result = backtester.run()

    metrics = result.metrics
    metrics["symbol"] = symbol
    metrics["candles"] = len(df)
    metrics["final_balance"] = result.final_balance
    return metrics


def run_backtest(args: argparse.Namespace) -> None:
    config = load_config()
    symbols = [s.strip() for s in args.symbols.split(",")] if args.symbols else [args.symbol or config.symbol]
    timeframe = args.timeframe or config.timeframe

    all_metrics = []
    for symbol in symbols:
        log.info("Backtesting %s (%s)...", symbol, timeframe)
        try:
            all_metrics.append(_run_single_backtest(symbol, timeframe, args, config))
        except Exception:
            log.exception("Falló el backtest de %s; se omite.", symbol)

    if not all_metrics:
        print("No se pudo completar ningún backtest.")
        return

    all_metrics.sort(key=lambda m: m["total_return_pct"], reverse=True)

    if len(all_metrics) == 1:
        m = all_metrics[0]
        print(f"\n=== Resultado del backtest: {m['symbol']} ({timeframe}, {m['candles']} velas) ===")
        print(f"Balance inicial: {args.balance:.2f}")
        print(f"Balance final:   {m['final_balance']:.2f}")
        for key in ("total_trades", "win_rate", "total_return_pct", "max_drawdown_pct", "profit_factor"):
            value = m[key]
            print(f"{key}: {value:.4f}" if isinstance(value, float) else f"{key}: {value}")
    else:
        print(f"\n=== Comparación de backtests ({timeframe}, balance inicial {args.balance:.2f}) ===")
        header = f"{'symbol':<12}{'return_%':>10}{'win_rate':>10}{'trades':>8}{'max_dd_%':>10}{'p_factor':>10}"
        print(header)
        print("-" * len(header))
        for m in all_metrics:
            print(
                f"{m['symbol']:<12}{m['total_return_pct']:>10.2f}{m['win_rate']:>10.2%}"
                f"{m['total_trades']:>8}{m['max_drawdown_pct']:>10.2f}{m['profit_factor']:>10.2f}"
            )

    print(
        "\nAVISO: resultados de backtesting no garantizan resultados futuros. "
        "Valida siempre en paper trading antes de considerar dinero real."
    )


def run_scan(_args: argparse.Namespace) -> None:
    config = load_config()
    strategy = _build_strategy(config)

    watchlist = []
    if config.crypto_watchlist:
        binance = BinanceBroker(config.api_key, config.api_secret, sandbox=True)
        watchlist += [(binance, symbol, config.timeframe) for symbol in config.crypto_watchlist]

    if config.stock_watchlist:
        if not config.alpaca_api_key or not config.alpaca_secret_key:
            log.warning("STOCK_WATCHLIST configurado pero faltan credenciales de Alpaca; se omite TradFi.")
        else:
            alpaca = AlpacaBroker(config.alpaca_api_key, config.alpaca_secret_key, paper=config.alpaca_paper)
            watchlist += [(alpaca, symbol, config.stock_timeframe) for symbol in config.stock_watchlist]

    if not watchlist:
        print("Watchlist vacía: configura CRYPTO_WATCHLIST y/o STOCK_WATCHLIST en .env.")
        return

    candidates = scan_watchlist(watchlist, strategy)

    print(f"\n=== Escaneo de watchlist ({len(candidates)} símbolos evaluados) ===")
    header = f"{'broker':<10}{'symbol':<12}{'signal':<8}{'score':>10}{'price':>14}"
    print(header)
    print("-" * len(header))
    for c in candidates:
        print(f"{c.broker:<10}{c.symbol:<12}{c.signal:<8}{c.score:>10.4f}{c.last_price:>14.2f}")

    print(
        "\nEsto es solo un escaneo informativo (no ejecuta órdenes). "
        "Para operar automáticamente en las mejores señales usa: python main.py paper"
    )


def run_paper(_args: argparse.Namespace) -> None:
    config = load_config()
    trader = MultiAssetTrader(config)
    trader.run_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot de trading multi-activo (backtest, escaneo y paper trading)")
    sub = parser.add_subparsers(dest="command", required=True)

    bt = sub.add_parser("backtest", help="Ejecuta un backtest con datos históricos")
    bt.add_argument("--symbol", default=None, help="Un solo símbolo (ignorado si se usa --symbols)")
    bt.add_argument("--symbols", default=None, help="Lista separada por comas, ej. BTC/USDT,ETH/USDT,SOL/USDT")
    bt.add_argument("--timeframe", default=None)
    bt.add_argument("--candles", type=int, default=3000)
    bt.add_argument("--balance", type=float, default=1000.0)
    bt.add_argument("--refresh", action="store_true", help="Ignora la caché y vuelve a descargar los datos")
    bt.set_defaults(func=run_backtest)

    scan = sub.add_parser(
        "scan", help="Evalúa la watchlist completa (cripto + TradFi) ahora mismo, sin ejecutar órdenes"
    )
    scan.set_defaults(func=run_scan)

    paper = sub.add_parser(
        "paper", help="Ejecuta el bot en modo paper trading sobre toda la watchlist (Binance Testnet + Alpaca paper)"
    )
    paper.set_defaults(func=run_paper)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
