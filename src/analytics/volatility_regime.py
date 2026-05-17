"""Volatility-regime helpers for market-weather classification.

This module converts historical price data into a transparent volatility regime:
normal, elevated, or extreme. It is intentionally conservative. If price data is
missing or insufficient, the module returns an unavailable result instead of
pretending that a regime was detected.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


NORMAL_VOLATILITY_REGIME = "normal"
ELEVATED_VOLATILITY_REGIME = "elevated"
EXTREME_VOLATILITY_REGIME = "extreme"
UNAVAILABLE_VOLATILITY_REGIME = "unavailable"


@dataclass(frozen=True)
class VolatilityRegimeResult:
    """Structured output for volatility-regime classification."""

    asset_symbol: str
    is_available: bool
    volatility_regime: str
    latest_realized_volatility: float | None
    normal_threshold: float | None
    extreme_threshold: float | None
    window_size: int
    reason: str


def _normalize_asset_symbol(asset_symbol: str) -> str:
    """Normalize asset symbol for consistent display and downstream use."""
    normalized = asset_symbol.strip().upper()

    if not normalized:
        raise ValueError("asset_symbol cannot be empty")

    return normalized


def _validate_price_frame(prices: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize the price DataFrame needed for volatility logic."""
    required_columns = {"timestamp", "price_usd"}
    missing_columns = required_columns.difference(prices.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required price columns: {missing}")

    out = prices.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out["price_usd"] = pd.to_numeric(out["price_usd"], errors="coerce")

    if out["timestamp"].isna().any():
        raise ValueError("timestamp contains invalid values")

    if out["price_usd"].isna().any():
        raise ValueError("price_usd contains invalid values")

    if (out["price_usd"] <= 0).any():
        raise ValueError("price_usd must be greater than zero")

    return out.sort_values("timestamp").reset_index(drop=True)


def calculate_price_returns(prices: pd.DataFrame) -> pd.Series:
    """Calculate fractional price returns from sorted historical prices.

    Returns are fractional, not percentage formatted. Example:
    price 100 -> 110 creates return 0.10, which means 10%.
    """
    clean_prices = _validate_price_frame(prices)

    returns = clean_prices["price_usd"].pct_change(fill_method=None).dropna()

    return returns.reset_index(drop=True)


def classify_volatility_regime(
    latest_volatility: float,
    normal_threshold: float,
    extreme_threshold: float,
) -> str:
    """Classify latest realized volatility using transparent thresholds."""
    if latest_volatility < 0:
        raise ValueError("latest_volatility cannot be negative")

    if normal_threshold < 0:
        raise ValueError("normal_threshold cannot be negative")

    if extreme_threshold < 0:
        raise ValueError("extreme_threshold cannot be negative")

    if extreme_threshold < normal_threshold:
        raise ValueError("extreme_threshold cannot be lower than normal_threshold")

    if latest_volatility > extreme_threshold:
        return EXTREME_VOLATILITY_REGIME

    if latest_volatility > normal_threshold:
        return ELEVATED_VOLATILITY_REGIME

    return NORMAL_VOLATILITY_REGIME


def _unavailable_result(
    asset_symbol: str,
    window_size: int,
    reason: str,
) -> VolatilityRegimeResult:
    """Build a consistent unavailable result without inventing a regime."""
    return VolatilityRegimeResult(
        asset_symbol=asset_symbol,
        is_available=False,
        volatility_regime=UNAVAILABLE_VOLATILITY_REGIME,
        latest_realized_volatility=None,
        normal_threshold=None,
        extreme_threshold=None,
        window_size=window_size,
        reason=reason,
    )


def build_volatility_regime(
    prices: pd.DataFrame,
    asset_symbol: str,
    window_size: int = 24,
) -> VolatilityRegimeResult:
    """Build a volatility-regime result from historical prices.

    The classifier uses rolling standard deviation of fractional returns as a
    realized-volatility proxy. It compares the latest rolling volatility with
    the historical rolling-volatility distribution for the supplied data.
    """
    normalized_asset = _normalize_asset_symbol(asset_symbol)

    if window_size < 2:
        raise ValueError("window_size must be at least 2")

    returns = calculate_price_returns(prices)

    if len(returns) < window_size:
        return _unavailable_result(
            asset_symbol=normalized_asset,
            window_size=window_size,
            reason=(
                f"Not enough price returns to calculate volatility regime for "
                f"{normalized_asset}. Required at least {window_size}, got {len(returns)}."
            ),
        )

    rolling_volatility = returns.rolling(window=window_size).std(ddof=0).dropna()

    if rolling_volatility.empty:
        return _unavailable_result(
            asset_symbol=normalized_asset,
            window_size=window_size,
            reason=(
                f"Rolling volatility is unavailable for {normalized_asset}; "
                "not enough valid rolling windows."
            ),
        )

    latest_realized_volatility = float(rolling_volatility.iloc[-1])
    normal_threshold = float(rolling_volatility.quantile(0.50))
    extreme_threshold = float(rolling_volatility.quantile(0.80))

    regime = classify_volatility_regime(
        latest_volatility=latest_realized_volatility,
        normal_threshold=normal_threshold,
        extreme_threshold=extreme_threshold,
    )

    reason = (
        f"Latest {window_size}-period realized volatility for {normalized_asset} is "
        f"{latest_realized_volatility:.4f}. Normal threshold is "
        f"{normal_threshold:.4f} and extreme threshold is {extreme_threshold:.4f}. "
        f"Classified volatility regime as {regime}."
    )

    return VolatilityRegimeResult(
        asset_symbol=normalized_asset,
        is_available=True,
        volatility_regime=regime,
        latest_realized_volatility=latest_realized_volatility,
        normal_threshold=normal_threshold,
        extreme_threshold=extreme_threshold,
        window_size=window_size,
        reason=reason,
    )
