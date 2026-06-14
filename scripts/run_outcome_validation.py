"""Run benchmark-adjusted outcome validation from the local SQLite vault.

This script loads real enriched whale events and historical prices from SQLite,
builds the outcome-validation table, prints a concise terminal summary, and can
optionally export the table to CSV or persist the results into a reusable
outcome-validation dataset.

It does not claim prediction.
It validates whether whale-flow signals were supported, failed, delayed,
reversed, inconclusive, or data-unavailable across +6h and +24h outcomes.
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

from src.analytics.outcome_validation_dataset import (
    build_outcome_validation_dataset_summary,
    load_outcome_validation_records,
    save_outcome_validation_records,
)
from src.analytics.outcome_validation_table import build_outcome_validation_table


DEFAULT_DB_PATH = ROOT / "data" / "db" / "whale_data.db"

REQUIRED_TABLES = {
    "enriched_whales",
    "historical_prices",
}

DISPLAY_COLUMNS = [
    "event_timestamp",
    "target_asset",
    "signal_direction",
    "rolling_net_flow",
    "6h_actual_return",
    "6h_benchmark_return",
    "6h_abnormal_return",
    "6h_label",
    "24h_actual_return",
    "24h_benchmark_return",
    "24h_abnormal_return",
    "24h_label",
    "overall_label",
    "evidence_quality",
    "failure_mode",
]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Run benchmark-adjusted +6h/+24h outcome validation for whale-flow "
            "signals from the local SQLite vault."
        )
    )

    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to the local SQLite whale-data database.",
    )
    parser.add_argument(
        "--target-asset",
        default="ETH",
        help="Target asset to validate, for example ETH or WBTC.",
    )
    parser.add_argument(
        "--benchmark-asset",
        default="BTC",
        help="Benchmark asset used for abnormal-return adjustment.",
    )
    parser.add_argument(
        "--window-hours",
        type=int,
        default=12,
        help="Rolling whale-flow signal window in hours.",
    )
    parser.add_argument(
        "--min-flow-usd",
        type=float,
        default=0.0,
        help="Minimum absolute rolling whale-flow threshold required for a signal.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Optional CSV path for exporting the validation table.",
    )
    parser.add_argument(
        "--save-dataset",
        action="store_true",
        help=(
            "Persist validation rows into the outcome_validation_records "
            "SQLite dataset table."
        ),
    )
    parser.add_argument(
        "--validation-notes",
        default="",
        help="Optional note stored with persisted validation records.",
    )

    return parser.parse_args()


def load_table(db_path: Path, table_name: str) -> pd.DataFrame:
    """Load a required table from SQLite into a DataFrame."""
    if table_name not in REQUIRED_TABLES:
        raise ValueError(f"Unsupported table requested: {table_name}")

    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)


def _format_return(value) -> str:
    """Format fractional returns as percentages for terminal display."""
    if pd.isna(value):
        return "unavailable"

    return f"{float(value) * 100:.4f}%"


def _format_usd(value) -> str:
    """Format USD-style values for terminal display."""
    if pd.isna(value):
        return "unavailable"

    return f"${float(value):,.2f}"


def _format_summary_value(key: str, value) -> str:
    """Format dataset summary values for terminal display."""
    if key == "support_rate" and value is not None:
        return f"{value:.2%}"

    if isinstance(value, float) and value == value:
        return f"{value:.6f}"

    return str(value)


def print_validation_summary(validation_df: pd.DataFrame) -> None:
    """Print the validation result in a concise research-readable format."""
    if validation_df.empty:
        print("[!] No non-zero signal events were available for validation.")
        return

    display_df = validation_df[DISPLAY_COLUMNS].copy()

    for column in [
        "6h_actual_return",
        "6h_benchmark_return",
        "6h_abnormal_return",
        "24h_actual_return",
        "24h_benchmark_return",
        "24h_abnormal_return",
    ]:
        display_df[column] = display_df[column].map(_format_return)

    display_df["rolling_net_flow"] = display_df["rolling_net_flow"].map(_format_usd)

    print("\n" + "=" * 88)
    print("OUTCOME VALIDATION SUMMARY")
    print("=" * 88)
    print(display_df.to_string(index=False))

    print("\nLabel counts:")
    for column in ["overall_label", "evidence_quality", "failure_mode"]:
        print(f"\n{column}:")
        print(validation_df[column].value_counts(dropna=False).to_string())

    print("\nImportant note:")
    print(
        "- This validation uses real whale events and historical price data from SQLite."
    )
    print(
        "- Liquidity is not attached here unless event-time aligned liquidity data is available."
    )
    print(
        "- The result is research evidence, not financial advice or guaranteed prediction."
    )


def print_dataset_summary(db_path: Path) -> None:
    """Print summary statistics for stored outcome-validation records."""
    records_df = load_outcome_validation_records(db_path)
    dataset_summary = build_outcome_validation_dataset_summary(records_df)

    print("\nOutcome validation dataset summary:")
    for key, value in dataset_summary.items():
        print(f"- {key}: {_format_summary_value(key, value)}")


def main() -> int:
    """Run the outcome-validation script."""
    args = parse_args()

    db_path = args.db_path

    print(f"[*] SQLite database: {db_path}")

    if not db_path.exists():
        print(f"[!] ERROR: database not found at {db_path}")
        return 1

    try:
        events_df = load_table(db_path=db_path, table_name="enriched_whales")
        prices_df = load_table(db_path=db_path, table_name="historical_prices")
    except Exception as exc:
        print(f"[!] ERROR while loading SQLite data: {exc}")
        return 1

    if events_df.empty:
        print("[!] ERROR: enriched_whales table is empty.")
        return 1

    if prices_df.empty:
        print("[!] ERROR: historical_prices table is empty.")
        return 1

    print(f"[*] Loaded whale events: {len(events_df)} rows")
    print(f"[*] Loaded historical prices: {len(prices_df)} rows")
    print(f"[*] Target asset: {args.target_asset.upper()}")
    print(f"[*] Benchmark asset: {args.benchmark_asset.upper()}")
    print(f"[*] Rolling window: {args.window_hours}h")
    print(f"[*] Min flow USD: {args.min_flow_usd}")

    try:
        validation_df = build_outcome_validation_table(
            events_df=events_df,
            prices_df=prices_df,
            target_asset=args.target_asset,
            benchmark_asset=args.benchmark_asset,
            window_hours=args.window_hours,
            min_flow_usd=args.min_flow_usd,
        )
    except ValueError as exc:
        print(f"[!] ERROR while building outcome validation table: {exc}")
        return 1

    print_validation_summary(validation_df)

    if args.output_csv is not None:
        output_path = args.output_csv
        output_path.parent.mkdir(parents=True, exist_ok=True)
        validation_df.to_csv(output_path, index=False)
        print(f"\n[*] Exported validation table to: {output_path}")

    if args.save_dataset:
        saved_count = save_outcome_validation_records(
            db_path=db_path,
            validation_df=validation_df,
            window_hours=args.window_hours,
            min_flow_usd=args.min_flow_usd,
            validation_notes=args.validation_notes,
        )
        print(
            "\n[*] Saved "
            f"{saved_count} validation record(s) to outcome_validation_records."
        )
        print_dataset_summary(db_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
