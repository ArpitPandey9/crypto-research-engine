import pytest

from src.analytics.mechanism_signal import (
    MechanismSignal,
    build_mechanism_signal,
    classify_signal_reliability,
)


def test_build_mechanism_signal_for_exchange_inflow_extreme_ratio():
    signal = build_mechanism_signal(
        whale_flow_usd=18_000_000,
        pool_depth_usd=100_000_000,
        source_type="wallet",
        destination_type="exchange",
        volatility_regime="normal",
    )

    assert isinstance(signal, MechanismSignal)
    assert signal.size_ratio == pytest.approx(0.18)
    assert signal.price_impact_risk == "Extreme Price-Impact Risk"
    assert signal.flow_context == "Exchange Inflow"
    assert signal.intent_label == "Possible Sell-Pressure Preparation"
    assert signal.evidence_confidence == "Medium"
    assert signal.volatility_regime == "normal"
    assert signal.signal_reliability == "Medium-High"
    assert "exchange-labeled destination" in signal.reason
    assert "Extreme Price-Impact Risk" in signal.reason


def test_build_mechanism_signal_for_dex_interaction_extreme_volatility():
    signal = build_mechanism_signal(
        whale_flow_usd=22_000_000,
        pool_depth_usd=100_000_000,
        source_type="wallet",
        destination_type="dex",
        interaction_type="swap",
        volatility_regime="extreme",
    )

    assert signal.size_ratio == pytest.approx(0.22)
    assert signal.price_impact_risk == "Extreme Price-Impact Risk"
    assert signal.flow_context == "DEX Interaction"
    assert signal.intent_label == "Protocol-Level Market Action"
    assert signal.evidence_confidence == "High"
    assert signal.signal_reliability == "Reduced"
    assert "known protocol" in signal.reason
    assert "extreme volatility" in signal.reason


def test_build_mechanism_signal_for_wallet_to_wallet_low_ratio():
    signal = build_mechanism_signal(
        whale_flow_usd=800_000,
        pool_depth_usd=100_000_000,
        source_type="wallet",
        destination_type="wallet",
        volatility_regime="normal",
    )

    assert signal.size_ratio == pytest.approx(0.008)
    assert signal.price_impact_risk == "Low Price-Impact Risk / Flow Likely Absorbed"
    assert signal.flow_context == "Wallet-to-Wallet"
    assert signal.intent_label == "Unknown / Possible Internal Movement"
    assert signal.evidence_confidence == "Low"
    assert signal.signal_reliability == "Low-Medium"
    assert "movement alone" in signal.reason


@pytest.mark.parametrize(
    ("flow_context", "size_ratio", "volatility_regime", "expected_reliability"),
    [
        ("DEX Interaction", 0.20, "normal", "High"),
        ("Exchange Inflow", 0.20, "normal", "Medium-High"),
        ("Exchange Outflow", 0.20, "normal", "Medium"),
        ("Wallet-to-Wallet", 0.20, "normal", "Low-Medium"),
        ("Unknown", 0.20, "normal", "Low"),
        ("DEX Interaction", 0.20, "extreme", "Reduced"),
        ("Exchange Inflow", 0.005, "normal", "Low-Medium"),
    ],
)
def test_classify_signal_reliability(
    flow_context, size_ratio, volatility_regime, expected_reliability
):
    assert (
        classify_signal_reliability(
            flow_context=flow_context,
            size_ratio=size_ratio,
            volatility_regime=volatility_regime,
        )
        == expected_reliability
    )


@pytest.mark.parametrize("bad_volatility", ["", "quiet", "panic"])
def test_build_mechanism_signal_rejects_unsupported_volatility_regime(bad_volatility):
    with pytest.raises(ValueError, match="Unsupported volatility_regime"):
        build_mechanism_signal(
            whale_flow_usd=1_000_000,
            pool_depth_usd=100_000_000,
            source_type="wallet",
            destination_type="exchange",
            volatility_regime=bad_volatility,
        )
