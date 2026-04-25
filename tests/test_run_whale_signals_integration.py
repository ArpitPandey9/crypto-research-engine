# tests/test_run_whale_signals_integration.py

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

import src.strategies.run_whale_signals as runner


def _write_enriched_whales(
    conn: sqlite3.Connection,
    rows: list[dict],
) -> None:
    df = pd.DataFrame(rows)
    df.to_sql("enriched_whales", conn, if_exists="replace", index=False)


def _write_historical_prices(
    conn: sqlite3.Connection,
    rows: list[dict],
) -> None:
    df = pd.DataFrame(rows)
    df.to_sql("historical_prices", conn, if_exists="replace", index=False)


def _seed_full_db(db_path: Path) -> None:
    """
    Create a fully seeded SQLite database with both enriched whale events
    and historical prices.
    """
    with sqlite3.connect(db_path) as conn:
        _write_enriched_whales(
            conn,
            [
                {
                    "timestamp": "2026-01-01 00:10:00+00:00",
                    "asset_type": "ETH",
                    "amount": 40.0,
                    "sender_address": "0xaaa",
                    "receiver_address": "0xwallet1",
                    "price_usd": 3000.0,
                    "true_usd_volume": 120000.0,
                },
                {
                    "timestamp": "2026-01-01 01:15:00+00:00",
                    "asset_type": "ETH",
                    "amount": 50.0,
                    "sender_address": "0xbbb",
                    "receiver_address": "0x28C6c06298d514Db089934071355E5743bf21d60",
                    "price_usd": 3100.0,
                    "true_usd_volume": 155000.0,
                },
                {
                    "timestamp": "2026-01-01 02:05:00+00:00",
                    "asset_type": "ETH",
                    "amount": 45.0,
                    "sender_address": "0xccc",
                    "receiver_address": "0xwallet2",
                    "price_usd": 3200.0,
                    "true_usd_volume": 144000.0,
                },
                {
                    "timestamp": "2026-01-01 00:20:00+00:00",
                    "asset_type": "WBTC",
                    "amount": 3.0,
                    "sender_address": "0xddd",
                    "receiver_address": "0xwallet3",
                    "price_usd": 60000.0,
                    "true_usd_volume": 180000.0,
                },
            ],
        )

        _write_historical_prices(
            conn,
            [
                {"timestamp": "2026-01-01 00:00:00+00:00", "asset_type": "ETH", "price_usd": 3000.0},
                {"timestamp": "2026-01-01 01:00:00+00:00", "asset_type": "ETH", "price_usd": 3100.0},
                {"timestamp": "2026-01-01 02:00:00+00:00", "asset_type": "ETH", "price_usd": 3200.0},
                {"timestamp": "2026-01-01 03:00:00+00:00", "asset_type": "ETH", "price_usd": 3300.0},
                {"timestamp": "2026-01-01 00:00:00+00:00", "asset_type": "BTC", "price_usd": 60000.0},
                {"timestamp": "2026-01-01 01:00:00+00:00", "asset_type": "BTC", "price_usd": 60500.0},
                {"timestamp": "2026-01-01 02:00:00+00:00", "asset_type": "BTC", "price_usd": 61000.0},
            ],
        )


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    """
    Return a temporary SQLite database path populated with realistic test data.
    """
    db_path = tmp_path / "whale_data.db"
    _seed_full_db(db_path)
    return db_path


@pytest.fixture
def patch_runner_db(monkeypatch: pytest.MonkeyPatch, seeded_db: Path) -> Path:
    """
    Patch the runner module so integration tests use the temporary SQLite DB.

    Important:
    runner.load_table() has a default db_path bound at function definition time,
    so we replace the function with a wrapper that always points at the temp DB.
    """
    monkeypatch.setattr(runner, "DB_PATH", seeded_db)

    original_load_table = runner.load_table

    def _patched_load_table(query: str):
        return original_load_table(query, db_path=seeded_db)

    monkeypatch.setattr(runner, "load_table", _patched_load_table)
    return seeded_db


def test_load_table_reads_from_seeded_sqlite_db(patch_runner_db: Path) -> None:
    df = runner.load_table("SELECT * FROM enriched_whales")

    assert not df.empty
    assert "asset_type" in df.columns
    assert set(df["asset_type"].astype(str).str.upper().unique()) == {"ETH", "WBTC"}


def test_main_prints_research_summary_for_eth(
    patch_runner_db: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner.main(
        target_asset="ETH",
        window_hours=2,
        min_flow_usd=0.0,
        cost_per_trade=0.001,
    )

    captured = capsys.readouterr()
    stdout = captured.out

    assert "WHALE FLOW STRATEGY RESEARCH SUMMARY" in stdout
    assert "Target Asset            : ETH" in stdout
    assert "Strategy Net Equity" in stdout
    assert "Alpha vs Buy & Hold" in stdout


def test_main_prints_research_summary_for_wbtc(
    patch_runner_db: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner.main(
        target_asset="WBTC",
        window_hours=2,
        min_flow_usd=0.0,
        cost_per_trade=0.001,
    )

    captured = capsys.readouterr()
    stdout = captured.out

    assert "WHALE FLOW STRATEGY RESEARCH SUMMARY" in stdout
    assert "Target Asset            : WBTC" in stdout
    assert "Strategy Net Equity" in stdout


def test_main_reports_missing_enriched_whales_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / "missing_events.db"

    with sqlite3.connect(db_path) as conn:
        _write_historical_prices(
            conn,
            [
                {"timestamp": "2026-01-01 00:00:00+00:00", "asset_type": "ETH", "price_usd": 3000.0},
            ],
        )

    monkeypatch.setattr(runner, "DB_PATH", db_path)

    original_load_table = runner.load_table

    def _patched_load_table(query: str):
        return original_load_table(query, db_path=db_path)

    monkeypatch.setattr(runner, "load_table", _patched_load_table)

    runner.main()

    captured = capsys.readouterr()
    stdout = captured.out

    assert "ERROR: Table 'enriched_whales' not found" in stdout


def test_main_reports_empty_enriched_whales(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / "empty_events.db"

    with sqlite3.connect(db_path) as conn:
        pd.DataFrame(
            columns=[
                "timestamp",
                "asset_type",
                "amount",
                "sender_address",
                "receiver_address",
                "price_usd",
                "true_usd_volume",
            ]
        ).to_sql("enriched_whales", conn, if_exists="replace", index=False)

        _write_historical_prices(
            conn,
            [
                {"timestamp": "2026-01-01 00:00:00+00:00", "asset_type": "ETH", "price_usd": 3000.0},
            ],
        )

    monkeypatch.setattr(runner, "DB_PATH", db_path)

    original_load_table = runner.load_table

    def _patched_load_table(query: str):
        return original_load_table(query, db_path=db_path)

    monkeypatch.setattr(runner, "load_table", _patched_load_table)

    runner.main()

    captured = capsys.readouterr()
    stdout = captured.out

    assert "ERROR: enriched_whales is empty" in stdout


def test_main_reports_missing_historical_prices_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / "missing_prices.db"

    with sqlite3.connect(db_path) as conn:
        _write_enriched_whales(
            conn,
            [
                {
                    "timestamp": "2026-01-01 00:10:00+00:00",
                    "asset_type": "ETH",
                    "amount": 40.0,
                    "sender_address": "0xaaa",
                    "receiver_address": "0xwallet1",
                    "price_usd": 3000.0,
                    "true_usd_volume": 120000.0,
                }
            ],
        )

    monkeypatch.setattr(runner, "DB_PATH", db_path)

    original_load_table = runner.load_table

    def _patched_load_table(query: str):
        return original_load_table(query, db_path=db_path)

    monkeypatch.setattr(runner, "load_table", _patched_load_table)

    runner.main()

    captured = capsys.readouterr()
    stdout = captured.out

    assert "ERROR: Table 'historical_prices' not found" in stdout