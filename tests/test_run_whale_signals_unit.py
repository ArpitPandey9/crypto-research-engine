from __future__ import annotations

import pandas as pd
import pytest
from pandas.errors import DatabaseError as PandasDatabaseError

import src.strategies.run_whale_signals as runner


def make_events_df() -> pd.DataFrame:
    return pd.DataFrame(
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
        ]
    )


def make_prices_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": "2026-01-01 00:00:00+00:00",
                "asset_type": "ETH",
                "price_usd": 3000.0,
            }
        ]
    )


def make_results_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": "2026-01-01 00:00:00+00:00",
                "target_asset": "ETH",
                "price_usd": 3000.0,
                "pressure_usd": 120000.0,
                "rolling_net_flow": 120000.0,
                "signal": 1,
                "position": 0,
                "asset_return": 0.0,
                "trade_flag": 0,
                "net_strategy_return": 0.0,
                "equity_asset": 1.0,
                "equity_strategy_net": 1.0,
            }
        ]
    )


def test_extract_table_name_returns_unknown_for_non_from_query() -> None:
    assert runner._extract_table_name_from_query("PRAGMA table_info(x)") == "unknown_table"


def test_load_table_reraises_non_missing_table_database_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    db_path = tmp_path / "unit.db"

    def fake_read_sql_query(query: str, conn) -> pd.DataFrame:
        raise PandasDatabaseError("Execution failed on sql 'SELECT 1': syntax error")

    monkeypatch.setattr(runner.pd, "read_sql_query", fake_read_sql_query)

    with pytest.raises(PandasDatabaseError):
        runner.load_table("SELECT 1", db_path=db_path)


def test_main_reports_strategy_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_load_table(query: str):
        if "enriched_whales" in query:
            return make_events_df()
        if "historical_prices" in query:
            return make_prices_df()
        raise AssertionError("Unexpected query")

    def fake_analyze_whale_flow(**kwargs):
        raise ValueError("Unsupported target_asset=BAD")

    monkeypatch.setattr(runner, "load_table", fake_load_table)
    monkeypatch.setattr(runner, "analyze_whale_flow", fake_analyze_whale_flow)

    runner.main(target_asset="BAD")

    captured = capsys.readouterr()
    assert "ERROR while building signals" in captured.out
    assert "Unsupported target_asset=BAD" in captured.out


def test_main_reports_empty_signal_dataframe(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_load_table(query: str):
        if "enriched_whales" in query:
            return make_events_df()
        if "historical_prices" in query:
            return make_prices_df()
        raise AssertionError("Unexpected query")

    def fake_analyze_whale_flow(**kwargs):
        return pd.DataFrame()

    monkeypatch.setattr(runner, "load_table", fake_load_table)
    monkeypatch.setattr(runner, "analyze_whale_flow", fake_analyze_whale_flow)

    runner.main()

    captured = capsys.readouterr()
    assert "ERROR: No signal dataframe was produced." in captured.out


def test_main_reports_empty_backtest_dataframe(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_load_table(query: str):
        if "enriched_whales" in query:
            return make_events_df()
        if "historical_prices" in query:
            return make_prices_df()
        raise AssertionError("Unexpected query")

    def fake_analyze_whale_flow(**kwargs):
        return pd.DataFrame(
            [
                {
                    "timestamp": "2026-01-01 00:00:00+00:00",
                    "target_asset": "ETH",
                    "price_usd": 3000.0,
                    "rolling_net_flow": 120000.0,
                    "signal": 1,
                }
            ]
        )

    def fake_backtest_whale_strategy(df: pd.DataFrame, cost_per_trade: float):
        return pd.DataFrame()

    monkeypatch.setattr(runner, "load_table", fake_load_table)
    monkeypatch.setattr(runner, "analyze_whale_flow", fake_analyze_whale_flow)
    monkeypatch.setattr(runner, "backtest_whale_strategy", fake_backtest_whale_strategy)

    runner.main()

    captured = capsys.readouterr()
    assert "ERROR: Backtest returned an empty dataframe." in captured.out


def test_main_happy_path_still_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_load_table(query: str):
        if "enriched_whales" in query:
            return make_events_df()
        if "historical_prices" in query:
            return make_prices_df()
        raise AssertionError("Unexpected query")

    def fake_analyze_whale_flow(**kwargs):
        return pd.DataFrame(
            [
                {
                    "timestamp": "2026-01-01 00:00:00+00:00",
                    "target_asset": "ETH",
                    "price_usd": 3000.0,
                    "rolling_net_flow": 120000.0,
                    "signal": 1,
                }
            ]
        )

    monkeypatch.setattr(runner, "load_table", fake_load_table)
    monkeypatch.setattr(runner, "analyze_whale_flow", fake_analyze_whale_flow)
    monkeypatch.setattr(runner, "backtest_whale_strategy", lambda **kwargs: make_results_df())

    runner.main()

    captured = capsys.readouterr()
    assert "WHALE FLOW STRATEGY RESEARCH SUMMARY" in captured.out
    assert "Target Asset            : ETH" in captured.out