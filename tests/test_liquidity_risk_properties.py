import pytest
from hypothesis import given, strategies as st

from src.analytics.liquidity_risk import calculate_size_ratio


positive_usd_values = st.floats(
    min_value=1.0,
    max_value=1_000_000_000_000.0,
    allow_nan=False,
    allow_infinity=False,
)

whale_flow_values = st.floats(
    min_value=-1_000_000_000_000.0,
    max_value=1_000_000_000_000.0,
    allow_nan=False,
    allow_infinity=False,
)


@given(
    whale_flow_usd=whale_flow_values,
    pool_depth_usd=positive_usd_values,
)
def test_size_ratio_is_never_negative_when_pool_depth_is_positive(
    whale_flow_usd,
    pool_depth_usd,
):
    size_ratio = calculate_size_ratio(
        whale_flow_usd=whale_flow_usd,
        pool_depth_usd=pool_depth_usd,
    )

    assert size_ratio >= 0


@given(
    whale_flow_usd=positive_usd_values,
    pool_depth_usd=positive_usd_values,
)
def test_size_ratio_uses_flow_magnitude_not_direction(
    whale_flow_usd,
    pool_depth_usd,
):
    positive_ratio = calculate_size_ratio(
        whale_flow_usd=whale_flow_usd,
        pool_depth_usd=pool_depth_usd,
    )
    negative_ratio = calculate_size_ratio(
        whale_flow_usd=-whale_flow_usd,
        pool_depth_usd=pool_depth_usd,
    )

    assert positive_ratio == pytest.approx(negative_ratio)


@given(
    smaller_flow_usd=positive_usd_values,
    extra_flow_usd=positive_usd_values,
    pool_depth_usd=positive_usd_values,
)
def test_size_ratio_does_not_decrease_when_flow_magnitude_increases(
    smaller_flow_usd,
    extra_flow_usd,
    pool_depth_usd,
):
    larger_flow_usd = smaller_flow_usd + extra_flow_usd

    smaller_ratio = calculate_size_ratio(
        whale_flow_usd=smaller_flow_usd,
        pool_depth_usd=pool_depth_usd,
    )
    larger_ratio = calculate_size_ratio(
        whale_flow_usd=larger_flow_usd,
        pool_depth_usd=pool_depth_usd,
    )

    assert larger_ratio >= smaller_ratio


@given(
    whale_flow_usd=positive_usd_values,
    smaller_pool_depth_usd=positive_usd_values,
    extra_pool_depth_usd=positive_usd_values,
)
def test_size_ratio_does_not_increase_when_pool_depth_increases(
    whale_flow_usd,
    smaller_pool_depth_usd,
    extra_pool_depth_usd,
):
    larger_pool_depth_usd = smaller_pool_depth_usd + extra_pool_depth_usd

    smaller_pool_ratio = calculate_size_ratio(
        whale_flow_usd=whale_flow_usd,
        pool_depth_usd=smaller_pool_depth_usd,
    )
    larger_pool_ratio = calculate_size_ratio(
        whale_flow_usd=whale_flow_usd,
        pool_depth_usd=larger_pool_depth_usd,
    )

    assert larger_pool_ratio <= smaller_pool_ratio
