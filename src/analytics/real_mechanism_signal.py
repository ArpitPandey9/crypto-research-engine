"""Real-data adapter for building whale-flow mechanism signals.

This module connects the mechanism-signal engine to real pool-depth data stored
in SQLite. It intentionally avoids fake source/destination labels. Until a
verified address-label pipeline exists, flow context is treated as Unknown.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.analytics.mechanism_signal import MechanismSignal, build_mechanism_signal
from src.data.dexscreener_client import DexPoolDepth
from src.data.pool_depth_repository import get_latest_pool_depth


UNKNOWN_FLOW_CONTEXT_NOTE = (
    "Verified source/destination labels are not available yet; "
    "flow context is treated as Unknown instead of being inferred."
)


@dataclass(frozen=True)
class RealMechanismSignalResult:
    """Result wrapper for a real-data mechanism signal."""

    asset_symbol: str
    is_available: bool
    signal: MechanismSignal | None
    pool_depth: DexPoolDepth | None
    unavailable_reason: str | None
    flow_context_note: str


def _normalize_asset_symbol(asset_symbol: str) -> str:
    """Normalize an asset symbol for consistent lookup and display."""
    normalized = asset_symbol.strip().upper()

    if not normalized:
        raise ValueError("asset_symbol cannot be empty")

    return normalized


def _validate_whale_flow(whale_flow_usd: float) -> None:
    """Reject zero whale-flow values because they do not represent whale flow."""
    if whale_flow_usd == 0:
        raise ValueError("whale_flow_usd must be non-zero")


def build_real_mechanism_signal(
    asset_symbol: str,
    whale_flow_usd: float,
    volatility_regime: str,
    *,
    db_path: Path | None = None,
    pool_depth_lookup: Callable[..., DexPoolDepth | None] = get_latest_pool_depth,
) -> RealMechanismSignalResult:
    """Build a real-data mechanism signal using stored DEX pool-depth data.

    The function uses real pool-depth data from SQLite. If pool depth is missing,
    it returns an unavailable result instead of creating fake liquidity.

    Flow context remains Unknown until a verified address-label pipeline exists.
    This prevents the dashboard from presenting unverified wallet/exchange/DEX
    interpretations as facts.
    """
    normalized_asset = _normalize_asset_symbol(asset_symbol)
    _validate_whale_flow(whale_flow_usd)

    if db_path is None:
        pool_depth = pool_depth_lookup(normalized_asset)
    else:
        pool_depth = pool_depth_lookup(normalized_asset, db_path=db_path)

    if pool_depth is None:
        return RealMechanismSignalResult(
            asset_symbol=normalized_asset,
            is_available=False,
            signal=None,
            pool_depth=None,
            unavailable_reason=(
                f"Real pool-depth data is unavailable for {normalized_asset}. "
                "Run the DEX pool-depth ingestion pipeline before building this signal."
            ),
            flow_context_note=UNKNOWN_FLOW_CONTEXT_NOTE,
        )

    signal = build_mechanism_signal(
        whale_flow_usd=whale_flow_usd,
        pool_depth_usd=pool_depth.liquidity_usd,
        source_type=None,
        destination_type=None,
        interaction_type=None,
        volatility_regime=volatility_regime,
    )

    return RealMechanismSignalResult(
        asset_symbol=normalized_asset,
        is_available=True,
        signal=signal,
        pool_depth=pool_depth,
        unavailable_reason=None,
        flow_context_note=UNKNOWN_FLOW_CONTEXT_NOTE,
    )
