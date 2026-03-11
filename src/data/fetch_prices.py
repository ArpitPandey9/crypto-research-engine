import pandas as pd
import requests

BASE = "https://api.coingecko.com/api/v3"


def fetch_daily_prices(coin_id: str, days: int = 365, vs_currency: str = "usd") -> pd.DataFrame:
    """
    Fetch daily price data for a given coin from CoinGecko.

    Important (industry reality):
    -----------------------------
    Even when requesting 'daily' interval, CoinGecko may return multiple timestamps
    that fall on the same calendar date (timezone / bucketing differences).
    When we convert timestamps -> YYYY-MM-DD, that can create duplicate dates.
    We therefore deduplicate to ensure exactly one row per (coin_id, date).

    We keep the LAST observation of the day (common convention for "daily close").
    """
    url = f"{BASE}/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs_currency, "days": days, "interval": "daily"}

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    payload = r.json()

    prices = payload["prices"]  # list of [timestamp_ms, price]
    df = pd.DataFrame(prices, columns=["timestamp_ms", "price"])

    # Convert timestamp -> date (YYYY-MM-DD)
    df["date"] = pd.to_datetime(df["timestamp_ms"], unit="ms").dt.date.astype(str)
    df["coin_id"] = coin_id

    # --- Deduplicate: keep last price per date ---
    # Sort by timestamp so "last" means latest timestamp within that date
    df = df.sort_values("timestamp_ms")
    df = df.drop_duplicates(subset=["coin_id", "date"], keep="last")

    # Return canonical research schema
    return df[["date", "price", "coin_id"]]