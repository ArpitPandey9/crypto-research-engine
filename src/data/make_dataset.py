from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.data.fetch_prices import fetch_btc_prices
from src.data.validate import validate_prices


# ==========
# Paths
# ==========
# PROJECT ROOT = .../crypto-research-engine/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"


# ==========
# Helpers
# ==========
def save_csv(df: pd.DataFrame, path: Path) -> None:
    """Save DataFrame to CSV, creating folders if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def log_duplicates(df: pd.DataFrame, max_rows: int = 10) -> None:
    """
    Print how many duplicate (coin_id, date) rows exist and show examples.

    Duplicate means: same coin_id AND same date appears more than once.
    """
    dup_count = df.duplicated(subset=["coin_id", "date"]).sum()
    print(f"Duplicate (coin_id, date) rows BEFORE dedup: {dup_count}")

    if dup_count > 0:
        # keep=False shows all rows that belong to duplicated groups
        dup_rows = df[df.duplicated(subset=["coin_id", "date"], keep=False)]
        print(f"Showing up to {max_rows} duplicate rows (examples):")
        print(dup_rows.head(max_rows))


def deduplicate_prices(df: pd.DataFrame, keep: str = "last") -> pd.DataFrame:
    """
    Remove duplicates by (coin_id, date).

    keep="last" means:
    - if a date appears multiple times, keep the last row for that date.
    """
    return df.drop_duplicates(subset=["coin_id", "date"], keep=keep)


def make_processed(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create the 'processed' dataset:
    - date as datetime
    - sorted by coin_id then date
    """
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values(["coin_id", "date"]).reset_index(drop=True)
    return out


# ==========
# Main pipeline
# ==========
def main(days: int = 365, show_dupes: bool = True) -> None:
    """
    End-to-end dataset builder (Day 1):
    1) Fetch BTC prices
    2) (Optional) log duplicates
    3) Deduplicate
    4) Validate
    5) Save raw + processed
    6) Print date range + preview
    """
    print("Building BTC dataset...")

    # 1) Fetch (download) data
    df = fetch_btc_prices(days=days)

    # 2) Log duplicates (optional learning/debug)
    if show_dupes:
        log_duplicates(df, max_rows=10)

    # 3) Deduplicate (safe-clean step)
    df = deduplicate_prices(df, keep="last")

    # Optional: show duplicates after dedup to confirm it's fixed
    if show_dupes:
        after = df.duplicated(subset=["coin_id", "date"]).sum()
        print(f"Duplicate (coin_id, date) rows AFTER dedup: {after}")

    # 4) Validate (quality gate)
    validate_prices(df)

    # 5) Save RAW
    raw_path = DATA_RAW / "btc_prices_raw.csv"
    save_csv(df, raw_path)
    print(f"Saved: {raw_path}")

    # 6) Build processed + save
    processed = make_processed(df)
    processed_path = DATA_PROCESSED / "btc_prices_processed.csv"
    save_csv(processed, processed_path)
    print(f"Saved: {processed_path}")

    # 7) Date range check (research sanity check)
    print("\nDate range:")
    print("Start:", processed["date"].min())
    print("End:", processed["date"].max())
    print("Rows:", len(processed))

    # 8) Preview
    print("\nPreview (processed):")
    print(processed.head())
    print("\nDone.")


if __name__ == "__main__":
    main(days=365, show_dupes=True)