import argparse

from src.backtester import Backtester
from src.config import load_config
from src.data_fetcher import load_or_fetch
from src.logger import get_logger
from src.paper_trader import PaperTrader
from src.risk import RiskManager
from src.strategy import SmaRsiStrategy, StrategyParams

log = get_logger("main")


def run_backtest(args: argparse.Namespace) -> None:
    config = load_config()
    symbol = args.symbol or config.symbol
    timeframe = args.timeframe or config.timeframe

    df = load_or_fetch(symbol, timeframe, max_candles=args.candles, force_refresh=args.refresh)
    log.info("Backtest sobre %d velas de %s (%s)", len(df), symbol, timeframe)

    strategy = SmaRsiStrategy(
        StrategyParams(
            fast_ma=config.fast_ma,
            slow_ma=config.slow_ma,
            rsi_period=config.rsi_period,
            rsi_oversold=config.rsi_oversold,
            rsi_overbought=config.rsi_overbought,
        )
    )
    risk_manager = RiskManager(
        risk_per_trade=config.risk_per_trade,
        max_daily_loss=config.max_daily_loss,
        atr_multiplier=config.atr_multiplier,
        reward_risk_ratio=config.reward_risk_ratio,
    )

    backtester = Backtester(df, strategy, risk_manager, initial_balance=args.balance)
    result = backtester.run()

    print("\n=== Resultado del backtest ===")
    print(f"Balance inicial: {args.balance:.2f}")
    print(f"Balance final:   {result.final_balance:.2f}")
    for key, value in result.metrics.items():
        print(f"{key}: {value:.4f}" if isinstance(value, float) else f"{key}: {value}")
    print(
        "\nAVISO: resultados de backtesting no garantizan resultados futuros. "
        "Valida siempre en Binance Testnet (paper trading) antes de considerar dinero real."
    )


def run_paper(_args: argparse.Namespace) -> None:
    config = load_config()
    trader = PaperTrader(config)
    trader.run_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot de trading para Binance (backtest + paper trading)")
    sub = parser.add_subparsers(dest="command", required=True)

    bt = sub.add_parser("backtest", help="Ejecuta un backtest con datos históricos")
    bt.add_argument("--symbol", default=None)
    bt.add_argument("--timeframe", default=None)
    bt.add_argument("--candles", type=int, default=3000)
    bt.add_argument("--balance", type=float, default=1000.0)
    bt.add_argument("--refresh", action="store_true", help="Ignora la caché y vuelve a descargar los datos")
    bt.set_defaults(func=run_backtest)

    paper = sub.add_parser("paper", help="Ejecuta el bot en modo paper trading (Binance Testnet)")
    paper.set_defaults(func=run_paper)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
