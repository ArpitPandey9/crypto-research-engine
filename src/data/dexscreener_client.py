"""DEX Screener client for real DEX pool-depth ingestion.

This module fetches live pair/liquidity data from the public DEX Screener API.
It does not create fake pool-depth values. If the API cannot provide usable
liquidity data, the caller receives a clear error.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import requests


DEXSCREENER_BASE_URL = "https://api.dexscreener.com"
DEFAULT_TIMEOUT_SECONDS = 10

TOKEN_CONFIGS = {
    "ETH": {
        "chain_id": "ethereum",
        "token_address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "token_symbol": "WETH",
    },
    "WBTC": {
        "chain_id": "ethereum",
        "token_address": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        "token_symbol": "WBTC",
    },
}


class DexScreenerError(RuntimeError):
    """Raised when DEX Screener data cannot be fetched or parsed safely."""


@dataclass(frozen=True)
class DexPoolDepth:
    """Normalized real DEX pool-depth record."""

    fetched_at_utc: datetime
    asset_symbol: str
    chain_id: str
    dex_id: str
    pair_address: str
    base_token_symbol: str
    quote_token_symbol: str
    price_usd: float | None
    liquidity_usd: float
    liquidity_base: float | None
    liquidity_quote: float | None
    volume_h24: float | None
    pair_url: str | None


def _to_float(value: Any) -> float | None:
    """Convert API values to float while preserving missing values as None."""
    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_token_config(asset_symbol: str) -> dict[str, str]:
    """Return token config for a supported dashboard asset."""
    normalized_symbol = asset_symbol.strip().upper()

    try:
        return TOKEN_CONFIGS[normalized_symbol]
    except KeyError as exc:
        supported = ", ".join(sorted(TOKEN_CONFIGS))
        raise ValueError(
            f"Unsupported asset_symbol: {asset_symbol}. Supported assets: {supported}"
        ) from exc


def fetch_token_pairs(
    asset_symbol: str,
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    http_get: Callable[..., Any] = requests.get,
) -> list[dict[str, Any]]:
    """Fetch real DEX Screener token pairs for a supported asset.

    Args:
        asset_symbol: Supported dashboard asset symbol such as ETH or WBTC.
        timeout: Request timeout in seconds.
        http_get: Injectable HTTP getter used by tests.

    Returns:
        Raw pair dictionaries from DEX Screener.

    Raises:
        ValueError: If the asset symbol is unsupported.
        DexScreenerError: If the request fails or response shape is unexpected.
    """
    config = _get_token_config(asset_symbol)
    chain_id = config["chain_id"]
    token_address = config["token_address"]

    url = f"{DEXSCREENER_BASE_URL}/token-pairs/v1/{chain_id}/{token_address}"
    response = http_get(url, timeout=timeout)

    if response.status_code != 200:
        raise DexScreenerError(
            f"DEX Screener request failed with status {response.status_code}: "
            f"{response.text}"
        )

    payload = response.json()

    if not isinstance(payload, list):
        raise DexScreenerError(
            f"Unexpected DEX Screener response for {asset_symbol}: expected list"
        )

    return payload


def _build_pool_depth(
    asset_symbol: str,
    pair: dict[str, Any],
    fetched_at_utc: datetime,
) -> DexPoolDepth:
    """Normalize one DEX Screener pair record into a DexPoolDepth object."""
    liquidity = pair.get("liquidity") or {}
    volume = pair.get("volume") or {}
    base_token = pair.get("baseToken") or {}
    quote_token = pair.get("quoteToken") or {}

    liquidity_usd = _to_float(liquidity.get("usd"))

    if liquidity_usd is None or liquidity_usd <= 0:
        raise DexScreenerError("Pair does not contain positive liquidity.usd")

    return DexPoolDepth(
        fetched_at_utc=fetched_at_utc,
        asset_symbol=asset_symbol.strip().upper(),
        chain_id=str(pair.get("chainId") or ""),
        dex_id=str(pair.get("dexId") or ""),
        pair_address=str(pair.get("pairAddress") or ""),
        base_token_symbol=str(base_token.get("symbol") or ""),
        quote_token_symbol=str(quote_token.get("symbol") or ""),
        price_usd=_to_float(pair.get("priceUsd")),
        liquidity_usd=liquidity_usd,
        liquidity_base=_to_float(liquidity.get("base")),
        liquidity_quote=_to_float(liquidity.get("quote")),
        volume_h24=_to_float(volume.get("h24")),
        pair_url=pair.get("url"),
    )


def select_deepest_usd_pool(
    asset_symbol: str,
    pairs: list[dict[str, Any]],
    *,
    fetched_at_utc: datetime | None = None,
) -> DexPoolDepth:
    """Select the pair with the highest positive USD liquidity."""
    if fetched_at_utc is None:
        fetched_at_utc = datetime.now(timezone.utc)

    valid_pairs: list[tuple[float, dict[str, Any]]] = []

    for pair in pairs:
        liquidity = pair.get("liquidity") or {}
        liquidity_usd = _to_float(liquidity.get("usd"))

        if liquidity_usd is not None and liquidity_usd > 0:
            valid_pairs.append((liquidity_usd, pair))

    if not valid_pairs:
        raise DexScreenerError("No pair with positive liquidity.usd found")

    _, deepest_pair = max(valid_pairs, key=lambda item: item[0])

    return _build_pool_depth(
        asset_symbol=asset_symbol,
        pair=deepest_pair,
        fetched_at_utc=fetched_at_utc,
    )


def fetch_deepest_pool_depth(
    asset_symbol: str,
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    http_get: Callable[..., Any] = requests.get,
) -> DexPoolDepth:
    """Fetch real DEX pairs and return the deepest USD-liquidity pool."""
    pairs = fetch_token_pairs(
        asset_symbol=asset_symbol,
        timeout=timeout,
        http_get=http_get,
    )
    return select_deepest_usd_pool(asset_symbol=asset_symbol, pairs=pairs)
