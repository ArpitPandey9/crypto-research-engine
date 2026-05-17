import pandas as pd
import pytest

from src.analytics.volatility_regime import (
    ELEVATED_VOLATILITY_REGIME,
    EXTREME_VOLATILITY_REGIME,
    NORMAL_VOLATILITY_REGIME,
    VolatilityRegimeResult,
    build_volatility_regime,
    calculate_price_returns,
    classify_volatility_regime,
)


def test_calculate_price_returns_sorts_by_timestamp_and_uses_fractional_change():
    prices = pd.DataFrame(
        [
            {"timestamp": "2026-01-01 02:00:00+00:00", "price_usd": 121.0},
            {"timestamp": "2026-01-01 00:00:00+00:00", "price_usd": 100.0},
            {"timestamp": "2026-01-01 01:00:00+00:00", "price_usd": 110.0},
        ]
    )

    returns = calculate_price_returns(prices)

    assert list(returns.round(4)) == [0.10, 0.10]


@pytest.mark.parametrize(
    ("latest_volatility", "normal_threshold", "extreme_threshold", "expected"),
    [
        (0.01, 0.02, 0.05, NORMAL_VOLATILITY_REGIME),
        (0.03, 0.02, 0.05, ELEVATED_VOLATILITY_REGIME),
        (0.08, 0.02, 0.05, EXTREME_VOLATILITY_REGIME),
    ],
)
def test_classify_volatility_regime_uses_thresholds(
    latest_volatility,
    normal_threshold,
    extreme_threshold,
    expected,
):
    assert (
        classify_volatility_regime(
            latest_volatility=latest_volatility,
            normal_threshold=normal_threshold,
            extreme_threshold=extreme_threshold,
        )
        == expected
    )


def test_build_volatility_regime_returns_unavailable_when_not_enough_data():
    prices = pd.DataFrame(
        [
            {"timestamp": "2026-01-01 00:00:00+00:00", "price_usd": 100.0},
            {"timestamp": "2026-01-01 01:00:00+00:00", "price_usd": 101.0},
        ]
    )

    result = build_volatility_regime(
        prices=prices,
        asset_symbol="ETH",
        window_size=3,
    )

    assert isinstance(result, VolatilityRegimeResult)
    assert result.asset_symbol == "ETH"
    assert result.is_available is False
    assert result.volatility_regime == "unavailable"
    assert "Not enough price returns" in result.reason


def test_build_volatility_regime_detects_extreme_latest_market_weather():
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

    prices = pd.DataFrame(
        [
            {
                "timestamp": f"2026-01-01 {hour:02d}:00:00+00:00",
                "price_usd": price,
            }
            for hour, price in enumerate(all_prices)
        ]
    )

    result = build_volatility_regime(
        prices=prices,
        asset_symbol="ETH",
        window_size=3,
    )

    assert result.is_available is True
    assert result.asset_symbol == "ETH"
    assert result.volatility_regime == EXTREME_VOLATILITY_REGIME
    assert result.latest_realized_volatility is not None
    assert result.latest_realized_volatility > result.extreme_threshold
    assert "extreme" in result.reason.lower()


def test_build_volatility_regime_rejects_non_positive_prices():
    prices = pd.DataFrame(
        [
            {"timestamp": "2026-01-01 00:00:00+00:00", "price_usd": 100.0},
            {"timestamp": "2026-01-01 01:00:00+00:00", "price_usd": 0.0},
            {"timestamp": "2026-01-01 02:00:00+00:00", "price_usd": 101.0},
            {"timestamp": "2026-01-01 03:00:00+00:00", "price_usd": 102.0},
        ]
    )

    with pytest.raises(ValueError, match="price_usd must be greater than zero"):
        build_volatility_regime(
            prices=prices,
            asset_symbol="ETH",
            window_size=2,
        )
