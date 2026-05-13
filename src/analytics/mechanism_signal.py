"""Dashboard-ready mechanism signal builder for whale-flow interpretation.

This module combines liquidity-risk context and flow-context interpretation into
one explainable research output. It is intentionally conservative: the goal is
to support interpretation, not to claim certainty about whale intent.
"""

from dataclasses import dataclass

from src.analytics.flow_context import (
    assign_evidence_confidence,
    build_flow_context_reason,
    classify_flow_context,
    infer_intent_label,
)
from src.analytics.liquidity_risk import (
    calculate_size_ratio,
    classify_price_impact_risk,
)


SUPPORTED_VOLATILITY_REGIMES = {"normal", "elevated", "extreme"}


@dataclass(frozen=True)
class MechanismSignal:
    """Structured dashboard output for a whale-flow mechanism interpretation."""

    size_ratio: float
    price_impact_risk: str
    flow_context: str
    intent_label: str
    evidence_confidence: str
    volatility_regime: str
    signal_reliability: str
    reason: str


def _normalize_volatility_regime(volatility_regime: str | None) -> str:
    """Normalize and validate the volatility-regime input."""
    if volatility_regime is None:
        raise ValueError("Unsupported volatility_regime: None")

    normalized = volatility_regime.strip().lower().replace("_", "-")

    if normalized not in SUPPORTED_VOLATILITY_REGIMES:
        raise ValueError(f"Unsupported volatility_regime: {volatility_regime}")

    return normalized


def classify_signal_reliability(
    flow_context: str,
    size_ratio: float,
    volatility_regime: str,
) -> str:
    """Classify how decision-useful the signal is in the current regime.

    Reliability is intentionally separate from price-impact risk.

    A signal can have high price-impact risk but reduced reliability when the
    market regime is noisy, because the observed price behavior may be driven by
    liquidations, panic, macro shocks, or broader liquidity stress rather than
    whale-flow alone.
    """
    volatility = _normalize_volatility_regime(volatility_regime)

    if size_ratio < 0:
        raise ValueError("size_ratio cannot be negative")

    if volatility == "extreme":
        return "Reduced"

    if flow_context == "Unknown":
        return "Low"

    if flow_context == "Wallet-to-Wallet":
        return "Low-Medium"

    if size_ratio < 0.01:
        return "Low-Medium"

    if flow_context == "DEX Interaction" and size_ratio >= 0.05:
        return "High"

    if flow_context == "Exchange Inflow" and size_ratio >= 0.05:
        return "Medium-High"

    if flow_context == "Exchange Outflow" and size_ratio >= 0.05:
        return "Medium"

    return "Medium"


def _build_mechanism_reason(
    flow_context_reason: str,
    size_ratio: float,
    price_impact_risk: str,
    volatility_regime: str,
    signal_reliability: str,
) -> str:
    """Build one explainable reason string for dashboard display."""
    size_ratio_pct = size_ratio * 100

    if volatility_regime == "extreme":
        volatility_reason = (
            "The market is in an extreme volatility regime, so reliability is "
            "reduced because price movement may be driven by broader market stress."
        )
    else:
        volatility_reason = (
            f"The volatility regime is {volatility_regime}, so the signal is not "
            "automatically reduced by extreme market noise."
        )

    return (
        f"{flow_context_reason} "
        f"Size ratio is {size_ratio_pct:.2f}%, which is classified as "
        f"{price_impact_risk}. "
        f"{volatility_reason} "
        f"Final signal reliability is {signal_reliability}."
    )


def build_mechanism_signal(
    whale_flow_usd: float,
    pool_depth_usd: float,
    source_type: str | None,
    destination_type: str | None,
    interaction_type: str | None = None,
    volatility_regime: str = "normal",
) -> MechanismSignal:
    """Build a dashboard-ready mechanism signal from whale-flow inputs.

    Args:
        whale_flow_usd: Signed or unsigned whale-flow value in USD.
        pool_depth_usd: Available liquidity or pool depth in USD.
        source_type: Labeled source category such as wallet or exchange.
        destination_type: Labeled destination category such as exchange, dex, or wallet.
        interaction_type: Optional protocol interaction label such as swap.
        volatility_regime: Market regime label: normal, elevated, or extreme.

    Returns:
        A structured mechanism signal containing labels and an explanation.
    """
    normalized_volatility = _normalize_volatility_regime(volatility_regime)

    size_ratio = calculate_size_ratio(
        whale_flow_usd=whale_flow_usd,
        pool_depth_usd=pool_depth_usd,
    )
    price_impact_risk = classify_price_impact_risk(size_ratio)

    flow_context = classify_flow_context(
        source_type=source_type,
        destination_type=destination_type,
        interaction_type=interaction_type,
    )
    intent_label = infer_intent_label(flow_context)
    evidence_confidence = assign_evidence_confidence(flow_context)

    signal_reliability = classify_signal_reliability(
        flow_context=flow_context,
        size_ratio=size_ratio,
        volatility_regime=normalized_volatility,
    )

    flow_context_reason = build_flow_context_reason(
        flow_context=flow_context,
        intent_label=intent_label,
        evidence_confidence=evidence_confidence,
    )

    reason = _build_mechanism_reason(
        flow_context_reason=flow_context_reason,
        size_ratio=size_ratio,
        price_impact_risk=price_impact_risk,
        volatility_regime=normalized_volatility,
        signal_reliability=signal_reliability,
    )

    return MechanismSignal(
        size_ratio=size_ratio,
        price_impact_risk=price_impact_risk,
        flow_context=flow_context,
        intent_label=intent_label,
        evidence_confidence=evidence_confidence,
        volatility_regime=normalized_volatility,
        signal_reliability=signal_reliability,
        reason=reason,
    )
