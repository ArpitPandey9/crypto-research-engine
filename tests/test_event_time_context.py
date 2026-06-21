import pandas as pd
import pytest

from src.analytics.event_time_context import (
    AVAILABLE_STATUS,
    EVENT_CONTEXT_COLUMNS,
    STALE_STATUS,
    UNAVAILABLE_STATUS,
    build_event_time_context,
)


def sample_records() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "record_key": "ETH|BTC|2026-01-01 08:00:00+00:00|signal=1",
                "event_timestamp": "2026-01-01 08:00:00+00:00",
                "target_asset": "eth",
                "target_price_asset": "eth",
                "overall_label": "worked",
                "failure_mode": "no_failure",
                "rolling_net_flow": 2_000_000.0,
            }
        ]
    )


def sample_prices() -> pd.DataFrame:
    prices = [100, 101, 100.5, 101.5, 101, 102, 101.4, 102.2, 102.0]
    return pd.DataFrame(
        [
            {
                "timestamp": f"2026-01-01 {hour:02d}:00:00+00:00",
                "asset_type": "ETH",
                "price_usd": price,
            }
            for hour, price in enumerate(prices)
        ]
    )


def test_build_event_time_context_adds_volatility_and_fresh_liquidity_context():
    pool_depths = pd.DataFrame(
        [
            {
                "fetched_at_utc": "2026-01-01 07:30:00+00:00",
                "asset_symbol": "ETH",
                "liquidity_usd": 100_000_000.0,
            }
        ]
    )

    context = build_event_time_context(
        records=sample_records(),
        price_history=sample_prices(),
        pool_depths=pool_depths,
        volatility_window_size=3,
        max_liquidity_staleness_hours=24,
    )

    row = context.iloc[0]

    assert list(context.columns) == EVENT_CONTEXT_COLUMNS
    assert row["target_asset"] == "ETH"
    assert row["event_volatility_status"] == AVAILABLE_STATUS
    assert row["event_liquidity_status"] == AVAILABLE_STATUS
    assert row["event_liquidity_depth_usd"] == pytest.approx(100_000_000.0)
    assert row["flow_to_liquidity_ratio"] == pytest.approx(0.02)
    assert row["price_impact_risk"] == "Medium Price-Impact Risk"
    assert isinstance(row["context_bucket"], str)
    assert "volatility=" in row["context_interpretation"]


def test_build_event_time_context_does_not_use_future_liquidity_snapshot():
    future_pool_depths = pd.DataFrame(
        [
            {
                "fetched_at_utc": "2026-01-01 09:00:00+00:00",
                "asset_symbol": "ETH",
                "liquidity_usd": 100_000_000.0,
            }
        ]
    )

    context = build_event_time_context(
        records=sample_records(),
        price_history=sample_prices(),
        pool_depths=future_pool_depths,
        volatility_window_size=3,
    )

    row = context.iloc[0]

    assert row["event_liquidity_status"] == UNAVAILABLE_STATUS
    assert pd.isna(row["flow_to_liquidity_ratio"])
    assert row["price_impact_risk"] == "unavailable"


def test_build_event_time_context_marks_stale_liquidity_as_unavailable_for_ratio():
    stale_pool_depths = pd.DataFrame(
        [
            {
                "fetched_at_utc": "2025-12-30 08:00:00+00:00",
                "asset_symbol": "ETH",
                "liquidity_usd": 100_000_000.0,
            }
        ]
    )

    context = build_event_time_context(
        records=sample_records(),
        price_history=sample_prices(),
        pool_depths=stale_pool_depths,
        volatility_window_size=3,
        max_liquidity_staleness_hours=24,
    )

    row = context.iloc[0]

    assert row["event_liquidity_status"] == STALE_STATUS
    assert row["event_liquidity_depth_usd"] == pytest.approx(100_000_000.0)
    assert pd.isna(row["flow_to_liquidity_ratio"])
    assert row["price_impact_risk"] == "unavailable"


def test_build_event_time_context_returns_empty_schema_for_empty_records():
    context = build_event_time_context(
        records=pd.DataFrame(),
        price_history=sample_prices(),
    )

    assert context.empty
    assert list(context.columns) == EVENT_CONTEXT_COLUMNS


def test_build_event_time_context_rejects_missing_record_columns():
    with pytest.raises(ValueError, match="Missing required event record columns"):
        build_event_time_context(
            records=pd.DataFrame({"event_timestamp": ["2026-01-01"]}),
            price_history=sample_prices(),
        )

def test_stale_liquidity_with_available_volatility_is_labeled_volatility_only_context():
    records = pd.DataFrame(
        [
            {
                "record_key": "ETH|BTC|2026-01-01 13:00:00+00:00|signal=1",
                "event_timestamp": "2026-01-01 13:00:00+00:00",
                "target_asset": "ETH",
                "target_price_asset": "ETH",
                "overall_label": "failed",
                "failure_mode": "unsupported_signal",
                "rolling_net_flow": 5_000_000.0,
            }
        ]
    )

    calm_prices = [
        100.0,
        100.5,
        101.0,
        101.3,
        101.8,
        102.0,
        102.2,
        102.4,
        102.7,
        103.0,
    ]
    shock_prices = [
        110.0,
        90.0,
        120.0,
        80.0,
    ]
    all_prices = calm_prices + shock_prices

    price_history = pd.DataFrame(
        [
            {
                "timestamp": f"2026-01-01 {hour:02d}:00:00+00:00",
                "asset_type": "ETH",
                "price_usd": price,
            }
            for hour, price in enumerate(all_prices)
        ]
    )

    stale_pool_depths = pd.DataFrame(
        [
            {
                "fetched_at_utc": "2025-12-30 13:00:00+00:00",
                "asset_symbol": "ETH",
                "liquidity_usd": 100_000_000.0,
            }
        ]
    )

    context = build_event_time_context(
        records=records,
        price_history=price_history,
        pool_depths=stale_pool_depths,
        volatility_window_size=3,
        max_liquidity_staleness_hours=24,
    )

    row = context.iloc[0]

    assert row["event_volatility_status"] == AVAILABLE_STATUS
    assert row["event_liquidity_status"] == STALE_STATUS
    assert pd.isna(row["flow_to_liquidity_ratio"])
    assert row["price_impact_risk"] == "unavailable"
    assert row["context_bucket"] == "volatility_only_context"



def test_build_event_time_context_rejects_empty_asset_symbol():
    records = sample_records()
    records.loc[0, "target_asset"] = " "

    with pytest.raises(ValueError, match="asset symbol cannot be empty"):
        build_event_time_context(
            records=records,
            price_history=sample_prices(),
        )


def test_build_event_time_context_rejects_invalid_event_timestamp():
    records = sample_records()
    records.loc[0, "event_timestamp"] = "not-a-timestamp"

    with pytest.raises(ValueError, match="event_timestamp contains invalid values"):
        build_event_time_context(
            records=records,
            price_history=sample_prices(),
        )


def test_build_event_time_context_rejects_missing_price_columns():
    with pytest.raises(ValueError, match="Missing required price columns"):
        build_event_time_context(
            records=sample_records(),
            price_history=pd.DataFrame(
                [{"timestamp": "2026-01-01 00:00:00+00:00", "price_usd": 100.0}]
            ),
        )


def test_build_event_time_context_rejects_invalid_price_timestamp():
    prices = pd.DataFrame(
        [
            {
                "timestamp": "bad-time",
                "asset_type": "ETH",
                "price_usd": 100.0,
            }
        ]
    )

    with pytest.raises(ValueError, match="timestamp contains invalid values"):
        build_event_time_context(
            records=sample_records(),
            price_history=prices,
        )


def test_build_event_time_context_rejects_invalid_price_value():
    prices = pd.DataFrame(
        [
            {
                "timestamp": "2026-01-01 00:00:00+00:00",
                "asset_type": "ETH",
                "price_usd": "bad-price",
            }
        ]
    )

    with pytest.raises(ValueError, match="price_usd contains invalid values"):
        build_event_time_context(
            records=sample_records(),
            price_history=prices,
        )


def test_build_event_time_context_rejects_missing_pool_depth_columns():
    with pytest.raises(ValueError, match="Missing required pool-depth columns"):
        build_event_time_context(
            records=sample_records(),
            price_history=sample_prices(),
            pool_depths=pd.DataFrame(
                [
                    {
                        "fetched_at_utc": "2026-01-01 07:00:00+00:00",
                        "asset_symbol": "ETH",
                    }
                ]
            ),
        )


def test_build_event_time_context_rejects_invalid_pool_depth_timestamp():
    with pytest.raises(ValueError, match="fetched_at_utc contains invalid values"):
        build_event_time_context(
            records=sample_records(),
            price_history=sample_prices(),
            pool_depths=pd.DataFrame(
                [
                    {
                        "fetched_at_utc": "bad-time",
                        "asset_symbol": "ETH",
                        "liquidity_usd": 100_000_000.0,
                    }
                ]
            ),
        )


def test_build_event_time_context_rejects_invalid_pool_depth_liquidity():
    with pytest.raises(ValueError, match="liquidity_usd contains invalid values"):
        build_event_time_context(
            records=sample_records(),
            price_history=sample_prices(),
            pool_depths=pd.DataFrame(
                [
                    {
                        "fetched_at_utc": "2026-01-01 07:00:00+00:00",
                        "asset_symbol": "ETH",
                        "liquidity_usd": "bad-liquidity",
                    }
                ]
            ),
        )


def test_build_event_time_context_marks_missing_pool_depths_unavailable():
    context = build_event_time_context(
        records=sample_records(),
        price_history=sample_prices(),
        pool_depths=None,
        volatility_window_size=3,
    )

    row = context.iloc[0]

    assert row["event_liquidity_status"] == UNAVAILABLE_STATUS
    assert pd.isna(row["flow_to_liquidity_ratio"])
    assert row["price_impact_risk"] == "unavailable"


def test_build_event_time_context_detects_normal_absorption_context():
    records = sample_records()
    records.loc[0, "rolling_net_flow"] = 500_000.0

    stable_prices = pd.DataFrame(
        [
            {
                "timestamp": f"2026-01-01 {hour:02d}:00:00+00:00",
                "asset_type": "ETH",
                "price_usd": 100.0 * (1.01**hour),
            }
            for hour in range(9)
        ]
    )

    fresh_pool_depths = pd.DataFrame(
        [
            {
                "fetched_at_utc": "2026-01-01 07:30:00+00:00",
                "asset_symbol": "ETH",
                "liquidity_usd": 100_000_000.0,
            }
        ]
    )

    context = build_event_time_context(
        records=records,
        price_history=stable_prices,
        pool_depths=fresh_pool_depths,
        volatility_window_size=3,
    )

    row = context.iloc[0]

    assert row["event_liquidity_status"] == AVAILABLE_STATUS
    assert row["flow_to_liquidity_ratio"] == pytest.approx(0.005)
    assert row["price_impact_risk"] == "Low Price-Impact Risk / Flow Likely Absorbed"
    assert row["context_bucket"] == "normal_absorption_context"


def test_build_event_time_context_detects_fragile_market_context():
    records = pd.DataFrame(
        [
            {
                "record_key": "ETH|BTC|2026-01-01 13:00:00+00:00|signal=1",
                "event_timestamp": "2026-01-01 13:00:00+00:00",
                "target_asset": "ETH",
                "target_price_asset": "ETH",
                "overall_label": "failed",
                "failure_mode": "unsupported_signal",
                "rolling_net_flow": 20_000_000.0,
            }
        ]
    )

    prices = pd.DataFrame(
        [
            {
                "timestamp": f"2026-01-01 {hour:02d}:00:00+00:00",
                "asset_type": "ETH",
                "price_usd": price,
            }
            for hour, price in enumerate(
                [100, 100.5, 101, 101.3, 101.8, 102, 102.2, 102.4, 102.7, 103, 110, 90, 120, 80]
            )
        ]
    )

    fresh_pool_depths = pd.DataFrame(
        [
            {
                "fetched_at_utc": "2026-01-01 12:30:00+00:00",
                "asset_symbol": "ETH",
                "liquidity_usd": 100_000_000.0,
            }
        ]
    )

    context = build_event_time_context(
        records=records,
        price_history=prices,
        pool_depths=fresh_pool_depths,
        volatility_window_size=3,
    )

    row = context.iloc[0]

    assert row["event_liquidity_status"] == AVAILABLE_STATUS
    assert row["flow_to_liquidity_ratio"] == pytest.approx(0.20)
    assert row["price_impact_risk"] == "Extreme Price-Impact Risk"
    assert row["context_bucket"] == "fragile_market_context"
