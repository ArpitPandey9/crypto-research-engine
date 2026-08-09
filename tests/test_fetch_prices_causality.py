from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest
import requests

from src.data.fetch_prices import HISTORICAL_PRICE_COLUMNS, PriceOracle


def _price_rows() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "timestamp": pd.Timestamp("2026-04-23 08:00:00+00:00"),
            "symbol": "ETHUSDT",
            "asset_type": "ETH",
            "open_time": pd.Timestamp("2026-04-23 08:00:00+00:00"),
            "close_time": pd.Timestamp("2026-04-23 08:59:59.999+00:00"),
            "price_available_at": pd.Timestamp("2026-04-23 09:00:00+00:00"),
            "open_price": 2344.43,
            "high_price": 2350.0,
            "low_price": 2330.0,
            "close_price": 2339.92,
            "price_usd": 2339.92,
            "source": "binance_spot_klines",
        },
        {
            "timestamp": pd.Timestamp("2026-04-23 09:00:00+00:00"),
            "symbol": "ETHUSDT",
            "asset_type": "ETH",
            "open_time": pd.Timestamp("2026-04-23 09:00:00+00:00"),
            "close_time": pd.Timestamp("2026-04-23 09:59:59.999+00:00"),
            "price_available_at": pd.Timestamp("2026-04-23 10:00:00+00:00"),
            "open_price": 2339.91,
            "high_price": 2345.0,
            "low_price": 2310.0,
            "close_price": 2316.25,
            "price_usd": 2316.25,
            "source": "binance_spot_klines",
        },
    ])


def test_historical_price_upsert_preserves_older_rows(tmp_path: Path) -> None:
    db = tmp_path / "prices.db"
    oracle = PriceOracle(db)
    with sqlite3.connect(db) as conn:
        pd.DataFrame([
            {"timestamp": "2026-04-22 00:00:00+00:00", "symbol": "ETHUSDT", "asset_type": "ETH", "price_usd": 2300.0}
        ]).to_sql("historical_prices", conn, if_exists="replace", index=False)
    oracle._persist_historical_prices(_price_rows().iloc[[0]])
    with sqlite3.connect(db) as conn:
        rows = pd.read_sql_query("SELECT timestamp, asset_type, price_usd FROM historical_prices ORDER BY timestamp", conn)
    assert len(rows) == 2
    assert float(rows.iloc[0]["price_usd"]) == 2300.0
    assert float(rows.iloc[1]["price_usd"]) == pytest.approx(2339.92)


def test_normalization_uses_only_price_available_before_transfer(tmp_path: Path) -> None:
    db = tmp_path / "prices.db"
    oracle = PriceOracle(db)
    with sqlite3.connect(db) as conn:
        pd.DataFrame([
            {
                "id": 1,
                "timestamp": "2026-04-23 09:32:45+00:00",
                "block_number": 1,
                "asset_type": "ETH",
                "amount": 819.99905374,
                "sender_address": "0xsender",
                "receiver_address": "0xreceiver",
                "transaction_hash": "0xhash",
            }
        ]).to_sql("institutional_transfers", conn, if_exists="replace", index=False)
    oracle._persist_historical_prices(_price_rows())
    out = oracle.normalize_whale_volume()
    row = out.iloc[0]
    assert float(row["price_usd"]) == pytest.approx(2339.92)
    assert pd.Timestamp(row["valuation_price_time"]) == pd.Timestamp("2026-04-23 09:00:00+00:00")
    assert float(row["valuation_lag_seconds"]) == pytest.approx(1965.0)
    assert float(row["true_usd_volume"]) == pytest.approx(819.99905374 * 2339.92)


def test_same_hour_close_is_not_available_at_mid_hour_event(tmp_path: Path) -> None:
    frame = PriceOracle._available_price_frame(_price_rows(), "ETH")
    event = pd.Timestamp("2026-04-23 09:32:45+00:00")
    eligible = frame[frame["valuation_price_time"] <= event]
    assert len(eligible) == 1
    assert float(eligible.iloc[-1]["price_usd"]) == pytest.approx(2339.92)


def _kline(open_ms: int, close_ms: int, open_price: str = "100", close_price: str = "101"):
    return [
        open_ms,
        open_price,
        "105",
        "95",
        close_price,
        "10",
        close_ms,
        "1000",
        5,
        "4",
        "400",
        "0",
    ]


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_asset_type_mapping_covers_known_and_unknown_symbols() -> None:
    assert PriceOracle._asset_type_for_symbol("ETHUSDT") == "ETH"
    assert PriceOracle._asset_type_for_symbol("BTCUSDT") == "BTC"
    assert PriceOracle._asset_type_for_symbol("SOLUSDT") == "SOLUSDT"


def test_download_symbol_prices_preserves_ohlc_and_availability(monkeypatch, tmp_path: Path) -> None:
    oracle = PriceOracle(tmp_path / "prices.db")
    captured = {}
    payload = [_kline(0, 3_599_999, open_price="100.5", close_price="101.25")]

    def fake_get(url, params, timeout):
        captured.update({"url": url, "params": params, "timeout": timeout})
        return _FakeResponse(payload)

    monkeypatch.setattr("src.data.fetch_prices.requests.get", fake_get)
    out = oracle._download_symbol_prices(
        "ETHUSDT",
        interval="1h",
        limit=500,
        start_time_ms=0,
        end_time_ms=3_600_000,
    )

    assert captured["url"] == oracle.binance_url
    assert captured["timeout"] == 15
    assert captured["params"] == {
        "symbol": "ETHUSDT",
        "interval": "1h",
        "limit": 500,
        "startTime": 0,
        "endTime": 3_600_000,
    }
    row = out.iloc[0]
    assert row["asset_type"] == "ETH"
    assert float(row["open_price"]) == pytest.approx(100.5)
    assert float(row["close_price"]) == pytest.approx(101.25)
    assert float(row["price_usd"]) == pytest.approx(101.25)
    assert pd.Timestamp(row["price_available_at"]) == pd.Timestamp("1970-01-01 01:00:00+00:00")
    assert row["source"] == "binance_spot_klines"


def test_download_symbol_prices_returns_stable_empty_frame(monkeypatch, tmp_path: Path) -> None:
    oracle = PriceOracle(tmp_path / "prices.db")
    monkeypatch.setattr(
        "src.data.fetch_prices.requests.get",
        lambda *args, **kwargs: _FakeResponse([]),
    )
    out = oracle._download_symbol_prices("BTCUSDT")
    assert out.empty
    assert list(out.columns) == list(HISTORICAL_PRICE_COLUMNS)


def test_schema_migration_and_upsert_are_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "prices.db"
    oracle = PriceOracle(db)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE historical_prices (timestamp TEXT NOT NULL, symbol TEXT, asset_type TEXT NOT NULL, price_usd REAL)"
        )
        conn.execute(
            "INSERT INTO historical_prices(timestamp,symbol,asset_type,price_usd) VALUES (?,?,?,?)",
            ("2026-04-23 08:00:00+00:00", "ETHUSDT", "ETH", 1.0),
        )
        conn.commit()

    oracle._persist_historical_prices(_price_rows().iloc[[0]])
    changed = _price_rows().iloc[[0]].copy()
    changed.loc[changed.index[0], "price_usd"] = 2400.0
    changed.loc[changed.index[0], "close_price"] = 2400.0
    oracle._persist_historical_prices(changed)

    with sqlite3.connect(db) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(historical_prices)")}
        rows = conn.execute(
            "SELECT COUNT(*), MAX(price_usd), MAX(close_price) FROM historical_prices WHERE asset_type='ETH'"
        ).fetchone()
    assert {"open_time", "close_time", "price_available_at", "open_price", "close_price", "source"}.issubset(cols)
    assert rows == (1, 2400.0, 2400.0)


def test_persist_empty_price_frame_is_noop(tmp_path: Path) -> None:
    db = tmp_path / "prices.db"
    oracle = PriceOracle(db)
    oracle._persist_historical_prices(pd.DataFrame())
    assert not db.exists()


def test_download_bulk_prices_persists_successful_symbols_and_tolerates_one_failure(monkeypatch, tmp_path: Path) -> None:
    db = tmp_path / "prices.db"
    oracle = PriceOracle(db)

    def fake_download(symbol, interval="1h", limit=1000, start_time_ms=None, end_time_ms=None):
        if symbol == "BTCUSDT":
            raise requests.RequestException("temporary")
        return _price_rows().iloc[[0]].copy()

    monkeypatch.setattr(oracle, "_download_symbol_prices", fake_download)
    out = oracle.download_bulk_prices(limit=12)
    assert len(out) == 1
    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM historical_prices").fetchone()[0]
    assert count == 1


def test_download_bulk_prices_does_not_create_history_when_all_downloads_fail(monkeypatch, tmp_path: Path) -> None:
    db = tmp_path / "prices.db"
    oracle = PriceOracle(db)

    def fail(*args, **kwargs):
        raise requests.RequestException("offline")

    monkeypatch.setattr(oracle, "_download_symbol_prices", fail)
    out = oracle.download_bulk_prices()
    assert out.empty
    assert list(out.columns) == list(HISTORICAL_PRICE_COLUMNS)
    assert not db.exists()


def test_download_price_range_validates_window(tmp_path: Path) -> None:
    oracle = PriceOracle(tmp_path / "prices.db")
    with pytest.raises(ValueError, match="end_time must be later"):
        oracle.download_price_range("2026-01-02", "2026-01-01")


def test_download_price_range_paginates_both_assets_and_persists(monkeypatch, tmp_path: Path) -> None:
    db = tmp_path / "prices.db"
    oracle = PriceOracle(db)
    calls = []

    def make_frame(symbol: str, hour: int) -> pd.DataFrame:
        ts = pd.Timestamp("2026-01-01 00:00:00+00:00") + pd.Timedelta(hours=hour)
        close = ts + pd.Timedelta(hours=1) - pd.Timedelta(milliseconds=1)
        asset = "ETH" if symbol == "ETHUSDT" else "BTC"
        price = 100.0 + hour
        return pd.DataFrame([{
            "timestamp": ts,
            "symbol": symbol,
            "asset_type": asset,
            "open_time": ts,
            "close_time": close,
            "price_available_at": close + pd.Timedelta(milliseconds=1),
            "open_price": price,
            "high_price": price + 2,
            "low_price": price - 2,
            "close_price": price + 1,
            "price_usd": price + 1,
            "source": "binance_spot_klines",
        }])

    def fake_download(symbol, interval="1h", limit=1000, start_time_ms=None, end_time_ms=None):
        calls.append((symbol, start_time_ms, end_time_ms, limit))
        # Return one row; because len(frame) < limit, each asset terminates after one page.
        return make_frame(symbol, 0)

    monkeypatch.setattr(oracle, "_download_symbol_prices", fake_download)
    out = oracle.download_price_range(
        "2026-01-01 00:00:00+00:00",
        "2026-01-01 03:00:00+00:00",
        limit=2,
    )
    assert set(out["asset_type"]) == {"ETH", "BTC"}
    assert len(calls) == 2
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM historical_prices").fetchone()[0] == 2


def test_download_price_range_returns_empty_when_provider_has_no_rows(monkeypatch, tmp_path: Path) -> None:
    oracle = PriceOracle(tmp_path / "prices.db")
    monkeypatch.setattr(
        oracle,
        "_download_symbol_prices",
        lambda *args, **kwargs: pd.DataFrame(columns=HISTORICAL_PRICE_COLUMNS),
    )
    out = oracle.download_price_range("2026-01-01", "2026-01-02")
    assert out.empty
    assert list(out.columns) == list(HISTORICAL_PRICE_COLUMNS)


def test_available_price_frame_supports_close_time_fallback_and_empty_asset() -> None:
    prices = pd.DataFrame([
        {
            "asset_type": "ETH",
            "close_time": "2026-01-01 00:59:59.999+00:00",
            "price_usd": 123.0,
        }
    ])
    out = PriceOracle._available_price_frame(prices, "ETH")
    assert pd.Timestamp(out.iloc[0]["valuation_price_time"]) == pd.Timestamp("2026-01-01 01:00:00+00:00")
    assert PriceOracle._available_price_frame(prices, "BTC").empty


def test_normalization_handles_stable_unknown_and_missing_crypto_price(tmp_path: Path) -> None:
    db = tmp_path / "prices.db"
    oracle = PriceOracle(db)
    transfers = pd.DataFrame([
        {
            "id": 1,
            "timestamp": "2026-04-23 07:30:00+00:00",  # before first completed ETH price
            "block_number": 1,
            "asset_type": "ETH",
            "amount": 2.0,
            "sender_address": "0xa",
            "receiver_address": "0xb",
            "transaction_hash": "0x1",
        },
        {
            "id": 2,
            "timestamp": "2026-04-23 09:32:45+00:00",
            "block_number": 2,
            "asset_type": "USDC",
            "amount": 25.0,
            "sender_address": "0xa",
            "receiver_address": "0xb",
            "transaction_hash": "0x2",
        },
        {
            "id": 3,
            "timestamp": "2026-04-23 09:32:45+00:00",
            "block_number": 3,
            "asset_type": "XYZ",
            "amount": 3.0,
            "sender_address": "0xa",
            "receiver_address": "0xb",
            "transaction_hash": "0x3",
        },
    ])
    with sqlite3.connect(db) as conn:
        transfers.to_sql("institutional_transfers", conn, if_exists="replace", index=False)
    oracle._persist_historical_prices(_price_rows())
    out = oracle.normalize_whale_volume().set_index("asset_type")
    assert pd.isna(out.loc["ETH", "price_usd"])
    assert float(out.loc["USDC", "price_usd"]) == 1.0
    assert float(out.loc["USDC", "true_usd_volume"]) == 25.0
    assert out.loc["USDC", "valuation_method"] == "stablecoin_parity_assumption"
    assert pd.isna(out.loc["XYZ", "price_usd"])
    assert out.loc["XYZ", "valuation_method"] == "unavailable"


def test_normalization_returns_empty_for_missing_tables_or_empty_inputs(tmp_path: Path) -> None:
    db = tmp_path / "prices.db"
    oracle = PriceOracle(db)
    assert oracle.normalize_whale_volume().empty

    with sqlite3.connect(db) as conn:
        pd.DataFrame(columns=[
            "timestamp", "asset_type", "amount", "sender_address", "receiver_address"
        ]).to_sql("institutional_transfers", conn, if_exists="replace", index=False)
        _price_rows().to_sql("historical_prices", conn, if_exists="replace", index=False)
    assert oracle.normalize_whale_volume().empty


def test_sql_value_serializes_missing_timestamp_and_scalar() -> None:
    assert PriceOracle._sql_value(pd.NA) is None
    assert PriceOracle._sql_value(pd.Timestamp("2026-01-01 00:00:00+00:00")) == "2026-01-01 00:00:00+00:00"
    assert PriceOracle._sql_value(7.5) == 7.5
