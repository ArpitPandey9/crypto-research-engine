import pandas as pd


def validate_prices(df: pd.DataFrame) -> None:
    """
    Validate daily price dataset for research usage.

    Raises
    ------
    ValueError
        If dataset violates any basic quality rules.

    Industry rationale
    ------------------
    Research pipelines must fail fast when inputs are invalid.
    Silent data issues can produce misleading backtests and incorrect conclusions.
    """
    required = {"date", "price", "coin_id"}

    # Schema check: all required columns must exist
    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns. Need {required}, got {set(df.columns)}")

    # Date parse check: ensures dates can be converted into a time index
    parsed = pd.to_datetime(df["date"], errors="coerce")
    if parsed.isna().any():
        raise ValueError("Found unparseable dates in 'date' column.")

    # Price should exist and be strictly positive
    if df["price"].isna().any():
        raise ValueError("Found missing prices.")
    if (df["price"] <= 0).any():
        raise ValueError("Found non-positive prices (<= 0).")

    # No duplicate (coin_id, date) rows: duplicates break time series logic
    if df.duplicated(subset=["coin_id", "date"]).any():
        raise ValueError("Found duplicate (coin_id, date) rows.")