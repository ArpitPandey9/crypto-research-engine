"""Persist real DEX pool-depth data into the local SQLite research database.

This script fetches pool-depth data from the real DEX Screener client and stores
the normalized records in SQLite. It never fabricates missing liquidity values.
If real data cannot be fetched or parsed, the error is allowed to surface.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable, Iterable

from src.data.dexscreener_client import DexPoolDepth, fetch_deepest_pool_depth


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT / "data" / "db" / "whale_data.db"
DEFAULT_ASSET_SYMBOLS = ("ETH", "WBTC")


def create_dex_pool_depths_table(conn: sqlite3.Connection) -> None:
    """Create the dex_pool_depths table if it does not already exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dex_pool_depths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetched_at_utc TEXT NOT NULL,
            asset_symbol TEXT NOT NULL,
            chain_id TEXT NOT NULL,
            dex_id TEXT NOT NULL,
            pair_address TEXT NOT NULL,
            base_token_symbol TEXT NOT NULL,
            quote_token_symbol TEXT NOT NULL,
            price_usd REAL,
            liquidity_usd REAL NOT NULL CHECK (liquidity_usd > 0),
            liquidity_base REAL,
            liquidity_quote REAL,
            volume_h24 REAL,
            pair_url TEXT,
            created_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_dex_pool_depths_asset_fetched
        ON dex_pool_depths (asset_symbol, fetched_at_utc)
        """
    )


def insert_pool_depth(conn: sqlite3.Connection, pool: DexPoolDepth) -> None:
    """Insert one normalized real DEX pool-depth record."""
    conn.execute(
        """
        INSERT INTO dex_pool_depths (
            fetched_at_utc,
            asset_symbol,
            chain_id,
            dex_id,
            pair_address,
            base_token_symbol,
            quote_token_symbol,
            price_usd,
            liquidity_usd,
            liquidity_base,
            liquidity_quote,
            volume_h24,
            pair_url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pool.fetched_at_utc.isoformat(),
            pool.asset_symbol,
            pool.chain_id,
            pool.dex_id,
            pool.pair_address,
            pool.base_token_symbol,
            pool.quote_token_symbol,
            pool.price_usd,
            pool.liquidity_usd,
            pool.liquidity_base,
            pool.liquidity_quote,
            pool.volume_h24,
            pool.pair_url,
        ),
    )


def update_dex_pool_depths(
    db_path: Path = DEFAULT_DB_PATH,
    asset_symbols: Iterable[str] = DEFAULT_ASSET_SYMBOLS,
    fetcher: Callable[[str], DexPoolDepth] = fetch_deepest_pool_depth,
) -> list[DexPoolDepth]:
    """Fetch real DEX pool-depth records and persist them to SQLite.

    Args:
        db_path: SQLite database path.
        asset_symbols: Asset symbols to fetch, such as ETH and WBTC.
        fetcher: Injectable fetch function used by tests.

    Returns:
        List of inserted DexPoolDepth records.

    Raises:
        Any exception raised by the fetcher or SQLite layer. This is deliberate:
        the pipeline should fail clearly rather than silently creating fake data.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    inserted: list[DexPoolDepth] = []

    with sqlite3.connect(db_path) as conn:
        create_dex_pool_depths_table(conn)

        for asset_symbol in asset_symbols:
            pool = fetcher(asset_symbol)
            insert_pool_depth(conn, pool)
            inserted.append(pool)

        conn.commit()

    return inserted


def main() -> None:
    """Run the pool-depth update pipeline from the command line."""
    inserted = update_dex_pool_depths()

    print("Inserted real DEX pool-depth records:")
    for pool in inserted:
        print(
            f"- {pool.asset_symbol}: "
            f"{pool.liquidity_usd:,.2f} USD liquidity "
            f"on {pool.dex_id} ({pool.chain_id}) "
            f"pair={pool.pair_address}"
        )


if __name__ == "__main__":
    main()
