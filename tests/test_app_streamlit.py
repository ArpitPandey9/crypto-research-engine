from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_APP = PROJECT_ROOT / "app.py"
APP_TEST_TIMEOUT = 15


def _write_enriched_whales(
    conn: sqlite3.Connection,
    rows: list[dict],
) -> None:
    pd.DataFrame(rows).to_sql("enriched_whales", conn, if_exists="replace", index=False)


def _write_historical_prices(
    conn: sqlite3.Connection,
    rows: list[dict],
) -> None:
    pd.DataFrame(rows).to_sql("historical_prices", conn, if_exists="replace", index=False)


def _seed_full_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)

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
def temp_app_project(tmp_path: Path) -> dict[str, Path]:
    """
    Build an isolated temporary app project:
    - copy app.py into tmp_path
    - seed tmp_path/data/db/whale_data.db
    """
    app_copy = tmp_path / "app.py"
    shutil.copy2(SOURCE_APP, app_copy)

    db_path = tmp_path / "data" / "db" / "whale_data.db"
    _seed_full_db(db_path)

    return {
        "app_path": app_copy,
        "db_path": db_path,
    }


@pytest.fixture
def temp_app_project_missing_db(tmp_path: Path) -> dict[str, Path]:
    """
    Build an isolated temporary app project with no database file.
    """
    app_copy = tmp_path / "app.py"
    shutil.copy2(SOURCE_APP, app_copy)

    return {
        "app_path": app_copy,
        "db_path": tmp_path / "data" / "db" / "whale_data.db",
    }


def _run_app(app_path: Path) -> AppTest:
    return AppTest.from_file(app_path).run(timeout=APP_TEST_TIMEOUT)


def test_app_renders_core_dashboard(temp_app_project: dict[str, Path]) -> None:
    at = _run_app(temp_app_project["app_path"])

    assert len(at.error) == 0

    assert len(at.title) == 1
    assert at.title[0].value == "Whale Flow Research Engine"

    assert len(at.caption) >= 1

    # Core controls exist
    assert len(at.sidebar.selectbox) == 1
    assert len(at.sidebar.slider) == 1
    assert len(at.sidebar.number_input) == 2
    assert len(at.sidebar.button) >= 2

    # Main sections render
    subheaders = {x.value for x in at.subheader}
    expected_subheaders = {
        "Data Freshness",
        "Research Summary",
        "Equity Curve Comparison",
        "Rolling Whale Net Flow",
        "Hourly Whale USD Volume",
        "How to read this dashboard",
        "Latest Research Rows",
        "Signal Distribution",
    }
    assert expected_subheaders.issubset(subheaders)

    # Tables render
    assert len(at.dataframe) >= 2


def test_app_can_switch_to_wbtc_and_rerun(temp_app_project: dict[str, Path]) -> None:
    at = _run_app(temp_app_project["app_path"])

    assert len(at.error) == 0

    at.sidebar.selectbox[0].set_value("WBTC")
    at.sidebar.slider[0].set_value(24)
    at.sidebar.number_input[0].set_value(100000.0)
    at.sidebar.number_input[1].set_value(0.002)

    # Refresh button is first, submit button is second in current app structure
    at.sidebar.button[1].click().run(timeout=APP_TEST_TIMEOUT)

    assert len(at.error) == 0
    assert len(at.dataframe) >= 1

    latest_rows_df = at.dataframe[0].value
    assert not latest_rows_df.empty
    assert "target_asset" in latest_rows_df.columns
    assert set(latest_rows_df["target_asset"].astype(str).unique()) == {"WBTC"}


def test_app_refresh_button_reruns_without_error(temp_app_project: dict[str, Path]) -> None:
    at = _run_app(temp_app_project["app_path"])

    assert len(at.error) == 0

    at.sidebar.button[0].click().run(timeout=APP_TEST_TIMEOUT)

    assert len(at.error) == 0
    assert len(at.title) == 1
    assert at.title[0].value == "Whale Flow Research Engine"


def test_app_shows_missing_db_error(temp_app_project_missing_db: dict[str, Path]) -> None:
    at = AppTest.from_file(temp_app_project_missing_db["app_path"]).run(timeout=APP_TEST_TIMEOUT)

    assert len(at.error) >= 1
    assert "Database not found at:" in at.error[0].value