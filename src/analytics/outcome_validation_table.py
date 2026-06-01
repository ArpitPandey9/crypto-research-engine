"""Build benchmark-adjusted outcome validation tables for whale-flow signals.

This module converts whale-flow signal events into an event-study style
validation table.

The goal is not to prove prediction.
The goal is to test whether signal classifications line up with observed
+6h and +24h outcomes after adjusting for BTC benchmark movement.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from src.analytics.outcome_validation import (
    calculate_abnormal_return,
    calculate_return,
    classify_evidence_quality,
    classify_failure_mode,
    label_horizon_outcome,
    summarize_overall_label,
)
from src.strategies.whale_signals import PRICE_ASSET_MAP, analyze_whale_flow


DEFAULT_HORIZONS = (6, 24)
DEFAULT_MAX_PRICE_LOOKUP_GAP = pd.Timedelta(hours=2)

OUTPUT_COLUMNS = [
    "event_timestamp",
    "target_asset",
    "target_price_asset",
    "benchmark_asset",
    "signal",
    "signal_direction",
    "rolling_net_flow",
    "event_asset_price",
    "6h_future_asset_price",
    "6h_benchmark_event_price",
    "6h_benchmark_future_price",
    "6h_actual_return",
    "6h_benchmark_return",
    "6h_abnormal_return",
    "6h_label",
    "24h_future_asset_price",
    "24h_benchmark_event_price",
    "24h_benchmark_future_price",
    "24h_actual_return",
    "24h_benchmark_return",
    "24h_abnormal_return",
    "24h_label",
    "overall_label",
    "evidence_quality",
    "failure_mode",
]


def _empty_output() -> pd.DataFrame:
    """Return an empty validation table with stable output columns."""
    return pd.DataFrame(columns=OUTPUT_COLUMNS)


def _prepare_prices(price_df: pd.DataFrame) -> pd.DataFrame:
    """Clean historical price data for timestamp-based lookup."""
    required_columns = {"timestamp", "asset_type", "price_usd"}
    missing = sorted(required_columns - set(price_df.columns))
    if missing:
        raise ValueError(f"Missing required price columns: {missing}")

    out = price_df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out["asset_type"] = out["asset_type"].fillna("UNKNOWN").astype(str).str.upper()
    out["price_usd"] = pd.to_numeric(out["price_usd"], errors="coerce")

    out = out.dropna(subset=["timestamp", "asset_type", "price_usd"])
    out = out.sort_values("timestamp").reset_index(drop=True)
    return out


def _coerce_utc_timestamp(value) -> pd.Timestamp:
    """Convert a timestamp-like value into a timezone-aware UTC timestamp."""
    ts = pd.Timestamp(value)

    if ts.tzinfo is None:
        return ts.tz_localize("UTC")

    return ts.tz_convert("UTC")


def _lookup_forward_price(
    prices: pd.DataFrame,
    asset_type: str,
    requested_ts,
    max_lookup_gap: pd.Timedelta,
) -> tuple[float | None, str | None]:
    """Find the first available price at or after a requested timestamp.

    Returns:
        (price_usd, matched_timestamp)

    If no price exists within max_lookup_gap, both values are None.
    """
    requested_ts = _coerce_utc_timestamp(requested_ts)
    clean_asset = str(asset_type).upper()

    asset_prices = prices[prices["asset_type"] == clean_asset].copy()
    future_rows = asset_prices[asset_prices["timestamp"] >= requested_ts].head(1)

    if future_rows.empty:
        return None, None

    matched = future_rows.iloc[0]
    matched_ts = matched["timestamp"]

    if matched_ts - requested_ts > max_lookup_gap:
        return None, None

    return float(matched["price_usd"]), str(matched_ts)


def _validate_horizons(horizons: Sequence[int]) -> tuple[int, ...]:
    """Validate that required +6h and +24h event windows are present."""
    clean_horizons = tuple(int(horizon) for horizon in horizons)

    if 6 not in clean_horizons or 24 not in clean_horizons:
        raise ValueError("horizons must include 6 and 24 hours.")

    if any(horizon <= 0 for horizon in clean_horizons):
        raise ValueError("horizons must be positive integers.")

    return clean_horizons


def build_outcome_validation_table(
    events_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    target_asset: str = "ETH",
    benchmark_asset: str = "BTC",
    window_hours: int = 12,
    min_flow_usd: float = 0.0,
    horizons: Sequence[int] = DEFAULT_HORIZONS,
    max_price_lookup_gap: pd.Timedelta = DEFAULT_MAX_PRICE_LOOKUP_GAP,
) -> pd.DataFrame:
    """Build a benchmark-adjusted outcome-validation table.

    The function:
    1. Builds whale-flow signals using existing project logic.
    2. Selects real event rows with non-zero signal.
    3. Looks up +6h and +24h target/benchmark prices.
    4. Calculates actual, benchmark, and abnormal returns.
    5. Assigns horizon labels, overall label, evidence quality, and failure mode.
    """
    clean_target_asset = str(target_asset).upper()
    clean_benchmark_asset = str(benchmark_asset).upper()
    clean_horizons = _validate_horizons(horizons)
    prices = _prepare_prices(prices_df)

    target_price_asset = PRICE_ASSET_MAP.get(clean_target_asset, clean_target_asset)

    signals_df = analyze_whale_flow(
        df=events_df,
        target_asset=clean_target_asset,
        window_hours=window_hours,
        min_flow_usd=min_flow_usd,
        price_df=prices_df,
    )

    events_to_validate = signals_df[
        (signals_df["event_count"] > 0) & (signals_df["signal"] != 0)
    ].copy()

    if events_to_validate.empty:
        return _empty_output()

    rows = []

    for _, event in events_to_validate.iterrows():
        event_ts = _coerce_utc_timestamp(event["timestamp"])
        signal_value = int(event["signal"])
        signal_direction = "positive" if signal_value > 0 else "negative"

        row = {
            "event_timestamp": str(event_ts),
            "target_asset": clean_target_asset,
            "target_price_asset": target_price_asset,
            "benchmark_asset": clean_benchmark_asset,
            "signal": signal_value,
            "signal_direction": signal_direction,
            "rolling_net_flow": float(event["rolling_net_flow"]),
            "event_asset_price": float(event["price_usd"]),
        }

        horizon_labels = {}

        for horizon in clean_horizons:
            future_ts = event_ts + pd.Timedelta(hours=horizon)
            prefix = f"{horizon}h"

            future_asset_price, matched_asset_ts = _lookup_forward_price(
                prices=prices,
                asset_type=target_price_asset,
                requested_ts=future_ts,
                max_lookup_gap=max_price_lookup_gap,
            )
            benchmark_event_price, matched_benchmark_event_ts = _lookup_forward_price(
                prices=prices,
                asset_type=clean_benchmark_asset,
                requested_ts=event_ts,
                max_lookup_gap=max_price_lookup_gap,
            )
            benchmark_future_price, matched_benchmark_future_ts = _lookup_forward_price(
                prices=prices,
                asset_type=clean_benchmark_asset,
                requested_ts=future_ts,
                max_lookup_gap=max_price_lookup_gap,
            )

            row[f"{prefix}_matched_asset_ts"] = matched_asset_ts
            row[f"{prefix}_matched_benchmark_event_ts"] = matched_benchmark_event_ts
            row[f"{prefix}_matched_benchmark_future_ts"] = matched_benchmark_future_ts

            if (
                future_asset_price is None
                or benchmark_event_price is None
                or benchmark_future_price is None
            ):
                row[f"{prefix}_actual_return"] = None
                row[f"{prefix}_benchmark_return"] = None
                row[f"{prefix}_abnormal_return"] = None
                row[f"{prefix}_label"] = "data_unavailable"
                horizon_labels[horizon] = "data_unavailable"
                continue

            actual_return = calculate_return(
                event_price=float(event["price_usd"]),
                future_price=future_asset_price,
            )
            benchmark_return = calculate_return(
                event_price=benchmark_event_price,
                future_price=benchmark_future_price,
            )
            abnormal_return = calculate_abnormal_return(
                actual_return=actual_return,
                benchmark_return=benchmark_return,
            )
            horizon_label = label_horizon_outcome(
                signal_direction=signal_direction,
                abnormal_return=abnormal_return,
            )

            row[f"{prefix}_future_asset_price"] = future_asset_price
            row[f"{prefix}_benchmark_event_price"] = benchmark_event_price
            row[f"{prefix}_benchmark_future_price"] = benchmark_future_price
            row[f"{prefix}_actual_return"] = actual_return
            row[f"{prefix}_benchmark_return"] = benchmark_return
            row[f"{prefix}_abnormal_return"] = abnormal_return
            row[f"{prefix}_label"] = horizon_label
            horizon_labels[horizon] = horizon_label

        label_6h = horizon_labels.get(6, "data_unavailable")
        label_24h = horizon_labels.get(24, "data_unavailable")

        row["overall_label"] = summarize_overall_label(
            label_6h=label_6h,
            label_24h=label_24h,
        )
        row["evidence_quality"] = classify_evidence_quality(
            label_6h=label_6h,
            label_24h=label_24h,
        )
        row["failure_mode"] = classify_failure_mode(
            label_6h=label_6h,
            label_24h=label_24h,
        )

        rows.append(row)

    validation_df = pd.DataFrame(rows)

    for column in OUTPUT_COLUMNS:
        if column not in validation_df.columns:
            validation_df[column] = None

    return validation_df[OUTPUT_COLUMNS]
