"""Read real DEX pool-depth snapshots from the local SQLite research database.

This repository layer does not invent missing liquidity values. If real pool-depth
data is unavailable, it returns None so the caller can display Unknown/Unavailable.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

from src.data.dexscreener_client import DexPoolDepth


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT / "data" / "db" / "whale_data.db"
DEFAULT_ASSET_SYMBOLS = ("ETH", "WBTC")


def _normalize_asset_symbol(asset_symbol: str) -> str:
    """Normalize an asset symbol for case-insensitive lookup."""
    return asset_symbol.strip().upper()


def _parse_datetime(value: str) -> datetime:
    """Parse an ISO-8601 datetime string stored by the ingestion pipeline."""
    return datetime.fromisoformat(value)


def _row_to_pool_depth(row: tuple) -> DexPoolDepth:
    """Convert a SQLite row into a normalized DexPoolDepth object."""
    return DexPoolDepth(
        fetched_at_utc=_parse_datetime(row[0]),
        asset_symbol=row[1],
        chain_id=row[2],
        dex_id=row[3],
        pair_address=row[4],
        base_token_symbol=row[5],
        quote_token_symbol=row[6],
        price_usd=row[7],
        liquidity_usd=row[8],
        liquidity_base=row[9],
        liquidity_quote=row[10],
        volume_h24=row[11],
        pair_url=row[12],
    )


def get_latest_pool_depth_from_connection(
    conn: sqlite3.Connection,
    asset_symbol: str,
) -> DexPoolDepth | None:
    """Return the latest real pool-depth snapshot for one asset.

    Returns None when the dex_pool_depths table or asset row is unavailable.
    This is deliberate: missing real data should be shown as unavailable, not
    replaced with fake or assumed liquidity.
    """
    normalized_symbol = _normalize_asset_symbol(asset_symbol)

    try:
        row = conn.execute(
            """
            SELECT
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
            FROM dex_pool_depths
            WHERE UPPER(asset_symbol) = ?
            ORDER BY fetched_at_utc DESC, id DESC
            LIMIT 1
            """,
            (normalized_symbol,),
        ).fetchone()
    except sqlite3.OperationalError as exc:
        if "no such table: dex_pool_depths" in str(exc):
            return None
        raise

    if row is None:
        return None

    return _row_to_pool_depth(row)


def get_latest_pool_depth(
    asset_symbol: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> DexPoolDepth | None:
    """Open the SQLite database and return latest real pool-depth for one asset."""
    db_path = Path(db_path)

    if not db_path.exists():
        return None

    with sqlite3.connect(db_path) as conn:
        return get_latest_pool_depth_from_connection(
            conn=conn,
            asset_symbol=asset_symbol,
        )


def get_latest_pool_depths(
    asset_symbols: Iterable[str] = DEFAULT_ASSET_SYMBOLS,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, DexPoolDepth | None]:
    """Return latest real pool-depth snapshots for multiple assets."""
    return {
        _normalize_asset_symbol(asset_symbol): get_latest_pool_depth(
            asset_symbol=asset_symbol,
            db_path=db_path,
        )
        for asset_symbol in asset_symbols
    }
