"""Backfill historical Ethereum blocks for whale-transfer research.

This script scans a controlled range of Ethereum blocks and persists real
whale-transfer observations into the local SQLite vault.

It does not fabricate events.
It only stores transfers detected from real block data.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Backfill historical Ethereum blocks for whale-transfer research."
    )

    parser.add_argument(
        "--start-block",
        type=int,
        default=None,
        help="First Ethereum block number to scan.",
    )
    parser.add_argument(
        "--end-block",
        type=int,
        default=None,
        help="Last Ethereum block number to scan, inclusive.",
    )
    parser.add_argument(
        "--latest-blocks",
        type=int,
        default=None,
        help="Scan this many blocks ending at the latest block.",
    )
    parser.add_argument(
        "--min-usd-value",
        type=float,
        default=100000.0,
        help="Minimum ERC-20 token amount threshold used by the scanner.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Optional pause between block requests to reduce RPC pressure.",
    )

    return parser.parse_args()


def resolve_block_range(
    start_block: int | None,
    end_block: int | None,
    latest_blocks: int | None,
    latest_block: int,
) -> tuple[int, int]:
    """Resolve CLI options into an inclusive block range."""
    has_explicit_range = start_block is not None or end_block is not None
    has_latest_window = latest_blocks is not None

    if has_explicit_range and has_latest_window:
        raise ValueError("Use either --start-block/--end-block or --latest-blocks, not both.")

    if has_latest_window:
        if latest_blocks is None or latest_blocks <= 0:
            raise ValueError("--latest-blocks must be greater than zero.")

        return max(0, latest_block - latest_blocks + 1), latest_block

    if start_block is None or end_block is None:
        raise ValueError("Provide both --start-block and --end-block, or use --latest-blocks.")

    if start_block < 0 or end_block < 0:
        raise ValueError("Block numbers cannot be negative.")

    if end_block < start_block:
        raise ValueError("--end-block must be greater than or equal to --start-block.")

    return start_block, end_block


def backfill_blocks(
    client: Any,
    start_block: int,
    end_block: int,
    min_usd_value: float,
    sleep_seconds: float = 0.0,
) -> int:
    """Scan an inclusive block range and return the number of successful blocks."""
    if min_usd_value < 0:
        raise ValueError("min_usd_value cannot be negative.")

    if sleep_seconds < 0:
        raise ValueError("sleep_seconds cannot be negative.")

    scanned_blocks = 0

    for block_number in range(start_block, end_block + 1):
        try:
            block_data = client.fetch_block_data(block_number)
            client.scan_for_whales(block_data, min_usd_value=min_usd_value)
            scanned_blocks += 1
        except Exception as exc:
            print(f"[WARN] Failed to scan block {block_number}: {exc}")

        if sleep_seconds > 0 and block_number < end_block:
            time.sleep(sleep_seconds)

    return scanned_blocks


def main() -> int:
    """Run the historical whale-block backfill."""
    from src.data.onchain_client import EVMClient

    args = parse_args()

    try:
        client = EVMClient()
    except Exception as exc:
        print(f"[!] ERROR: failed to initialize EVM client: {exc}")
        return 1

    try:
        start_block, end_block = resolve_block_range(
            start_block=args.start_block,
            end_block=args.end_block,
            latest_blocks=args.latest_blocks,
            latest_block=client.w3.eth.block_number,
        )
    except ValueError as exc:
        print(f"[!] ERROR: {exc}")
        client.vault.close()
        return 1

    print("[*] Historical whale-block backfill")
    print(f"[*] Start block: {start_block}")
    print(f"[*] End block: {end_block}")
    print(f"[*] Min USD value: {args.min_usd_value}")
    print(f"[*] Sleep seconds: {args.sleep_seconds}")

    scanned_blocks = backfill_blocks(
        client=client,
        start_block=start_block,
        end_block=end_block,
        min_usd_value=args.min_usd_value,
        sleep_seconds=args.sleep_seconds,
    )

    client.vault.close()

    print(f"[*] Backfill complete. Blocks attempted successfully: {scanned_blocks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())