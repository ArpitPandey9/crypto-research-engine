import pytest

from src.analytics.flow_context import (
    classify_flow_context,
    infer_intent_label,
    assign_evidence_confidence,
    build_flow_context_reason,
)


@pytest.mark.parametrize(
    ("source_type", "destination_type", "interaction_type", "expected_context"),
    [
        ("wallet", "exchange", None, "Exchange Inflow"),
        ("exchange", "wallet", None, "Exchange Outflow"),
        ("wallet", "dex", "swap", "DEX Interaction"),
        ("wallet", "bridge", None, "Bridge Movement"),
        ("wallet", "wallet", None, "Wallet-to-Wallet"),
        ("unknown", "unknown", None, "Unknown"),
    ],
)
def test_classify_flow_context(
    source_type, destination_type, interaction_type, expected_context
):
    assert (
        classify_flow_context(
            source_type=source_type,
            destination_type=destination_type,
            interaction_type=interaction_type,
        )
        == expected_context
    )


@pytest.mark.parametrize(
    ("flow_context", "expected_label"),
    [
        ("Exchange Inflow", "Possible Sell-Pressure Preparation"),
        ("Exchange Outflow", "Possible Custody / Accumulation Movement"),
        ("DEX Interaction", "Protocol-Level Market Action"),
        ("Bridge Movement", "Cross-Chain Movement"),
        ("Wallet-to-Wallet", "Unknown / Possible Internal Movement"),
        ("Unknown", "Insufficient Context"),
    ],
)
def test_infer_intent_label(flow_context, expected_label):
    assert infer_intent_label(flow_context) == expected_label


@pytest.mark.parametrize(
    ("flow_context", "expected_confidence"),
    [
        ("DEX Interaction", "High"),
        ("Exchange Inflow", "Medium"),
        ("Exchange Outflow", "Medium"),
        ("Bridge Movement", "Medium"),
        ("Wallet-to-Wallet", "Low"),
        ("Unknown", "Low"),
    ],
)
def test_assign_evidence_confidence(flow_context, expected_confidence):
    assert assign_evidence_confidence(flow_context) == expected_confidence


def test_build_flow_context_reason_for_exchange_inflow():
    reason = build_flow_context_reason(
        flow_context="Exchange Inflow",
        intent_label="Possible Sell-Pressure Preparation",
        evidence_confidence="Medium",
    )

    assert "exchange-labeled destination" in reason
    assert "does not confirm selling" in reason


def test_build_flow_context_reason_for_dex_interaction():
    reason = build_flow_context_reason(
        flow_context="DEX Interaction",
        intent_label="Protocol-Level Market Action",
        evidence_confidence="High",
    )

    assert "known protocol" in reason
    assert "does not prove full economic intent" in reason


def test_unknown_flow_context_rejects_unsupported_context():
    with pytest.raises(ValueError, match="Unsupported flow_context"):
        infer_intent_label("Unsupported Context")


def test_unknown_confidence_rejects_unsupported_context():
    with pytest.raises(ValueError, match="Unsupported flow_context"):
        assign_evidence_confidence("Unsupported Context")