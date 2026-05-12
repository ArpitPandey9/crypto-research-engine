"""Flow-context helpers for the whale-flow mechanism layer.

This module converts basic source/destination/protocol context into cautious,
explainable interpretation labels for the dashboard.
"""


EXCHANGE_INFLOW = "Exchange Inflow"
EXCHANGE_OUTFLOW = "Exchange Outflow"
DEX_INTERACTION = "DEX Interaction"
BRIDGE_MOVEMENT = "Bridge Movement"
WALLET_TO_WALLET = "Wallet-to-Wallet"
UNKNOWN = "Unknown"

POSSIBLE_SELL_PRESSURE = "Possible Sell-Pressure Preparation"
POSSIBLE_CUSTODY_ACCUMULATION = "Possible Custody / Accumulation Movement"
PROTOCOL_MARKET_ACTION = "Protocol-Level Market Action"
CROSS_CHAIN_MOVEMENT = "Cross-Chain Movement"
UNKNOWN_INTERNAL_MOVEMENT = "Unknown / Possible Internal Movement"
INSUFFICIENT_CONTEXT = "Insufficient Context"

HIGH_CONFIDENCE = "High"
MEDIUM_CONFIDENCE = "Medium"
LOW_CONFIDENCE = "Low"


def _normalize(value: str | None) -> str:
    """Normalize optional string inputs for rule-based classification."""
    if value is None:
        return ""

    return value.strip().lower().replace("_", "-")


def classify_flow_context(
    source_type: str | None,
    destination_type: str | None,
    interaction_type: str | None = None,
) -> str:
    """Classify the high-level context of a whale-flow event.

    Args:
        source_type: Labeled source category such as wallet, exchange, or unknown.
        destination_type: Labeled destination category such as wallet, exchange, dex,
            bridge, or unknown.
        interaction_type: Optional protocol interaction label such as swap.

    Returns:
        A cautious flow-context label for downstream interpretation.
    """
    source = _normalize(source_type)
    destination = _normalize(destination_type)
    interaction = _normalize(interaction_type)

    if destination == "dex" or interaction in {"swap", "router", "pool"}:
        return DEX_INTERACTION

    if destination == "bridge" or interaction == "bridge":
        return BRIDGE_MOVEMENT

    if source == "wallet" and destination == "exchange":
        return EXCHANGE_INFLOW

    if source == "exchange" and destination == "wallet":
        return EXCHANGE_OUTFLOW

    if source == "wallet" and destination == "wallet":
        return WALLET_TO_WALLET

    return UNKNOWN


def infer_intent_label(flow_context: str) -> str:
    """Infer a cautious intent label from a flow-context label.

    Raises:
        ValueError: If the flow_context is not supported.
    """
    labels = {
        EXCHANGE_INFLOW: POSSIBLE_SELL_PRESSURE,
        EXCHANGE_OUTFLOW: POSSIBLE_CUSTODY_ACCUMULATION,
        DEX_INTERACTION: PROTOCOL_MARKET_ACTION,
        BRIDGE_MOVEMENT: CROSS_CHAIN_MOVEMENT,
        WALLET_TO_WALLET: UNKNOWN_INTERNAL_MOVEMENT,
        UNKNOWN: INSUFFICIENT_CONTEXT,
    }

    try:
        return labels[flow_context]
    except KeyError as exc:
        raise ValueError(f"Unsupported flow_context: {flow_context}") from exc


def assign_evidence_confidence(flow_context: str) -> str:
    """Assign evidence confidence for a flow-context label.

    Raises:
        ValueError: If the flow_context is not supported.
    """
    confidence = {
        DEX_INTERACTION: HIGH_CONFIDENCE,
        EXCHANGE_INFLOW: MEDIUM_CONFIDENCE,
        EXCHANGE_OUTFLOW: MEDIUM_CONFIDENCE,
        BRIDGE_MOVEMENT: MEDIUM_CONFIDENCE,
        WALLET_TO_WALLET: LOW_CONFIDENCE,
        UNKNOWN: LOW_CONFIDENCE,
    }

    try:
        return confidence[flow_context]
    except KeyError as exc:
        raise ValueError(f"Unsupported flow_context: {flow_context}") from exc


def build_flow_context_reason(
    flow_context: str,
    intent_label: str,
    evidence_confidence: str,
) -> str:
    """Build an explainable reason for a flow-context interpretation."""
    if flow_context == EXCHANGE_INFLOW:
        return (
            f"{flow_context} suggests {intent_label} with "
            f"{evidence_confidence} evidence confidence because value moved toward "
            "an exchange-labeled destination, but this does not confirm selling."
        )

    if flow_context == EXCHANGE_OUTFLOW:
        return (
            f"{flow_context} suggests {intent_label} with "
            f"{evidence_confidence} evidence confidence because value moved out of "
            "an exchange-labeled source, but this does not confirm accumulation."
        )

    if flow_context == DEX_INTERACTION:
        return (
            f"{flow_context} suggests {intent_label} with "
            f"{evidence_confidence} evidence confidence because the event interacted "
            "with a known protocol, router, or pool, but it does not prove full "
            "economic intent."
        )

    if flow_context == BRIDGE_MOVEMENT:
        return (
            f"{flow_context} suggests {intent_label} with "
            f"{evidence_confidence} evidence confidence because value appears to "
            "move across chains rather than directly into a market venue."
        )

    if flow_context == WALLET_TO_WALLET:
        return (
            f"{flow_context} suggests {intent_label} with "
            f"{evidence_confidence} evidence confidence because movement alone does "
            "not reveal whether the transfer was internal, OTC, custody-related, "
            "or market-directed."
        )

    if flow_context == UNKNOWN:
        return (
            f"{flow_context} suggests {intent_label} with "
            f"{evidence_confidence} evidence confidence because the system does not "
            "have enough labeled context to infer intent."
        )

    raise ValueError(f"Unsupported flow_context: {flow_context}")