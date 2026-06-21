"""Event-time market-context layer for outcome-validation research.

This module explains the market conditions around each validated whale-flow
event. It does not create new signals and it does not invent missing liquidity.

The goal is to help answer a research question:

Did worked, failed, and short-lived whale-flow signals happen under different
volatility and liquidity conditions?
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from src.analytics.liquidity_risk import (
    EXTREME_PRICE_IMPACT_RISK,
    HIGH_PRICE_IMPACT_RISK,
    LOW_PRICE_IMPACT_RISK,
    calculate_size_ratio,
    classify_price_impact_risk,
)
from src.analytics.volatility_regime import (
    ELEVATED_VOLATILITY_REGIME,
    EXTREME_VOLATILITY_REGIME,
    NORMAL_VOLATILITY_REGIME,
    UNAVAILABLE_VOLATILITY_REGIME,
    build_volatility_regime,
)


AVAILABLE_STATUS = "available"
UNAVAILABLE_STATUS = "unavailable"
STALE_STATUS = "stale"

EVENT_CONTEXT_COLUMNS = [
    "record_key",
    "event_timestamp",
    "target_asset",
    "overall_label",
    "failure_mode",
    "rolling_net_flow",
    "event_volatility_regime",
    "event_realized_volatility",
    "event_volatility_status",
    "event_liquidity_depth_usd",
    "event_liquidity_snapshot_time",
    "event_liquidity_staleness_hours",
    "event_liquidity_status",
    "flow_to_liquidity_ratio",
    "price_impact_risk",
    "context_bucket",
    "context_interpretation",
]

REQUIRED_RECORD_COLUMNS = {
    "record_key",
    "event_timestamp",
    "target_asset",
    "overall_label",
    "failure_mode",
    "rolling_net_flow",
}

REQUIRED_PRICE_COLUMNS = {
    "timestamp",
    "asset_type",
    "price_usd",
}

REQUIRED_POOL_COLUMNS = {
    "fetched_at_utc",
    "asset_symbol",
    "liquidity_usd",
}


def _missing_columns(frame: pd.DataFrame, required_columns: set[str]) -> list[str]:
    """Return sorted missing columns for clear validation errors."""
    return sorted(required_columns - set(frame.columns))


def _normalize_asset_symbol(value: object) -> str:
    """Normalize an asset symbol for joins and display."""
    normalized = str(value).strip().upper()

    if not normalized or normalized == "NAN":
        raise ValueError("asset symbol cannot be empty")

    return normalized


def _normalize_event_records(records: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize outcome-validation records."""
    missing = _missing_columns(records, REQUIRED_RECORD_COLUMNS)
    if missing:
        raise ValueError(f"Missing required event record columns: {missing}")

    out = records.copy()
    out["event_timestamp"] = pd.to_datetime(
        out["event_timestamp"],
        utc=True,
        errors="coerce",
    )

    if out["event_timestamp"].isna().any():
        raise ValueError("event_timestamp contains invalid values")

    out["target_asset"] = out["target_asset"].map(_normalize_asset_symbol)

    if "target_price_asset" in out.columns:
        out["target_price_asset"] = out["target_price_asset"].fillna(
            out["target_asset"]
        )
        out["target_price_asset"] = out["target_price_asset"].map(
            _normalize_asset_symbol
        )
    else:
        out["target_price_asset"] = out["target_asset"]

    out["rolling_net_flow"] = pd.to_numeric(
        out["rolling_net_flow"],
        errors="coerce",
    )

    return out.sort_values("event_timestamp").reset_index(drop=True)


def _normalize_price_history(price_history: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize historical price data."""
    missing = _missing_columns(price_history, REQUIRED_PRICE_COLUMNS)
    if missing:
        raise ValueError(f"Missing required price columns: {missing}")

    out = price_history.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out["asset_type"] = out["asset_type"].map(_normalize_asset_symbol)
    out["price_usd"] = pd.to_numeric(out["price_usd"], errors="coerce")

    if out["timestamp"].isna().any():
        raise ValueError("timestamp contains invalid values")

    if out["price_usd"].isna().any():
        raise ValueError("price_usd contains invalid values")

    return out.sort_values("timestamp").reset_index(drop=True)


def _normalize_pool_depths(pool_depths: pd.DataFrame | None) -> pd.DataFrame:
    """Validate and normalize DEX pool-depth snapshots."""
    if pool_depths is None or pool_depths.empty:
        return pd.DataFrame(columns=sorted(REQUIRED_POOL_COLUMNS))

    missing = _missing_columns(pool_depths, REQUIRED_POOL_COLUMNS)
    if missing:
        raise ValueError(f"Missing required pool-depth columns: {missing}")

    out = pool_depths.copy()
    out["fetched_at_utc"] = pd.to_datetime(
        out["fetched_at_utc"],
        utc=True,
        errors="coerce",
    )
    out["asset_symbol"] = out["asset_symbol"].map(_normalize_asset_symbol)
    out["liquidity_usd"] = pd.to_numeric(out["liquidity_usd"], errors="coerce")

    if out["fetched_at_utc"].isna().any():
        raise ValueError("fetched_at_utc contains invalid values")

    if out["liquidity_usd"].isna().any():
        raise ValueError("liquidity_usd contains invalid values")

    return out.sort_values("fetched_at_utc").reset_index(drop=True)


def _build_event_volatility_context(
    record: pd.Series,
    price_history: pd.DataFrame,
    window_size: int,
) -> dict[str, object]:
    """Build prior-only volatility context for one event."""
    event_timestamp = record["event_timestamp"]
    price_asset = record["target_price_asset"]

    event_prices = price_history[
        (price_history["asset_type"] == price_asset)
        & (price_history["timestamp"] <= event_timestamp)
    ][["timestamp", "price_usd"]]

    result = build_volatility_regime(
        prices=event_prices,
        asset_symbol=price_asset,
        window_size=window_size,
    )

    return {
        "event_volatility_regime": result.volatility_regime,
        "event_realized_volatility": result.latest_realized_volatility,
        "event_volatility_status": (
            AVAILABLE_STATUS if result.is_available else UNAVAILABLE_STATUS
        ),
        "volatility_reason": result.reason,
    }


def _build_event_liquidity_context(
    record: pd.Series,
    pool_depths: pd.DataFrame,
    max_staleness_hours: int,
) -> dict[str, object]:
    """Build prior-only liquidity context for one event."""
    event_timestamp = record["event_timestamp"]
    target_asset = record["target_asset"]

    if pool_depths.empty:
        return {
            "event_liquidity_depth_usd": None,
            "event_liquidity_snapshot_time": None,
            "event_liquidity_staleness_hours": None,
            "event_liquidity_status": UNAVAILABLE_STATUS,
            "flow_to_liquidity_ratio": None,
            "price_impact_risk": "unavailable",
            "liquidity_reason": "No pool-depth snapshots are available.",
        }

    candidates = pool_depths[
        (pool_depths["asset_symbol"] == target_asset)
        & (pool_depths["fetched_at_utc"] <= event_timestamp)
    ].sort_values("fetched_at_utc")

    if candidates.empty:
        return {
            "event_liquidity_depth_usd": None,
            "event_liquidity_snapshot_time": None,
            "event_liquidity_staleness_hours": None,
            "event_liquidity_status": UNAVAILABLE_STATUS,
            "flow_to_liquidity_ratio": None,
            "price_impact_risk": "unavailable",
            "liquidity_reason": (
                "No prior pool-depth snapshot exists at or before the event time."
            ),
        }

    latest = candidates.iloc[-1]
    staleness = event_timestamp - latest["fetched_at_utc"]
    staleness_hours = staleness / timedelta(hours=1)

    if staleness_hours > max_staleness_hours:
        return {
            "event_liquidity_depth_usd": float(latest["liquidity_usd"]),
            "event_liquidity_snapshot_time": latest["fetched_at_utc"].isoformat(),
            "event_liquidity_staleness_hours": float(staleness_hours),
            "event_liquidity_status": STALE_STATUS,
            "flow_to_liquidity_ratio": None,
            "price_impact_risk": "unavailable",
            "liquidity_reason": (
                f"Latest prior pool-depth snapshot is {staleness_hours:.2f} hours "
                f"old, above the {max_staleness_hours}-hour freshness limit."
            ),
        }

    liquidity_usd = float(latest["liquidity_usd"])
    rolling_net_flow = record["rolling_net_flow"]

    if pd.isna(rolling_net_flow):
        return {
            "event_liquidity_depth_usd": liquidity_usd,
            "event_liquidity_snapshot_time": latest["fetched_at_utc"].isoformat(),
            "event_liquidity_staleness_hours": float(staleness_hours),
            "event_liquidity_status": AVAILABLE_STATUS,
            "flow_to_liquidity_ratio": None,
            "price_impact_risk": "unavailable",
            "liquidity_reason": "Rolling net flow is unavailable.",
        }

    ratio = calculate_size_ratio(
        whale_flow_usd=float(rolling_net_flow),
        pool_depth_usd=liquidity_usd,
    )

    return {
        "event_liquidity_depth_usd": liquidity_usd,
        "event_liquidity_snapshot_time": latest["fetched_at_utc"].isoformat(),
        "event_liquidity_staleness_hours": float(staleness_hours),
        "event_liquidity_status": AVAILABLE_STATUS,
        "flow_to_liquidity_ratio": ratio,
        "price_impact_risk": classify_price_impact_risk(ratio),
        "liquidity_reason": (
            f"Prior pool-depth snapshot is {staleness_hours:.2f} hours old. "
            f"Flow-to-liquidity ratio is {ratio:.4f}."
        ),
    }


def _classify_context_bucket(
    volatility_regime: str,
    liquidity_status: str,
    price_impact_risk: str,
) -> str:
    """Classify the combined event-time context."""
    if (
        volatility_regime == UNAVAILABLE_VOLATILITY_REGIME
        and liquidity_status != AVAILABLE_STATUS
    ):
        return "context_unavailable"

    if (
        liquidity_status == AVAILABLE_STATUS
        and price_impact_risk != "unavailable"
        and volatility_regime == NORMAL_VOLATILITY_REGIME
        and price_impact_risk == LOW_PRICE_IMPACT_RISK
    ):
        return "normal_absorption_context"

    if (
        liquidity_status == AVAILABLE_STATUS
        and price_impact_risk in {HIGH_PRICE_IMPACT_RISK, EXTREME_PRICE_IMPACT_RISK}
        and volatility_regime in {ELEVATED_VOLATILITY_REGIME, EXTREME_VOLATILITY_REGIME}
    ):
        return "fragile_market_context"

    if volatility_regime in {ELEVATED_VOLATILITY_REGIME, EXTREME_VOLATILITY_REGIME}:
        return "volatility_only_context"

    if liquidity_status != AVAILABLE_STATUS:
        return "liquidity_unavailable_context"

    return "mixed_market_context"


def _build_interpretation(
    context_bucket: str,
    volatility_context: dict[str, object],
    liquidity_context: dict[str, object],
) -> str:
    """Create a short human-readable interpretation."""
    return (
        f"{context_bucket}: volatility={volatility_context['event_volatility_regime']} "
        f"({volatility_context['event_volatility_status']}), "
        f"liquidity={liquidity_context['event_liquidity_status']}, "
        f"price_impact_risk={liquidity_context['price_impact_risk']}."
    )


def build_event_time_context(
    records: pd.DataFrame,
    price_history: pd.DataFrame,
    pool_depths: pd.DataFrame | None = None,
    volatility_window_size: int = 24,
    max_liquidity_staleness_hours: int = 24,
) -> pd.DataFrame:
    """Attach prior-only volatility and liquidity context to validation records."""
    if records.empty:
        return pd.DataFrame(columns=EVENT_CONTEXT_COLUMNS)

    normalized_records = _normalize_event_records(records)
    normalized_prices = _normalize_price_history(price_history)
    normalized_pools = _normalize_pool_depths(pool_depths)

    context_rows = []

    for _, record in normalized_records.iterrows():
        volatility_context = _build_event_volatility_context(
            record=record,
            price_history=normalized_prices,
            window_size=volatility_window_size,
        )
        liquidity_context = _build_event_liquidity_context(
            record=record,
            pool_depths=normalized_pools,
            max_staleness_hours=max_liquidity_staleness_hours,
        )
        context_bucket = _classify_context_bucket(
            volatility_regime=str(volatility_context["event_volatility_regime"]),
            liquidity_status=str(liquidity_context["event_liquidity_status"]),
            price_impact_risk=str(liquidity_context["price_impact_risk"]),
        )

        row = {
            "record_key": record["record_key"],
            "event_timestamp": record["event_timestamp"].isoformat(),
            "target_asset": record["target_asset"],
            "overall_label": record["overall_label"],
            "failure_mode": record["failure_mode"],
            "rolling_net_flow": record["rolling_net_flow"],
            **volatility_context,
            **liquidity_context,
            "context_bucket": context_bucket,
            "context_interpretation": _build_interpretation(
                context_bucket=context_bucket,
                volatility_context=volatility_context,
                liquidity_context=liquidity_context,
            ),
        }
        context_rows.append(row)

    context_df = pd.DataFrame(context_rows)

    return context_df[EVENT_CONTEXT_COLUMNS]
