"""Historical price ingestion and causal whale-volume normalization.

V3 goals:
- preserve Binance OHLC and explicit open/close/availability timestamps
- persist price history non-destructively with idempotent upserts
- normalize whale transfers only with prices available at or before transfer time
- retain valuation timestamp/lag metadata for auditability
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[1]
DB_PATH = PROJECT_ROOT / "data" / "db" / "whale_data.db"

HISTORICAL_PRICE_COLUMNS = [
    "timestamp",
    "symbol",
    "asset_type",
    "open_time",
    "close_time",
    "price_available_at",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "price_usd",
    "source",
]


class PriceOracle:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.binance_url = "https://api.binance.com/api/v3/klines"
        self.price_symbol_map: Dict[str, str] = {
            "ETH": "ETHUSDT",
            "BTC": "BTCUSDT",
            "WBTC": "BTCUSDT",
        }

    @staticmethod
    def _asset_type_for_symbol(symbol: str) -> str:
        if symbol == "ETHUSDT":
            return "ETH"
        if symbol == "BTCUSDT":
            return "BTC"
        return symbol

    def _download_symbol_prices(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 1000,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
    ) -> pd.DataFrame:
        """Fetch one Binance kline page and preserve full timing semantics."""
        logging.info("Fetching %s (%s, limit=%s) from Binance...", symbol, interval, limit)
        params: dict[str, object] = {"symbol": symbol, "interval": interval, "limit": limit}
        if start_time_ms is not None:
            params["startTime"] = int(start_time_ms)
        if end_time_ms is not None:
            params["endTime"] = int(end_time_ms)

        response = requests.get(self.binance_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if not data:
            return pd.DataFrame(columns=HISTORICAL_PRICE_COLUMNS)

        raw = pd.DataFrame(
            data,
            columns=[
                "open_time_ms", "open", "high", "low", "close", "volume",
                "close_time_ms", "quote_asset_volume", "number_of_trades",
                "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore",
            ],
        )

        out = pd.DataFrame()
        out["open_time"] = pd.to_datetime(raw["open_time_ms"], unit="ms", utc=True)
        out["close_time"] = pd.to_datetime(raw["close_time_ms"], unit="ms", utc=True)
        # Binance close_time is the final millisecond inside the bar. The close is
        # treated as available at the next millisecond, i.e. the exact bar boundary.
        out["price_available_at"] = out["close_time"] + pd.Timedelta(milliseconds=1)
        out["timestamp"] = out["open_time"]  # backward-compatible bucket-start alias
        out["symbol"] = symbol
        out["asset_type"] = self._asset_type_for_symbol(symbol)
        out["open_price"] = pd.to_numeric(raw["open"], errors="coerce")
        out["high_price"] = pd.to_numeric(raw["high"], errors="coerce")
        out["low_price"] = pd.to_numeric(raw["low"], errors="coerce")
        out["close_price"] = pd.to_numeric(raw["close"], errors="coerce")
        out["price_usd"] = out["close_price"]  # compatibility: research close series
        out["source"] = "binance_spot_klines"
        out = out[HISTORICAL_PRICE_COLUMNS].dropna(
            subset=["timestamp", "asset_type", "open_price", "close_price", "price_available_at"]
        )
        return out.sort_values(["asset_type", "timestamp"]).reset_index(drop=True)

    def _ensure_historical_price_schema(self, conn: sqlite3.Connection) -> None:
        """Create/migrate historical_prices without deleting existing history."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historical_prices (
                timestamp TEXT NOT NULL,
                symbol TEXT,
                asset_type TEXT NOT NULL,
                price_usd REAL,
                open_time TEXT,
                close_time TEXT,
                price_available_at TEXT,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                source TEXT
            )
            """
        )
        existing = {row[1] for row in conn.execute("PRAGMA table_info(historical_prices)")}
        additions = {
            "open_time": "TEXT",
            "close_time": "TEXT",
            "price_available_at": "TEXT",
            "open_price": "REAL",
            "high_price": "REAL",
            "low_price": "REAL",
            "close_price": "REAL",
            "source": "TEXT",
        }
        for column, sql_type in additions.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE historical_prices ADD COLUMN {column} {sql_type}")

        # Current project history is unique by asset/timestamp. This index makes
        # subsequent writes idempotent instead of destructive.
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_historical_prices_asset_ts "
            "ON historical_prices(asset_type, timestamp)"
        )

    @staticmethod
    def _sql_value(value):
        if pd.isna(value):
            return None
        if isinstance(value, pd.Timestamp):
            # Match the legacy pandas/SQLite text representation (space separator)
            # so an existing candle is updated rather than duplicated under a T-separated key.
            return str(value)
        return value

    def _persist_historical_prices(self, prices_df: pd.DataFrame) -> None:
        """Upsert fetched bars while preserving all older rows."""
        if prices_df.empty:
            return
        with sqlite3.connect(self.db_path) as conn:
            self._ensure_historical_price_schema(conn)
            sql = """
                INSERT INTO historical_prices (
                    timestamp, symbol, asset_type, price_usd, open_time, close_time,
                    price_available_at, open_price, high_price, low_price, close_price, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(asset_type, timestamp) DO UPDATE SET
                    symbol=excluded.symbol,
                    price_usd=excluded.price_usd,
                    open_time=excluded.open_time,
                    close_time=excluded.close_time,
                    price_available_at=excluded.price_available_at,
                    open_price=excluded.open_price,
                    high_price=excluded.high_price,
                    low_price=excluded.low_price,
                    close_price=excluded.close_price,
                    source=excluded.source
            """
            rows = []
            for _, row in prices_df.iterrows():
                rows.append(tuple(self._sql_value(row.get(col)) for col in [
                    "timestamp", "symbol", "asset_type", "price_usd", "open_time", "close_time",
                    "price_available_at", "open_price", "high_price", "low_price", "close_price", "source"
                ]))
            conn.executemany(sql, rows)
            conn.commit()

    def download_bulk_prices(self, interval: str = "1h", limit: int = 1000) -> pd.DataFrame:
        """Fetch latest ETH/BTC bars and non-destructively upsert them."""
        frames: List[pd.DataFrame] = []
        for symbol in ["ETHUSDT", "BTCUSDT"]:
            try:
                frame = self._download_symbol_prices(symbol=symbol, interval=interval, limit=limit)
                if not frame.empty:
                    frames.append(frame)
            except requests.RequestException as exc:
                logging.error("Failed to fetch %s from Binance: %s", symbol, exc)
        if not frames:
            logging.error("No price data downloaded. historical_prices will not be updated.")
            return pd.DataFrame(columns=HISTORICAL_PRICE_COLUMNS)
        prices_df = pd.concat(frames, ignore_index=True).sort_values(["asset_type", "timestamp"]).reset_index(drop=True)
        self._persist_historical_prices(prices_df)
        logging.info("Upserted %s fetched price rows without deleting prior history.", len(prices_df))
        return prices_df

    def download_price_range(
        self,
        start_time,
        end_time,
        interval: str = "1h",
        limit: int = 1000,
    ) -> pd.DataFrame:
        """Backfill an explicit UTC range with paginated, idempotent Binance fetches."""
        start = pd.Timestamp(start_time)
        end = pd.Timestamp(end_time)
        start = start.tz_localize("UTC") if start.tzinfo is None else start.tz_convert("UTC")
        end = end.tz_localize("UTC") if end.tzinfo is None else end.tz_convert("UTC")
        if end <= start:
            raise ValueError("end_time must be later than start_time")

        all_frames: List[pd.DataFrame] = []
        for symbol in ["ETHUSDT", "BTCUSDT"]:
            cursor_ms = int(start.timestamp() * 1000)
            end_ms = int(end.timestamp() * 1000)
            while cursor_ms <= end_ms:
                frame = self._download_symbol_prices(
                    symbol=symbol,
                    interval=interval,
                    limit=limit,
                    start_time_ms=cursor_ms,
                    end_time_ms=end_ms,
                )
                if frame.empty:
                    break
                all_frames.append(frame)
                last_open = pd.to_datetime(frame["open_time"], utc=True).max()
                next_cursor = int((last_open + pd.Timedelta(hours=1)).timestamp() * 1000)
                if next_cursor <= cursor_ms:
                    break
                cursor_ms = next_cursor
                if len(frame) < limit:
                    break

        if not all_frames:
            return pd.DataFrame(columns=HISTORICAL_PRICE_COLUMNS)
        out = pd.concat(all_frames, ignore_index=True).drop_duplicates(["asset_type", "timestamp"], keep="last")
        out = out.sort_values(["asset_type", "timestamp"]).reset_index(drop=True)
        self._persist_historical_prices(out)
        logging.info("Backfilled/upserted %s price rows for explicit range.", len(out))
        return out

    @staticmethod
    def _available_price_frame(prices_df: pd.DataFrame, asset_type: str) -> pd.DataFrame:
        """Return close prices keyed by the time they actually became available."""
        subset = prices_df[prices_df["asset_type"] == asset_type].copy()
        if subset.empty:
            return pd.DataFrame(columns=["valuation_price_time", "price_usd"])

        if "price_available_at" in subset.columns:
            available = pd.to_datetime(subset["price_available_at"], utc=True, errors="coerce")
        else:
            available = pd.Series(pd.NaT, index=subset.index, dtype="datetime64[ns, UTC]")
        if "close_time" in subset.columns:
            fallback = pd.to_datetime(subset["close_time"], utc=True, errors="coerce") + pd.Timedelta(milliseconds=1)
            available = available.fillna(fallback)

        subset["valuation_price_time"] = available
        subset["price_usd"] = pd.to_numeric(subset["price_usd"], errors="coerce")
        subset = subset.dropna(subset=["valuation_price_time", "price_usd"])
        return subset[["valuation_price_time", "price_usd"]].sort_values("valuation_price_time")

    def normalize_whale_volume(self) -> pd.DataFrame:
        """Causally normalize transfers using only already-completed market bars."""
        logging.info("Starting causal whale volume normalization...")
        try:
            with sqlite3.connect(self.db_path) as conn:
                whales_df = pd.read_sql_query("SELECT * FROM institutional_transfers", conn)
                prices_df = pd.read_sql_query("SELECT * FROM historical_prices", conn)
        except (sqlite3.Error, pd.errors.DatabaseError) as exc:
            logging.error("Database read error: %s", exc)
            return pd.DataFrame()

        if whales_df.empty:
            logging.warning("institutional_transfers is empty. Run onchain_client first.")
            return pd.DataFrame()
        if prices_df.empty:
            logging.warning("historical_prices is empty. Run download_bulk_prices first.")
            return pd.DataFrame()

        whales_df["timestamp"] = pd.to_datetime(whales_df["timestamp"], utc=True, errors="coerce")
        prices_df["timestamp"] = pd.to_datetime(prices_df["timestamp"], utc=True, errors="coerce")
        whales_df = whales_df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

        frames: List[pd.DataFrame] = []
        for whale_asset, price_asset in [("ETH", "ETH"), ("WBTC", "BTC")]:
            whales = whales_df[whales_df["asset_type"] == whale_asset].copy().sort_values("timestamp")
            if whales.empty:
                continue
            prices = self._available_price_frame(prices_df, price_asset)
            if prices.empty:
                whales["price_usd"] = pd.NA
                whales["valuation_price_time"] = pd.NaT
            else:
                whales = pd.merge_asof(
                    whales,
                    prices,
                    left_on="timestamp",
                    right_on="valuation_price_time",
                    direction="backward",
                )
            whales["true_usd_volume"] = pd.to_numeric(whales["amount"], errors="coerce") * pd.to_numeric(whales["price_usd"], errors="coerce")
            whales["valuation_lag_seconds"] = (whales["timestamp"] - whales["valuation_price_time"]).dt.total_seconds()
            whales["valuation_method"] = "last_completed_binance_hourly_close"
            frames.append(whales)

        stable = whales_df[whales_df["asset_type"].isin(["USDC", "USDT"])].copy()
        if not stable.empty:
            stable["price_usd"] = 1.0
            stable["true_usd_volume"] = pd.to_numeric(stable["amount"], errors="coerce")
            stable["valuation_price_time"] = stable["timestamp"]
            stable["valuation_lag_seconds"] = 0.0
            stable["valuation_method"] = "stablecoin_parity_assumption"
            frames.append(stable)

        other = whales_df[~whales_df["asset_type"].isin(["ETH", "WBTC", "USDC", "USDT"])].copy()
        if not other.empty:
            other["price_usd"] = pd.NA
            other["true_usd_volume"] = pd.NA
            other["valuation_price_time"] = pd.NaT
            other["valuation_lag_seconds"] = pd.NA
            other["valuation_method"] = "unavailable"
            frames.append(other)

        if not frames:
            logging.warning("No enriched whale frames were created.")
            return pd.DataFrame()
        final_df = pd.concat(frames, ignore_index=True).sort_values("timestamp").reset_index(drop=True)
        # SQLite cannot reliably bind timezone-aware pandas Timestamp objects when
        # a column has mixed timestamp/NA values across pandas versions. Persist an
        # explicit UTC text representation while returning the typed dataframe.
        persist_df = final_df.copy()
        for column in ["timestamp", "valuation_price_time"]:
            if column in persist_df.columns:
                persist_df[column] = persist_df[column].map(
                    lambda value: None if pd.isna(value) else str(pd.Timestamp(value))
                )
        with sqlite3.connect(self.db_path) as conn:
            persist_df.to_sql("enriched_whales", conn, if_exists="replace", index=False)
        logging.info("Saved %s causally enriched rows to enriched_whales.", len(final_df))
        return final_df


if __name__ == "__main__":
    oracle = PriceOracle()
    oracle.download_bulk_prices()
    oracle.normalize_whale_volume()
