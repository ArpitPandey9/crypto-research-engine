# src/data/fetch_prices.py

"""
Module: Historical Price Oracle & Whale Volume Normalizer (V2)
Description:
- Fetches bulk historical prices from Binance
- Stores ETH and BTC price series in the local SQLite vault
- Enriches institutional transfers with asset-aware USD normalization
- Writes a permanent enriched_whales table for downstream strategy and app usage
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List

import pandas as pd
import requests


# ==========================================
# LOGGING
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ==========================================
# GLOBAL PROJECT PATHS
# ==========================================
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[1]
DB_PATH = PROJECT_ROOT / "data" / "db" / "whale_data.db"


# ==========================================
# PRICE ORACLE
# ==========================================
class PriceOracle:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.binance_url = "https://api.binance.com/api/v3/klines"

        # Asset-to-symbol mapping for normalization
        self.price_symbol_map: Dict[str, str] = {
            "ETH": "ETHUSDT",
            "BTC": "BTCUSDT",
            "WBTC": "BTCUSDT",
        }

    def _download_symbol_prices(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        Fetch bulk historical klines for one Binance symbol.
        """
        logging.info("Fetching %s (%s, limit=%s) from Binance...", symbol, interval, limit)

        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }

        response = requests.get(self.binance_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(
            data,
            columns=[
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_asset_volume",
                "number_of_trades",
                "taker_buy_base_asset_volume",
                "taker_buy_quote_asset_volume",
                "ignore",
            ],
        )

        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df["price_usd"] = df["close"].astype(float)
        df["symbol"] = symbol

        # Asset type used later for joins / normalization
        if symbol == "ETHUSDT":
            df["asset_type"] = "ETH"
        elif symbol == "BTCUSDT":
            df["asset_type"] = "BTC"
        else:
            df["asset_type"] = symbol

        out = df[["timestamp", "symbol", "asset_type", "price_usd"]].copy()
        out = out.sort_values(["asset_type", "timestamp"]).reset_index(drop=True)
        return out

    def download_bulk_prices(self, interval: str = "1h", limit: int = 1000) -> pd.DataFrame:
        """
        Fetch and persist ETH + BTC hourly price series.
        """
        frames: List[pd.DataFrame] = []

        for symbol in ["ETHUSDT", "BTCUSDT"]:
            try:
                symbol_df = self._download_symbol_prices(symbol=symbol, interval=interval, limit=limit)
                if not symbol_df.empty:
                    frames.append(symbol_df)
            except requests.RequestException as e:
                logging.error("Failed to fetch %s from Binance: %s", symbol, e)

        if not frames:
            logging.error("No price data downloaded. historical_prices will not be updated.")
            return pd.DataFrame()

        prices_df = pd.concat(frames, ignore_index=True)
        prices_df = prices_df.sort_values(["asset_type", "timestamp"]).reset_index(drop=True)

        try:
            with sqlite3.connect(self.db_path) as conn:
                prices_df.to_sql("historical_prices", conn, if_exists="replace", index=False)
                logging.info(
                    "Saved %s total price rows to historical_prices.",
                    len(prices_df),
                )
        except sqlite3.Error as e:
            logging.error("Database write error while saving historical_prices: %s", e)

        return prices_df

    def normalize_whale_volume(self) -> pd.DataFrame:
        """
        Reads institutional_transfers + historical_prices,
        enriches whale transfers with the correct USD normalization,
        and writes enriched_whales back to the vault.
        """
        logging.info("Starting whale volume normalization...")

        try:
            with sqlite3.connect(self.db_path) as conn:
                whales_df = pd.read_sql_query("SELECT * FROM institutional_transfers", conn)
                prices_df = pd.read_sql_query("SELECT * FROM historical_prices", conn)
        except sqlite3.Error as e:
            logging.error("Database read error: %s", e)
            return pd.DataFrame()

        if whales_df.empty:
            logging.warning("institutional_transfers is empty. Run onchain_client first.")
            return pd.DataFrame()

        if prices_df.empty:
            logging.warning("historical_prices is empty. Run download_bulk_prices first.")
            return pd.DataFrame()

        whales_df["timestamp"] = pd.to_datetime(whales_df["timestamp"], utc=True)
        prices_df["timestamp"] = pd.to_datetime(prices_df["timestamp"], utc=True)

        whales_df = whales_df.sort_values("timestamp").reset_index(drop=True)
        prices_df = prices_df.sort_values(["asset_type", "timestamp"]).reset_index(drop=True)

        # Split by asset class so each transfer matches the right price stream
        eth_whales = whales_df[whales_df["asset_type"] == "ETH"].copy()
        wbtc_whales = whales_df[whales_df["asset_type"] == "WBTC"].copy()
        stable_whales = whales_df[whales_df["asset_type"].isin(["USDC", "USDT"])].copy()
        other_whales = whales_df[
            ~whales_df["asset_type"].isin(["ETH", "WBTC", "USDC", "USDT"])
        ].copy()

        eth_prices = prices_df[prices_df["asset_type"] == "ETH"][["timestamp", "price_usd"]].copy()
        btc_prices = prices_df[prices_df["asset_type"] == "BTC"][["timestamp", "price_usd"]].copy()

        enriched_frames: List[pd.DataFrame] = []

        if not eth_whales.empty and not eth_prices.empty:
            eth_enriched = pd.merge_asof(
                left=eth_whales.sort_values("timestamp"),
                right=eth_prices.sort_values("timestamp"),
                on="timestamp",
                direction="backward",
            )
            eth_enriched["true_usd_volume"] = eth_enriched["amount"] * eth_enriched["price_usd"]
            enriched_frames.append(eth_enriched)

        if not wbtc_whales.empty and not btc_prices.empty:
            wbtc_enriched = pd.merge_asof(
                left=wbtc_whales.sort_values("timestamp"),
                right=btc_prices.sort_values("timestamp"),
                on="timestamp",
                direction="backward",
            )
            wbtc_enriched["true_usd_volume"] = wbtc_enriched["amount"] * wbtc_enriched["price_usd"]
            enriched_frames.append(wbtc_enriched)

        if not stable_whales.empty:
            stable_whales["price_usd"] = 1.0
            stable_whales["true_usd_volume"] = stable_whales["amount"]
            enriched_frames.append(stable_whales)

        if not other_whales.empty:
            # Keep unknown assets visible, but mark missing normalization clearly
            other_whales["price_usd"] = pd.NA
            other_whales["true_usd_volume"] = pd.NA
            enriched_frames.append(other_whales)

        if not enriched_frames:
            logging.warning("No enriched whale frames were created.")
            return pd.DataFrame()

        final_df = pd.concat(enriched_frames, ignore_index=True)
        final_df = final_df.sort_values("timestamp").reset_index(drop=True)

        try:
            with sqlite3.connect(self.db_path) as conn:
                final_df.to_sql("enriched_whales", conn, if_exists="replace", index=False)
                logging.info(
                    "SUCCESS: Saved %s rows to enriched_whales.",
                    len(final_df),
                )
        except sqlite3.Error as e:
            logging.error("Database write error while saving enriched_whales: %s", e)

        return final_df


# ==========================================
# EXECUTION
# ==========================================
if __name__ == "__main__":
    oracle = PriceOracle()
    oracle.download_bulk_prices()
    oracle.normalize_whale_volume()