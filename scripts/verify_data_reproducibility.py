from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "db" / "whale_data.db"

REQUIRED_SAMPLE_FILES = [
    ROOT / "data" / "samples" / "outcome_validation_v2_sample.csv",
    ROOT / "data" / "samples" / "event_time_context_v3_sample.csv",
    ROOT / "data" / "samples" / "context_conditioned_outcomes_v4_sample.csv",
]

EXPECTED_TABLES = [
    "institutional_transfers",
    "historical_prices",
    "enriched_whales",
    "dex_pool_depths",
    "outcome_validation_records",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify local data reproducibility artifacts for the Crypto Research Engine."
    )
    parser.add_argument(
        "--require-db",
        action="store_true",
        help="Fail if data/db/whale_data.db is missing.",
    )
    return parser.parse_args()


def check_samples() -> bool:
    print("=== Sample artifact check ===")
    ok = True

    for path in REQUIRED_SAMPLE_FILES:
        rel = path.relative_to(ROOT)
        if path.exists() and path.stat().st_size > 0:
            print(f"PASS: {rel} ({path.stat().st_size} bytes)")
        else:
            print(f"FAIL: missing or empty sample file: {rel}")
            ok = False

    return ok


def check_database(require_db: bool) -> bool:
    print("\n=== SQLite database check ===")
    print(f"DB path: {DB_PATH.relative_to(ROOT)}")

    if not DB_PATH.exists():
        message = "FAIL" if require_db else "WARN"
        print(f"{message}: local SQLite database is missing.")
        print("INFO: data/db/*.db is intentionally ignored by Git.")
        print("INFO: tests and sample-artifact review can still run without the DB.")
        return not require_db

    print(f"PASS: database exists ({DB_PATH.stat().st_size} bytes)")

    ok = True
    with sqlite3.connect(DB_PATH) as conn:
        existing_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = ? ORDER BY name", ("table",)
            ).fetchall()
        }

        for table in EXPECTED_TABLES:
            if table not in existing_tables:
                print(f"WARN: expected table missing: {table}")
                ok = False
                continue

            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"PASS: {table}: {count} rows")

    return ok


def main() -> int:
    args = parse_args()

    print("============================================================")
    print("DATA REPRODUCIBILITY CHECK")
    print("============================================================")
    print(f"Repo root: {ROOT}")

    samples_ok = check_samples()
    db_ok = check_database(require_db=args.require_db)

    print("\n============================================================")
    if samples_ok and db_ok:
        print("RESULT: PASS")
        return 0

    if samples_ok and not args.require_db:
        print("RESULT: PASS WITH WARNINGS")
        return 0

    print("RESULT: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
