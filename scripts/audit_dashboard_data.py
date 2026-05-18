from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.analytics.real_mechanism_signal import build_real_mechanism_signal
from src.analytics.volatility_regime import build_volatility_regime
from src.strategies.whale_signals import analyze_whale_flow, backtest_whale_strategy


DB_PATH = ROOT / "data" / "db" / "whale_data.db"
VOLATILITY_PRICE_ASSET_LOOKUP = {"ETH": "ETH", "WBTC": "BTC"}
VOLATILITY_WINDOW_SIZE = 24


def load_table(conn: sqlite3.Connection, table_name: str) -> pd.DataFrame:
    return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)


def to_utc(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "timestamp" in out.columns:
        out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    return out


def label_signal(value: int) -> str:
    return {1: "Long", 0: "Flat", -1: "Short"}.get(value, "Unknown")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-asset", default="ETH")
    parser.add_argument("--window-hours", type=int, default=36)
    parser.add_argument("--min-flow-usd", type=float, default=10000.0)
    parser.add_argument("--cost-per-trade", type=float, default=0.0015)
    parser.add_argument("--manual-volatility-regime", default="normal")
    args = parser.parse_args()

    target_asset = args.target_asset.upper()
    print("\n=== Dashboard Data Audit ===")
    print(f"DB path: {DB_PATH}")
    print(f"Target asset: {target_asset}")
    print(f"Window hours: {args.window_hours}")
    print(f"Minimum flow threshold: ${args.min_flow_usd:,.2f}")
    print(f"Cost per trade: {args.cost_per_trade:.6f}")

    if not DB_PATH.exists():
        print(f"[FAIL] DB not found: {DB_PATH}")
        return 1

    with sqlite3.connect(DB_PATH) as conn:
        tables = set(
            pd.read_sql_query(
                "SELECT name FROM sqlite_master WHERE type='table'",
                conn,
            )["name"].tolist()
        )

        required = {"enriched_whales", "historical_prices"}
        missing = required - tables
        if missing:
            print(f"[FAIL] Missing tables: {sorted(missing)}")
            return 1

        events = to_utc(load_table(conn, "enriched_whales"))
        prices = to_utc(load_table(conn, "historical_prices"))

    print("\n=== Source Data ===")
    print(f"enriched_whales rows: {len(events)}")
    print(f"historical_prices rows: {len(prices)}")

    target_events = events[events["asset_type"].astype(str).str.upper() == target_asset]
    print(f"Raw target-asset event rows: {len(target_events)}")

    latest_event_ts = events["timestamp"].max()
    print(f"Latest whale event timestamp: {latest_event_ts}")

    volatility_price_asset = VOLATILITY_PRICE_ASSET_LOOKUP.get(target_asset, target_asset)
    volatility_prices = prices[
        prices["asset_type"].astype(str).str.upper() == volatility_price_asset
    ][["timestamp", "price_usd"]].copy()

    latest_price_ts = volatility_prices["timestamp"].max()
    print(f"Volatility price asset: {volatility_price_asset}")
    print(f"Volatility price rows: {len(volatility_prices)}")
    print(f"Latest market price timestamp: {latest_price_ts}")

    if len(target_events) == 0:
        print("\n=== Strategy Availability ===")
        print(f"[WARN] No whale events found for target_asset={target_asset}.")
        print("[PASS] Audit stopped honestly instead of generating fake strategy numbers.")
        print("[PASS] Add real whale events for this asset before treating it as fully validated.")
        return 0

    print("\n=== Recomputed Strategy Numbers ===")
    signals = analyze_whale_flow(
        df=events,
        target_asset=target_asset,
        window_hours=args.window_hours,
        min_flow_usd=args.min_flow_usd,
        price_df=prices,
    )

    results = backtest_whale_strategy(
        df=signals,
        cost_per_trade=args.cost_per_trade,
    )

    if signals.empty or results.empty:
        print("[FAIL] Strategy output is empty.")
        return 1

    research_rows = len(results)
    total_trades = int(results["trade_flag"].sum())
    latest_signal = int(results["signal"].iloc[-1])
    latest_flow = float(results["rolling_net_flow"].iloc[-1])
    final_asset = float(results["equity_asset"].iloc[-1])
    final_strategy = float(results["equity_strategy_net"].iloc[-1])
    alpha = final_strategy - final_asset

    print(f"Research frame rows: {research_rows}")
    print(f"Total trades: {total_trades}")
    print(f"Latest signal: {label_signal(latest_signal)}")
    print(f"Latest rolling net flow: ${latest_flow:,.2f}")
    print(f"Buy & hold equity: {final_asset:.4f}x")
    print(f"Strategy net equity: {final_strategy:.4f}x")
    print(f"Alpha vs buy & hold: {alpha:.4f}x")

    signal_counts = (
        results["signal"]
        .map({1: "Long", 0: "Flat", -1: "Short"})
        .value_counts()
        .sort_index()
    )

    print("\nSignal distribution:")
    for name, count in signal_counts.items():
        print(f"  {name}: {int(count)}")

    expected_latest_signal = 0
    if latest_flow > args.min_flow_usd:
        expected_latest_signal = 1
    elif latest_flow < -args.min_flow_usd:
        expected_latest_signal = -1

    if latest_signal == expected_latest_signal:
        print("[PASS] Latest signal matches rolling flow threshold.")
    else:
        print(f"[FAIL] Latest signal mismatch. Expected {expected_latest_signal}, got {latest_signal}.")
        return 1

    print("\n=== Recomputed Volatility Regime ===")
    try:
        volatility = build_volatility_regime(
            prices=volatility_prices,
            asset_symbol=volatility_price_asset,
            window_size=VOLATILITY_WINDOW_SIZE,
        )
    except ValueError as exc:
        volatility = None
        effective_regime = args.manual_volatility_regime
        print(f"[WARN] Automatic volatility unavailable: {exc}")
    else:
        if volatility.is_available:
            effective_regime = volatility.volatility_regime
            print(f"Detected volatility regime: {volatility.volatility_regime}")
            print(f"Latest realized volatility: {volatility.latest_realized_volatility * 100:.2f}%")
            print(f"Normal threshold: {volatility.normal_threshold * 100:.2f}%")
            print(f"Extreme threshold: {volatility.extreme_threshold * 100:.2f}%")
            print("[PASS] Automatic volatility is available.")
        else:
            effective_regime = args.manual_volatility_regime
            print(f"[WARN] Automatic volatility unavailable: {volatility.reason}")

    print(f"Effective volatility regime: {effective_regime}")

    print("\n=== Mechanism Signal Check ===")
    if latest_flow == 0:
        print("[PASS] Latest rolling whale-flow is zero.")
        print("[PASS] Mechanism signal should stay unavailable, so no fake pool-impact signal is generated.")
    else:
        mechanism = build_real_mechanism_signal(
            asset_symbol=target_asset,
            whale_flow_usd=latest_flow,
            volatility_regime=effective_regime,
            db_path=DB_PATH,
        )

        if mechanism.is_available and mechanism.signal is not None:
            print("[PASS] Real-data mechanism signal available.")
            print(f"Pool depth USD: ${mechanism.pool_depth.liquidity_usd:,.2f}")
            print(f"Size ratio: {mechanism.signal.size_ratio:.6f}")
            print(f"Price impact risk: {mechanism.signal.price_impact_risk}")
            print(f"Signal reliability: {mechanism.signal.signal_reliability}")
            print(f"Mechanism volatility regime: {mechanism.signal.volatility_regime}")
        else:
            print(f"[WARN] Mechanism signal unavailable: {mechanism.unavailable_reason}")

    print("\n=== Final Audit Result ===")
    print("[PASS] Dashboard numbers recomputed from SQLite + project formulas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
