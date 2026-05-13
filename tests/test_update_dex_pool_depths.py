import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.data.dexscreener_client import DexPoolDepth
from src.data.update_dex_pool_depths import (
    create_dex_pool_depths_table,
    insert_pool_depth,
    update_dex_pool_depths,
)


def make_pool(asset_symbol="ETH", liquidity_usd=1_000_000.0):
    return DexPoolDepth(
        fetched_at_utc=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        asset_symbol=asset_symbol,
        chain_id="ethereum",
        dex_id="uniswap",
        pair_address="0xpair",
        base_token_symbol="WETH" if asset_symbol == "ETH" else "WBTC",
        quote_token_symbol="USDC",
        price_usd=3000.0 if asset_symbol == "ETH" else 80000.0,
        liquidity_usd=liquidity_usd,
        liquidity_base=100.0,
        liquidity_quote=700_000.0,
        volume_h24=50_000.0,
        pair_url="https://dexscreener.com/ethereum/0xpair",
    )


def test_create_dex_pool_depths_table_creates_expected_columns(tmp_path):
    db_path = tmp_path / "test.db"

    with sqlite3.connect(db_path) as conn:
        create_dex_pool_depths_table(conn)
        columns = conn.execute("PRAGMA table_info(dex_pool_depths)").fetchall()

    column_names = {column[1] for column in columns}

    assert "id" in column_names
    assert "fetched_at_utc" in column_names
    assert "asset_symbol" in column_names
    assert "chain_id" in column_names
    assert "dex_id" in column_names
    assert "pair_address" in column_names
    assert "liquidity_usd" in column_names
    assert "pair_url" in column_names


def test_insert_pool_depth_persists_real_normalized_pool_record(tmp_path):
    db_path = tmp_path / "test.db"
    pool = make_pool(asset_symbol="ETH", liquidity_usd=5_000_000.0)

    with sqlite3.connect(db_path) as conn:
        create_dex_pool_depths_table(conn)
        insert_pool_depth(conn, pool)
        row = conn.execute(
            """
            SELECT
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
            """
        ).fetchone()

    assert row == (
        "ETH",
        "ethereum",
        "uniswap",
        "0xpair",
        "WETH",
        "USDC",
        3000.0,
        5_000_000.0,
        100.0,
        700_000.0,
        50_000.0,
        "https://dexscreener.com/ethereum/0xpair",
    )


def test_update_dex_pool_depths_fetches_and_inserts_supported_assets(tmp_path):
    db_path = tmp_path / "test.db"
    requested_assets = []

    def fake_fetcher(asset_symbol):
        requested_assets.append(asset_symbol)
        return make_pool(asset_symbol=asset_symbol)

    inserted = update_dex_pool_depths(
        db_path=db_path,
        asset_symbols=("ETH", "WBTC"),
        fetcher=fake_fetcher,
    )

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT asset_symbol, liquidity_usd
            FROM dex_pool_depths
            ORDER BY asset_symbol
            """
        ).fetchall()

    assert requested_assets == ["ETH", "WBTC"]
    assert [pool.asset_symbol for pool in inserted] == ["ETH", "WBTC"]
    assert rows == [("ETH", 1_000_000.0), ("WBTC", 1_000_000.0)]


def test_update_dex_pool_depths_does_not_swallow_fetch_errors(tmp_path):
    db_path = tmp_path / "test.db"

    def failing_fetcher(asset_symbol):
        raise RuntimeError(f"fetch failed for {asset_symbol}")

    with pytest.raises(RuntimeError, match="fetch failed for ETH"):
        update_dex_pool_depths(
            db_path=db_path,
            asset_symbols=("ETH",),
            fetcher=failing_fetcher,
        )
