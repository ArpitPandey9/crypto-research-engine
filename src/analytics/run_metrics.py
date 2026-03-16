from pathlib import Path
import pandas as pd

from src.analytics.metrics import (
    total_return,
    annualized_return,
    annualized_volatility,
    sharpe_ratio,
    max_drawdown,
    exposure,
    trade_count,
)

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


def main():
    results_path = PROCESSED / "results_ma_btc.csv"
    df = pd.read_csv(results_path, index_col=0, parse_dates=True)

    metrics = {
        "asset_total_return": total_return(df["equity_asset"]),
        "strategy_total_return": total_return(df["equity_strategy"]),
        "asset_annualized_return": annualized_return(df["equity_asset"]),
        "strategy_annualized_return": annualized_return(df["equity_strategy"]),
        "asset_annualized_volatility": annualized_volatility(df["asset_return"]),
        "strategy_annualized_volatility": annualized_volatility(df["strategy_return"]),
        "asset_sharpe": sharpe_ratio(df["asset_return"]),
        "strategy_sharpe": sharpe_ratio(df["strategy_return"]),
        "asset_max_drawdown": max_drawdown(df["equity_asset"]),
        "strategy_max_drawdown": max_drawdown(df["equity_strategy"]),
        "strategy_exposure": exposure(df["position"]),
        "strategy_trade_count": trade_count(df["position"]),
    }

    metrics_df = pd.DataFrame.from_dict(metrics, orient="index", columns=["value"])

    output_path = PROCESSED / "metrics_ma_btc.csv"
    metrics_df.to_csv(output_path)

    print("Saved:", output_path)
    print("\nMetrics summary:\n")
    print(metrics_df)


if __name__ == "__main__":
    main()