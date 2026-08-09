"""Benchmark-adjusted outcome validation with explicit signal-availability timing.

V3 keeps legacy research artifacts reproducible while ensuring new validation
records are anchored to when a signal was actually available, not merely to the
left-labeled hourly bucket start.
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
METHODOLOGY_VERSION = "v3_signal_availability"

OUTPUT_COLUMNS = [
    "methodology_version",
    "event_timestamp",
    "signal_bucket_start",
    "signal_available_at",
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
    return pd.DataFrame(columns=OUTPUT_COLUMNS)


def _coerce_utc_timestamp(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def _prepare_prices(price_df: pd.DataFrame) -> pd.DataFrame:
    required = {"timestamp", "asset_type", "price_usd"}
    missing = sorted(required - set(price_df.columns))
    if missing:
        raise ValueError(f"Missing required price columns: {missing}")

    out = price_df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out["asset_type"] = out["asset_type"].fillna("UNKNOWN").astype(str).str.upper()
    out["price_usd"] = pd.to_numeric(out["price_usd"], errors="coerce")

    if "price_available_at" in out.columns:
        available = pd.to_datetime(out["price_available_at"], utc=True, errors="coerce")
    elif "close_time" in out.columns:
        available = pd.to_datetime(out["close_time"], utc=True, errors="coerce") + pd.Timedelta(milliseconds=1)
    else:
        # Legacy project rows stored hourly close under the candle-open timestamp.
        # Preserve reproducibility but make the inferred availability explicit.
        available = out["timestamp"] + pd.Timedelta(hours=1)
    out["price_available_at"] = available
    out = out.dropna(subset=["timestamp", "asset_type", "price_usd", "price_available_at"])
    return out.sort_values(["asset_type", "price_available_at"]).reset_index(drop=True)


def _lookup_latest_available_price(
    prices: pd.DataFrame,
    asset_type: str,
    requested_ts,
    max_lookup_gap: pd.Timedelta,
) -> tuple[float | None, str | None]:
    """Latest price that was actually available at or before requested_ts."""
    requested_ts = _coerce_utc_timestamp(requested_ts)
    rows = prices[(prices["asset_type"] == str(asset_type).upper()) & (prices["price_available_at"] <= requested_ts)]
    if rows.empty:
        return None, None
    matched = rows.tail(1).iloc[0]
    matched_ts = matched["price_available_at"]
    if requested_ts - matched_ts > max_lookup_gap:
        return None, None
    return float(matched["price_usd"]), str(matched_ts)


def _lookup_forward_available_price(
    prices: pd.DataFrame,
    asset_type: str,
    requested_ts,
    max_lookup_gap: pd.Timedelta,
) -> tuple[float | None, str | None]:
    """First price becoming available at or after requested_ts."""
    requested_ts = _coerce_utc_timestamp(requested_ts)
    rows = prices[(prices["asset_type"] == str(asset_type).upper()) & (prices["price_available_at"] >= requested_ts)]
    if rows.empty:
        return None, None
    matched = rows.head(1).iloc[0]
    matched_ts = matched["price_available_at"]
    if matched_ts - requested_ts > max_lookup_gap:
        return None, None
    return float(matched["price_usd"]), str(matched_ts)


def _validate_horizons(horizons: Sequence[int]) -> tuple[int, ...]:
    clean = tuple(int(h) for h in horizons)
    if 6 not in clean or 24 not in clean:
        raise ValueError("horizons must include 6 and 24 hours.")
    if any(h <= 0 for h in clean):
        raise ValueError("horizons must be positive integers.")
    return clean


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
    """Build V3 validation anchored to ``signal_available_at``."""
    clean_target = str(target_asset).upper()
    clean_benchmark = str(benchmark_asset).upper()
    clean_horizons = _validate_horizons(horizons)
    prices = _prepare_prices(prices_df)
    target_price_asset = PRICE_ASSET_MAP.get(clean_target, clean_target)

    signals = analyze_whale_flow(
        df=events_df,
        target_asset=clean_target,
        window_hours=window_hours,
        min_flow_usd=min_flow_usd,
        price_df=prices_df,
    )
    selected = signals[(signals["event_count"] > 0) & (signals["signal"] != 0)].copy()
    if selected.empty:
        return _empty_output()

    rows: list[dict[str, object]] = []
    for _, event in selected.iterrows():
        bucket_start = _coerce_utc_timestamp(event["timestamp"])
        signal_available_at = _coerce_utc_timestamp(event.get("signal_available_at", bucket_start + pd.Timedelta(hours=1)))
        signal_value = int(event["signal"])
        direction = "positive" if signal_value > 0 else "negative"

        # event_asset_price is the completed close for this signal bucket and is
        # available exactly at signal_available_at under V3 ingestion semantics.
        row: dict[str, object] = {
            "methodology_version": METHODOLOGY_VERSION,
            "event_timestamp": str(signal_available_at),
            "signal_bucket_start": str(bucket_start),
            "signal_available_at": str(signal_available_at),
            "target_asset": clean_target,
            "target_price_asset": target_price_asset,
            "benchmark_asset": clean_benchmark,
            "signal": signal_value,
            "signal_direction": direction,
            "rolling_net_flow": float(event["rolling_net_flow"]),
            "event_asset_price": float(event["price_usd"]),
        }

        benchmark_event_price, benchmark_event_ts = _lookup_latest_available_price(
            prices, clean_benchmark, signal_available_at, max_price_lookup_gap
        )

        horizon_labels: dict[int, str] = {}
        for horizon in clean_horizons:
            prefix = f"{horizon}h"
            future_ts = signal_available_at + pd.Timedelta(hours=horizon)
            future_asset_price, matched_asset_ts = _lookup_forward_available_price(
                prices, target_price_asset, future_ts, max_price_lookup_gap
            )
            benchmark_future_price, benchmark_future_ts = _lookup_forward_available_price(
                prices, clean_benchmark, future_ts, max_price_lookup_gap
            )
            row[f"{prefix}_matched_asset_ts"] = matched_asset_ts
            row[f"{prefix}_matched_benchmark_event_ts"] = benchmark_event_ts
            row[f"{prefix}_matched_benchmark_future_ts"] = benchmark_future_ts

            if future_asset_price is None or benchmark_event_price is None or benchmark_future_price is None:
                row[f"{prefix}_actual_return"] = None
                row[f"{prefix}_benchmark_return"] = None
                row[f"{prefix}_abnormal_return"] = None
                row[f"{prefix}_label"] = "data_unavailable"
                horizon_labels[horizon] = "data_unavailable"
                continue

            actual = calculate_return(float(event["price_usd"]), future_asset_price)
            benchmark = calculate_return(benchmark_event_price, benchmark_future_price)
            abnormal = calculate_abnormal_return(actual, benchmark)
            label = label_horizon_outcome(signal_direction=direction, abnormal_return=abnormal)
            row[f"{prefix}_future_asset_price"] = future_asset_price
            row[f"{prefix}_benchmark_event_price"] = benchmark_event_price
            row[f"{prefix}_benchmark_future_price"] = benchmark_future_price
            row[f"{prefix}_actual_return"] = actual
            row[f"{prefix}_benchmark_return"] = benchmark
            row[f"{prefix}_abnormal_return"] = abnormal
            row[f"{prefix}_label"] = label
            horizon_labels[horizon] = label

        label_6h = horizon_labels.get(6, "data_unavailable")
        label_24h = horizon_labels.get(24, "data_unavailable")
        row["overall_label"] = summarize_overall_label(label_6h=label_6h, label_24h=label_24h)
        row["evidence_quality"] = classify_evidence_quality(label_6h=label_6h, label_24h=label_24h)
        row["failure_mode"] = classify_failure_mode(label_6h=label_6h, label_24h=label_24h)
        rows.append(row)

    validation = pd.DataFrame(rows)
    for column in OUTPUT_COLUMNS:
        if column not in validation.columns:
            validation[column] = None
    return validation[OUTPUT_COLUMNS]
