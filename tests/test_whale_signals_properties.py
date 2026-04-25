# tests/test_whale_signals_properties.py

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, strategies as st

from src.strategies.whale_signals import analyze_whale_flow, backtest_whale_strategy


def make_enriched_events() -> pd.DataFrame:
    """
    Deterministic enriched-whale dataset for scenario tests.
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
    Market-price table similar to historical_prices.
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


@pytest.mark.parametrize(
    ("target_asset", "expected_first_price"),
    [
        ("ETH", 3000.0),
        ("WBTC", 60000.0),
    ],
)
def test_target_asset_uses_correct_market_series(
    target_asset: str,
    expected_first_price: float,
) -> None:
    events_df = make_enriched_events()
    prices_df = make_price_frame()

    result = analyze_whale_flow(
        df=events_df,
        target_asset=target_asset,
        window_hours=2,
        min_flow_usd=0.0,
        price_df=prices_df,
    )

    assert not result.empty
    assert set(result["target_asset"].unique()) == {target_asset}
    assert float(result["price_usd"].iloc[0]) == expected_first_price


@pytest.mark.parametrize(
    ("min_flow_usd", "expected_all_flat"),
    [
        (0.0, False),
        (1_000_000.0, True),
    ],
)
def test_signal_threshold_behavior(
    min_flow_usd: float,
    expected_all_flat: bool,
) -> None:
    events_df = make_enriched_events()
    prices_df = make_price_frame()

    result = analyze_whale_flow(
        df=events_df,
        target_asset="ETH",
        window_hours=2,
        min_flow_usd=min_flow_usd,
        price_df=prices_df,
    )

    assert not result.empty
    if expected_all_flat:
        assert (result["signal"] == 0).all()
    else:
        assert (result["signal"] != 0).any()


def test_analyze_whale_flow_sorts_output_timestamps() -> None:
    events_df = make_enriched_events().sample(frac=1.0, random_state=42).reset_index(drop=True)
    prices_df = make_price_frame().sample(frac=1.0, random_state=42).reset_index(drop=True)

    result = analyze_whale_flow(
        df=events_df,
        target_asset="ETH",
        window_hours=2,
        min_flow_usd=0.0,
        price_df=prices_df,
    )

    timestamps = pd.to_datetime(result["timestamp"], utc=True)
    assert timestamps.is_monotonic_increasing


def test_missing_market_series_raises_clear_error() -> None:
    events_df = make_enriched_events()
    bad_prices_df = pd.DataFrame(
        [
            {"timestamp": "2026-01-01 00:00:00+00:00", "asset_type": "ETH", "price_usd": 3000.0},
            {"timestamp": "2026-01-01 01:00:00+00:00", "asset_type": "ETH", "price_usd": 3100.0},
        ]
    )

    with pytest.raises(ValueError, match="expected market series: BTC"):
        analyze_whale_flow(
            df=events_df,
            target_asset="WBTC",
            window_hours=2,
            min_flow_usd=0.0,
            price_df=bad_prices_df,
        )


@st.composite
def backtest_input_frames(draw) -> pd.DataFrame:
    """
    Build random but valid backtest inputs for property-based testing.
    """
    n = draw(st.integers(min_value=3, max_value=30))

    prices = draw(
        st.lists(
            st.floats(
                min_value=1.0,
                max_value=10000.0,
                allow_nan=False,
                allow_infinity=False,
            ),
            min_size=n,
            max_size=n,
        )
    )

    signals = draw(
        st.lists(
            st.sampled_from([-1, 0, 1]),
            min_size=n,
            max_size=n,
        )
    )

    rolling_flows = draw(
        st.lists(
            st.floats(
                min_value=-1_000_000.0,
                max_value=1_000_000.0,
                allow_nan=False,
                allow_infinity=False,
            ),
            min_size=n,
            max_size=n,
        )
    )

    timestamps = pd.date_range("2026-01-01 00:00:00", periods=n, freq="h", tz="UTC")

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "target_asset": ["ETH"] * n,
            "price_usd": prices,
            "signal": signals,
            "rolling_net_flow": rolling_flows,
        }
    )


@given(df=backtest_input_frames())
def test_backtest_invariants_hold_for_generated_inputs(df: pd.DataFrame) -> None:
    result = backtest_whale_strategy(df, cost_per_trade=0.001)

    assert len(result) == len(df)
    assert result["position"].iloc[0] == 0

    expected_positions = df["signal"].shift(1).fillna(0).astype(int).tolist()
    assert result["position"].tolist() == expected_positions

    assert set(result["trade_flag"].dropna().unique()).issubset({0, 1})

    rounded_costs = {round(float(x), 6) for x in result["transaction_cost"].dropna().unique()}
    assert rounded_costs.issubset({0.0, 0.001})

    required_cols = [
        "asset_return",
        "position",
        "trade_flag",
        "transaction_cost",
        "gross_strategy_return",
        "net_strategy_return",
        "equity_asset",
        "equity_strategy_gross",
        "equity_strategy_net",
    ]
    assert result[required_cols].notna().all().all()
    assert np.isfinite(result[required_cols].to_numpy()).all()


@given(df=backtest_input_frames())
def test_backtest_signal_and_position_domain_is_valid(df: pd.DataFrame) -> None:
    result = backtest_whale_strategy(df, cost_per_trade=0.0)

    assert set(result["signal"].unique()).issubset({-1, 0, 1})
    assert set(result["position"].unique()).issubset({-1, 0, 1})


@given(df=backtest_input_frames())
def test_backtest_sorts_rows_by_timestamp(df: pd.DataFrame) -> None:
    shuffled = df.sample(frac=1.0).reset_index(drop=True)
    result = backtest_whale_strategy(shuffled, cost_per_trade=0.001)

    timestamps = pd.to_datetime(result["timestamp"], utc=True)
    assert timestamps.is_monotonic_increasing