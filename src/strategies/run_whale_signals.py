# src/strategies/run_whale_signals.py

"""
Module: Whale Strategy Execution Engine (V3)
Description:
- Connects to the local SQLite vault
- Loads enriched whale events
- Loads historical market prices
- Runs whale-flow signal generation for an explicit target asset
- Executes the vectorized backtest
- Prints a clean research summary

Design goals:
- explicit target-asset execution
- deterministic DB reads
- graceful missing-table handling
- interview/GitHub-readable structure
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
from pandas.errors import DatabaseError as PandasDatabaseError

from src.strategies.whale_signals import analyze_whale_flow, backtest_whale_strategy


# ==========================================
# GLOBAL PROJECT PATHS
# ==========================================
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "db" / "whale_data.db"


# ==========================================
# CUSTOM EXCEPTIONS
# ==========================================
class MissingTableError(RuntimeError):
    """
    Raised when an expected SQLite table does not exist.
    """

    def __init__(self, table_name: str):
        self.table_name = table_name
        super().__init__(f"Missing required table: {table_name}")


# ==========================================
# DATA ACCESS
# ==========================================
def _extract_table_name_from_query(query: str) -> str:
    """
    Best-effort extraction of table name from simple SELECT queries.

    Assumes patterns like:
    SELECT * FROM table_name
    """
    normalized = " ".join(query.strip().split()).lower()
    marker = " from "
    if marker in normalized:
        return normalized.split(marker, 1)[1].split()[0]
    return "unknown_table"


def load_table(query: str, db_path: Path = DB_PATH) -> pd.DataFrame:
    """
    Load a SQL query result into a DataFrame.

    If the underlying table is missing, normalize the error into MissingTableError
    so the caller can handle it cleanly.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query(query, conn)
    except PandasDatabaseError as exc:
        message = str(exc).lower()
        if "no such table" in message:
            raise MissingTableError(_extract_table_name_from_query(query)) from exc
        raise
    except sqlite3.OperationalError as exc:
        message = str(exc).lower()
        if "no such table" in message:
            raise MissingTableError(_extract_table_name_from_query(query)) from exc
        raise


# ==========================================
# MAIN EXECUTION
# ==========================================
def main(
    target_asset: str = "ETH",
    window_hours: int = 12,
    min_flow_usd: float = 0.0,
    cost_per_trade: float = 0.001,
) -> None:
    """
    Execute the whale-flow strategy end-to-end for a chosen target asset.
    """
    print(f"\n[*] Connecting to Whale Vault at: {DB_PATH} ...")

    try:
        events_df = load_table("SELECT * FROM enriched_whales")
    except MissingTableError as exc:
        print(f"[!] ERROR: Table '{exc.table_name}' not found. Run the data pipeline first.")
        return

    try:
        price_df = load_table("SELECT * FROM historical_prices")
    except MissingTableError as exc:
        print(f"[!] ERROR: Table '{exc.table_name}' not found. Run the price pipeline first.")
        return

    if events_df.empty:
        print("[!] ERROR: enriched_whales is empty. No whale events available.")
        return

    if price_df.empty:
        print("[!] ERROR: historical_prices is empty. No market prices available.")
        return

    print(f"[*] Loaded {len(events_df)} enriched whale-event rows.")
    print(f"[*] Loaded {len(price_df)} historical price rows.")
    print(f"[*] Target asset: {target_asset}")
    print(f"[*] Rolling window: {window_hours}h")
    print(f"[*] Min flow threshold: {min_flow_usd}")
    print(f"[*] Cost per trade: {cost_per_trade}")

    try:
        signals_df = analyze_whale_flow(
            df=events_df,
            target_asset=target_asset,
            window_hours=window_hours,
            min_flow_usd=min_flow_usd,
            price_df=price_df,
        )
    except ValueError as exc:
        print(f"[!] ERROR while building signals: {exc}")
        return

    if signals_df.empty:
        print("[!] ERROR: No signal dataframe was produced.")
        return

    results_df = backtest_whale_strategy(
        df=signals_df,
        cost_per_trade=cost_per_trade,
    )

    if results_df.empty:
        print("[!] ERROR: Backtest returned an empty dataframe.")
        return

    total_trades = int(results_df["trade_flag"].sum())
    final_asset_equity = float(results_df["equity_asset"].iloc[-1])
    final_strategy_equity = float(results_df["equity_strategy_net"].iloc[-1])
    alpha_vs_buy_hold = final_strategy_equity - final_asset_equity

    print("\n" + "=" * 52)
    print("        WHALE FLOW STRATEGY RESEARCH SUMMARY")
    print("=" * 52)
    print(f"Target Asset            : {target_asset}")
    print(f"Rows in Research Frame  : {len(results_df)}")
    print(f"Total Trades            : {total_trades}")
    print(f"Buy & Hold Equity       : {final_asset_equity:.4f}x")
    print(f"Strategy Net Equity     : {final_strategy_equity:.4f}x")
    print(f"Alpha vs Buy & Hold     : {alpha_vs_buy_hold:.4f}x")
    print("=" * 52)

    print("\n[*] Tail of research results:")
    print(
        results_df[
            [
                "timestamp",
                "target_asset",
                "price_usd",
                "pressure_usd",
                "rolling_net_flow",
                "signal",
                "position",
                "asset_return",
                "net_strategy_return",
                "equity_asset",
                "equity_strategy_net",
            ]
        ].tail(10).to_string(index=False)
    )
    print()


if __name__ == "__main__":
    main()