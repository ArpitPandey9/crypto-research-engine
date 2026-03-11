from pathlib import Path
import pandas as pd

from src.data.fetch_prices import fetch_daily_prices
from src.data.validate import validate_prices

# Project root discovery (portable across machines)
ROOT = Path(__file__).resolve().parents[2]

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"


def main() -> None:
    """
    Build and persist price datasets for BTC and ETH.

    Outputs
    -------
    1) Raw long CSV:
       date, price, coin_id

    2) Processed long CSV:
       typed datetime, sorted (coin_id, date)

    3) Processed wide CSV:
       index=date, columns=[bitcoin, ethereum], values=price

    Industry rationale
    ------------------
    - Persisting intermediate artifacts improves reproducibility.
    - Keeping both long and wide forms makes downstream research easier.
    """
    # Fetch each asset independently (clean separation)
    btc = fetch_daily_prices("bitcoin", days=365)
    eth = fetch_daily_prices("ethereum", days=365)

    # Combine into a single "long" dataset
    df = pd.concat([btc, eth], ignore_index=True)

    # Validate dataset to prevent silent errors downstream
    validate_prices(df)

    # Ensure output folders exist
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    # Save RAW long dataset (minimal transformations)
    raw_path = RAW / "prices_btc_eth_long_raw.csv"
    df.to_csv(raw_path, index=False)

    # Process long dataset: type conversion + sorting
    df2 = df.copy()
    df2["date"] = pd.to_datetime(df2["date"])
    df2 = df2.sort_values(["coin_id", "date"]).reset_index(drop=True)

    long_path = PROCESSED / "prices_btc_eth_long_processed.csv"
    df2.to_csv(long_path, index=False)

    # Create wide dataset: one column per asset, indexed by date
    wide = df2.pivot(index="date", columns="coin_id", values="price").sort_index()
    wide_path = PROCESSED / "prices_btc_eth_wide_processed.csv"
    wide.to_csv(wide_path)

    print("Saved:", raw_path)
    print("Saved:", long_path)
    print("Saved:", wide_path)
    print("\nWide preview:\n", wide.head())


if __name__ == "__main__":
    main()