# tests/test_whale_signals.py

from __future__ import annotations

import pandas as pd
import pytest

from src.strategies.whale_signals import analyze_whale_flow, backtest_whale_strategy


def make_enriched_events() -> pd.DataFrame:
    """
    Build a small deterministic enriched-whale dataset for tests.
    """
    return pd.DataFrame(
        [
            {
                "timestamp": "2026-01-01 00:10:00+00:00",
                "asset_type": "ETH",
                "amount": 40.0,
                "sender_address": "0xaaa",
                "receiver_address": "0xwallet1",
                "price_usd": 3000.0,
                "true_usd_volume": 120000.0,
            },
            {
                "timestamp": "2026-01-01 01:15:00+00:00",
                "asset_type": "ETH",
                "amount": 50.0,
                "sender_address": "0xbbb",
                "receiver_address": "0x28C6c06298d514Db089934071355E5743bf21d60",
                "price_usd": 3100.0,
                "true_usd_volume": 155000.0,
            },
            {
                "timestamp": "2026-01-01 02:05:00+00:00",
                "asset_type": "ETH",
                "amount": 45.0,
                "sender_address": "0xccc",
                "receiver_address": "0xwallet2",
                "price_usd": 3200.0,
                "true_usd_volume": 144000.0,
            },
            {
                "timestamp": "2026-01-01 00:20:00+00:00",
                "asset_type": "WBTC",
                "amount": 3.0,
                "sender_address": "0xddd",
                "receiver_address": "0xwallet3",
                "price_usd": 60000.0,
                "true_usd_volume": 180000.0,
            },
        ]
    )


def make_price_frame() -> pd.DataFrame:
    """
    Build a clean hourly market-price table similar to historical_prices.
    """
    return pd.DataFrame(
        [
            {"timestamp": "2026-01-01 00:00:00+00:00", "asset_type": "ETH", "price_usd": 3000.0},
            {"timestamp": "2026-01-01 01:00:00+00:00", "asset_type": "ETH", "price_usd": 3100.0},
            {"timestamp": "2026-01-01 02:00:00+00:00", "asset_type": "ETH", "price_usd": 3200.0},
            {"timestamp": "2026-01-01 03:00:00+00:00", "asset_type": "ETH", "price_usd": 3300.0},
            {"timestamp": "2026-01-01 00:00:00+00:00", "asset_type": "BTC", "price_usd": 60000.0},
            {"timestamp": "2026-01-01 01:00:00+00:00", "asset_type": "BTC", "price_usd": 60500.0},
            {"timestamp": "2026-01-01 02:00:00+00:00", "asset_type": "BTC", "price_usd": 61000.0},
        ]
    )


def test_analyze_whale_flow_returns_expected_columns() -> None:
    events_df = make_enriched_events()
    prices_df = make_price_frame()

    result = analyze_whale_flow(
        df=events_df,
        target_asset="ETH",
        window_hours=2,
        min_flow_usd=0.0,
        price_df=prices_df,
    )

    expected_columns = {
        "timestamp",
        "price_usd",
        "pressure_usd",
        "true_usd_volume",
        "event_count",
        "target_asset",
        "rolling_net_flow",
        "signal",
    }

    assert expected_columns.issubset(result.columns)
    assert not result.empty
    assert set(result["target_asset"].unique()) == {"ETH"}


def test_analyze_whale_flow_filters_to_target_asset_only() -> None:
    events_df = make_enriched_events()
    prices_df = make_price_frame()

    result = analyze_whale_flow(
        df=events_df,
        target_asset="WBTC",
        window_hours=2,
        min_flow_usd=0.0,
        price_df=prices_df,
    )

    assert set(result["target_asset"].unique()) == {"WBTC"}
    assert not result.empty


def test_analyze_whale_flow_rejects_invalid_target_asset() -> None:
    events_df = make_enriched_events()
    prices_df = make_price_frame()

    with pytest.raises(ValueError, match="Unsupported target_asset"):
        analyze_whale_flow(
            df=events_df,
            target_asset="DOGE",
            window_hours=2,
            min_flow_usd=0.0,
            price_df=prices_df,
        )


def test_analyze_whale_flow_rejects_invalid_window() -> None:
    events_df = make_enriched_events()
    prices_df = make_price_frame()

    with pytest.raises(ValueError, match="window_hours must be at least 1"):
        analyze_whale_flow(
            df=events_df,
            target_asset="ETH",
            window_hours=0,
            min_flow_usd=0.0,
            price_df=prices_df,
        )


def test_exchange_receiver_creates_negative_pressure() -> None:
    events_df = make_enriched_events()
    prices_df = make_price_frame()

    result = analyze_whale_flow(
        df=events_df,
        target_asset="ETH",
        window_hours=1,
        min_flow_usd=0.0,
        price_df=prices_df,
    )

    # At 01:00, there is a known exchange receiver event, so hourly pressure should be negative.
    row = result.loc[result["timestamp"] == pd.Timestamp("2026-01-01 01:00:00+00:00")]
    assert not row.empty
    assert float(row["pressure_usd"].iloc[0]) < 0


def test_backtest_returns_expected_columns() -> None:
    events_df = make_enriched_events()
    prices_df = make_price_frame()

    signals = analyze_whale_flow(
        df=events_df,
        target_asset="ETH",
        window_hours=2,
        min_flow_usd=0.0,
        price_df=prices_df,
    )

    result = backtest_whale_strategy(signals, cost_per_trade=0.001)

    expected_columns = {
        "asset_return",
        "position",
        "trade_flag",
        "transaction_cost",
        "gross_strategy_return",
        "net_strategy_return",
        "equity_asset",
        "equity_strategy_gross",
        "equity_strategy_net",
    }

    assert expected_columns.issubset(result.columns)
    assert not result.empty


def test_backtest_position_is_shifted_signal() -> None:
    events_df = make_enriched_events()
    prices_df = make_price_frame()

    signals = analyze_whale_flow(
        df=events_df,
        target_asset="ETH",
        window_hours=2,
        min_flow_usd=0.0,
        price_df=prices_df,
    )

    result = backtest_whale_strategy(signals, cost_per_trade=0.001)

    assert result["position"].iloc[0] == 0
    if len(result) > 1:
        assert result["position"].iloc[1] == result["signal"].iloc[0]


def test_backtest_rejects_missing_required_columns() -> None:
    bad_df = pd.DataFrame({"timestamp": ["2026-01-01 00:00:00+00:00"]})

    with pytest.raises(ValueError, match="Missing required columns"):
        backtest_whale_strategy(bad_df)