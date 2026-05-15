from datetime import datetime, timezone

import pytest

from src.data.dexscreener_client import DexPoolDepth
from src.analytics.real_mechanism_signal import (
    RealMechanismSignalResult,
    build_real_mechanism_signal,
)


def make_pool(asset_symbol="ETH", liquidity_usd=100_000_000.0):
    return DexPoolDepth(
        fetched_at_utc=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        asset_symbol=asset_symbol,
        chain_id="ethereum",
        dex_id="uniswap",
        pair_address="0xpool",
        base_token_symbol="WETH" if asset_symbol == "ETH" else "WBTC",
        quote_token_symbol="USDC",
        price_usd=3000.0 if asset_symbol == "ETH" else 80000.0,
        liquidity_usd=liquidity_usd,
        liquidity_base=100.0,
        liquidity_quote=700_000.0,
        volume_h24=50_000.0,
        pair_url="https://dexscreener.com/ethereum/0xpool",
    )


def test_build_real_mechanism_signal_uses_real_pool_depth_without_fake_context():
    def fake_pool_lookup(asset_symbol, db_path=None):
        assert asset_symbol == "ETH"
        return make_pool(asset_symbol="ETH", liquidity_usd=100_000_000.0)

    result = build_real_mechanism_signal(
        asset_symbol="ETH",
        whale_flow_usd=18_000_000,
        volatility_regime="normal",
        pool_depth_lookup=fake_pool_lookup,
    )

    assert isinstance(result, RealMechanismSignalResult)
    assert result.is_available is True
    assert result.unavailable_reason is None
    assert result.pool_depth is not None
    assert result.signal is not None

    assert result.signal.size_ratio == pytest.approx(0.18)
    assert result.signal.price_impact_risk == "Extreme Price-Impact Risk"
    assert result.signal.flow_context == "Unknown"
    assert result.signal.intent_label == "Insufficient Context"
    assert result.signal.evidence_confidence == "Low"
    assert result.signal.signal_reliability == "Low"
    assert result.flow_context_note == (
        "Verified source/destination labels are not available yet; "
        "flow context is treated as Unknown instead of being inferred."
    )


def test_build_real_mechanism_signal_returns_unavailable_when_pool_depth_missing():
    def missing_pool_lookup(asset_symbol, db_path=None):
        return None

    result = build_real_mechanism_signal(
        asset_symbol="DOGE",
        whale_flow_usd=1_000_000,
        volatility_regime="normal",
        pool_depth_lookup=missing_pool_lookup,
    )

    assert result.is_available is False
    assert result.signal is None
    assert result.pool_depth is None
    assert result.unavailable_reason == (
        "Real pool-depth data is unavailable for DOGE. "
        "Run the DEX pool-depth ingestion pipeline before building this signal."
    )


def test_build_real_mechanism_signal_rejects_zero_whale_flow():
    def fake_pool_lookup(asset_symbol, db_path=None):
        return make_pool(asset_symbol="ETH")

    with pytest.raises(ValueError, match="whale_flow_usd must be non-zero"):
        build_real_mechanism_signal(
            asset_symbol="ETH",
            whale_flow_usd=0,
            volatility_regime="normal",
            pool_depth_lookup=fake_pool_lookup,
        )


def test_build_real_mechanism_signal_preserves_extreme_volatility_reduction():
    def fake_pool_lookup(asset_symbol, db_path=None):
        return make_pool(asset_symbol="ETH", liquidity_usd=100_000_000.0)

    result = build_real_mechanism_signal(
        asset_symbol="ETH",
        whale_flow_usd=20_000_000,
        volatility_regime="extreme",
        pool_depth_lookup=fake_pool_lookup,
    )

    assert result.is_available is True
    assert result.signal is not None
    assert result.signal.price_impact_risk == "Extreme Price-Impact Risk"
    assert result.signal.signal_reliability == "Reduced"
    assert "extreme volatility" in result.signal.reason


def test_build_real_mechanism_signal_normalizes_asset_symbol():
    def fake_pool_lookup(asset_symbol, db_path=None):
        assert asset_symbol == "ETH"
        return make_pool(asset_symbol="ETH")

    result = build_real_mechanism_signal(
        asset_symbol=" eth ",
        whale_flow_usd=5_000_000,
        volatility_regime="normal",
        pool_depth_lookup=fake_pool_lookup,
    )

    assert result.asset_symbol == "ETH"


def test_build_real_mechanism_signal_does_not_pass_none_db_path_to_lookup():
    calls = {}

    def strict_pool_lookup(asset_symbol):
        calls["asset_symbol"] = asset_symbol
        return make_pool(asset_symbol="ETH")

    result = build_real_mechanism_signal(
        asset_symbol="ETH",
        whale_flow_usd=5_000_000,
        volatility_regime="normal",
        pool_depth_lookup=strict_pool_lookup,
    )

    assert result.is_available is True
    assert calls == {"asset_symbol": "ETH"}
