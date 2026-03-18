from pathlib import Path
import pandas as pd

from src.strategies.ma_crossover import generate_signals, backtest

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


def main():
    prices_path = PROCESSED / "prices_btc_eth_wide_processed.csv"
    prices = pd.read_csv(prices_path, index_col=0, parse_dates=True)

    btc = prices["bitcoin"].copy()

    signals = generate_signals(btc, fast=20, slow=50)
    results = backtest(signals, cost_per_trade=0.001)

    signals_path = PROCESSED / "signals_ma_btc.csv"
    results_path = PROCESSED / "results_ma_btc.csv"

    signals.to_csv(signals_path)
    results.to_csv(results_path)

    print("Saved:", signals_path)
    print("Saved:", results_path)

    print("\nResult rows:", results.shape[0])
    print(results.head())

    print("\nFinal equity values:")
    print("Buy and Hold:", results["equity_asset"].iloc[-1])
    print("Strategy Gross:", results["equity_strategy_gross"].iloc[-1])
    print("Strategy Net:", results["equity_strategy_net"].iloc[-1])


if __name__ == "__main__":
    main()