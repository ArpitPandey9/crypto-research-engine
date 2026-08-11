#!/usr/bin/env python3
"""Read-only comparison of legacy V2 research results vs causal V5/V3 methodology.

This script does NOT write to SQLite and does NOT persist new validation rows.

It compares:
1) Legacy close-to-close backtest vs V5 causal next-open backtest
   using the same current data and whale-flow signals.
2) Stored historical V2 outcome-validation records vs freshly recomputed
   causal signal-availability outcome-validation results.

Run from the repository root:
    .venv/bin/python scripts/compare_legacy_v2_vs_causal_v5.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd


REPO_ROOT = Path.cwd().resolve()
DB_PATH = REPO_ROOT / "data" / "db" / "whale_data.db"

# Controlled dashboard/backtest parameters.
BACKTEST_TARGET = "ETH"
BACKTEST_WINDOW_HOURS = 36
BACKTEST_MIN_FLOW_USD = 10_000.0
BACKTEST_COST_PER_TRADE = 0.0015

# Historical outcome-validation parameters.
OUTCOME_TARGET = "ETH"
OUTCOME_BENCHMARK = "BTC"
OUTCOME_WINDOW_HOURS = 12
OUTCOME_MIN_FLOW_USD = 0.0


if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analytics.outcome_validation_table import build_outcome_validation_table
from src.strategies.whale_signals import (
    analyze_whale_flow,
    backtest_whale_strategy,
    backtest_whale_strategy_causal,
)


def _load_sqlite_read_only() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"SQLite database not found: {DB_PATH}")

    uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        events = pd.read_sql_query("SELECT * FROM enriched_whales", conn)
        prices = pd.read_sql_query("SELECT * FROM historical_prices", conn)

        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type='table' AND name='outcome_validation_records'"
        ).fetchone()

        if table_exists:
            stored = pd.read_sql_query(
                "SELECT * FROM outcome_validation_records ORDER BY event_timestamp",
                conn,
            )
        else:
            stored = pd.DataFrame()

    return events, prices, stored


def _last_float(df: pd.DataFrame, column: str) -> float | None:
    if df.empty or column not in df.columns:
        return None
    value = df[column].iloc[-1]
    return None if pd.isna(value) else float(value)


def _trade_count(df: pd.DataFrame) -> int:
    if df.empty or "trade_flag" not in df.columns:
        return 0
    return int(pd.to_numeric(df["trade_flag"], errors="coerce").fillna(0).sum())


def _fmt_x(value: float | None) -> str:
    return "unavailable" if value is None else f"{value:.6f}x"


def _fmt_usd(value) -> str:
    if value is None or pd.isna(value):
        return "unavailable"
    return f"${float(value):,.2f}"


def _print_counts(title: str, series: pd.Series) -> None:
    print(title)
    if series.empty:
        print("  <none>")
        return
    counts = series.fillna("<NULL>").astype(str).value_counts(dropna=False)
    for label, count in counts.items():
        print(f"  {label}: {int(count)}")


def compare_backtests(events: pd.DataFrame, prices: pd.DataFrame) -> None:
    print("=" * 96)
    print("A. CONTROLLED BACKTEST COMPARISON")
    print("=" * 96)
    print(
        f"Target={BACKTEST_TARGET} | window={BACKTEST_WINDOW_HOURS}h | "
        f"min_flow=${BACKTEST_MIN_FLOW_USD:,.2f} | cost={BACKTEST_COST_PER_TRADE:.4f}"
    )
    print("Same current data + same signal frame; execution methodology changes only.")
    print()

    signals = analyze_whale_flow(
        df=events,
        target_asset=BACKTEST_TARGET,
        window_hours=BACKTEST_WINDOW_HOURS,
        min_flow_usd=BACKTEST_MIN_FLOW_USD,
        price_df=prices,
    )

    legacy = backtest_whale_strategy(
        signals.copy(),
        cost_per_trade=BACKTEST_COST_PER_TRADE,
    )
    causal = backtest_whale_strategy_causal(
        signals.copy(),
        cost_per_trade=BACKTEST_COST_PER_TRADE,
    )

    legacy_bh = _last_float(legacy, "equity_asset")
    legacy_net = _last_float(legacy, "equity_strategy_net")
    causal_bh = _last_float(causal, "equity_asset")
    causal_net = _last_float(causal, "equity_strategy_net")

    legacy_difference = (
        None if legacy_bh is None or legacy_net is None else legacy_net - legacy_bh
    )
    causal_difference = (
        None if causal_bh is None or causal_net is None else causal_net - causal_bh
    )

    print("LEGACY CLOSE-TO-CLOSE")
    print(f"  rows:              {len(legacy)}")
    print(f"  trades:            {_trade_count(legacy)}")
    print(f"  buy_hold_equity:   {_fmt_x(legacy_bh)}")
    print(f"  strategy_net:      {_fmt_x(legacy_net)}")
    print(f"  strategy_minus_buy_hold: {_fmt_x(legacy_difference)}")
    print()

    print("V5 CAUSAL NEXT-OPEN")
    print(f"  rows:              {len(causal)}")
    print(f"  trades:            {_trade_count(causal)}")
    print(f"  buy_hold_equity:   {_fmt_x(causal_bh)}")
    print(f"  strategy_net:      {_fmt_x(causal_net)}")
    print(f"  strategy_minus_buy_hold: {_fmt_x(causal_difference)}")

    if "causal_execution_ok" in causal.columns:
        bad = int((~causal["causal_execution_ok"].astype(bool)).sum())
        print(f"  causal_failures:   {bad}")

    print()
    print("EXECUTION METHOD DELTA (V5 - legacy)")
    if legacy_net is not None and causal_net is not None:
        print(f"  strategy_net_delta:      {causal_net - legacy_net:+.6f}x")
    else:
        print("  strategy_net_delta:      unavailable")

    if legacy_difference is not None and causal_difference is not None:
        print(f"  difference_delta:             {causal_difference - legacy_difference:+.6f}x")
    else:
        print("  difference_delta:             unavailable")
    print(f"  trade_count_delta:       {_trade_count(causal) - _trade_count(legacy):+d}")
    print()


def _prepare_stored_legacy(stored: pd.DataFrame) -> pd.DataFrame:
    if stored.empty:
        return stored.copy()

    out = stored.copy()

    # Keep only the historical ETH/BTC 12h / min-flow=0 parameter set when
    # those columns exist.
    if "target_asset" in out.columns:
        out = out[out["target_asset"].astype(str).str.upper() == OUTCOME_TARGET]
    if "benchmark_asset" in out.columns:
        out = out[out["benchmark_asset"].astype(str).str.upper() == OUTCOME_BENCHMARK]
    if "window_hours" in out.columns:
        out = out[pd.to_numeric(out["window_hours"], errors="coerce") == OUTCOME_WINDOW_HOURS]
    if "min_flow_usd" in out.columns:
        out = out[pd.to_numeric(out["min_flow_usd"], errors="coerce") == OUTCOME_MIN_FLOW_USD]

    # V5/V3 rows, if later persisted, must not be mixed into the historical
    # baseline. Existing pre-remediation rows often have NULL methodology_version.
    if "methodology_version" in out.columns:
        method = out["methodology_version"]
        keep = method.isna() | method.astype(str).str.lower().isin(
            {"", "none", "nan", "legacy_v2", "v2", "legacy"}
        )
        out = out[keep]

    out["legacy_event_timestamp"] = pd.to_datetime(
        out["event_timestamp"], utc=True, errors="coerce"
    )
    out = out.dropna(subset=["legacy_event_timestamp"]).copy()

    # Historical V2 event_timestamp was the left-labeled signal bucket start.
    out["match_bucket_start"] = out["legacy_event_timestamp"]
    return out.sort_values("legacy_event_timestamp").reset_index(drop=True)


def compare_outcomes(
    events: pd.DataFrame,
    prices: pd.DataFrame,
    stored: pd.DataFrame,
) -> None:
    print("=" * 96)
    print("B. STORED V2 OUTCOMES VS FRESH CAUSAL V5/V3 OUTCOMES")
    print("=" * 96)
    print(
        f"Target={OUTCOME_TARGET} | benchmark={OUTCOME_BENCHMARK} | "
        f"window={OUTCOME_WINDOW_HOURS}h | min_flow=${OUTCOME_MIN_FLOW_USD:,.2f}"
    )
    print()

    legacy = _prepare_stored_legacy(stored)

    fresh = build_outcome_validation_table(
        events_df=events,
        prices_df=prices,
        target_asset=OUTCOME_TARGET,
        benchmark_asset=OUTCOME_BENCHMARK,
        window_hours=OUTCOME_WINDOW_HOURS,
        min_flow_usd=OUTCOME_MIN_FLOW_USD,
    ).copy()

    if not fresh.empty:
        fresh["fresh_bucket_start"] = pd.to_datetime(
            fresh["signal_bucket_start"], utc=True, errors="coerce"
        )
        fresh["fresh_signal_available_at"] = pd.to_datetime(
            fresh["signal_available_at"], utc=True, errors="coerce"
        )

    print(f"stored_legacy_rows: {len(legacy)}")
    print(f"fresh_causal_rows:  {len(fresh)}")
    print()

    _print_counts(
        "STORED V2 overall_label counts:",
        legacy["overall_label"] if "overall_label" in legacy.columns else pd.Series(dtype=object),
    )
    print()
    _print_counts(
        "FRESH V5/V3 overall_label counts:",
        fresh["overall_label"] if "overall_label" in fresh.columns else pd.Series(dtype=object),
    )
    print()

    if legacy.empty or fresh.empty:
        print("MATCHED CASE COMPARISON")
        print("  unavailable because one side is empty.")
        return

    merge_cols_legacy = [
        "match_bucket_start",
        "legacy_event_timestamp",
        "overall_label",
        "rolling_net_flow",
        "label_6h",
        "label_24h",
        "abnormal_return_6h",
        "abnormal_return_24h",
    ]
    merge_cols_legacy = [c for c in merge_cols_legacy if c in legacy.columns]

    merge_cols_fresh = [
        "fresh_bucket_start",
        "fresh_signal_available_at",
        "overall_label",
        "rolling_net_flow",
        "6h_label",
        "24h_label",
        "6h_abnormal_return",
        "24h_abnormal_return",
        "methodology_version",
    ]
    merge_cols_fresh = [c for c in merge_cols_fresh if c in fresh.columns]

    left = legacy[merge_cols_legacy].copy()
    right = fresh[merge_cols_fresh].copy()

    left = left.rename(
        columns={
            "overall_label": "legacy_overall_label",
            "rolling_net_flow": "legacy_rolling_net_flow",
            "label_6h": "legacy_6h_label",
            "label_24h": "legacy_24h_label",
            "abnormal_return_6h": "legacy_6h_abnormal_return",
            "abnormal_return_24h": "legacy_24h_abnormal_return",
        }
    )
    right = right.rename(
        columns={
            "overall_label": "fresh_overall_label",
            "rolling_net_flow": "fresh_rolling_net_flow",
            "6h_label": "fresh_6h_label",
            "24h_label": "fresh_24h_label",
            "6h_abnormal_return": "fresh_6h_abnormal_return",
            "24h_abnormal_return": "fresh_24h_abnormal_return",
        }
    )

    matched = left.merge(
        right,
        left_on="match_bucket_start",
        right_on="fresh_bucket_start",
        how="outer",
        indicator=True,
        validate="one_to_one",
    )

    matched_only = matched[matched["_merge"] == "both"].copy()
    stored_only = matched[matched["_merge"] == "left_only"].copy()
    fresh_only = matched[matched["_merge"] == "right_only"].copy()

    if not matched_only.empty:
        matched_only["overall_label_changed"] = (
            matched_only["legacy_overall_label"].astype(str)
            != matched_only["fresh_overall_label"].astype(str)
        )
        matched_only["flow_delta_usd"] = (
            pd.to_numeric(matched_only["fresh_rolling_net_flow"], errors="coerce")
            - pd.to_numeric(matched_only["legacy_rolling_net_flow"], errors="coerce")
        )

    print("TIMESTAMP-ADJUSTED MATCHING")
    print(f"  matched_cases: {len(matched_only)}")
    print(f"  stored_only:   {len(stored_only)}")
    print(f"  fresh_only:    {len(fresh_only)}")

    changed_count = (
        int(matched_only["overall_label_changed"].sum())
        if "overall_label_changed" in matched_only.columns
        else 0
    )
    print(f"  overall_label_changes: {changed_count}")
    print()

    if not matched_only.empty:
        display_cols = [
            "legacy_event_timestamp",
            "fresh_signal_available_at",
            "legacy_overall_label",
            "fresh_overall_label",
            "legacy_rolling_net_flow",
            "fresh_rolling_net_flow",
            "flow_delta_usd",
            "overall_label_changed",
        ]
        display_cols = [c for c in display_cols if c in matched_only.columns]

        display = matched_only[display_cols].copy()
        for col in [
            "legacy_rolling_net_flow",
            "fresh_rolling_net_flow",
            "flow_delta_usd",
        ]:
            if col in display.columns:
                display[col] = display[col].map(
                    lambda x: "unavailable" if pd.isna(x) else f"{float(x):,.2f}"
                )

        print("MATCHED CASES")
        print(display.to_string(index=False))
        print()

    if not stored_only.empty:
        print("STORED-ONLY BUCKETS")
        values = stored_only["match_bucket_start"].dropna().astype(str).tolist()
        for value in values:
            print(f"  {value}")
        print()

    if not fresh_only.empty:
        print("FRESH-ONLY BUCKETS")
        values = fresh_only["fresh_bucket_start"].dropna().astype(str).tolist()
        for value in values:
            print(f"  {value}")
        print()

    print("RESEARCH-CONCLUSION IMPACT")
    if len(matched_only) == 0:
        print("  No timestamp-adjusted matched cases; manual investigation required.")
    elif changed_count == 0 and len(stored_only) == 0 and len(fresh_only) == 0:
        print(
            "  All historical cases matched and overall labels were unchanged; "
            "the causal remediation changes timing/provenance while preserving "
            "the case-level overall-label conclusion for this sample."
        )
    elif changed_count == 0:
        print(
            "  Matched cases kept the same overall labels, but the event universe "
            "changed (stored-only and/or fresh-only cases exist)."
        )
    else:
        print(
            f"  {changed_count} matched case(s) changed overall label under the "
            "causal methodology; public research conclusions must be updated."
        )


def main() -> int:
    print("# LEGACY V2 VS CAUSAL V5 FINAL COMPARISON")
    print(f"Repo root: {REPO_ROOT}")
    print(f"DB:        {DB_PATH}")
    print("Mode:      READ ONLY")
    print()

    events, prices, stored = _load_sqlite_read_only()

    print("SOURCE ROWS")
    print(f"  enriched_whales:            {len(events)}")
    print(f"  historical_prices:           {len(prices)}")
    print(f"  stored_outcome_validation:   {len(stored)}")
    print()

    compare_backtests(events, prices)
    compare_outcomes(events, prices, stored)

    print()
    print("=" * 96)
    print("FINAL SAFETY")
    print("=" * 96)
    print("SQLite opened with mode=ro; no dataset rows were written by this script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
