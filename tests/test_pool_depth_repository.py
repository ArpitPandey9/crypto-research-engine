import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.data.dexscreener_client import DexPoolDepth
from src.data.pool_depth_repository import (
    get_latest_pool_depth,
    get_latest_pool_depths,
    get_latest_pool_depth_from_connection,
)
from src.data.update_dex_pool_depths import (
    create_dex_pool_depths_table,
    insert_pool_depth,
)


def make_pool(
    asset_symbol="ETH",
    fetched_at_utc=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
    liquidity_usd=1_000_000.0,
    pair_address="0xpair",
):
    return DexPoolDepth(
        fetched_at_utc=fetched_at_utc,
        asset_symbol=asset_symbol,
        chain_id="ethereum",
        dex_id="uniswap",
        pair_address=pair_address,
        base_token_symbol="WETH" if asset_symbol == "ETH" else "WBTC",
        quote_token_symbol="USDC",
        price_usd=3000.0 if asset_symbol == "ETH" else 80000.0,
        liquidity_usd=liquidity_usd,
        liquidity_base=100.0,
        liquidity_quote=700_000.0,
        volume_h24=50_000.0,
        pair_url=f"https://dexscreener.com/ethereum/{pair_address}",
    )


def test_get_latest_pool_depth_from_connection_returns_latest_real_snapshot(tmp_path):
    db_path = tmp_path / "test.db"

    older_pool = make_pool(
        asset_symbol="ETH",
        fetched_at_utc=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        liquidity_usd=1_000_000.0,
        pair_address="0xolder",
    )
    newer_pool = make_pool(
        asset_symbol="ETH",
        fetched_at_utc=datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc),
        liquidity_usd=2_000_000.0,
        pair_address="0xnewer",
    )

    with sqlite3.connect(db_path) as conn:
        create_dex_pool_depths_table(conn)
        insert_pool_depth(conn, older_pool)
        insert_pool_depth(conn, newer_pool)

        latest = get_latest_pool_depth_from_connection(conn, "ETH")

    assert latest is not None
    assert latest.asset_symbol == "ETH"
    assert latest.pair_address == "0xnewer"
    assert latest.liquidity_usd == pytest.approx(2_000_000.0)
    assert latest.fetched_at_utc == datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc)


def test_get_latest_pool_depth_from_connection_is_case_insensitive(tmp_path):
    db_path = tmp_path / "test.db"

    with sqlite3.connect(db_path) as conn:
        create_dex_pool_depths_table(conn)
        insert_pool_depth(conn, make_pool(asset_symbol="ETH"))

        latest = get_latest_pool_depth_from_connection(conn, "eth")

    assert latest is not None
    assert latest.asset_symbol == "ETH"


def test_get_latest_pool_depth_from_connection_returns_none_for_missing_asset(tmp_path):
    db_path = tmp_path / "test.db"

    with sqlite3.connect(db_path) as conn:
        create_dex_pool_depths_table(conn)
        insert_pool_depth(conn, make_pool(asset_symbol="ETH"))

        latest = get_latest_pool_depth_from_connection(conn, "WBTC")

    assert latest is None


def test_get_latest_pool_depth_from_connection_returns_none_when_table_missing(tmp_path):
    db_path = tmp_path / "test.db"

    with sqlite3.connect(db_path) as conn:
        latest = get_latest_pool_depth_from_connection(conn, "ETH")

    assert latest is None


def test_get_latest_pool_depth_returns_none_when_database_missing(tmp_path):
    missing_db_path = tmp_path / "missing.db"

    latest = get_latest_pool_depth("ETH", db_path=missing_db_path)

    assert latest is None


def test_get_latest_pool_depth_reads_latest_record_from_database_path(tmp_path):
    db_path = tmp_path / "test.db"

    with sqlite3.connect(db_path) as conn:
        create_dex_pool_depths_table(conn)
        insert_pool_depth(
            conn,
            make_pool(
                asset_symbol="WBTC",
                liquidity_usd=9_000_000.0,
                pair_address="0xwbtc",
            ),
        )

    latest = get_latest_pool_depth("WBTC", db_path=db_path)

    assert latest is not None
    assert latest.asset_symbol == "WBTC"
    assert latest.liquidity_usd == pytest.approx(9_000_000.0)
    assert latest.pair_address == "0xwbtc"


def test_get_latest_pool_depths_returns_mapping_for_multiple_assets(tmp_path):
    db_path = tmp_path / "test.db"

    with sqlite3.connect(db_path) as conn:
        create_dex_pool_depths_table(conn)
        insert_pool_depth(conn, make_pool(asset_symbol="ETH", liquidity_usd=1_000_000.0))
        insert_pool_depth(conn, make_pool(asset_symbol="WBTC", liquidity_usd=2_000_000.0))

    latest_by_asset = get_latest_pool_depths(("ETH", "WBTC", "DOGE"), db_path=db_path)

    assert latest_by_asset["ETH"] is not None
    assert latest_by_asset["WBTC"] is not None
    assert latest_by_asset["DOGE"] is None
    assert latest_by_asset["ETH"].liquidity_usd == pytest.approx(1_000_000.0)
    assert latest_by_asset["WBTC"].liquidity_usd == pytest.approx(2_000_000.0)
