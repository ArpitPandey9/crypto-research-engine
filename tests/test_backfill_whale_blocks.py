from __future__ import annotations

import pytest

from scripts.backfill_whale_blocks import backfill_blocks, resolve_block_range


class FakeClient:
    def __init__(self, fail_on_block=None):
        self.fail_on_block = fail_on_block
        self.fetched_blocks = []
        self.scanned_blocks = []

    def fetch_block_data(self, block_number: int):
        self.fetched_blocks.append(block_number)

        if block_number == self.fail_on_block:
            raise RuntimeError("rpc failure")

        return {"number": block_number}

    def scan_for_whales(self, block_data, min_usd_value: float):
        self.scanned_blocks.append((block_data["number"], min_usd_value))


def test_resolve_block_range_uses_explicit_range() -> None:
    assert resolve_block_range(
        start_block=100,
        end_block=105,
        latest_blocks=None,
        latest_block=200,
    ) == (100, 105)


def test_resolve_block_range_uses_latest_window() -> None:
    assert resolve_block_range(
        start_block=None,
        end_block=None,
        latest_blocks=5,
        latest_block=200,
    ) == (196, 200)


def test_resolve_block_range_rejects_mixed_modes() -> None:
    with pytest.raises(ValueError, match="Use either"):
        resolve_block_range(
            start_block=100,
            end_block=105,
            latest_blocks=5,
            latest_block=200,
        )


def test_resolve_block_range_rejects_missing_endpoints() -> None:
    with pytest.raises(ValueError, match="Provide both"):
        resolve_block_range(
            start_block=100,
            end_block=None,
            latest_blocks=None,
            latest_block=200,
        )


def test_resolve_block_range_rejects_invalid_order() -> None:
    with pytest.raises(ValueError, match="greater than or equal"):
        resolve_block_range(
            start_block=105,
            end_block=100,
            latest_blocks=None,
            latest_block=200,
        )


def test_backfill_blocks_scans_inclusive_range() -> None:
    client = FakeClient()

    scanned_count = backfill_blocks(
        client=client,
        start_block=100,
        end_block=102,
        min_usd_value=100000.0,
        sleep_seconds=0.0,
    )

    assert scanned_count == 3
    assert client.fetched_blocks == [100, 101, 102]
    assert client.scanned_blocks == [
        (100, 100000.0),
        (101, 100000.0),
        (102, 100000.0),
    ]


def test_backfill_blocks_continues_after_fetch_error() -> None:
    client = FakeClient(fail_on_block=101)

    scanned_count = backfill_blocks(
        client=client,
        start_block=100,
        end_block=102,
        min_usd_value=50000.0,
        sleep_seconds=0.0,
    )

    assert scanned_count == 2
    assert client.fetched_blocks == [100, 101, 102]
    assert client.scanned_blocks == [
        (100, 50000.0),
        (102, 50000.0),
    ]


def test_backfill_blocks_rejects_negative_threshold() -> None:
    with pytest.raises(ValueError, match="min_usd_value cannot be negative"):
        backfill_blocks(
            client=FakeClient(),
            start_block=100,
            end_block=101,
            min_usd_value=-1.0,
            sleep_seconds=0.0,
        )