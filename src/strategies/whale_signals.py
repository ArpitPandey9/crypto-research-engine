# src/strategies/whale_signals.py

"""
Module: Whale Flow Strategy (V4)
Description:
- Enforces explicit target-asset research and backtesting
- Converts irregular whale events into a fixed hourly series
- Supports explicit traded-asset -> market-price-series mapping
- Generates rolling whale-flow signals
- Runs a deterministic vectorized backtest

Industry goals:
- no mixed-asset backtests
- explicit validation
- reproducible signal path
- clean market-price alias logic
- GitHub/interview-readable structure
"""

from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

# Starter exchange hot-wallet map.
# Expand later using stronger wallet-label datasets.
EXCHANGE_DIRECTORY = {
    "0x28C6c06298d514Db089934071355E5743bf21d60".lower(): "Binance 14",
    "0xf977814e90da44bfa03b6295a0616a897441acec".lower(): "Binance 8",
    "0x5041ed759cb4bcc0e11894458a5ebc983fb13eb3".lower(): "Coinbase 3",
}

SUPPORTED_TARGET_ASSETS = {"ETH", "WBTC", "USDC", "USDT"}

# Traded asset -> market-price series mapping
# Example:
# - WBTC trades as an ERC-20 wrapped asset
# - but its market-price series should come from BTC
PRICE_ASSET_MAP = {
    "ETH": "ETH",
    "WBTC": "BTC",
    "USDC": "USDC",
    "USDT": "USDT",
}


def _validate_required_columns(df: pd.DataFrame, required: Iterable[str]) -> None:
    """Raise early if required columns are missing."""
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _prepare_event_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize and validate enriched whale event data.

    Expected input:
    - timestamp
    - asset_type
    - amount
    - sender_address
    - receiver_address
    - price_usd
    - true_usd_volume
    """
    required_columns = [
        "timestamp",
        "asset_type",
        "amount",
        "sender_address",
        "receiver_address",
        "price_usd",
        "true_usd_volume",
    ]
    _validate_required_columns(df, required_columns)

    out = df.copy()

    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out = out.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    out["asset_type"] = out["asset_type"].fillna("UNKNOWN").astype(str).str.upper()
    out["sender_address"] = out["sender_address"].fillna("").astype(str)
    out["receiver_address"] = out["receiver_address"].fillna("").astype(str)

    out["amount"] = pd.to_numeric(out["amount"], errors="coerce")
    out["price_usd"] = pd.to_numeric(out["price_usd"], errors="coerce")
    out["true_usd_volume"] = pd.to_numeric(out["true_usd_volume"], errors="coerce")

    out = out.dropna(subset=["true_usd_volume"])
    return out


def _prepare_price_frame(price_df: pd.DataFrame, target_asset: str) -> pd.DataFrame:
    """
    Standardize an optional historical market-price dataframe.

    Expected columns:
    - timestamp
    - asset_type
    - price_usd

    Notes
    -----
    Some traded assets should map to a different market-price series.
    Example:
    - WBTC should use BTC market prices
    """
    required_columns = ["timestamp", "asset_type", "price_usd"]
    _validate_required_columns(price_df, required_columns)

    market_price_asset = PRICE_ASSET_MAP.get(target_asset, target_asset)

    out = price_df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out = out.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    out["asset_type"] = out["asset_type"].fillna("UNKNOWN").astype(str).str.upper()
    out["price_usd"] = pd.to_numeric(out["price_usd"], errors="coerce")
    if "open_price" in out.columns:
        out["open_price"] = pd.to_numeric(out["open_price"], errors="coerce")
    else:
        out["open_price"] = pd.NA
    if "price_available_at" in out.columns:
        out["price_available_at"] = pd.to_datetime(out["price_available_at"], utc=True, errors="coerce")
    elif "close_time" in out.columns:
        out["price_available_at"] = pd.to_datetime(out["close_time"], utc=True, errors="coerce") + pd.Timedelta(milliseconds=1)
    else:
        # Backward-compatible interpretation of legacy project rows: timestamp is
        # the hourly bucket start and price_usd is that bucket's close.
        out["price_available_at"] = out["timestamp"] + pd.Timedelta(hours=1)
    out = out.dropna(subset=["price_usd"])

    out = out[out["asset_type"] == market_price_asset].copy()
    return out


def _assign_flow_direction(events: pd.DataFrame) -> pd.DataFrame:
    """
    Assign directional pressure:
    - transfer INTO known exchange wallet => bearish pressure (-1)
    - otherwise => bullish pressure (+1)
    """
    out = events.copy()
    out["flow_direction"] = 1

    out.loc[
        out["receiver_address"].str.lower().isin(EXCHANGE_DIRECTORY.keys()),
        "flow_direction",
    ] = -1

    out["pressure_usd"] = out["true_usd_volume"] * out["flow_direction"]
    return out


def _build_hourly_price_series(
    target_events: pd.DataFrame,
    target_asset: str,
    price_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Build a fixed hourly market-price series for the chosen target asset.

    Preference order:
    1. Use dedicated historical market prices if provided
    2. Fall back to last observed transfer-linked prices for that asset
    """
    if price_df is not None:
        clean_prices = _prepare_price_frame(price_df, target_asset)
        if clean_prices.empty:
            raise ValueError(
                f"No hourly market prices found for target_asset={target_asset} "
                f"(expected market series: {PRICE_ASSET_MAP.get(target_asset, target_asset)})"
            )

        price_cols = ["price_usd", "open_price", "price_available_at"]
        hourly_price = (
            clean_prices.set_index("timestamp")[price_cols]
            .sort_index()
            .resample("1h")
            .last()
            .reset_index()
        )
        hourly_price["price_usd"] = hourly_price["price_usd"].ffill()
        hourly_price["open_price"] = hourly_price["open_price"].ffill()
        hourly_price["price_available_at"] = pd.to_datetime(
            hourly_price["price_available_at"], utc=True, errors="coerce"
        )
        return hourly_price

    if target_events.empty:
        raise ValueError(f"No target-asset events found for target_asset={target_asset}")

    hourly_price = (
        target_events.set_index("timestamp")[["price_usd"]]
        .sort_index()
        .resample("1h")
        .last()
        .ffill()
        .reset_index()
    )
    hourly_price["open_price"] = pd.NA
    hourly_price["price_available_at"] = hourly_price["timestamp"] + pd.Timedelta(hours=1)
    return hourly_price


def _build_hourly_research_frame(
    events: pd.DataFrame,
    target_asset: str,
    price_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Convert target-asset whale events into a fixed hourly research frame.

    Output columns:
    - timestamp
    - price_usd
    - pressure_usd
    - true_usd_volume
    - event_count
    - target_asset
    """
    target_events = events[events["asset_type"] == target_asset].copy()

    if target_events.empty:
        raise ValueError(f"No whale events found for target_asset={target_asset}")

    target_events = target_events.set_index("timestamp").sort_index()

    hourly_price = _build_hourly_price_series(
        target_events=target_events.reset_index(),
        target_asset=target_asset,
        price_df=price_df,
    )

    hourly_pressure = (
        target_events[["pressure_usd"]]
        .resample("1h")
        .sum()
        .fillna(0.0)
        .reset_index()
    )

    hourly_volume = (
        target_events[["true_usd_volume"]]
        .resample("1h")
        .sum()
        .fillna(0.0)
        .reset_index()
    )

    hourly_count = (
        target_events[["flow_direction"]]
        .resample("1h")
        .count()
        .rename(columns={"flow_direction": "event_count"})
        .reset_index()
    )

    research = hourly_price.merge(hourly_pressure, on="timestamp", how="outer")
    research = research.merge(hourly_volume, on="timestamp", how="outer")
    research = research.merge(hourly_count, on="timestamp", how="outer")

    research = research.sort_values("timestamp").reset_index(drop=True)

    research["price_usd"] = research["price_usd"].ffill()
    research["pressure_usd"] = research["pressure_usd"].fillna(0.0)
    research["true_usd_volume"] = research["true_usd_volume"].fillna(0.0)
    research["event_count"] = research["event_count"].fillna(0).astype(int)
    research["target_asset"] = target_asset
    research["bucket_start"] = pd.to_datetime(research["timestamp"], utc=True, errors="coerce")
    research["bucket_end"] = research["bucket_start"] + pd.Timedelta(hours=1)
    research["signal_available_at"] = research["bucket_end"]
    research["open_price_usd"] = pd.to_numeric(research.get("open_price"), errors="coerce")
    research["close_price_usd"] = pd.to_numeric(research["price_usd"], errors="coerce")

    research = research.dropna(subset=["price_usd"]).reset_index(drop=True)
    return research


def analyze_whale_flow(
    df: pd.DataFrame,
    target_asset: str = "ETH",
    window_hours: int = 12,
    min_flow_usd: float = 0.0,
    price_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Build fixed-frequency whale flow signals for a chosen target asset.

    Parameters
    ----------
    df : pd.DataFrame
        Enriched whale-event dataframe (for example from enriched_whales)
    target_asset : str
        Asset to trade / research, e.g. ETH or WBTC
    window_hours : int
        Rolling lookback window in hours
    min_flow_usd : float
        Minimum absolute rolling flow threshold before taking a position
    price_df : pd.DataFrame | None
        Optional dedicated historical price dataframe, e.g. historical_prices

    Returns
    -------
    pd.DataFrame
        Hourly research frame with price, flow, and trading signal
    """
    target_asset = target_asset.upper()

    if target_asset not in SUPPORTED_TARGET_ASSETS:
        raise ValueError(
            f"Unsupported target_asset={target_asset}. "
            f"Supported: {sorted(SUPPORTED_TARGET_ASSETS)}"
        )

    if window_hours < 1:
        raise ValueError("window_hours must be at least 1")

    logger.info(
        "Analyzing whale flow for target_asset=%s, window_hours=%s, min_flow_usd=%s",
        target_asset,
        window_hours,
        min_flow_usd,
    )

    events = _prepare_event_frame(df)
    events = _assign_flow_direction(events)

    research = _build_hourly_research_frame(
        events=events,
        target_asset=target_asset,
        price_df=price_df,
    )

    research = research.sort_values("timestamp").reset_index(drop=True)
    research = research.set_index("timestamp")

    research["rolling_net_flow"] = (
        research["pressure_usd"]
        .rolling(f"{window_hours}h", min_periods=1)
        .sum()
    )

    research["signal"] = 0
    research.loc[research["rolling_net_flow"] > min_flow_usd, "signal"] = 1
    research.loc[research["rolling_net_flow"] < -min_flow_usd, "signal"] = -1

    return research.reset_index()


def backtest_whale_strategy(
    df: pd.DataFrame,
    cost_per_trade: float = 0.001,
) -> pd.DataFrame:
    """
    Run a vectorized backtest on a fixed-hour whale signal dataframe.

    Trading logic:
    - signal observed at hour t
    - position applied from hour t+1
    - cost charged when position changes
    """
    logger.info("Running whale strategy backtest with cost_per_trade=%s", cost_per_trade)

    required_columns = [
        "timestamp",
        "target_asset",
        "price_usd",
        "signal",
        "rolling_net_flow",
    ]
    _validate_required_columns(df, required_columns)

    out = df.copy()
    out = out.sort_values("timestamp").reset_index(drop=True)

    out["price_usd"] = pd.to_numeric(out["price_usd"], errors="coerce")
    out = out.dropna(subset=["price_usd"]).reset_index(drop=True)

    out["asset_return"] = out["price_usd"].pct_change().fillna(0.0)

    # Position starts after the signal is observed
    out["position"] = out["signal"].shift(1).fillna(0).astype(int)

    # Trade/cost model
    out["trade_flag"] = out["position"].diff().fillna(0).ne(0).astype(int)
    out["transaction_cost"] = out["trade_flag"] * cost_per_trade

    # Strategy return path
    out["gross_strategy_return"] = out["position"] * out["asset_return"]
    out["net_strategy_return"] = out["gross_strategy_return"] - out["transaction_cost"]

    # Equity curves
    out["equity_asset"] = (1.0 + out["asset_return"]).cumprod()
    out["equity_strategy_gross"] = (1.0 + out["gross_strategy_return"]).cumprod()
    out["equity_strategy_net"] = (1.0 + out["net_strategy_return"]).cumprod()

    logger.info("Backtest complete for target_asset=%s", out["target_asset"].iloc[0])
    return out

def backtest_whale_strategy_causal(
    df: pd.DataFrame,
    cost_per_trade: float = 0.001,
) -> pd.DataFrame:
    """Run the V5 causal backtest using next-bar open execution.

    Semantics
    ---------
    - a signal for bucket t is final only at ``signal_available_at``
    - the position is entered at the next bucket's open price
    - returns are measured next-open to following-open
    - every executed position must satisfy entry_time >= source signal availability

    The legacy close-to-close helper remains available as ``backtest_whale_strategy``
    only for historical methodology reproducibility.
    """
    logger.info("Running causal whale strategy backtest with cost_per_trade=%s", cost_per_trade)
    required = [
        "timestamp", "target_asset", "signal", "rolling_net_flow",
        "open_price_usd", "signal_available_at",
    ]
    _validate_required_columns(df, required)

    out = df.copy().sort_values("timestamp").reset_index(drop=True)
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out["signal_available_at"] = pd.to_datetime(out["signal_available_at"], utc=True, errors="coerce")
    out["open_price_usd"] = pd.to_numeric(out["open_price_usd"], errors="coerce")
    if out["open_price_usd"].isna().any():
        raise ValueError(
            "Causal next-open backtest requires non-missing open_price_usd for every research row. "
            "Refresh/backfill historical_prices with V3 OHLC metadata first."
        )
    if out[["timestamp", "signal_available_at"]].isna().any().any():
        raise ValueError("Causal backtest requires valid timestamp and signal_available_at values")

    # Row t position comes from signal t-1, finalized at the boundary where row t opens.
    out["position"] = out["signal"].shift(1).fillna(0).astype(int)
    out["source_signal_available_at"] = out["signal_available_at"].shift(1)
    out["entry_time"] = out["timestamp"]
    out["execution_price_usd"] = out["open_price_usd"]
    out["next_execution_price_usd"] = out["execution_price_usd"].shift(-1)
    out["asset_return"] = (
        out["next_execution_price_usd"] / out["execution_price_usd"] - 1.0
    ).fillna(0.0)

    active = out["position"] != 0
    causal_ok = (~active) | (
        out["source_signal_available_at"].notna()
        & (out["entry_time"] >= out["source_signal_available_at"])
    )
    out["causal_execution_ok"] = causal_ok.astype(bool)
    if not bool(out["causal_execution_ok"].all()):
        raise ValueError("Causal execution invariant failed: entry precedes signal availability")

    out["trade_flag"] = out["position"].diff().fillna(0).ne(0).astype(int)
    out["transaction_cost"] = out["trade_flag"] * cost_per_trade
    out["gross_strategy_return"] = out["position"] * out["asset_return"]
    out["net_strategy_return"] = out["gross_strategy_return"] - out["transaction_cost"]
    out["equity_asset"] = (1.0 + out["asset_return"]).cumprod()
    out["equity_strategy_gross"] = (1.0 + out["gross_strategy_return"]).cumprod()
    out["equity_strategy_net"] = (1.0 + out["net_strategy_return"]).cumprod()
    out["methodology_version"] = "v5_causal_next_open"
    logger.info("Causal backtest complete for target_asset=%s", out["target_asset"].iloc[0])
    return out
