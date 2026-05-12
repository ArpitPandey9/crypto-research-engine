import pytest

from src.analytics.liquidity_risk import (
    calculate_size_ratio,
    classify_price_impact_risk,
)


def test_calculate_size_ratio_uses_absolute_flow_magnitude():
    assert calculate_size_ratio(2_000_000, 100_000_000) == pytest.approx(0.02)
    assert calculate_size_ratio(-2_000_000, 100_000_000) == pytest.approx(0.02)


@pytest.mark.parametrize(
    ("whale_flow_usd", "pool_depth_usd", "expected_ratio"),
    [
        (0, 100_000_000, 0.0),
        (500_000, 100_000_000, 0.005),
        (2_000_000, 100_000_000, 0.02),
        (7_500_000, 100_000_000, 0.075),
        (40_000_000, 100_000_000, 0.40),
    ],
)
def test_calculate_size_ratio(whale_flow_usd, pool_depth_usd, expected_ratio):
    assert calculate_size_ratio(whale_flow_usd, pool_depth_usd) == pytest.approx(
        expected_ratio
    )


@pytest.mark.parametrize(
    ("pool_depth_usd", "expected_error"),
    [
        (0, "pool_depth_usd must be greater than zero"),
        (-1, "pool_depth_usd must be greater than zero"),
    ],
)
def test_calculate_size_ratio_rejects_invalid_pool_depth(
    pool_depth_usd, expected_error
):
    with pytest.raises(ValueError, match=expected_error):
        calculate_size_ratio(1_000_000, pool_depth_usd)


@pytest.mark.parametrize(
    ("size_ratio", "expected_label"),
    [
        (0.0, "Low Price-Impact Risk / Flow Likely Absorbed"),
        (0.0099, "Low Price-Impact Risk / Flow Likely Absorbed"),
        (0.01, "Medium Price-Impact Risk"),
        (0.0499, "Medium Price-Impact Risk"),
        (0.05, "High Price-Impact Risk"),
        (0.0999, "High Price-Impact Risk"),
        (0.10, "Extreme Price-Impact Risk"),
        (0.40, "Extreme Price-Impact Risk"),
    ],
)
def test_classify_price_impact_risk(size_ratio, expected_label):
    assert classify_price_impact_risk(size_ratio) == expected_label


@pytest.mark.parametrize("invalid_ratio", [-0.01, -1])
def test_classify_price_impact_risk_rejects_negative_ratio(invalid_ratio):
    with pytest.raises(ValueError, match="size_ratio cannot be negative"):
        classify_price_impact_risk(invalid_ratio)