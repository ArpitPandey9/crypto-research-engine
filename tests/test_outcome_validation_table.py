import pandas as pd
import pytest

from src.analytics.outcome_validation_table import build_outcome_validation_table


def _events_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": "2026-01-01 00:00:00+00:00",
                "asset_type": "ETH",
                "amount": 10.0,
                "sender_address": "0xaaa",
                "receiver_address": "0xbbb",
                "price_usd": 100.0,
                "true_usd_volume": 1_000.0,
            }
        ]
    )


def _prices_df(
    eth_6h: float = 105.0,
    eth_24h: float = 110.0,
    btc_6h: float = 102.0,
    btc_24h: float = 103.0,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": "2026-01-01 00:00:00+00:00",
                "asset_type": "ETH",
                "price_usd": 100.0,
            },
            {
                "timestamp": "2026-01-01 06:00:00+00:00",
                "asset_type": "ETH",
                "price_usd": eth_6h,
            },
            {
                "timestamp": "2026-01-02 00:00:00+00:00",
                "asset_type": "ETH",
                "price_usd": eth_24h,
            },
            {
                "timestamp": "2026-01-01 00:00:00+00:00",
                "asset_type": "BTC",
                "price_usd": 100.0,
            },
            {
                "timestamp": "2026-01-01 06:00:00+00:00",
                "asset_type": "BTC",
                "price_usd": btc_6h,
            },
            {
                "timestamp": "2026-01-02 00:00:00+00:00",
                "asset_type": "BTC",
                "price_usd": btc_24h,
            },
        ]
    )


def test_build_outcome_validation_table_labels_supported_signal():
    result = build_outcome_validation_table(
        events_df=_events_df(),
        prices_df=_prices_df(),
        target_asset="ETH",
        benchmark_asset="BTC",
        min_flow_usd=0.0,
    )

    assert len(result) == 1
    row = result.iloc[0]

    assert row["signal_direction"] == "positive"
    assert row["6h_abnormal_return"] == pytest.approx(0.03)
    assert row["24h_abnormal_return"] == pytest.approx(0.07)
    assert row["6h_label"] == "worked"
    assert row["24h_label"] == "worked"
    assert row["overall_label"] == "worked"
    assert row["evidence_quality"] == "strong"
    assert row["failure_mode"] == "no_failure"


def test_build_outcome_validation_table_labels_unsupported_signal():
    result = build_outcome_validation_table(
        events_df=_events_df(),
        prices_df=_prices_df(
            eth_6h=101.0,
            eth_24h=101.0,
            btc_6h=103.0,
            btc_24h=105.0,
        ),
        target_asset="ETH",
        benchmark_asset="BTC",
        min_flow_usd=0.0,
    )

    row = result.iloc[0]

    assert row["6h_abnormal_return"] == pytest.approx(-0.02)
    assert row["24h_abnormal_return"] == pytest.approx(-0.04)
    assert row["6h_label"] == "failed"
    assert row["24h_label"] == "failed"
    assert row["overall_label"] == "failed"
    assert row["evidence_quality"] == "strong"
    assert row["failure_mode"] == "unsupported_signal"


def test_build_outcome_validation_table_marks_missing_future_prices_unavailable():
    prices = _prices_df().query(
        "timestamp in ['2026-01-01 00:00:00+00:00']"
    ).copy()

    result = build_outcome_validation_table(
        events_df=_events_df(),
        prices_df=prices,
        target_asset="ETH",
        benchmark_asset="BTC",
        min_flow_usd=0.0,
    )

    row = result.iloc[0]

    assert row["6h_label"] == "data_unavailable"
    assert row["24h_label"] == "data_unavailable"
    assert row["overall_label"] == "data_unavailable"
    assert row["evidence_quality"] == "unavailable"
    assert row["failure_mode"] == "data_unavailable"


def test_build_outcome_validation_table_returns_empty_when_threshold_blocks_signal():
    result = build_outcome_validation_table(
        events_df=_events_df(),
        prices_df=_prices_df(),
        target_asset="ETH",
        benchmark_asset="BTC",
        min_flow_usd=10_000_000.0,
    )

    assert result.empty
    assert "overall_label" in result.columns


def test_build_outcome_validation_table_rejects_missing_price_columns():
    bad_prices = pd.DataFrame(
        [
            {
                "timestamp": "2026-01-01 00:00:00+00:00",
                "asset_type": "ETH",
            }
        ]
    )

    with pytest.raises(ValueError, match="Missing required price columns"):
        build_outcome_validation_table(
            events_df=_events_df(),
            prices_df=bad_prices,
            target_asset="ETH",
            benchmark_asset="BTC",
        )


def test_build_outcome_validation_table_requires_6h_and_24h_horizons():
    with pytest.raises(ValueError, match="horizons must include 6 and 24"):
        build_outcome_validation_table(
            events_df=_events_df(),
            prices_df=_prices_df(),
            target_asset="ETH",
            benchmark_asset="BTC",
            horizons=(6,),
        )
