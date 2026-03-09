import pandas as pd

def validate_prices(df: pd.DataFrame) -> None:
    required = {"date", "price", "coin_id"}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns. Need {required}, got {set(df.columns)}")

    if df["price"].isna().any():
        raise ValueError("Found missing prices.")

    if (df["price"] <= 0).any():
        raise ValueError("Found non-positive prices.")

    if df.duplicated(subset=["coin_id", "date"]).any():
        raise ValueError("Found duplicate (coin_id, date) rows.")