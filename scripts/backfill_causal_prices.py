"""Backfill causal OHLC history for the full observed whale-event window.

The script derives its range from institutional_transfers, adds a safety buffer
for prior valuation and +24h outcome validation, non-destructively upserts
Binance ETH/BTC bars, then rebuilds enriched_whales using prior-completed prices.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.fetch_prices import PriceOracle

DEFAULT_DB = ROOT / "data" / "db" / "whale_data.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill causal ETH/BTC OHLC price history.")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB)
    parser.add_argument("--pre-buffer-hours", type=int, default=2)
    parser.add_argument("--post-buffer-hours", type=int, default=25)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.db_path.exists():
        print(f"[!] Database not found: {args.db_path}")
        return 1
    with sqlite3.connect(args.db_path) as conn:
        try:
            bounds = pd.read_sql_query(
                "SELECT MIN(timestamp) AS min_ts, MAX(timestamp) AS max_ts FROM institutional_transfers",
                conn,
            ).iloc[0]
        except Exception as exc:
            print(f"[!] Failed to read institutional_transfers: {exc}")
            return 1
    if pd.isna(bounds["min_ts"]) or pd.isna(bounds["max_ts"]):
        print("[!] No institutional transfer timestamps available.")
        return 1

    start = pd.Timestamp(bounds["min_ts"])
    end = pd.Timestamp(bounds["max_ts"])
    start = start.tz_localize("UTC") if start.tzinfo is None else start.tz_convert("UTC")
    end = end.tz_localize("UTC") if end.tzinfo is None else end.tz_convert("UTC")
    start = start.floor("h") - pd.Timedelta(hours=args.pre_buffer_hours)
    end = end.ceil("h") + pd.Timedelta(hours=args.post_buffer_hours)

    print(f"[*] DB: {args.db_path}")
    print(f"[*] Backfill start: {start}")
    print(f"[*] Backfill end:   {end}")
    oracle = PriceOracle(args.db_path)
    prices = oracle.download_price_range(start, end)
    if prices.empty:
        print("[!] No price rows fetched; enriched_whales was not rebuilt.")
        return 1
    enriched = oracle.normalize_whale_volume()
    print(f"[*] Fetched/upserted rows this run: {len(prices)}")
    print(f"[*] Rebuilt enriched_whales rows: {len(enriched)}")
    causal = pd.to_numeric(enriched.get("valuation_lag_seconds"), errors="coerce")
    negative = int((causal < 0).sum()) if causal is not None else 0
    print(f"[*] Negative valuation lags: {negative}")
    if negative:
        print("[!] FAIL: future price detected in whale valuation.")
        return 2
    print("[PASS] Causal price backfill and whale normalization completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
