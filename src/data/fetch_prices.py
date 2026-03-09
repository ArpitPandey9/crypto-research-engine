import pandas as pd
import requests

BASE = "https://api.coingecko.com/api/v3"

def fetch_btc_prices(days: int = 365) -> pd.DataFrame:
    url = f"{BASE}/coins/bitcoin/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    payload = r.json()

    prices = payload["prices"]  # list of [timestamp_ms, price]
    df = pd.DataFrame(prices, columns=["timestamp_ms", "price"])

    df["date"] = pd.to_datetime(df["timestamp_ms"], unit="ms").dt.date.astype(str)
    df["coin_id"] = "bitcoin"

    df: pd.DataFrame = df[["date", "price", "coin_id"]].copy()

    # If the same date appears more than once, keep the last one
    df = df.drop_duplicates(subset=["coin_id", "date"], keep="last")

    return df