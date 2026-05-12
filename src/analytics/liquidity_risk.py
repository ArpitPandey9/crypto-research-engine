"""Liquidity-risk helpers for the whale-flow mechanism layer.

This module converts whale-flow size and liquidity depth into transparent
price-impact risk labels. The goal is not to predict price perfectly. The goal
is to provide simple, explainable market-structure context for the dashboard.
"""


LOW_PRICE_IMPACT_RISK = "Low Price-Impact Risk / Flow Likely Absorbed"
MEDIUM_PRICE_IMPACT_RISK = "Medium Price-Impact Risk"
HIGH_PRICE_IMPACT_RISK = "High Price-Impact Risk"
EXTREME_PRICE_IMPACT_RISK = "Extreme Price-Impact Risk"


def calculate_size_ratio(whale_flow_usd: float, pool_depth_usd: float) -> float:
    """Calculate whale-flow size relative to available liquidity depth.

    The ratio uses absolute whale-flow magnitude because price-impact risk
    depends on trade/flow size relative to liquidity, not on directional sign.

    Args:
        whale_flow_usd: Signed or unsigned whale-flow value in USD.
        pool_depth_usd: Available liquidity or pool depth in USD.

    Returns:
        Absolute whale-flow size divided by pool depth.

    Raises:
        ValueError: If pool_depth_usd is less than or equal to zero.
    """
    if pool_depth_usd <= 0:
        raise ValueError("pool_depth_usd must be greater than zero")

    return abs(whale_flow_usd) / pool_depth_usd


def classify_price_impact_risk(size_ratio: float) -> str:
    """Classify price-impact risk from a size ratio.

    Thresholds are intentionally simple and transparent:

    - < 1%: low price-impact risk / likely absorbed
    - 1% to < 5%: medium price-impact risk
    - 5% to < 10%: high price-impact risk
    - >= 10%: extreme price-impact risk

    Args:
        size_ratio: Absolute whale-flow value divided by pool depth.

    Returns:
        Human-readable price-impact risk label.

    Raises:
        ValueError: If size_ratio is negative.
    """
    if size_ratio < 0:
        raise ValueError("size_ratio cannot be negative")

    if size_ratio < 0.01:
        return LOW_PRICE_IMPACT_RISK

    if size_ratio < 0.05:
        return MEDIUM_PRICE_IMPACT_RISK

    if size_ratio < 0.10:
        return HIGH_PRICE_IMPACT_RISK

    return EXTREME_PRICE_IMPACT_RISK